#!/usr/bin/env python3
"""Extract a file path from IDE hook stdin JSON."""

from __future__ import annotations

import json
import sys


def from_mapping(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    for key in ("file_path", "path", "filePath"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    for container_key in ("tool_input", "toolInput", "tool_response", "toolResponse"):
        container = obj.get(container_key)
        if isinstance(container, dict):
            for key in ("file_path", "path"):
                value = container.get(key)
                if isinstance(value, str) and value:
                    return value
    return ""


def fallback_from_text(raw: str) -> str:
    needle = "ui-acceptance-contract.yaml"
    idx = raw.find(needle)
    if idx < 0:
        return ""
    start = idx
    while start > 0 and raw[start - 1] not in " \t\r\n\"'":
        start -= 1
    return raw[start : idx + len(needle)]


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        data = None
    path = from_mapping(data) if data is not None else ""
    if not path:
        path = fallback_from_text(raw)
    if path:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
