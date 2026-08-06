from __future__ import annotations

import os
from typing import Any

import jwt
from pydantic import BaseModel, ConfigDict

from orchestration.models import ClassificationLevel
from utils.tokens import check_token_scope, verify_session_token
from mcp.tracing import _trace_id_var, write_alr14_span

_DEV_JWT_SECRET_ENV = "COORDINATION_JWT_SECRET"
_DEFAULT_DEV_SECRET = "dev-secret-mvp"


def get_jwt_secret() -> str:
    return os.getenv(_DEV_JWT_SECRET_ENV, _DEFAULT_DEV_SECRET)


class ToolContext(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    pipeline_id: str | None = None
    node_id: str | None = None
    role_instance_id: str | None = None
    token_payload: dict | None = None
    clearance: ClassificationLevel = ClassificationLevel.INTERNAL
    trace_id: str = ""


def _resolve_token_payload(ctx: ToolContext, token: str | None) -> dict | None:
    if ctx.token_payload is not None:
        return ctx.token_payload
    if token:
        secret = get_jwt_secret()
        try:
            payload = verify_session_token(secret, token)
            return payload
        except Exception:
            return None
    return None


def _get_node_type_from_def(pipeline_def, node_id: str | None) -> str | None:
    if node_id is None or pipeline_def is None:
        return None
    try:
        for n in pipeline_def.nodes:
            if n.node_id == node_id:
                return n.node_type
    except Exception:
        pass
    return None


_BOT_ONLY_TOOLS = {
    "submit_artifact",
    "approve_pr",
    "reject_pr",
    "soft_submit_artifact",
    "review_artifact_pr",
}


def authorize(
    ctx: ToolContext,
    tool_name: str,
    node_type_required: str | None = None,
    instance_id_required: str | None = None,
    artifact_classification: int | None = None,
    pipeline_def: Any | None = None,
) -> None:
    token_payload = ctx.token_payload
    trace_id = ctx.trace_id or _trace_id_var.get("")

    if token_payload is None:
        write_alr14_span(trace_id, tool_name, token_payload, "no_token_payload")
        raise PermissionError("E_PERMISSION_DENIED: Missing token payload")

    allowed_tools = token_payload.get("allowed_tools", [])
    if "*" not in allowed_tools and tool_name not in allowed_tools:
        write_alr14_span(trace_id, tool_name, token_payload, f"scope_missing:{tool_name}")
        raise PermissionError("E_PERMISSION_DENIED: Token scope mismatch for tool")

    if node_type_required is not None:
        node_id = ctx.node_id or token_payload.get("node_id")
        actual_node_type = _get_node_type_from_def(pipeline_def, node_id)
        if actual_node_type is None and node_id is not None:
            pass
        if actual_node_type is not None and actual_node_type != node_type_required:
            write_alr14_span(
                trace_id, tool_name, token_payload,
                f"node_type_mismatch actual={actual_node_type} required={node_type_required}"
            )
            raise PermissionError("E_PERMISSION_DENIED: Node type mismatch")

    if instance_id_required is not None:
        if ctx.role_instance_id != instance_id_required:
            write_alr14_span(
                trace_id, tool_name, token_payload,
                f"instance_id_mismatch ctx={ctx.role_instance_id} required={instance_id_required}"
            )
            raise PermissionError("E_PERMISSION_DENIED: Role instance id mismatch")

    if tool_name in _BOT_ONLY_TOOLS:
        token_type = token_payload.get("token_type")
        if token_type not in ("bot", "admin"):
            write_alr14_span(trace_id, tool_name, token_payload, f"bot_only token_type={token_type}")
            raise PermissionError("E_PERMISSION_DENIED: This action is bot/admin only")

    if artifact_classification is not None:
        if artifact_classification > int(ctx.clearance):
            write_alr14_span(
                trace_id, tool_name, token_payload,
                f"clearance_mismatch artifact={artifact_classification} ctx={int(ctx.clearance)}"
            )
            raise PermissionError("E_PERMISSION_DENIED: Clearance level mismatch")


def check_token_and_get_payload(token: str | None) -> tuple[dict | None, str | None]:
    if not token:
        return None, None
    secret = get_jwt_secret()
    try:
        payload = verify_session_token(secret, token)
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "E_TOKEN_EXPIRED"
    except jwt.InvalidTokenError:
        return None, "E_TOKEN_SCOPE_MISMATCH"
    except Exception as exc:
        msg = str(exc)
        if "E_TOKEN_EXPIRED" in msg:
            return None, "E_TOKEN_EXPIRED"
        if "E_TOKEN_SCOPE_MISMATCH" in msg:
            return None, "E_TOKEN_SCOPE_MISMATCH"
        return None, "E_TOKEN_SCOPE_MISMATCH"
