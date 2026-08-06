from __future__ import annotations

from typing import Protocol

from repo.branch_naming import format_branch_name
from repo.hub import (
    BranchProtectionConfig,
    LFSConfig,
    PrDetail,
    RepoUnreachableError,
)
from repo.lfs import DEFAULT_THRESHOLD_MB
from repo.pr_template import ensure_pr_template_valid


class HTTPClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        json: dict | None = None,
        data: bytes | None = None,
    ) -> tuple[int, dict | str]: ...


class RequestsHTTPClient:
    def __init__(self):
        try:
            import httpx  # noqa: F401
        except ImportError:
            pass

    def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        json: dict | None = None,
        data: bytes | None = None,
    ) -> tuple[int, dict | str]:
        import httpx

        try:
            resp = httpx.request(
                method,
                url,
                headers=headers,
                json=json,
                content=data,
                timeout=30,
            )
        except Exception as e:
            raise ConnectionError(str(e)) from e
        status = resp.status_code
        try:
            body: dict | str = resp.json()
        except Exception:
            body = resp.text
        return status, body


class MockHTTPClient:
    def __init__(self, always_raise: Exception | None = None):
        self.requests: list[dict] = []
        self.always_raise = always_raise
        self.next_response: tuple[int, dict | str] = (200, {})

    def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        json: dict | None = None,
        data: bytes | None = None,
    ) -> tuple[int, dict | str]:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "json": json,
                "data": data,
            }
        )
        if self.always_raise is not None:
            raise self.always_raise
        return self.next_response


class GitHubProvider:
    def __init__(
        self,
        owner: str,
        repo: str,
        token: str | None = None,
        client: HTTPClient | None = None,
        api_base: str = "https://api.github.com",
    ):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.client = client or RequestsHTTPClient()
        self.api_base = api_base.rstrip("/")
        self._lfs_enabled = True
        self._lfs_threshold = DEFAULT_THRESHOLD_MB

    def _headers(self) -> dict:
        h = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _api(self, path: str) -> str:
        return f"{self.api_base}/repos/{self.owner}/{self.repo}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        data: bytes | None = None,
    ) -> tuple[int, dict | str]:
        try:
            return self.client.request(
                method,
                self._api(path),
                headers=self._headers(),
                json=json,
                data=data,
            )
        except ConnectionError as e:
            raise RepoUnreachableError(str(e)) from e

    def init_branch_protection(self, main: str, config: BranchProtectionConfig) -> None:
        payload = {
            "required_status_checks": {
                "strict": config.require_status_checks,
                "contexts": [],
            }
            if config.require_status_checks
            else None,
            "required_pull_request_reviews": {
                "required_approving_review_count": config.require_approvals,
            },
            "allow_force_pushes": config.allow_force_push,
        }
        self._request("PUT", f"branches/{main}/protection", json=payload)

    def create_feat_branch(
        self, pipeline_id: str, instance_id: str, node_type: str, seq: int
    ) -> str:
        branch_name = format_branch_name(pipeline_id, instance_id, node_type, seq)
        _, data = self._request("GET", "git/ref/heads/main")
        sha = ""
        if isinstance(data, dict):
            obj = data.get("object", {})
            sha = obj.get("sha", "")
        self._request(
            "POST",
            "git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )
        return branch_name

    def commit_push_file(
        self,
        branch: str,
        path: str,
        content_bytes: bytes,
        commit_msg: str,
        lfs_cfg: LFSConfig | None = None,
    ) -> str:
        import base64

        encoded = base64.b64encode(content_bytes).decode("ascii")
        _, data = self._request("GET", f"contents/{path}?ref={branch}")
        sha = ""
        if isinstance(data, dict):
            sha = data.get("sha", "")
        payload = {
            "message": commit_msg,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        _, resp = self._request("PUT", f"contents/{path}", json=payload)
        commit_sha = ""
        if isinstance(resp, dict):
            c = resp.get("commit", {})
            commit_sha = c.get("sha", "")
        return commit_sha

    def open_pr(
        self, from_branch: str, to_branch: str, title: str, pr_template_yaml: dict
    ) -> str:
        ensure_pr_template_valid(pr_template_yaml)
        import json as _json

        body = (
            "## PR Template\n```yaml\n"
            + _json.dumps(pr_template_yaml, indent=2, default=str)
            + "\n```"
        )
        _, data = self._request(
            "POST",
            "pulls",
            json={
                "title": title,
                "head": from_branch,
                "base": to_branch,
                "body": body,
            },
        )
        pr_id = ""
        if isinstance(data, dict):
            pr_id = str(data.get("number", ""))
        return pr_id

    def approve_and_squash_merge(self, pr_id: str, bot_actor: str) -> str:
        self._request(
            "POST",
            f"pulls/{pr_id}/reviews",
            json={"event": "APPROVE", "body": f"Approved by {bot_actor}"},
        )
        _, data = self._request(
            "PUT",
            f"pulls/{pr_id}/merge",
            json={"merge_method": "squash"},
        )
        sha = ""
        if isinstance(data, dict):
            sha = data.get("sha", "")
        return sha

    def reject_pr(self, pr_id: str, reason: str) -> None:
        self._request(
            "POST",
            f"pulls/{pr_id}/reviews",
            json={"event": "REQUEST_CHANGES", "body": reason},
        )
        self._request("PATCH", f"pulls/{pr_id}", json={"state": "closed"})

    def get_pr_detail(self, pr_id: str) -> PrDetail:
        _, data = self._request("GET", f"pulls/{pr_id}")
        title = ""
        from_branch = ""
        to_branch = ""
        state = "open"
        if isinstance(data, dict):
            title = data.get("title", "")
            h = data.get("head", {})
            b = data.get("base", {})
            from_branch = h.get("ref", "")
            to_branch = b.get("ref", "")
            raw_state = (data.get("state") or "open").lower()
            merged = data.get("merged", False)
            if merged:
                state = "merged"
            elif raw_state == "closed":
                state = "closed"
            else:
                state = raw_state if raw_state in {"open", "rejected"} else "open"
        return PrDetail(
            pr_id=str(pr_id),
            from_branch=from_branch,
            to_branch=to_branch,
            title=title,
            template={},
            files=[],
            diff_unified="",
            commits=[],
            state=state,
        )

    def git_show(self, path: str, ref: str) -> bytes:
        import base64

        _, data = self._request("GET", f"contents/{path}?ref={ref}")
        content = ""
        encoding = ""
        if isinstance(data, dict):
            content = data.get("content", "")
            encoding = data.get("encoding", "")
        if encoding == "base64":
            return base64.b64decode(content)
        return content.encode("utf-8")

    def list_files(self, path_filter: str = "**/*", ref: str = "HEAD") -> list[str]:
        import fnmatch

        _, data = self._request(
            "GET",
            f"git/trees/{ref}?recursive=1",
        )
        tree = []
        if isinstance(data, dict):
            tree = data.get("tree", []) or []
        files = [item.get("path", "") for item in tree if item.get("type") == "blob"]
        files = [f for f in files if f]
        if path_filter == "**/*":
            return files
        return [f for f in files if fnmatch.fnmatch(f, path_filter)]

    def is_lfs_enabled(self) -> bool:
        return self._lfs_enabled

    def ensure_lfs(self, threshold_mb: int = 10) -> None:
        self._lfs_enabled = True
        self._lfs_threshold = threshold_mb
        self._request("PUT", "lfs", json={"enabled": True})

    def is_main_protected_direct_push(self) -> bool:
        try:
            status, _ = self._request("GET", "branches/main/protection")
            return 200 <= status < 300
        except RepoUnreachableError:
            return False
