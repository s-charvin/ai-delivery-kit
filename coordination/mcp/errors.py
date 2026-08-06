from __future__ import annotations

import jwt

from config.constants import ERROR_CODES
from repo.hub import (
    LFSPushFailedError,
    MergeConflictError,
    PRTemplateInvalidError,
    ProtectedBranchError,
    RepoUnreachableError,
)


_E_INTERNAL_UNEXPECTED_DEF = {
    "code": 9999,
    "zh": "内部未预期错误",
    "en": "Internal unexpected error",
}


def _get_error_def(code: str) -> dict:
    if code in ERROR_CODES:
        return ERROR_CODES[code]
    if code == "E_INTERNAL_UNEXPECTED":
        return _E_INTERNAL_UNEXPECTED_DEF
    return _E_INTERNAL_UNEXPECTED_DEF


def tool_error(exc: Exception, trace_id: str, lang: str = "zh") -> dict:
    error_code: str | None = None
    extra_data: dict = {}

    if isinstance(exc, (KeyError, RepoUnreachableError)):
        error_code = "E_REPO_UNREACHABLE"
    elif isinstance(exc, ProtectedBranchError):
        error_code = "E_PROTECTED_BRANCH"
    elif isinstance(exc, PRTemplateInvalidError):
        error_code = "E_PR_TEMPLATE_MISSING_FIELD"
        extra_data["missing"] = getattr(exc, "missing_fields", [])
    elif isinstance(exc, PermissionError):
        error_code = "E_PERMISSION_DENIED"
    elif isinstance(exc, jwt.ExpiredSignatureError):
        error_code = "E_TOKEN_EXPIRED"
    elif isinstance(exc, jwt.InvalidTokenError):
        error_code = "E_TOKEN_SCOPE_MISMATCH"
    elif isinstance(exc, LFSPushFailedError):
        error_code = "E_LFS_PUSH_FAILED"
    elif isinstance(exc, MergeConflictError):
        error_code = "E_MERGE_CONFLICT"
    else:
        code_attr = getattr(exc, "error_code", None)
        msg = str(exc)
        if code_attr is not None and isinstance(code_attr, str) and code_attr.startswith("E_"):
            error_code = code_attr
        elif getattr(exc, "code", None) is not None and isinstance(exc.code, str) and exc.code.startswith("E_"):
            error_code = exc.code
        else:
            import re
            m = re.match(r"^(E_[A-Z0-9_]+)\s*[:：]", msg)
            if m:
                error_code = m.group(1)
            elif "E_PERMISSION_DENIED" in msg:
                error_code = "E_PERMISSION_DENIED"
            elif "E_TOKEN_EXPIRED" in msg:
                error_code = "E_TOKEN_EXPIRED"
            elif "E_TOKEN_SCOPE_MISMATCH" in msg:
                error_code = "E_TOKEN_SCOPE_MISMATCH"
            elif "E_NOT_OPTIONAL" in msg:
                error_code = "E_NOT_OPTIONAL"
            elif "E_NODE_NOT_DONE" in msg:
                error_code = "E_NODE_NOT_DONE"
            elif "E_ADDENDUM_AUTH" in msg:
                error_code = "E_ADDENDUM_AUTH"
            elif "E_INCOMPATIBLE_NOT_DOWNSTREAM" in msg:
                error_code = "E_INCOMPATIBLE_NOT_DOWNSTREAM"

    if error_code is None:
        error_code = "E_INTERNAL_UNEXPECTED"

    err_def = _get_error_def(error_code)
    base_msg = err_def.get(lang, err_def.get("en", str(exc)))
    message = base_msg
    if error_code != "E_INTERNAL_UNEXPECTED" and str(exc) and base_msg not in str(exc):
        message = f"{base_msg} | {str(exc)}"
    if error_code == "E_INTERNAL_UNEXPECTED":
        message = f"{base_msg}: {str(exc)}"

    result = {
        "ok": False,
        "data": extra_data if extra_data else None,
        "error_code": error_code,
        "error_message": message,
        "trace_id": trace_id,
    }
    return result
