from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from repo.branch_naming import format_branch_name
from repo.hub import (
    BranchProtectionConfig,
    LFSPushFailedError,
    LFSConfig,
    MergeConflictError,
    ProtectedBranchError,
    PrDetail,
    RepoUnreachableError,
)
from repo.lfs import (
    DEFAULT_THRESHOLD_MB,
    ensure_gitattributes,
    generate_lfs_pointer,
    should_use_lfs,
)
from repo.pr_template import ensure_pr_template_valid


def _run_git(
    workdir: Path,
    *args: str,
    check: bool = True,
    env: dict | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    cmd = ["git", "-C", str(workdir), *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            env=merged_env,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "protected" in stderr.lower() or "not allowed" in stderr.lower():
            raise ProtectedBranchError(stderr) from e
        if "conflict" in stderr.lower():
            raise MergeConflictError(stderr) from e
        raise RepoUnreachableError(f"git command failed: {e.stderr}") from e


class LocalHubRepo:
    repo_root: Path
    hub_path: Path
    work_path: Path
    _bot_actor: str = "coordination-bot"
    _lfs_threshold_mb: int = DEFAULT_THRESHOLD_MB
    _lfs_enabled: bool = True

    def __init__(self, repo_root: Path, init_bare_if_missing: bool = True):
        self.repo_root = Path(repo_root).resolve()
        self.hub_path = self.repo_root / "hub.git"
        self.work_path = self.repo_root / "work"

        if init_bare_if_missing and not self.hub_path.exists():
            self._bootstrap()

    def _bootstrap(self) -> None:
        self.repo_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(self.hub_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.work_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", str(self.work_path), "init", "-b", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(self.work_path), "remote", "add", "hub", str(self.hub_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        _run_git(self.work_path, "config", "user.name", self._bot_actor)
        _run_git(self.work_path, "config", "user.email", f"{self._bot_actor}@local")
        bp_cfg = BranchProtectionConfig(protected_branches=["main"])
        protection_data: dict = {}
        for branch in bp_cfg.protected_branches:
            protection_data[branch] = {
                "direct_push": False,
                "only_bot": bp_cfg.bot_actor,
                "require_approvals": bp_cfg.require_approvals,
                "require_status_checks": bp_cfg.require_status_checks,
                "allow_force_push": bp_cfg.allow_force_push,
            }
        (self.work_path / ".protected.json").write_text(json.dumps(protection_data, indent=2))
        _run_git(self.work_path, "add", ".protected.json")
        _run_git(
            self.work_path,
            "commit",
            "-m",
            "init: bootstrap main branch with protection rules",
            env={
                "GIT_COMMITTER_NAME": self._bot_actor,
                "GIT_COMMITTER_EMAIL": f"{self._bot_actor}@local",
                "GIT_AUTHOR_NAME": self._bot_actor,
                "GIT_AUTHOR_EMAIL": f"{self._bot_actor}@local",
            },
        )
        _run_git(
            self.work_path,
            "push",
            "-u",
            "hub",
            "main",
            env={
                "GIT_COMMITTER_NAME": self._bot_actor,
                "GIT_COMMITTER_EMAIL": f"{self._bot_actor}@local",
            },
        )

    def _protected_json_path(self) -> Path:
        return self.work_path / ".protected.json"

    def init_branch_protection(self, main: str, config: BranchProtectionConfig) -> None:
        self._bot_actor = config.bot_actor
        data: dict = {}
        path = self._protected_json_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                data = {}
        for branch in config.protected_branches:
            data[branch] = {
                "direct_push": False,
                "only_bot": config.bot_actor,
                "require_approvals": config.require_approvals,
                "require_status_checks": config.require_status_checks,
                "allow_force_push": config.allow_force_push,
            }
        path.write_text(json.dumps(data, indent=2))
        self._commit_and_push(
            "main",
            ".protected.json",
            path.read_bytes(),
            "chore: update branch protection rules",
            as_bot=True,
        )

    def _read_protection(self) -> dict:
        path = self._protected_json_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}

    def _check_direct_push_allowed(self, branch: str, committer_name: str) -> None:
        protection = self._read_protection()
        rule = protection.get(branch)
        if not rule:
            return
        if rule.get("direct_push") is False:
            only_bot = rule.get("only_bot")
            if only_bot and committer_name != only_bot:
                raise ProtectedBranchError(
                    f"Direct push to '{branch}' not allowed for '{committer_name}' (only '{only_bot}')"
                )

    def is_main_protected_direct_push(self) -> bool:
        try:
            self._run_git_with_protection_check(
                "main",
                "status",
                committer_name="malicious-user",
            )
        except ProtectedBranchError:
            return True
        try:
            test_file = self.work_path / f"._test_protect_{uuid.uuid4().hex}.txt"
            test_file.write_text("test")
            _run_git(self.work_path, "add", str(test_file.name))
            try:
                _run_git(
                    self.work_path,
                    "commit",
                    "-m",
                    "test: protection check",
                    env={
                        "GIT_COMMITTER_NAME": "malicious-user",
                        "GIT_COMMITTER_EMAIL": "bad@local",
                        "GIT_AUTHOR_NAME": "malicious-user",
                        "GIT_AUTHOR_EMAIL": "bad@local",
                    },
                    check=False,
                )
                _run_git(
                    self.work_path,
                    "push",
                    "hub",
                    "main",
                    env={
                        "GIT_COMMITTER_NAME": "malicious-user",
                        "GIT_COMMITTER_EMAIL": "bad@local",
                    },
                    check=False,
                )
            finally:
                _run_git(self.work_path, "reset", "HEAD~1", "--soft", check=False)
                _run_git(self.work_path, "checkout", "--", ".", check=False)
                if test_file.exists():
                    test_file.unlink()
        except ProtectedBranchError:
            return True
        return True

    def _run_git_with_protection_check(
        self, branch: str, *args: str, committer_name: str | None = None
    ) -> subprocess.CompletedProcess:
        committer = committer_name or self._bot_actor
        self._check_direct_push_allowed(branch, committer)
        return _run_git(
            self.work_path,
            *args,
            env={
                "GIT_COMMITTER_NAME": committer,
                "GIT_COMMITTER_EMAIL": f"{committer}@local",
                "GIT_AUTHOR_NAME": committer,
                "GIT_AUTHOR_EMAIL": f"{committer}@local",
            },
        )

    def create_feat_branch(
        self, pipeline_id: str, instance_id: str, node_type: str, seq: int
    ) -> str:
        branch_name = format_branch_name(pipeline_id, instance_id, node_type, seq)
        _run_git(self.work_path, "fetch", "hub")
        _run_git(self.work_path, "checkout", "-B", branch_name, "hub/main")
        return branch_name

    def _commit_and_push(
        self,
        branch: str,
        path: str,
        content_bytes: bytes,
        commit_msg: str,
        as_bot: bool = False,
    ) -> str:
        _run_git(self.work_path, "checkout", branch)
        target = self.work_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content_bytes)
        _run_git(self.work_path, "add", path)
        actor = self._bot_actor if as_bot else "local-user"
        _run_git(
            self.work_path,
            "diff",
            "--cached",
            "--quiet",
            check=False,
        )
        result = _run_git(
            self.work_path,
            "diff",
            "--cached",
            "--name-only",
            check=False,
        )
        if not result.stdout.strip():
            _run_git(self.work_path, "reset", path)
            result = _run_git(self.work_path, "rev-parse", "HEAD")
            return result.stdout.strip()
        try:
            _run_git(
                self.work_path,
                "commit",
                "-m",
                commit_msg,
                env={
                    "GIT_COMMITTER_NAME": actor,
                    "GIT_COMMITTER_EMAIL": f"{actor}@local",
                    "GIT_AUTHOR_NAME": actor,
                    "GIT_AUTHOR_EMAIL": f"{actor}@local",
                },
            )
        except ProtectedBranchError:
            raise
        self._check_direct_push_allowed(branch, actor)
        try:
            _run_git(
                self.work_path,
                "push",
                "hub",
                branch,
                env={
                    "GIT_COMMITTER_NAME": actor,
                    "GIT_COMMITTER_EMAIL": f"{actor}@local",
                },
            )
        except subprocess.CalledProcessError as e:
            raise RepoUnreachableError(f"push failed: {e.stderr}") from e
        result = _run_git(self.work_path, "rev-parse", "HEAD")
        return result.stdout.strip()

    def commit_push_file(
        self,
        branch: str,
        path: str,
        content_bytes: bytes,
        commit_msg: str,
        lfs_cfg: LFSConfig | None = None,
    ) -> str:
        _run_git(self.work_path, "fetch", "hub", check=False)
        result = _run_git(
            self.work_path,
            "rev-parse",
            "--verify",
            f"hub/{branch}",
            check=False,
        )
        if result.returncode == 0:
            _run_git(self.work_path, "checkout", "-B", branch, f"hub/{branch}")
        else:
            _run_git(self.work_path, "checkout", "-B", branch, "hub/main")

        threshold = (lfs_cfg.threshold_mb if lfs_cfg and lfs_cfg.enabled else None) or (
            self._lfs_threshold_mb if self._lfs_enabled else 1024 * 1024
        )
        use_lfs = self._lfs_enabled and should_use_lfs(len(content_bytes), threshold)
        stored_bytes: bytes = content_bytes
        if use_lfs:
            try:
                ensure_gitattributes(self.work_path, path)
                self._commit_and_push(
                    branch,
                    ".gitattributes",
                    (self.work_path / ".gitattributes").read_bytes(),
                    "chore: update .gitattributes for LFS",
                    as_bot=False,
                )
                _run_git(self.work_path, "checkout", branch)
                stored_bytes = generate_lfs_pointer(content_bytes).encode("utf-8")
                lfs_store = self.work_path / ".lfs_store"
                lfs_store.mkdir(exist_ok=True)
                import hashlib

                sha = hashlib.sha256(content_bytes).hexdigest()
                (lfs_store / sha).write_bytes(content_bytes)
            except Exception as e:
                raise LFSPushFailedError(f"LFS setup failed: {e}") from e
        return self._commit_and_push(branch, path, stored_bytes, commit_msg, as_bot=False)

    def _prs_dir(self) -> Path:
        return self.work_path / ".prs"

    def open_pr(
        self, from_branch: str, to_branch: str, title: str, pr_template_yaml: dict
    ) -> str:
        ensure_pr_template_valid(pr_template_yaml)
        self._prs_dir().mkdir(parents=True, exist_ok=True)
        pr_id = f"pr-{uuid.uuid4().hex[:8]}"
        _run_git(self.work_path, "fetch", "hub")
        result = _run_git(
            self.work_path,
            "diff",
            "--name-only",
            f"hub/{to_branch}...hub/{from_branch}",
            check=False,
        )
        files = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        diff_result = _run_git(
            self.work_path,
            "diff",
            f"hub/{to_branch}...hub/{from_branch}",
            check=False,
        )
        diff_unified = diff_result.stdout
        commits_result = _run_git(
            self.work_path,
            "log",
            "--format=%H",
            f"hub/{to_branch}..hub/{from_branch}",
            check=False,
        )
        commits = [l.strip() for l in commits_result.stdout.splitlines() if l.strip()]
        pr = PrDetail(
            pr_id=pr_id,
            from_branch=from_branch,
            to_branch=to_branch,
            title=title,
            template=pr_template_yaml,
            files=files,
            diff_unified=diff_unified,
            commits=commits,
            state="open",
        )
        pr_file = self._prs_dir() / f"{pr_id}.json"
        pr_file.write_text(pr.model_dump_json(indent=2))
        self._commit_and_push(
            from_branch,
            f".prs/{pr_id}.json",
            pr_file.read_bytes(),
            f"chore: create {pr_id}",
            as_bot=False,
        )
        return pr_id

    def approve_and_squash_merge(self, pr_id: str, bot_actor: str) -> str:
        pr = self.get_pr_detail(pr_id)
        _run_git(self.work_path, "fetch", "hub")
        _run_git(self.work_path, "checkout", "hub/main", "-B", "__squash_tmp")
        merge_result = _run_git(
            self.work_path,
            "merge",
            "--squash",
            f"hub/{pr.from_branch}",
            check=False,
        )
        if merge_result.returncode != 0:
            stderr = merge_result.stderr or ""
            _run_git(self.work_path, "merge", "--abort", check=False)
            _run_git(self.work_path, "checkout", "main", check=False)
            _run_git(self.work_path, "branch", "-D", "__squash_tmp", check=False)
            if "conflict" in stderr.lower():
                raise MergeConflictError(stderr)
            raise RepoUnreachableError(f"squash merge failed: {stderr}")
        pr.state = "merged"
        self._prs_dir().mkdir(parents=True, exist_ok=True)
        pr_file = self._prs_dir() / f"{pr_id}.json"
        pr_file.write_text(pr.model_dump_json(indent=2))
        _run_git(self.work_path, "add", "-A", check=False)
        commit_result = _run_git(
            self.work_path,
            "commit",
            "-m",
            f"merge(pr): {pr.title} ({pr_id})",
            env={
                "GIT_COMMITTER_NAME": bot_actor,
                "GIT_COMMITTER_EMAIL": f"{bot_actor}@local",
                "GIT_AUTHOR_NAME": bot_actor,
                "GIT_AUTHOR_EMAIL": f"{bot_actor}@local",
            },
            check=False,
        )
        if commit_result.returncode != 0:
            _run_git(self.work_path, "checkout", "main", check=False)
            _run_git(self.work_path, "branch", "-D", "__squash_tmp", check=False)
            raise RepoUnreachableError(f"squash commit failed: {commit_result.stderr}")
        self._check_direct_push_allowed("main", bot_actor)
        _run_git(self.work_path, "branch", "-M", "__squash_tmp", "main")
        try:
            _run_git(
                self.work_path,
                "push",
                "hub",
                "main",
                "--force-with-lease",
                env={
                    "GIT_COMMITTER_NAME": bot_actor,
                    "GIT_COMMITTER_EMAIL": f"{bot_actor}@local",
                },
            )
        except subprocess.CalledProcessError as e:
            raise RepoUnreachableError(f"push main failed: {e.stderr}") from e
        rev = _run_git(self.work_path, "rev-parse", "main")
        return rev.stdout.strip()

    def reject_pr(self, pr_id: str, reason: str) -> None:
        pr = self.get_pr_detail(pr_id)
        pr.state = "rejected"
        pr.template["reject_reason"] = reason
        (self._prs_dir() / f"{pr_id}.json").write_text(pr.model_dump_json(indent=2))
        self._commit_and_push(
            pr.from_branch,
            f".prs/{pr_id}.json",
            (self._prs_dir() / f"{pr_id}.json").read_bytes(),
            f"chore: reject {pr_id}",
            as_bot=True,
        )

    def get_pr_detail(self, pr_id: str) -> PrDetail:
        pr_file = self._prs_dir() / f"{pr_id}.json"
        if not pr_file.exists():
            _run_git(self.work_path, "fetch", "hub", check=False)
            for b in ["main", "master"]:
                r = _run_git(
                    self.work_path,
                    "show",
                    f"hub/{b}:.prs/{pr_id}.json",
                    check=False,
                )
                if r.returncode == 0 and r.stdout.strip():
                    pr_file.parent.mkdir(parents=True, exist_ok=True)
                    pr_file.write_text(r.stdout)
                    break
        if not pr_file.exists():
            raise RepoUnreachableError(f"PR {pr_id} not found")
        try:
            data = json.loads(pr_file.read_text())
            return PrDetail(**data)
        except Exception as e:
            raise RepoUnreachableError(f"PR {pr_id} invalid: {e}") from e

    def git_show(self, path: str, ref: str) -> bytes:
        target_ref = ref
        if "/" not in ref and ref != "HEAD":
            r = _run_git(
                self.work_path,
                "rev-parse",
                "--verify",
                f"hub/{ref}",
                check=False,
            )
            if r.returncode == 0:
                target_ref = f"hub/{ref}"
        try:
            result = _run_git(self.work_path, "cat-file", "-p", f"{target_ref}:{path}")
            return result.stdout.encode("utf-8")
        except Exception as e:
            raise RepoUnreachableError(f"git-show failed: {e}") from e

    def list_files(self, path_filter: str = "**/*", ref: str = "HEAD") -> list[str]:
        target_ref = ref
        if ref != "HEAD" and "/" not in ref:
            r = _run_git(
                self.work_path,
                "rev-parse",
                "--verify",
                f"hub/{ref}",
                check=False,
            )
            if r.returncode == 0:
                target_ref = f"hub/{ref}"
        try:
            result = _run_git(self.work_path, "ls-tree", "-r", "--name-only", target_ref)
            files = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        except Exception:
            return []
        if path_filter == "**/*":
            return files
        import fnmatch

        return [f for f in files if fnmatch.fnmatch(f, path_filter)]

    def is_lfs_enabled(self) -> bool:
        return self._lfs_enabled

    def ensure_lfs(self, threshold_mb: int = 10) -> None:
        self._lfs_enabled = True
        self._lfs_threshold_mb = threshold_mb
