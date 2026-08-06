from __future__ import annotations

from typing import Any

from utils.hashing import audit_entry_hash, hash_chain_validate


def validate_chain(entries: list[Any]) -> tuple[bool, int | None]:
    return hash_chain_validate(entries)


def repair_chain(entries: list[Any]) -> list[Any]:
    if not entries:
        return entries

    valid, first_bad_index = validate_chain(entries)
    if valid or first_bad_index is None:
        return entries

    start_idx = first_bad_index
    for i in range(start_idx, len(entries)):
        prev_hash = "" if i == 0 else entries[i - 1].hash
        entries[i].prev_hash = prev_hash
        new_hash = audit_entry_hash(
            entries[i].prev_hash,
            entries[i].action,
            entries[i].actor,
            entries[i].payload,
        )
        entries[i].hash = new_hash

    return entries
