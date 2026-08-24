#!/usr/bin/env python3
"""Validate requirement-level status.json against frozen UI-truth index gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")
UI_TRUTH_INDEX = Path("contracts") / "ui-truth-index.json"


def _locate_layout_dir() -> Path | None:
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
else:  # pragma: no cover
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
VISUAL_ACCEPTANCE_STATUSES = frozenset(
    {"visual_acceptance_passed", "merged", "archived"}
)
VERIFICATION_REQUIRED_STATUSES = frozenset({"merged", "archived"})
VERIFICATION_ARTIFACT = "verification.md"
DEFAULT_VERIFICATION_SECTIONS = ("评审轮次记录", "验证命令与结果", "签署")


def find_repo_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / ".git").exists():
            return cand
        if (cand / ".ai-delivery" / "meta" / "project-binding.json").is_file():
            return cand
    return start


def ui_truth_index_path(subreq_dir: Path) -> Path:
    return subreq_dir / UI_TRUTH_INDEX


def load_ui_truth_index(subreq_dir: Path) -> dict[str, Any] | None:
    path = ui_truth_index_path(subreq_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def index_units(subreq_dir: Path) -> list[dict[str, Any]]:
    data = load_ui_truth_index(subreq_dir)
    if not data:
        return []
    units = data.get("units")
    if not isinstance(units, list):
        return []
    return [u for u in units if isinstance(u, dict)]


def has_ui_artifacts(subreq_dir: Path) -> bool:
    return ui_truth_index_path(subreq_dir).is_file() and bool(index_units(subreq_dir))


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


def _check_repo_relative_file(
    repo_root: Path, rel: Any, *, field: str, subreq_id: str, unit_id: str
) -> list[str]:
    if not isinstance(rel, str) or not rel.strip() or Path(rel).is_absolute():
        return [
            f"[GATE] {subreq_id} unit {unit_id} {field} must be a repo-relative path"
        ]
    if not (repo_root / rel).is_file():
        return [
            f"[GATE] {subreq_id} unit {unit_id} {field} missing at repo root: {rel}"
        ]
    return []


def check_ui_truth_index(
    subreq_id: str, subreq_dir: Path, repo_root: Path, status: str
) -> list[str]:
    path = ui_truth_index_path(subreq_dir)
    if not path.is_file():
        return [
            f"[GATE] {subreq_id} status={status} requires {UI_TRUTH_INDEX.as_posix()}"
        ]
    data = load_ui_truth_index(subreq_dir)
    if data is None:
        return [f"[GATE] {subreq_id} cannot parse {UI_TRUTH_INDEX.as_posix()}"]
    units = index_units(subreq_dir)
    if not units:
        return [
            f"[GATE] {subreq_id} status={status} {UI_TRUTH_INDEX.as_posix()} "
            f"has no units[]"
        ]
    errors: list[str] = []
    for i, unit in enumerate(units):
        unit_id = unit.get("unit_id") or f"units[{i}]"
        for field in ("component_path", "preview_path"):
            errors.extend(
                _check_repo_relative_file(
                    repo_root,
                    unit.get(field),
                    field=field,
                    subreq_id=subreq_id,
                    unit_id=str(unit_id),
                )
            )
        if unit.get("stack") == "flutter":
            errors.extend(
                _check_repo_relative_file(
                    repo_root,
                    unit.get("golden_test"),
                    field="golden_test",
                    subreq_id=subreq_id,
                    unit_id=str(unit_id),
                )
            )
    return errors


def validate_status_file(status_path: Path, req_root: Path) -> list[str]:
    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"[STATUS] cannot read status.json: {exc}"]

    sub_requirements = status_data.get("sub_requirements")
    if not isinstance(sub_requirements, dict):
        return ["[STATUS] sub_requirements must be a mapping"]

    verification_sections = verification_required_sections(req_root)
    repo_root = find_repo_root(req_root)
    errors: list[str] = []

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
        ui_bearing = infer_ui_bearing(entry, subreq_dir)

        if status in VISUAL_ACCEPTANCE_STATUSES and ui_bearing:
            if not has_visual_acceptance_evidence(subreq_dir):
                errors.append(
                    f"[GATE] {subreq_id} status={status} requires visual-acceptance.md "
                    f"or visual-acceptance/*.png"
                )

        if status in POST_FREEZE_STATUSES:
            if status in UI_IMPLIES_UI_STATUSES and ui_bearing:
                errors.extend(
                    check_ui_truth_index(subreq_id, subreq_dir, repo_root, status)
                )

        if status in VERIFICATION_REQUIRED_STATUSES:
            errors.extend(
                check_verification_evidence(
                    subreq_id, subreq_dir, status, verification_sections
                )
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
    args = parser.parse_args()

    if args.status is None:
        parser.error("status path is required")

    status_path = args.status.resolve()
    req_root = args.req_root.resolve() if args.req_root else status_path.parent.resolve()

    errors = validate_status_file(status_path, req_root)
    if not errors:
        print(f"OK: {status_path}")
        return 0

    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    print(f"INVALID: {status_path} ({len(errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
