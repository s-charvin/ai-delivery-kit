#!/usr/bin/env python3
"""Validate requirement-level status.json against frozen UI-truth index gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")
UI_TRUTH_INDEX = Path("contracts") / "ui-truth-index.json"
UI_TRUTH_SCHEMA_VERSION = 2
VISUAL_ACCEPTANCE_ARTIFACT = "visual-acceptance.json"
VISUAL_ACCEPTANCE_SCHEMA_VERSION = 1
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UNIT_TYPES = frozenset({"page", "component", "modal", "shared-component"})
STACKS = frozenset({"flutter", "web"})
CONFIRMATION_STATUSES = frozenset({"confirmed", "waived"})
EVIDENCE_ORIGINS = frozenset({"figma", "requirement", "project", "user-decision"})
UI_TRUTH_MODES = frozenset({"none", "existing", "runtime-baseline", "figma"})
UI_TRUTH_CAPABILITY_MODES = frozenset({"runtime-baseline", "figma"})
DESIGN_MODES = frozenset({"none", "light", "full"})
LEGACY_MODE_FIELDS = frozenset({"ui_contract_exempt", "no_design_client"})
SURFACE_KINDS = frozenset({"viewport", "container"})
ORIENTATIONS = frozenset({"portrait", "landscape", "not-applicable"})
REVIEW_MODES = frozenset({"visual", "behavior", "both"})
COVERAGE_STATUSES = frozenset({"covered", "not_applicable"})
COVERAGE_DIMENSIONS = frozenset(
    {
        "state",
        "layout",
        "content",
        "interaction",
        "motion",
        "assets",
        "theme",
        "accessibility",
        "platform",
        "performance",
    }
)
ACCEPTANCE_RESULTS = frozenset({"passed", "waived"})
ACCEPTANCE_EVIDENCE_KINDS = frozenset({"preview", "test", "manual", "image-diff"})
VISUAL_EVIDENCE_KINDS = frozenset({"preview", "image-diff"})
BEHAVIOR_EVIDENCE_KINDS = frozenset({"test", "manual"})
WEB_PREVIEW_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".html"})
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})


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


def legacy_participation_errors(req_root: Path) -> list[str]:
    """Reject removed routing fields and participation profiles."""
    def legacy_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            found = {key for key in value if key in LEGACY_MODE_FIELDS}
            for nested in value.values():
                found.update(legacy_keys(nested))
            return found
        if isinstance(value, list):
            found: set[str] = set()
            for nested in value:
                found.update(legacy_keys(nested))
            return found
        return set()

    def has_legacy_profile(value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("participation") == "no_design_client":
                return True
            return any(has_legacy_profile(nested) for nested in value.values())
        if isinstance(value, list):
            return any(has_legacy_profile(nested) for nested in value)
        return False

    candidates = [req_root / ".ai-delivery" / "meta" / "project-binding.json"]
    candidates.extend(
        cand / ".ai-delivery" / "meta" / "project-binding.json"
        for cand in req_root.parents
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        stale_keys = legacy_keys(data)
        if stale_keys:
            return [
                "[MODE] legacy project-binding field(s) are forbidden: "
                + ", ".join(sorted(stale_keys))
            ]
        if has_legacy_profile(data):
            return [
                "[MODE] no_design_client participation profile is removed; "
                "use ui_truth_mode and design_mode"
            ]
    return []


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


def infer_ui_bearing(entry: dict, subreq_dir: Path | None = None) -> bool:
    """Use the explicit surface flag; never infer it from artifacts or status."""
    return entry.get("ui_bearing") is True


def mode_errors(entry: dict) -> list[str]:
    errors: list[str] = []
    def legacy_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            found = {key for key in value if key in LEGACY_MODE_FIELDS}
            for nested in value.values():
                found.update(legacy_keys(nested))
            return found
        if isinstance(value, list):
            found: set[str] = set()
            for nested in value:
                found.update(legacy_keys(nested))
            return found
        return set()

    for field in sorted(legacy_keys(entry)):
        errors.append(f"legacy field {field} is forbidden")
    bearing = entry.get("ui_bearing")
    truth = entry.get("ui_truth_mode")
    design = entry.get("design_mode")
    if type(bearing) is not bool:
        errors.append("ui_bearing must be a boolean")
    if truth not in UI_TRUTH_MODES:
        errors.append(
            "ui_truth_mode must be one of: " + ", ".join(sorted(UI_TRUTH_MODES))
        )
    if design not in DESIGN_MODES:
        errors.append(
            "design_mode must be one of: " + ", ".join(sorted(DESIGN_MODES))
        )
    if isinstance(bearing, bool) and truth in UI_TRUTH_MODES:
        expected = truth != "none"
        if bearing != expected:
            errors.append(
                f"ui_bearing={str(bearing).lower()} is inconsistent with "
                f"ui_truth_mode={truth} (expected {str(expected).lower()})"
            )
    if type(entry.get("design_approved")) is not bool:
        errors.append("design_approved must be a boolean")
    elif design == "none" and entry.get("design_approved") is True:
        errors.append("design_mode=none cannot set design_approved=true")
    return errors


def requires_ui_truth(entry: dict) -> bool:
    return entry.get("ui_truth_mode") in UI_TRUTH_CAPABILITY_MODES


def design_artifact_required(entry: dict, status: str) -> bool:
    return entry.get("design_mode") in {"light", "full"} and status in POST_FREEZE_STATUSES


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


def _contains_identifier(text: str, identifier: str) -> bool:
    """Match an ASCII machine id as a token, not as a substring of another id."""
    return re.search(
        rf"(?<![a-z0-9-]){re.escape(identifier)}(?![a-z0-9-])", text
    ) is not None


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


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _is_positive_number(value: Any) -> bool:
    return _is_finite_number(value) and value > 0


def _check_evidence_source(
    value: dict[str, Any],
    *,
    prefix: str,
    figma_requires_node: bool,
    allowed_origins: frozenset[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    origin = value.get("evidence_origin")
    if origin not in EVIDENCE_ORIGINS:
        errors.append(
            f"{prefix} evidence_origin must be one of: "
            f"{', '.join(sorted(EVIDENCE_ORIGINS))}"
        )
    elif allowed_origins is not None and origin not in allowed_origins:
        errors.append(
            f"{prefix} evidence_origin must be one of: "
            f"{', '.join(sorted(allowed_origins))}"
        )
    if not _is_non_empty_string(value.get("source_ref")):
        errors.append(f"{prefix} source_ref is required")
    if figma_requires_node and origin == "figma" and not _is_non_empty_string(
        value.get("source_node")
    ):
        errors.append(f"{prefix} source_node is required for figma evidence")
    return errors


def _check_confirmation(
    confirmation: Any, *, prefix: str, preview_sha256: Any | None
) -> list[str]:
    if not isinstance(confirmation, dict):
        return [f"{prefix} confirmation must be an object"]

    errors: list[str] = []
    status = confirmation.get("status")
    if status not in CONFIRMATION_STATUSES:
        errors.append(
            f"{prefix} confirmation.status must be one of: "
            f"{', '.join(sorted(CONFIRMATION_STATUSES))}"
        )
    if not _is_iso8601_timestamp(confirmation.get("confirmed_at")):
        errors.append(
            f"{prefix} confirmation.confirmed_at must be an ISO-8601 timestamp with timezone"
        )
    if not _is_non_empty_string(confirmation.get("confirmed_by")):
        errors.append(f"{prefix} confirmation.confirmed_by is required")
    if status == "waived" and not _is_non_empty_string(confirmation.get("note")):
        errors.append(f"{prefix} waiver note is required")

    if preview_sha256 is not None:
        reviewed = confirmation.get("reviewed_preview_sha256")
        if not isinstance(reviewed, str) or not SHA256_RE.fullmatch(reviewed):
            errors.append(
                f"{prefix} confirmation.reviewed_preview_sha256 must be a lowercase "
                "64-character SHA-256"
            )
        elif reviewed != preview_sha256:
            errors.append(
                f"{prefix} confirmation.reviewed_preview_sha256 must match preview_sha256"
            )
    return errors


def check_ui_truth_index(
    subreq_id: str,
    subreq_dir: Path,
    repo_root: Path,
    status: str,
    expected_mode: str | None = None,
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
    index_mode = data.get("ui_truth_mode")
    if index_mode not in UI_TRUTH_CAPABILITY_MODES:
        errors.append(
            f"[GATE] {subreq_id} {UI_TRUTH_INDEX.as_posix()} ui_truth_mode "
            "must be runtime-baseline or figma"
        )
    if expected_mode in UI_TRUTH_CAPABILITY_MODES and index_mode != expected_mode:
        errors.append(
            f"[GATE] {subreq_id} {UI_TRUTH_INDEX.as_posix()} ui_truth_mode "
            f"must match status.json ({expected_mode})"
        )
    effective_mode = index_mode if index_mode in UI_TRUTH_CAPABILITY_MODES else expected_mode
    if type(data.get("schema_version")) is not int or data["schema_version"] != UI_TRUTH_SCHEMA_VERSION:
        errors.append(
            f"[GATE] {subreq_id} {UI_TRUTH_INDEX.as_posix()} schema_version "
            f"must equal {UI_TRUTH_SCHEMA_VERSION}"
        )

    design_source = data.get("design_source")
    if not isinstance(design_source, dict):
        errors.append(f"[GATE] {subreq_id} design_source must be an object")
    else:
        source_origin = design_source.get("evidence_origin")
        if source_origin not in EVIDENCE_ORIGINS:
            errors.append(
                f"[GATE] {subreq_id} design_source.evidence_origin must be one of: "
                f"{', '.join(sorted(EVIDENCE_ORIGINS))}"
            )
        elif effective_mode == "figma" and source_origin != "figma":
            errors.append(
                f"[GATE] {subreq_id} figma ui truth requires design_source.evidence_origin=figma"
            )
        elif effective_mode == "runtime-baseline" and source_origin == "figma":
            errors.append(
                f"[GATE] {subreq_id} runtime-baseline cannot use figma design_source evidence"
            )
        if not _is_non_empty_string(design_source.get("source_ref")):
            errors.append(f"[GATE] {subreq_id} design_source.source_ref is required")
        if effective_mode == "figma":
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
    seen_global_scenario_ids: set[str] = set()
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

        if effective_mode == "figma" and not _is_non_empty_string(unit.get("source_node")):
            errors.append(f"[GATE] {subreq_id} unit {unit_id} source_node is required for figma evidence")

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

        profiles = unit.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            errors.append(f"[GATE] {subreq_id} unit {unit_id} has no profiles[]")
            profiles = []
        seen_profile_ids: set[str] = set()
        for profile_index, profile in enumerate(profiles):
            fallback_profile = f"profiles[{profile_index}]"
            if not isinstance(profile, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_profile} must be an object"
                )
                continue
            raw_profile_id = profile.get("profile_id")
            profile_id = (
                raw_profile_id
                if _is_non_empty_string(raw_profile_id)
                else fallback_profile
            )
            if not isinstance(raw_profile_id, str) or not KEBAB_CASE_RE.fullmatch(
                raw_profile_id
            ):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_profile} "
                    "profile_id must be kebab-case"
                )
            elif raw_profile_id in seen_profile_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} duplicate profile_id: "
                    f"{raw_profile_id}"
                )
            else:
                seen_profile_ids.add(raw_profile_id)

            surface = profile.get("surface")
            if not isinstance(surface, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                    "surface must be an object"
                )
            else:
                if surface.get("kind") not in SURFACE_KINDS:
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                        f"surface.kind must be one of: {', '.join(sorted(SURFACE_KINDS))}"
                    )
                for field in ("width", "height"):
                    if not _is_positive_number(surface.get(field)):
                        errors.append(
                            f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                            f"surface.{field} must be a positive number"
                        )
                if "device_pixel_ratio" in surface and not _is_positive_number(
                    surface.get("device_pixel_ratio")
                ):
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                        "surface.device_pixel_ratio must be a positive number"
                    )

            if profile.get("orientation") not in ORIENTATIONS:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                    f"orientation must be one of: {', '.join(sorted(ORIENTATIONS))}"
                )
            for field in ("theme", "locale", "input_mode"):
                if not _is_non_empty_string(profile.get(field)):
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                        f"{field} is required"
                    )
            if not _is_positive_number(profile.get("text_scale")):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                    "text_scale must be a positive number"
                )
            if type(profile.get("reduced_motion")) is not bool:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} "
                    "reduced_motion must be a boolean"
                )

        states = unit.get("states")
        if not isinstance(states, list) or not states:
            errors.append(f"[GATE] {subreq_id} unit {unit_id} has no states[]")
            states = []
        seen_state_ids: set[str] = set()
        for state_index, state in enumerate(states):
            fallback_state = f"states[{state_index}]"
            if not isinstance(state, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_state} must be an object"
                )
                continue
            raw_state_id = state.get("state_id")
            state_id = (
                raw_state_id if _is_non_empty_string(raw_state_id) else fallback_state
            )
            if not isinstance(raw_state_id, str) or not KEBAB_CASE_RE.fullmatch(
                raw_state_id
            ):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_state} "
                    "state_id must be kebab-case"
                )
            elif raw_state_id in seen_state_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} duplicate state_id: {raw_state_id}"
                )
            else:
                seen_state_ids.add(raw_state_id)
            errors.extend(
                _check_evidence_source(
                    state,
                    prefix=f"[GATE] {subreq_id} unit {unit_id} state {state_id}",
                    figma_requires_node=effective_mode == "figma",
                    allowed_origins=(
                        frozenset({"figma", "requirement", "project", "user-decision"})
                        if effective_mode == "figma"
                        else frozenset({"requirement", "project", "user-decision"})
                    ),
                )
            )

        scenarios = unit.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            errors.append(f"[GATE] {subreq_id} unit {unit_id} has no scenarios[]")
            scenarios = []
        seen_scenario_ids: set[str] = set()
        scenario_dimensions: dict[str, set[str]] = {}
        scenario_state_ids: set[str] = set()
        scenario_profile_ids: set[str] = set()
        preview_suffixes = (
            frozenset({".png"}) if stack == "flutter" else WEB_PREVIEW_SUFFIXES
        )

        for scenario_index, scenario in enumerate(scenarios):
            fallback_scenario = f"scenarios[{scenario_index}]"
            if not isinstance(scenario, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_scenario} must be an object"
                )
                continue
            raw_scenario_id = scenario.get("scenario_id")
            scenario_id = (
                raw_scenario_id
                if _is_non_empty_string(raw_scenario_id)
                else fallback_scenario
            )
            prefix = f"[GATE] {subreq_id} unit {unit_id} scenario {scenario_id}"
            if not isinstance(raw_scenario_id, str) or not KEBAB_CASE_RE.fullmatch(
                raw_scenario_id
            ):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_scenario} "
                    "scenario_id must be kebab-case"
                )
            elif raw_scenario_id in seen_scenario_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} duplicate scenario_id: "
                    f"{raw_scenario_id}"
                )
            elif raw_scenario_id in seen_global_scenario_ids:
                errors.append(
                    f"[GATE] {subreq_id} duplicate scenario_id across units: "
                    f"{raw_scenario_id}"
                )
            else:
                seen_scenario_ids.add(raw_scenario_id)
                seen_global_scenario_ids.add(raw_scenario_id)

            state_id = scenario.get("state_id")
            if not _is_non_empty_string(state_id):
                errors.append(f"{prefix} state_id is required")
            elif state_id not in seen_state_ids:
                errors.append(f"{prefix} references unknown state {state_id}")
            else:
                scenario_state_ids.add(state_id)

            profile_id = scenario.get("profile_id")
            if not _is_non_empty_string(profile_id):
                errors.append(f"{prefix} profile_id is required")
            elif profile_id not in seen_profile_ids:
                errors.append(f"{prefix} references unknown profile {profile_id}")
            else:
                scenario_profile_ids.add(profile_id)

            raw_dimensions = scenario.get("dimensions")
            valid_dimensions: set[str] = set()
            if not isinstance(raw_dimensions, list) or not raw_dimensions:
                errors.append(f"{prefix} dimensions must be a non-empty array")
            else:
                for dimension in raw_dimensions:
                    if dimension not in COVERAGE_DIMENSIONS:
                        errors.append(
                            f"{prefix} dimension must be one of: "
                            f"{', '.join(sorted(COVERAGE_DIMENSIONS))}"
                        )
                    elif dimension in valid_dimensions:
                        errors.append(f"{prefix} duplicate dimension: {dimension}")
                    else:
                        valid_dimensions.add(dimension)
            if isinstance(raw_scenario_id, str):
                scenario_dimensions[raw_scenario_id] = valid_dimensions

            review_mode = scenario.get("review_mode")
            if review_mode not in REVIEW_MODES:
                errors.append(
                    f"{prefix} review_mode must be one of: "
                    f"{', '.join(sorted(REVIEW_MODES))}"
                )
            errors.extend(
                _check_evidence_source(
                    scenario,
                    prefix=prefix,
                    figma_requires_node=False,
                    allowed_origins=(
                        frozenset({"figma", "requirement", "project", "user-decision"})
                        if effective_mode == "figma"
                        else frozenset({"requirement", "project", "user-decision"})
                    ),
                )
            )

            preview_sha256: Any | None = None
            if review_mode in {"visual", "both"}:
                preview_file, file_errors = _resolve_repo_relative_file(
                    repo_root,
                    scenario.get("preview_path"),
                    field="preview_path",
                    subreq_id=subreq_id,
                    unit_id=f"{unit_id} scenario {scenario_id}",
                    allowed_suffixes=preview_suffixes,
                )
                errors.extend(file_errors)
                preview_sha256 = scenario.get("preview_sha256")
                errors.extend(
                    _check_content_hash(
                        preview_file,
                        preview_sha256,
                        field="preview_sha256",
                        subreq_id=subreq_id,
                        unit_id=f"{unit_id} scenario {scenario_id}",
                    )
                )
            errors.extend(
                _check_confirmation(
                    scenario.get("confirmation"),
                    prefix=prefix,
                    preview_sha256=preview_sha256,
                )
            )

        for state_id in sorted(seen_state_ids - scenario_state_ids):
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} state {state_id} is not used by any scenario"
            )
        for profile_id in sorted(seen_profile_ids - scenario_profile_ids):
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} profile {profile_id} is not used by any scenario"
            )

        coverage = unit.get("coverage")
        if not isinstance(coverage, list):
            errors.append(f"[GATE] {subreq_id} unit {unit_id} coverage must be an array")
            coverage = []
        seen_coverage_dimensions: set[str] = set()
        covered_by_dimension: dict[str, set[str]] = {}
        for coverage_index, row in enumerate(coverage):
            fallback_coverage = f"coverage[{coverage_index}]"
            if not isinstance(row, dict):
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} {fallback_coverage} must be an object"
                )
                continue
            dimension = row.get("dimension")
            row_prefix = f"[GATE] {subreq_id} unit {unit_id} coverage {dimension}"
            if dimension not in COVERAGE_DIMENSIONS:
                errors.append(
                    f"{row_prefix} dimension must be one of: "
                    f"{', '.join(sorted(COVERAGE_DIMENSIONS))}"
                )
                continue
            if dimension in seen_coverage_dimensions:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} duplicate coverage dimension: "
                    f"{dimension}"
                )
                continue
            seen_coverage_dimensions.add(dimension)

            coverage_status = row.get("status")
            if coverage_status not in COVERAGE_STATUSES:
                errors.append(
                    f"{row_prefix} coverage status must be one of: "
                    f"{', '.join(sorted(COVERAGE_STATUSES))}"
                )
            scenario_ids = row.get("scenario_ids")
            valid_scenario_ids: set[str] = set()
            if not isinstance(scenario_ids, list):
                errors.append(f"{row_prefix} scenario_ids must be an array")
            else:
                for covered_scenario_id in scenario_ids:
                    if covered_scenario_id not in seen_scenario_ids:
                        errors.append(
                            f"{row_prefix} references unknown scenario {covered_scenario_id}"
                        )
                    elif covered_scenario_id in valid_scenario_ids:
                        errors.append(
                            f"{row_prefix} duplicate scenario_id: {covered_scenario_id}"
                        )
                    else:
                        valid_scenario_ids.add(covered_scenario_id)
            covered_by_dimension[dimension] = valid_scenario_ids
            if coverage_status == "covered" and not valid_scenario_ids:
                errors.append(f"{row_prefix} covered status requires scenario_ids")
            if coverage_status == "not_applicable":
                if valid_scenario_ids:
                    errors.append(
                        f"{row_prefix} not_applicable coverage cannot reference scenarios"
                    )
                if not _is_non_empty_string(row.get("note")):
                    errors.append(
                        f"{row_prefix} not_applicable coverage requires a note"
                    )

        for dimension in sorted(COVERAGE_DIMENSIONS - seen_coverage_dimensions):
            errors.append(
                f"[GATE] {subreq_id} unit {unit_id} missing coverage dimension: {dimension}"
            )
        for scenario_id, dimensions in scenario_dimensions.items():
            for dimension in dimensions:
                if scenario_id not in covered_by_dimension.get(dimension, set()):
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} scenario {scenario_id} "
                        f"dimension {dimension} is missing from coverage"
                    )
        for dimension, scenario_ids in covered_by_dimension.items():
            for scenario_id in scenario_ids:
                if dimension not in scenario_dimensions.get(scenario_id, set()):
                    errors.append(
                        f"[GATE] {subreq_id} unit {unit_id} coverage {dimension} "
                        f"references scenario {scenario_id} without that dimension"
                    )

    for unit_id, dependencies in dependency_records:
        for dependency in dependencies:
            if dependency not in seen_unit_ids:
                errors.append(
                    f"[GATE] {subreq_id} unit {unit_id} references unknown dependency {dependency}"
                )
    return errors


def _check_acceptance_file_evidence(
    evidence: dict[str, Any],
    *,
    prefix: str,
    repo_root: Path,
    subreq_id: str,
    scenario_id: str,
    indexed_preview_path: Any | None,
    indexed_preview_sha256: Any | None,
) -> list[str]:
    errors: list[str] = []
    kind = evidence.get("kind")
    if kind not in ACCEPTANCE_EVIDENCE_KINDS:
        return [
            f"{prefix} kind must be one of: "
            f"{', '.join(sorted(ACCEPTANCE_EVIDENCE_KINDS))}"
        ]
    if not _is_non_empty_string(evidence.get("summary")):
        errors.append(f"{prefix} summary is required")

    if kind in {"preview", "test"}:
        if kind == "preview" and (
            evidence.get("path") != indexed_preview_path
            or evidence.get("sha256") != indexed_preview_sha256
        ):
            errors.append(
                f"{prefix} preview evidence must match the indexed scenario preview"
            )
        allowed_suffixes = WEB_PREVIEW_SUFFIXES if kind == "preview" else None
        evidence_file, file_errors = _resolve_repo_relative_file(
            repo_root,
            evidence.get("path"),
            field="path",
            subreq_id=subreq_id,
            unit_id=f"visual acceptance scenario {scenario_id} evidence {kind}",
            allowed_suffixes=allowed_suffixes,
        )
        errors.extend(file_errors)
        errors.extend(
            _check_content_hash(
                evidence_file,
                evidence.get("sha256"),
                field="sha256",
                subreq_id=subreq_id,
                unit_id=f"visual acceptance scenario {scenario_id} evidence {kind}",
            )
        )
        if not _is_non_empty_string(evidence.get("command")):
            errors.append(f"{prefix} command is required")
    elif kind == "manual":
        if not _is_non_empty_string(evidence.get("reviewed_by")):
            errors.append(f"{prefix} reviewed_by is required")
        if not _is_iso8601_timestamp(evidence.get("reviewed_at")):
            errors.append(
                f"{prefix} reviewed_at must be an ISO-8601 timestamp with timezone"
            )
    elif kind == "image-diff":
        for role in ("reference", "candidate", "diff"):
            image_file, file_errors = _resolve_repo_relative_file(
                repo_root,
                evidence.get(f"{role}_path"),
                field=f"{role}_path",
                subreq_id=subreq_id,
                unit_id=f"visual acceptance scenario {scenario_id} image-diff",
                allowed_suffixes=IMAGE_SUFFIXES,
            )
            errors.extend(file_errors)
            errors.extend(
                _check_content_hash(
                    image_file,
                    evidence.get(f"{role}_sha256"),
                    field=f"{role}_sha256",
                    subreq_id=subreq_id,
                    unit_id=f"visual acceptance scenario {scenario_id} image-diff",
                )
            )
        if not _is_non_empty_string(evidence.get("metric")):
            errors.append(f"{prefix} metric is required")
        threshold = evidence.get("threshold")
        actual = evidence.get("actual")
        if not _is_finite_number(threshold) or threshold < 0:
            errors.append(f"{prefix} threshold must be a non-negative number")
        if not _is_finite_number(actual) or actual < 0:
            errors.append(f"{prefix} actual must be a non-negative number")
        elif _is_finite_number(threshold):
            if actual > threshold:
                errors.append(f"{prefix} actual must not exceed threshold")
        if not _is_non_empty_string(evidence.get("command")):
            errors.append(f"{prefix} command is required")
    return errors


def check_visual_acceptance(
    subreq_id: str, subreq_dir: Path, repo_root: Path, status: str
) -> list[str]:
    acceptance_path = subreq_dir / VISUAL_ACCEPTANCE_ARTIFACT
    if not acceptance_path.is_file():
        return [
            f"[GATE] {subreq_id} status={status} requires {VISUAL_ACCEPTANCE_ARTIFACT}"
        ]
    try:
        data = json.loads(acceptance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            f"[GATE] {subreq_id} cannot parse {VISUAL_ACCEPTANCE_ARTIFACT}: {exc}"
        ]
    if not isinstance(data, dict):
        return [f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} must be an object"]

    errors: list[str] = []
    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != VISUAL_ACCEPTANCE_SCHEMA_VERSION
    ):
        errors.append(
            f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} schema_version "
            f"must equal {VISUAL_ACCEPTANCE_SCHEMA_VERSION}"
        )
    if not _is_iso8601_timestamp(data.get("generated_at")):
        errors.append(
            f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} generated_at "
            "must be an ISO-8601 timestamp with timezone"
        )

    index_path = ui_truth_index_path(subreq_dir)
    errors.extend(
        _check_content_hash(
            index_path if index_path.is_file() else None,
            data.get("ui_truth_index_sha256"),
            field="ui_truth_index_sha256",
            subreq_id=subreq_id,
            unit_id="visual acceptance",
        )
    )

    expected_scenarios: dict[str, dict[str, Any]] = {}
    index = load_ui_truth_index(subreq_dir)
    if index:
        for unit in index.get("units", []):
            if not isinstance(unit, dict):
                continue
            for scenario in unit.get("scenarios", []):
                if not isinstance(scenario, dict):
                    continue
                scenario_id = scenario.get("scenario_id")
                review_mode = scenario.get("review_mode")
                if _is_non_empty_string(scenario_id) and review_mode in REVIEW_MODES:
                    expected_scenarios[scenario_id] = {
                        "review_mode": review_mode,
                        "preview_path": scenario.get("preview_path"),
                        "preview_sha256": scenario.get("preview_sha256"),
                    }

    scenario_results = data.get("scenarios")
    if not isinstance(scenario_results, list):
        errors.append(
            f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} scenarios must be an array"
        )
        scenario_results = []
    seen_scenarios: set[str] = set()
    for scenario_index, scenario_result in enumerate(scenario_results):
        fallback_scenario = f"scenarios[{scenario_index}]"
        if not isinstance(scenario_result, dict):
            errors.append(
                f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} "
                f"{fallback_scenario} must be an object"
            )
            continue
        scenario_id = scenario_result.get("scenario_id")
        prefix = f"[GATE] {subreq_id} visual acceptance scenario {scenario_id}"
        if not _is_non_empty_string(scenario_id):
            errors.append(f"{prefix} scenario_id is required")
            continue
        if scenario_id not in expected_scenarios:
            errors.append(f"{prefix} references unknown scenario {scenario_id}")
            continue
        if scenario_id in seen_scenarios:
            errors.append(f"{prefix} is duplicated")
            continue
        seen_scenarios.add(scenario_id)

        result = scenario_result.get("result")
        if result not in ACCEPTANCE_RESULTS:
            errors.append(
                f"{prefix} result must be one of: "
                f"{', '.join(sorted(ACCEPTANCE_RESULTS))}"
            )
        evidence_rows = scenario_result.get("evidence")
        if not isinstance(evidence_rows, list):
            errors.append(f"{prefix} evidence must be an array")
            evidence_rows = []

        evidence_kinds: set[str] = set()
        for evidence_index, evidence in enumerate(evidence_rows):
            evidence_prefix = f"{prefix} evidence[{evidence_index}]"
            if not isinstance(evidence, dict):
                errors.append(f"{evidence_prefix} must be an object")
                continue
            kind = evidence.get("kind")
            if kind in ACCEPTANCE_EVIDENCE_KINDS:
                evidence_kinds.add(kind)
            errors.extend(
                _check_acceptance_file_evidence(
                    evidence,
                    prefix=evidence_prefix,
                    repo_root=repo_root,
                    subreq_id=subreq_id,
                    scenario_id=scenario_id,
                    indexed_preview_path=expected_scenarios[scenario_id].get(
                        "preview_path"
                    ),
                    indexed_preview_sha256=expected_scenarios[scenario_id].get(
                        "preview_sha256"
                    ),
                )
            )

        if result == "passed":
            if not evidence_rows:
                errors.append(f"{prefix} passed result requires evidence")
            review_mode = expected_scenarios[scenario_id]["review_mode"]
            if review_mode in {"visual", "both"} and not (
                evidence_kinds & VISUAL_EVIDENCE_KINDS
            ):
                errors.append(f"{prefix} requires preview or image-diff evidence")
            if review_mode in {"behavior", "both"} and not (
                evidence_kinds & BEHAVIOR_EVIDENCE_KINDS
            ):
                errors.append(f"{prefix} requires test or manual evidence")
        elif result == "waived":
            if not _is_non_empty_string(scenario_result.get("note")):
                errors.append(f"{prefix} waiver note is required")
            if not _is_non_empty_string(scenario_result.get("waived_by")):
                errors.append(f"{prefix} waived_by is required")
            if not _is_iso8601_timestamp(scenario_result.get("waived_at")):
                errors.append(
                    f"{prefix} waived_at must be an ISO-8601 timestamp with timezone"
                )

    for scenario_id in sorted(set(expected_scenarios) - seen_scenarios):
        errors.append(
            f"[GATE] {subreq_id} {VISUAL_ACCEPTANCE_ARTIFACT} "
            f"missing scenario result: {scenario_id}"
        )
    return errors


DESIGN_ARTIFACT_STATUSES = frozenset(
    {
        "spec_ready",
        "plan_ready",
        "tasks_ready",
        "in_dev",
        "visual_acceptance_passed",
        "merged",
        "archived",
    }
)


def check_solution_design_artifact(
    subreq_id: str,
    subreq_dir: Path,
    status: str,
    entry: dict[str, Any],
    index: dict[str, Any] | None,
) -> list[str]:
    """Validate conditional design.md and scenario references.

    Runtime Coverage remains exclusively in the UI truth index. The solution
    design only needs to cite scenario IDs and assign implementation and
    verification responsibility.
    """
    mode = entry.get("design_mode")
    design_path = subreq_dir / "design.md"
    errors: list[str] = []
    if mode == "none":
        if design_path.is_file():
            errors.append(
                f"[DESIGN] {subreq_id} design_mode=none must not produce design.md"
            )
        return errors
    if mode in {"light", "full"} and entry.get("design_approved") is True and not design_path.is_file():
        errors.append(
            f"[DESIGN] {subreq_id} design_approved=true requires design.md"
        )
    if status in DESIGN_ARTIFACT_STATUSES and not design_path.is_file():
        errors.append(
            f"[DESIGN] {subreq_id} status={status} design_mode={mode} requires design.md"
        )
        return errors
    if not design_path.is_file() or index is None:
        return errors
    try:
        text = design_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"[DESIGN] {subreq_id} cannot read design.md: {exc}"]
    scenario_ids: list[str] = []
    for unit in index.get("units", []):
        if not isinstance(unit, dict):
            continue
        for scenario in unit.get("scenarios", []):
            if isinstance(scenario, dict) and _is_non_empty_string(scenario.get("scenario_id")):
                scenario_ids.append(scenario["scenario_id"])
    for scenario_id in sorted(set(scenario_ids)):
        if not _contains_identifier(text, scenario_id):
            errors.append(
                f"[DESIGN] {subreq_id} design.md must reference indexed scenario_id {scenario_id}"
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
    for field in sorted(LEGACY_MODE_FIELDS):
        if field in status_data:
            errors.append(f"[STATUS] legacy field {field} is forbidden")
    errors.extend(legacy_participation_errors(req_root))

    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            errors.append(f"[STATUS] sub_requirements.{subreq_id} must be a mapping")
            continue

        status = entry.get("status")
        if not isinstance(status, str):
            errors.append(f"[STATUS] sub_requirements.{subreq_id}.status missing")
            continue

        errors.extend(
            f"[STATUS] sub_requirements.{subreq_id}: {message}"
            for message in mode_errors(entry)
        )

        subreq_dir = req_root / "sub-requirements" / subreq_id
        index_file = ui_truth_index_path(subreq_dir)
        index = load_ui_truth_index(subreq_dir) if index_file.is_file() else None
        # Mode/artifact consistency is checked even for blocked slices. A
        # blocker may pause execution, but it must not preserve a removed
        # design bypass or a forged approval flag.
        errors.extend(
            check_solution_design_artifact(
                subreq_id, subreq_dir, status, entry, index
            )
        )

        truth_mode = entry.get("ui_truth_mode")

        if status == "acceptance_frozen" and truth_mode not in UI_TRUTH_CAPABILITY_MODES:
            errors.append(
                f"[STATUS] {subreq_id} acceptance_frozen is only valid for "
                "ui_truth_mode=figma or runtime-baseline"
            )
        if status == "visual_acceptance_passed" and truth_mode not in UI_TRUTH_CAPABILITY_MODES:
            errors.append(
                f"[STATUS] {subreq_id} visual_acceptance_passed is only valid for "
                "ui_truth_mode=figma or runtime-baseline"
            )
        if truth_mode not in UI_TRUTH_CAPABILITY_MODES and index_file.is_file():
            errors.append(
                f"[STATUS] {subreq_id} ui-truth-index.json is forbidden when "
                f"ui_truth_mode={truth_mode}"
            )
        if truth_mode not in UI_TRUTH_CAPABILITY_MODES and (
            subreq_dir / VISUAL_ACCEPTANCE_ARTIFACT
        ).is_file():
            errors.append(
                f"[STATUS] {subreq_id} visual-acceptance.json is forbidden when "
                f"ui_truth_mode={truth_mode}"
            )

        # A blocker pauses execution, but it does not make an invalid state or
        # a stale capability artifact legal. Keep post-freeze evidence checks
        # below the blocker boundary so blocked slices are still auditable
        # without requiring them to complete the paused capability.
        if status.startswith("blocked_"):
            continue

        if status in POST_FREEZE_STATUSES and truth_mode in UI_TRUTH_CAPABILITY_MODES:
            errors.extend(
                check_ui_truth_index(
                    subreq_id, subreq_dir, repo_root, status, expected_mode=truth_mode
                )
            )

        if status in VISUAL_ACCEPTANCE_STATUSES and truth_mode in UI_TRUTH_CAPABILITY_MODES:
            errors.extend(
                check_visual_acceptance(subreq_id, subreq_dir, repo_root, status)
            )

        if (
            entry.get("design_mode") in {"light", "full"}
            and status in DESIGN_ARTIFACT_STATUSES
            and entry.get("design_approved") is not True
        ):
            errors.append(
                f"[STATUS] {subreq_id} status={status} requires design_approved=true "
                f"for design_mode={entry.get('design_mode')}"
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
