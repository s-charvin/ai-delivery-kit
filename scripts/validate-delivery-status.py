#!/usr/bin/env python3
"""Validate requirement-level status.json against frozen UI-truth index gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")
UI_TRUTH_INDEX = Path("contracts") / "ui-truth-index.json"
UI_TRUTH_SCHEMA_VERSION = 1
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UNIT_TYPES = frozenset({"page", "component", "modal", "shared-component"})
STACKS = frozenset({"flutter", "web"})
CONFIRMATION_STATUSES = frozenset({"confirmed", "waived"})
WEB_PREVIEW_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".html"})


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
DEFAULT_VERIFICATION_MARKERS = (
    "ai-delivery-verification:review-rounds",
    "ai-delivery-verification:commands-results",
    "ai-delivery-verification:sign-off",
)


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


def verification_required_markers(req_root: Path) -> tuple[str, ...]:
    if load_workflow_policy is None:
        return DEFAULT_VERIFICATION_MARKERS
    policy = load_workflow_policy(req_root)
    markers = policy.get("verification_policy", {}).get("required_markers")
    if isinstance(markers, list) and markers:
        return tuple(
            marker for marker in markers if isinstance(marker, str) and marker
        )
    return DEFAULT_VERIFICATION_MARKERS


def check_verification_evidence(
    subreq_id: str, subreq_dir: Path, status: str, markers: tuple[str, ...]
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
    missing = [marker for marker in markers if marker not in raw]
    if missing:
        return [
            f"[GATE] {subreq_id} status={status} {VERIFICATION_ARTIFACT} is missing "
            f"required marker(s): {', '.join(missing)}"
        ]
    return []


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso8601_timestamp(value: Any) -> bool:
    if not _is_non_empty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _resolve_repo_relative_file(
    repo_root: Path,
    rel: Any,
    *,
    field: str,
    subreq_id: str,
    unit_id: str,
    allowed_suffixes: frozenset[str] | None = None,
) -> tuple[Path | None, list[str]]:
    prefix = f"[GATE] {subreq_id} unit {unit_id} {field}"
    if not _is_non_empty_string(rel):
        return None, [f"{prefix} must be a repo-relative path"]

    rel_path = Path(rel)
    windows_path = PureWindowsPath(rel)
    if rel_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return None, [f"{prefix} must be a repo-relative path"]
    if ".." in rel_path.parts or ".." in windows_path.parts:
        return None, [
            f"{prefix} must stay within repository root ('..' is forbidden): {rel}"
        ]

    try:
        resolved_root = repo_root.resolve(strict=True)
        resolved = (resolved_root / rel_path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return None, [f"{prefix} missing or unreadable at repo root: {rel} ({exc})"]

    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None, [f"{prefix} resolves outside repository root: {rel}"]

    if not resolved.is_file():
        return None, [f"{prefix} is not a file at repo root: {rel}"]
    if allowed_suffixes is not None and resolved.suffix.lower() not in allowed_suffixes:
        expected = " or ".join(sorted(allowed_suffixes))
        return None, [f"{prefix} must end with {expected}: {rel}"]
    return resolved, []


def _check_content_hash(
    path: Path | None,
    expected: Any,
    *,
    field: str,
    subreq_id: str,
    unit_id: str,
) -> list[str]:
    prefix = f"[GATE] {subreq_id} unit {unit_id} {field}"
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        return [f"{prefix} must be a lowercase 64-character SHA-256"]
    if path is None:
        return []
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        return [f"{prefix} cannot hash file: {exc}"]
    if actual != expected:
        return [f"{prefix} mismatch: expected {expected}, got {actual}"]
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

    errors: list[str] = []
    if type(data.get("schema_version")) is not int or data["schema_version"] != UI_TRUTH_SCHEMA_VERSION:
        errors.append(
            f"[GATE] {subreq_id} {UI_TRUTH_INDEX.as_posix()} schema_version "
            f"must equal {UI_TRUTH_SCHEMA_VERSION}"
        )

    design_source = data.get("design_source")
    if not isinstance(design_source, dict):
        errors.append(f"[GATE] {subreq_id} design_source must be an object")
    else:
        for field in ("file_key", "root_node", "revision"):
            if not _is_non_empty_string(design_source.get(field)):
                errors.append(f"[GATE] {subreq_id} design_source.{field} is required")
        if not _is_iso8601_timestamp(design_source.get("captured_at")):
            errors.append(
                f"[GATE] {subreq_id} design_source.captured_at must be an ISO-8601 timestamp with timezone"
            )

    units = data.get("units")
    if not isinstance(units, list) or not units:
        errors.append(
            f"[GATE] {subreq_id} status={status} {UI_TRUTH_INDEX.as_posix()} has no units[]"
        )
        return errors

    seen_unit_ids: set[str] = set()
    dependency_records: list[tuple[str, list[str]]] = []

    for i, unit in enumerate(units):
        fallback_id = f"units[{i}]"
        if not isinstance(unit, dict):
            errors.append(f"[GATE] {subreq_id} unit {fallback_id} must be an object")
            continue

        raw_unit_id = unit.get("unit_id")
        unit_id = raw_unit_id if _is_non_empty_string(raw_unit_id) else fallback_id
        if not isinstance(raw_unit_id, str) or not KEBAB_CASE_RE.fullmatch(raw_unit_id):
            errors.append(
                f"[GATE] {subreq_id} unit {fallback_id} unit_id must be kebab-case"
            )
        elif raw_unit_id in seen_unit_ids:
            errors.append(f"[GATE] {subreq_id} duplicate unit_id: {raw_unit_id}")
        else:
            seen_unit_ids.add(raw_unit_id)

        unit_type = unit.get("type")
        if unit_type not in UNIT_TYPES:
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} type must be one of: "
                f"{', '.join(sorted(UNIT_TYPES))}"
            )

        stack = unit.get("stack")
        if stack not in STACKS:
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} stack must be one of: "
                f"{', '.join(sorted(STACKS))}"
            )

        if not _is_non_empty_string(unit.get("source_node")):
            errors.append(f"[GATE] {subreq_id} unit {unit_id} source_node is required")

        dependencies = unit.get("dependencies")
        valid_dependencies: list[str] = []
        if not isinstance(dependencies, list):
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} dependencies must be an array"
            )
        else:
            seen_dependencies: set[str] = set()
            for dependency in dependencies:
                if not isinstance(dependency, str) or not KEBAB_CASE_RE.fullmatch(dependency):
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} dependency ids must be kebab-case"
                    )
                    continue
                if dependency == raw_unit_id:
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} cannot depend on itself"
                    )
                if dependency in seen_dependencies:
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} duplicate dependency: {dependency}"
                    )
                    continue
                seen_dependencies.add(dependency)
                valid_dependencies.append(dependency)
            if isinstance(raw_unit_id, str):
                dependency_records.append((raw_unit_id, valid_dependencies))

        component_suffixes = frozenset({".dart"}) if stack == "flutter" else None
        component_file, file_errors = _resolve_repo_relative_file(
            repo_root,
            unit.get("component_path"),
            field="component_path",
            subreq_id=subreq_id,
            unit_id=str(unit_id),
            allowed_suffixes=component_suffixes,
        )
        errors.extend(file_errors)
        errors.extend(
            _check_content_hash(
                component_file,
                unit.get("component_sha256"),
                field="component_sha256",
                subreq_id=subreq_id,
                unit_id=str(unit_id),
            )
        )

        if stack == "flutter" or "golden_test" in unit or "golden_test_sha256" in unit:
            test_suffixes = (
                frozenset({".dart"})
                if stack == "flutter"
                else frozenset({".js", ".jsx", ".ts", ".tsx"})
            )
            golden_file, file_errors = _resolve_repo_relative_file(
                repo_root,
                unit.get("golden_test"),
                field="golden_test",
                subreq_id=subreq_id,
                unit_id=str(unit_id),
                allowed_suffixes=test_suffixes,
            )
            errors.extend(file_errors)
            errors.extend(
                _check_content_hash(
                    golden_file,
                    unit.get("golden_test_sha256"),
                    field="golden_test_sha256",
                    subreq_id=subreq_id,
                    unit_id=str(unit_id),
                )
            )

        states = unit.get("states")
        if not isinstance(states, list) or not states:
            errors.append(f"[GATE] {subreq_id} unit {unit_id} has no states[]")
            continue

        seen_state_ids: set[str] = set()
        for state_index, state in enumerate(states):
            fallback_state = f"states[{state_index}]"
            if not isinstance(state, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_state} must be an object"
                )
                continue

            raw_state_id = state.get("state_id")
            state_id = raw_state_id if _is_non_empty_string(raw_state_id) else fallback_state
            if not isinstance(raw_state_id, str) or not KEBAB_CASE_RE.fullmatch(raw_state_id):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_state} state_id must be kebab-case"
                )
            elif raw_state_id in seen_state_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} duplicate state_id: {raw_state_id}"
                )
            else:
                seen_state_ids.add(raw_state_id)

            if not _is_non_empty_string(state.get("source_node")):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} source_node is required"
                )

            preview_suffixes = (
                frozenset({".png"}) if stack == "flutter" else WEB_PREVIEW_SUFFIXES
            )
            preview_file, file_errors = _resolve_repo_relative_file(
                repo_root,
                state.get("preview_path"),
                field="preview_path",
                subreq_id=subreq_id,
                unit_id=f"{unit_id} state {state_id}",
                allowed_suffixes=preview_suffixes,
            )
            errors.extend(file_errors)
            errors.extend(
                _check_content_hash(
                    preview_file,
                    state.get("preview_sha256"),
                    field="preview_sha256",
                    subreq_id=subreq_id,
                    unit_id=f"{unit_id} state {state_id}",
                )
            )

            confirmation = state.get("confirmation")
            if not isinstance(confirmation, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} confirmation must be an object"
                )
                continue
            confirmation_status = confirmation.get("status")
            if confirmation_status not in CONFIRMATION_STATUSES:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} confirmation.status "
                    f"must be one of: {', '.join(sorted(CONFIRMATION_STATUSES))}"
                )
            if not _is_iso8601_timestamp(confirmation.get("confirmed_at")):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} "
                    "confirmation.confirmed_at must be an ISO-8601 timestamp with timezone"
                )
            if not _is_non_empty_string(confirmation.get("confirmed_by")):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} "
                    "confirmation.confirmed_by is required"
                )
            if confirmation_status == "waived" and not _is_non_empty_string(
                confirmation.get("note")
            ):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} state {state_id} waiver note is required"
                )

    for unit_id, dependencies in dependency_records:
        for dependency in dependencies:
            if dependency not in seen_unit_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} references unknown dependency {dependency}"
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

    verification_markers = verification_required_markers(req_root)
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

        if status in POST_FREEZE_STATUSES and ui_bearing:
            errors.extend(
                check_ui_truth_index(subreq_id, subreq_dir, repo_root, status)
            )

        if status in VERIFICATION_REQUIRED_STATUSES:
            errors.extend(
                check_verification_evidence(
                    subreq_id, subreq_dir, status, verification_markers
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
