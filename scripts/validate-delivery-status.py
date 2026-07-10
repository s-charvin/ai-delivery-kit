#!/usr/bin/env python3
"""Validate requirement-level status.json against frozen UI contract gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

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


def find_contracts(subreq_dir: Path) -> list[Path]:
    if not subreq_dir.is_dir():
        return []
    return sorted(subreq_dir.rglob("ui-acceptance-contract.yaml"))


def has_ui_artifacts(subreq_dir: Path) -> bool:
    if not subreq_dir.is_dir():
        return False
    if find_contracts(subreq_dir):
        return True
    return (subreq_dir / "section-map.json").exists()


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
        ui_artifacts = has_ui_artifacts(subreq_dir)

        if status in POST_FREEZE_STATUSES:
            if status in UI_IMPLIES_UI_STATUSES and not contracts:
                errors.append(
                    f"[GATE] {subreq_id} status={status} requires ui-acceptance-contract.yaml"
                )
            elif ui_artifacts and not contracts and status != "acceptance_frozen":
                errors.append(
                    f"[GATE] {subreq_id} has section-map but no ui-acceptance-contract.yaml"
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
        help="Path to validate-ui-contract.py",
    )
    args = parser.parse_args()

    if args.status is None:
        parser.error("status path is required")

    status_path = args.status.resolve()
    req_root = args.req_root.resolve() if args.req_root else status_path.parent.resolve()

    script_dir = Path(__file__).resolve().parent
    validator_script = args.validator.resolve() if args.validator else script_dir / "validate-ui-contract.py"

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
