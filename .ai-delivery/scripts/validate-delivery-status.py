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

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")


def _locate_layout_dir() -> Path | None:
    """Find the orchestrator scripts dir by walking up from this file.

    Handles both layouts this validator lives in: the kit repo
    (``<kit>/scripts/``) and a bootstrapped repo (``<repo>/.ai-delivery/scripts/``,
    where ``.agents/`` is a *sibling* of ``.ai-delivery/``, not a parent).
    Returns None when unavailable so the pre-existing UI-contract gates keep
    working even without the layout contract.
    """
    here = Path(__file__).resolve()
    for base in here.parents:
        cand = base / LAYOUT_REL
        if (cand / "layout.py").is_file():
            return cand
    return None


_layout_dir = _locate_layout_dir()
if _layout_dir is not None:
    sys.path.insert(0, str(_layout_dir))
    from layout import is_new_layout, load_workflow_policy  # noqa: E402
else:  # pragma: no cover - only when the skill layer is absent
    is_new_layout = None  # type: ignore[assignment]
    load_workflow_policy = None  # type: ignore[assignment]

POST_FREEZE_STATUSES = frozenset(
    {
        "acceptance_frozen",
        "spec_ready",
        "plan_ready",
        "tasks_ready",
        "in_dev",
        "visual_acceptance_passed",
        "merged",
        "archived",
    }
)
UI_IMPLIES_UI_STATUSES = frozenset(
    {
        "acceptance_frozen",
        "visual_acceptance_passed",
        "merged",
        "archived",
    }
)
VISUAL_ACCEPTANCE_STATUSES = frozenset({"visual_acceptance_passed", "merged", "archived"})
# Delivered end-state in status.json: force implementation lookup even if
# HTML meta.delivery.status is still "frozen" (blocks raise-status-only shortcut).
STATUSES_REQUIRING_IMPLEMENTED_LOOKUP = frozenset({"merged", "archived"})
DELIVERY_IMPLEMENTED_FIELDS = ("type", "target", "requirement", "version", "status")

# superpowers verification discipline: `merged`/`archived` are only credible with
# hard evidence on disk. Enforced on new-layout sub-requirements only, so repos
# bootstrapped before the unified layout keep validating cleanly.
VERIFICATION_REQUIRED_STATUSES = frozenset({"merged", "archived"})
VERIFICATION_ARTIFACT = "verification.md"
DEFAULT_VERIFICATION_SECTIONS = ("评审轮次记录", "验证命令与结果", "签署")


CONTRACT_META_PATTERN = re.compile(
    r'<script[^>]*id=["\']ui-contract-meta["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)

# A pointer must carry at least one directory segment; bare "ui-contract.html"
# mentions in prose are not pointers.
CONTRACT_POINTER_PATTERN = re.compile(r"[A-Za-z0-9_\-./]+/ui-contract\.html")
# Lines marked as historical notes are exempt from the dangling-pointer check.
POINTER_HISTORY_PATTERN = re.compile(
    r"superseded|replaced by|deleted|已删除|取代", re.IGNORECASE
)
POINTER_SCAN_SUFFIXES = (".md", ".json")


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


def verification_required_sections(req_root: Path) -> tuple[str, ...]:
    """Section titles that must appear in verification.md, from workflow policy."""
    if load_workflow_policy is None:
        return DEFAULT_VERIFICATION_SECTIONS
    policy = load_workflow_policy(req_root)
    sections = policy.get("verification_policy", {}).get("required_sections")
    if isinstance(sections, list) and sections:
        return tuple(s for s in sections if isinstance(s, str) and s)
    return DEFAULT_VERIFICATION_SECTIONS


def check_verification_evidence(
    subreq_id: str, subreq_dir: Path, status: str, sections: tuple[str, ...]
) -> list[str]:
    """Require verification.md with its mandatory section titles.

    Existence + section titles only — never a semantic judgement about the
    contents. Skipped for legacy-layout sub-requirements.
    """
    if is_new_layout is None or not is_new_layout(subreq_dir):
        return []
    evidence = subreq_dir / VERIFICATION_ARTIFACT
    if not evidence.is_file():
        return [
            f"[GATE] {subreq_id} status={status} requires {VERIFICATION_ARTIFACT} "
            f"(final review clean + full analyze/test results + sign-off)"
        ]
    try:
        raw = evidence.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"[GATE] {subreq_id} cannot read {VERIFICATION_ARTIFACT}: {exc}"]
    missing = [section for section in sections if section not in raw]
    if missing:
        return [
            f"[GATE] {subreq_id} status={status} {VERIFICATION_ARTIFACT} is missing "
            f"required section(s): {', '.join(missing)}"
        ]
    return []


def pointer_resolves(
    token: str, file_dir: Path, req_root: Path, existing: list[Path]
) -> bool:
    normalized = token
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return False
    candidate = Path(normalized)
    if candidate.is_absolute() and candidate.is_file():
        return True
    for base in (file_dir, req_root):
        if (base / normalized).is_file():
            return True
    # Tolerate different anchor points: the pointer may be written relative to
    # another directory than the one we can reconstruct.
    token_posix = candidate.as_posix()
    return any(path.as_posix().endswith(token_posix) for path in existing)


def find_dangling_contract_pointers(req_root: Path) -> list[str]:
    """Reject references to ui-contract.html files that no longer exist.

    Contracts have no aggregate index, so pointers live scattered across the
    requirement directory (status.json notes, visual-acceptance.md,
    progress/todo records). When a contract is deleted or rebuilt under a new
    unit id, active pointers must be redirected in the same change; a line
    carrying a history marker ("superseded" / "deleted" / 已删除 / 取代) is an
    allowed historical note and is skipped.
    """
    if not req_root.is_dir():
        return []
    existing = sorted(req_root.rglob("ui-contract.html"))
    errors: list[str] = []
    for path in sorted(req_root.rglob("*")):
        if not path.is_file() or path.suffix not in POINTER_SCAN_SUFFIXES:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(raw.splitlines(), start=1):
            if POINTER_HISTORY_PATTERN.search(line):
                continue
            for match in CONTRACT_POINTER_PATTERN.finditer(line):
                # Skip placeholder-style tokens such as "<unit-id>/ui-contract.html".
                if match.start() > 0 and line[match.start() - 1] in "<>":
                    continue
                token = match.group(0)
                if pointer_resolves(token, path.parent, req_root, existing):
                    continue
                rel = path.relative_to(req_root)
                errors.append(
                    f"[POINTER] {rel}:{lineno} references missing ui-contract.html: "
                    f"{token} — redirect the pointer to the current contract or "
                    "mark the line as a historical note (superseded/deleted)"
                )
    return errors


def run_contract_validator(contract: Path, validator_script: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(validator_script), str(contract)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def require_implemented_lookup(
    subreq_id: str, contract: Path, meta: dict[str, Any] | None
) -> list[str]:
    """Require complete delivery.implemented when status.json is merged.

    Independent of HTML meta.delivery.status: raising status alone while leaving
    meta frozen + implemented:null must fail.
    """
    prefix = f"[GATE] {subreq_id} merged requires delivery.implemented in {contract}"
    if meta is None:
        return [f"{prefix}: cannot parse #ui-contract-meta"]

    delivery = meta.get("delivery")
    if not isinstance(delivery, dict):
        return [f"{prefix}: delivery object missing"]

    implemented = delivery.get("implemented")
    if not isinstance(implemented, dict):
        return [
            f"{prefix}: delivery.implemented must be an object with "
            f"{', '.join(DELIVERY_IMPLEMENTED_FIELDS)}"
        ]

    errors: list[str] = []
    for field in DELIVERY_IMPLEMENTED_FIELDS:
        if not is_nonempty_str(implemented.get(field)):
            errors.append(f"{prefix}: missing delivery.implemented.{field}")
    return errors


def validate_status_file(status_path: Path, req_root: Path, validator_script: Path) -> list[str]:
    errors: list[str] = []

    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"[STATUS] cannot read status.json: {exc}"]

    sub_requirements = status_data.get("sub_requirements")
    if not isinstance(sub_requirements, dict):
        return ["[STATUS] sub_requirements must be a mapping"]

    verification_sections = verification_required_sections(req_root)

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
            # `ui_bearing` still *infers* True for these statuses when the field
            # is absent, so UI slices remain gated. An explicit ui_bearing:false
            # (a pure backend/infra slice) must not be forced to produce a UI
            # contract — otherwise non-UI slices can never legitimately reach
            # merged.
            if status in UI_IMPLIES_UI_STATUSES and ui_bearing and not contracts:
                errors.append(
                    f"[GATE] {subreq_id} status={status} requires ui-contract.html"
                )

        if status in STATUSES_REQUIRING_IMPLEMENTED_LOOKUP and contracts:
            for contract in contracts:
                meta = load_contract_meta(contract)
                errors.extend(require_implemented_lookup(subreq_id, contract, meta))

        if status in VERIFICATION_REQUIRED_STATUSES:
            errors.extend(
                check_verification_evidence(
                    subreq_id, subreq_dir, status, verification_sections
                )
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

    errors.extend(find_dangling_contract_pointers(req_root))

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
