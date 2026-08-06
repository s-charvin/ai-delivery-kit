from __future__ import annotations

from datetime import datetime, timezone

import jwt

from orchestration.models import TokenType

_ALG = "HS256"

UTC = timezone.utc


def create_session_token(
    secret: str,
    node_id: str,
    allowed_tools: list[str],
    expires_at_iso: str,
    token_type: TokenType = TokenType.BOT,
) -> str:
    payload = {
        "node_id": node_id,
        "allowed_tools": allowed_tools,
        "exp": datetime.fromisoformat(expires_at_iso).replace(tzinfo=UTC)
        if datetime.fromisoformat(expires_at_iso).tzinfo is None
        else datetime.fromisoformat(expires_at_iso),
        "token_type": token_type.value,
    }
    return jwt.encode(payload, secret, algorithm=_ALG)


def verify_session_token(secret: str, token: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("E_TOKEN_EXPIRED: Token has expired")
    except jwt.PyJWTError:
        raise ValueError("E_TOKEN_SCOPE_MISMATCH: Token validation failed")


def check_token_scope(payload: dict, tool_name: str) -> bool:
    allowed = payload.get("allowed_tools", [])
    return "*" in allowed or tool_name in allowed
