from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel


class BranchProtectionConfig(BaseModel):
    protected_branches: list[str]
    require_approvals: int = 1
    require_status_checks: bool = True
    allow_force_push: bool = False
    bot_actor: str = "coordination-bot"


class PrDetail(BaseModel):
    pr_id: str
    from_branch: str
    to_branch: str
    title: str
    template: dict
    files: list[str]
    diff_unified: str
    commits: list[str]
    state: Literal["open", "merged", "rejected", "closed"] = "open"


class LFSConfig(BaseModel):
    enabled: bool = True
    threshold_mb: int = 10


class RepoInitConfig(BaseModel):
    url: str
    provider: Literal["local", "github", "gitlab", "gitea"] = "local"
    credential_ref: str | None = None
    webhook_secret_ref: str | None = None
    clone_strategy: Literal["https", "ssh"] = "https"
    branch_naming_regex: str = (
        r"^feat/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+-[0-9]{3,}$"
    )


class HubRepoError(Exception):
    code: str

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class ProtectedBranchError(HubRepoError):
    def __init__(self, message: str = "Direct push to protected branch is not allowed"):
        super().__init__(message, "E_PROTECTED_BRANCH")


class RepoUnreachableError(HubRepoError):
    def __init__(self, message: str = "Repository is unreachable"):
        super().__init__(message, "E_REPO_UNREACHABLE")


class LFSPushFailedError(HubRepoError):
    def __init__(self, message: str = "LFS push failed"):
        super().__init__(message, "E_LFS_PUSH_FAILED")


class PRTemplateInvalidError(HubRepoError):
    missing_fields: list[str]

    def __init__(self, missing_fields: list[str], message: str | None = None):
        self.missing_fields = missing_fields
        if message is None:
            message = f"PR template missing required fields: {missing_fields}"
        super().__init__(message, "E_PR_TEMPLATE_MISSING_FIELD")


class MergeConflictError(HubRepoError):
    def __init__(self, message: str = "Merge conflict detected"):
        super().__init__(message, "E_MERGE_CONFLICT")


@runtime_checkable
class HubRepo(Protocol):
    def init_branch_protection(self, main: str, config: BranchProtectionConfig) -> None: ...

    def create_feat_branch(
        self, pipeline_id: str, instance_id: str, node_type: str, seq: int
    ) -> str: ...

    def commit_push_file(
        self,
        branch: str,
        path: str,
        content_bytes: bytes,
        commit_msg: str,
        lfs_cfg: LFSConfig | None = None,
    ) -> str: ...

    def open_pr(
        self, from_branch: str, to_branch: str, title: str, pr_template_yaml: dict
    ) -> str: ...

    def approve_and_squash_merge(self, pr_id: str, bot_actor: str) -> str: ...

    def reject_pr(self, pr_id: str, reason: str) -> None: ...

    def get_pr_detail(self, pr_id: str) -> PrDetail: ...

    def git_show(self, path: str, ref: str) -> bytes: ...

    def list_files(self, path_filter: str = "**/*", ref: str = "HEAD") -> list[str]: ...

    def is_lfs_enabled(self) -> bool: ...

    def ensure_lfs(self, threshold_mb: int = 10) -> None: ...

    def is_main_protected_direct_push(self) -> bool: ...
