from __future__ import annotations

import hashlib
import json
from typing import Any


def content_integrity_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def audit_entry_hash(prev_hash: str, action: str, actor: str, payload: dict) -> str:
    key = f"{prev_hash}|{action}|{actor}|{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
    return "sha256:" + hashlib.sha256(key.encode()).hexdigest()


def hash_chain_validate(entries: list[Any]) -> tuple[bool, int | None]:
    for i, entry in enumerate(entries):
        prev_hash = "" if i == 0 else entries[i - 1].hash

        if entry.prev_hash != prev_hash:
            return (False, i)

        expected_hash = audit_entry_hash(
            entry.prev_hash, entry.action, entry.actor, entry.payload
        )
        if entry.hash != expected_hash:
            return (False, i)

    return (True, None)
