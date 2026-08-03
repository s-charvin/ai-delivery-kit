#!/usr/bin/env python3
"""Validate requirement-level status.json against frozen UI contract gates."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

POST_FREEZE_STATUSES = frozenset(
    {
        "acceptance_frozen",
        "spec_ready",
        "plan_ready",
        "tasks_ready",
        "in_dev",
        "visual_acceptance_passed",
        "merged",
    }
)
UI_IMPLIES_UI_STATUSES = frozenset(
    {
        "acceptance_frozen",
        "visual_acceptance_passed",
        "merged",
    }
)
VISUAL_ACCEPTANCE_STATUSES = frozenset({"visual_acceptance_passed", "merged"})


CONTRACT_META_PATTERN = re.compile(
    r'<script[^>]*id=["\']ui-contract-meta["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)


def find_contracts(subreq_dir: Path) -> list[Path]:
    """Find every ui-contract.html under a sub-requirement (one per unit)."""
    if not subreq_dir.is_dir():
        return []
    return sorted(subreq_dir.rglob("ui-contract.html"))


def has_ui_artifacts(subreq_dir: Path) -> bool:
    return bool(find_contracts(subreq_dir))


def load_contract_meta(contract: Path) -> dict[str, Any] | None:
    """Parse the embedded #ui-contract-meta JSON so callers can inspect
    meta.unit (type/dependencies) without re-implementing the HTML parser."""
    try:
        raw = contract.read_text(encoding="utf-8")
    except OSError:
        return None
    match = CONTRACT_META_PATTERN.search(raw)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def discover_units(subreq_dir: Path) -> list[tuple[Path, dict[str, Any] | None]]:
    """Return (contract_path, meta.unit) pairs for every unit contract found.

    Exposes each unit's type/dependencies so implementation-order tooling
    (shared-component -> page -> modal) can consume it without re-parsing.
    """
    units: list[tuple[Path, dict[str, Any] | None]] = []
    for contract in find_contracts(subreq_dir):
        meta = load_contract_meta(contract)
        unit = meta.get("unit") if isinstance(meta, dict) else None
        units.append((contract, unit if isinstance(unit, dict) else None))
    return units


def infer_ui_bearing(entry: dict, subreq_dir: Path) -> bool:
    ui_bearing = entry.get("ui_bearing")
    if ui_bearing is True:
        return True
    if ui_bearing is False:
        return False
    if has_ui_artifacts(subreq_dir):
        return True
    status = entry.get("status", "")
    if status in UI_IMPLIES_UI_STATUSES:
        return True
    return False


def has_visual_acceptance_evidence(subreq_dir: Path) -> bool:
    if (subreq_dir / "visual-acceptance.md").is_file():
        return True
    evidence_dir = subreq_dir / "visual-acceptance"
    if evidence_dir.is_dir():
        return any(evidence_dir.glob("*.png"))
    return False


def run_contract_validator(contract: Path, validator_script: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(validator_script), str(contract)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def validate_status_file(status_path: Path, req_root: Path, validator_script: Path) -> list[str]:
    errors: list[str] = []

    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"[STATUS] cannot read status.json: {exc}"]

    sub_requirements = status_data.get("sub_requirements")
    if not isinstance(sub_requirements, dict):
        return ["[STATUS] sub_requirements must be a mapping"]

    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            errors.append(f"[STATUS] sub_requirements.{subreq_id} must be a mapping")
            continue

        status = entry.get("status")
        if not isinstance(status, str):
            errors.append(f"[STATUS] sub_requirements.{subreq_id}.status missing")
            continue

        if status.startswith("blocked_"):
            continue

        subreq_dir = req_root / "sub-requirements" / subreq_id
        contracts = find_contracts(subreq_dir)
        ui_bearing = infer_ui_bearing(entry, subreq_dir)

        if status in VISUAL_ACCEPTANCE_STATUSES and ui_bearing:
            if not has_visual_acceptance_evidence(subreq_dir):
                errors.append(
                    f"[GATE] {subreq_id} status={status} requires visual-acceptance.md "
                    f"or visual-acceptance/*.png"
                )

        if status in POST_FREEZE_STATUSES:
            if status in UI_IMPLIES_UI_STATUSES and not contracts:
                errors.append(
                    f"[GATE] {subreq_id} status={status} requires ui-contract.html"
                )

        if status == "merged" and contracts:
            for contract in contracts:
                ok, output = run_contract_validator(contract, validator_script)
                if not ok:
                    errors.append(
                        f"[GATE] {subreq_id} merged but contract invalid: {contract}\n{output}"
                    )

        if status in POST_FREEZE_STATUSES and contracts:
            for contract in contracts:
                ok, output = run_contract_validator(contract, validator_script)
                if not ok:
                    errors.append(
                        f"[GATE] {subreq_id} status={status} but contract invalid: {contract}\n{output}"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "status",
        type=Path,
        nargs="?",
        help="Path to requirement-level status.json",
    )
    parser.add_argument(
        "--req-root",
        type=Path,
        default=None,
        help="Requirement root directory (parent of sub-requirements/)",
    )
    parser.add_argument(
        "--validator",
        type=Path,
        default=None,
        help="Path to validate-ui-contract-html.py",
    )
    args = parser.parse_args()

    if args.status is None:
        parser.error("status path is required")

    status_path = args.status.resolve()
    req_root = args.req_root.resolve() if args.req_root else status_path.parent.resolve()

    script_dir = Path(__file__).resolve().parent
    validator_script = args.validator.resolve() if args.validator else script_dir / "validate-ui-contract-html.py"

    if not validator_script.exists():
        print(f"ERROR: validator not found: {validator_script}", file=sys.stderr)
        return 2

    errors = validate_status_file(status_path, req_root, validator_script)
    if not errors:
        print(f"OK: {status_path}")
        return 0

    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    print(f"INVALID: {status_path} ({len(errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
