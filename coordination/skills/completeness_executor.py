from __future__ import annotations

from typing import Any

from jsonpath_ng import parse as _jp_parse

from skills.models import CompletenessContract


def _path_matches(contract_path: str, content_obj: Any) -> bool:
    try:
        expr = _jp_parse(contract_path)
        results = expr.find(content_obj)
    except Exception:
        return False
    if not results:
        return False
    for m in results:
        val = m.value
        if val is None:
            return False
        if isinstance(val, (list, dict)) and len(val) == 0:
            return False
    return True


def evaluate(contract: CompletenessContract, content_obj: dict | list) -> tuple[bool, list[str]]:
    if not contract.json_paths:
        return True, []

    results: list[tuple[str, bool]] = []
    for jp in contract.json_paths:
        ok = _path_matches(jp, content_obj)
        results.append((jp, ok))

    failed_paths: list[str] = [p for p, ok in results if not ok]
    passed_count = sum(1 for _, ok in results if ok)
    total_count = len(results)

    threshold = contract.threshold
    mode = contract.mode

    if threshold is not None and threshold < 1.0:
        actual_ratio = passed_count / total_count if total_count > 0 else 0.0
        passed = actual_ratio >= threshold
        return passed, failed_paths

    if mode == "or":
        passed = passed_count > 0
    else:
        passed = passed_count == total_count

    return passed, failed_paths
