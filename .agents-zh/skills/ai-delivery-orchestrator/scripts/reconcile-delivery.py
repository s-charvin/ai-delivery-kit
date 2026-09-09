#!/usr/bin/env python3
"""Reconcile requirement delivery state and emit next orchestrator action."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Resolve the sibling layout resolver (single source of truth for artifact paths
# and for the one normalize/hash implementation behind drift detection).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import resolve_validator_script, spec_drift  # noqa: E402
from design_contract import validate_design_entry  # noqa: E402

TERMINAL_STATUSES = frozenset({"archived"})
BLOCKED_PREFIX = "blocked_"
DESIGN_PENDING_STATUSES = frozenset({"split_ready", "acceptance_frozen", "spec_ready", "plan_ready", "tasks_ready"})
DESIGN_GATE_STATUSES = DESIGN_PENDING_STATUSES | frozenset(
    {"in_dev", "visual_acceptance_passed", "merged"}
)
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
UI_TRUTH_MODES = frozenset({"none", "existing", "runtime-baseline", "figma"})
UI_TRUTH_CAPABILITY_MODES = frozenset({"runtime-baseline", "figma"})
DESIGN_MODES = frozenset({"none", "light", "full"})
LEGACY_MODE_FIELDS = frozenset({"ui_contract_exempt", "no_design_client"})

# spec-kit living-spec persistence: once derived artifacts exist, a changed
# spec.md makes plan/tasks stale. Report from plan_ready onwards; only send the
# pipeline back where nothing has been implemented yet (downgrade set) —
# forcing a downgrade mid-development would discard real work instead.
DRIFT_CHECK_STATUSES = frozenset(
    {"plan_ready", "tasks_ready", "in_dev", "visual_acceptance_passed"}
)
DRIFT_DOWNGRADE_STATUSES = frozenset({"plan_ready", "tasks_ready"})

# Abstract stage actions only. Framework-specific tooling is resolved at
# runtime via references/framework-adaptation.md — reconcile stays a pure
# state machine and never hard-codes third-party skill names.
ACTION_BY_STATUS: dict[str, str] = {
    "draft": "requirement-breakdown",
    "spec_ready": "plan",
    "plan_ready": "tasks",
    "tasks_ready": "implement",
    "in_dev": "implement",
    "visual_acceptance_passed": "finish",
    "merged": "archive",
}


def is_blocked(status: str) -> bool:
    return status.startswith(BLOCKED_PREFIX)


def find_ui_truth_index(subreq_dir: Path) -> Path | None:
    """Return the ui-truth-index.json path if it exists under a sub-requirement."""
    if not subreq_dir.is_dir():
        return None
    index = subreq_dir / "contracts" / "ui-truth-index.json"
    return index if index.is_file() else None


def has_ui_artifacts(subreq_dir: Path) -> bool:
    return find_ui_truth_index(subreq_dir) is not None


def ui_truth_mode(entry: dict) -> str | None:
    value = entry.get("ui_truth_mode")
    return value if isinstance(value, str) else None


def design_mode(entry: dict) -> str | None:
    value = entry.get("design_mode")
    return value if isinstance(value, str) else None


def requires_ui_truth(entry: dict) -> bool:
    return ui_truth_mode(entry) in UI_TRUTH_CAPABILITY_MODES


def infer_ui_bearing(entry: dict, subreq_dir: Path | None = None) -> bool:
    """Return the declared surface flag; modes, not artifacts, drive routing.

    The optional directory argument is retained for callers that imported the
    old helper, but no longer infers a UI surface from generated artifacts.
    """
    return entry.get("ui_bearing") is True


def mode_errors(entry: dict, *, strict_design: bool = False) -> list[str]:
    """Return deterministic mode/legacy-field errors for one status entry."""
    errors: list[str] = []
    def legacy_keys(value: object) -> set[str]:
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
        if field == "ui_contract_exempt":
            errors.append("legacy field ui_contract_exempt is forbidden")
        else:
            errors.append(f"legacy field {field} is forbidden")
    bearing = entry.get("ui_bearing")
    truth = ui_truth_mode(entry)
    design = design_mode(entry)
    if type(bearing) is not bool:
        errors.append("[MODE] ui_bearing must be a boolean")
    if truth not in UI_TRUTH_MODES:
        errors.append(
            "[MODE] ui_truth_mode must be one of: "
            + ", ".join(sorted(UI_TRUTH_MODES))
        )
    if design not in DESIGN_MODES:
        errors.append(
            "[MODE] design_mode must be one of: "
            + ", ".join(sorted(DESIGN_MODES))
        )
    if type(entry.get("design_approved")) is not bool:
        errors.append("[MODE] design_approved must be a boolean")
    elif design == "none" and entry.get("design_approved") is True:
        errors.append("[MODE] design_mode=none cannot set design_approved=true")
    if strict_design or "state_flow_required" in entry:
        state_flow_required = entry.get("state_flow_required")
        if type(state_flow_required) is not bool:
            errors.append("[MODE] state_flow_required must be a boolean")
        elif state_flow_required and design != "full":
            errors.append("[MODE] state_flow_required=true requires design_mode=full")
    if strict_design and "design_review" not in entry:
        errors.append("[MODE] design_review object is required")
    if isinstance(bearing, bool) and isinstance(truth, str) and truth in UI_TRUTH_MODES:
        expected = truth != "none"
        if bearing != expected:
            errors.append(
                f"[MODE] ui_bearing={str(bearing).lower()} is inconsistent with "
                f"ui_truth_mode={truth} (expected {str(expected).lower()})"
            )
    return errors


def design_gate_satisfied(entry: dict, subreq_dir: Path | None = None) -> bool:
    """Whether solution-design work is complete for the selected mode."""
    mode = design_mode(entry)
    if mode == "none":
        return True
    if entry.get("design_approved") is not True:
        return False
    # A status flag cannot stand in for the canonical artifact. This check is
    # kept in reconcile as well as the validator so an unseeded invocation
    # cannot silently skip the solution-design action.
    if subreq_dir is None or not (subreq_dir / "design.md").is_file():
        return subreq_dir is None
    return not validate_design_entry(
        entry,
        subreq_dir,
        status=entry.get("status", ""),
        legacy_allowed=entry.get("status") in {"merged", "archived"},
    )


def solution_design_pending(entry: dict, subreq_dir: Path | None = None) -> bool:
    return design_mode(entry) in {"light", "full"} and not design_gate_satisfied(
        entry, subreq_dir
    )


def design_artifact_errors(entry: dict, subreq_dir: Path, status: str) -> list[str]:
    """Reject stale/forged design artifacts independently of the validator."""
    mode = design_mode(entry)
    design_path = subreq_dir / "design.md"
    if mode == "none":
        if design_path.is_file():
            return ["design_mode=none must not produce design.md"]
        return []
    if mode not in {"light", "full"}:
        return []
    if status in DESIGN_ARTIFACT_STATUSES and not design_path.is_file():
        return [f"status={status} requires design.md"]
    if entry.get("design_approved") is True and not design_path.is_file():
        return ["design_approved=true requires design.md"]
    if entry.get("design_approved") is True:
        return validate_design_entry(
            entry,
            subreq_dir,
            status=status,
            legacy_allowed=status in {"merged", "archived"},
        )
    return []


def _load_legacy_dependency_json(req_root: Path) -> dict[str, list[str]]:
    """Fallback when dependency-graph.json is absent (legacy per-subreq files)."""
    deps: dict[str, list[str]] = {}
    subreq_dirs = req_root / "sub-requirements"
    if not subreq_dirs.is_dir():
        return deps
    for child in sorted(subreq_dirs.iterdir()):
        if not child.is_dir():
            continue
        dep_file = child / "dependency.json"
        if not dep_file.exists():
            continue
        try:
            dep_data = json.loads(dep_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw = dep_data.get("depends_on") or []
        deps[child.name] = list(raw) if isinstance(raw, list) else []
    return deps


def load_dependency_graph(req_root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Load deps from canonical dependency-graph.json; legacy fallback with WARN.

    When ``dependency-graph.json`` exists it is the sole source (per-subreq
    ``dependency.json`` is ignored). When missing, scan legacy files and emit
    a ``[WARN]`` so callers can surface the layout drift.
    """
    warnings: list[str] = []
    graph_path = req_root / "dependency-graph.json"
    if not graph_path.exists():
        deps = _load_legacy_dependency_json(req_root)
        if deps:
            warnings.append(
                "[WARN] legacy dependency.json: dependency-graph.json missing; "
                "using per-subreq dependency.json (derived view)"
            )
        return deps, warnings

    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, warnings

    deps: dict[str, list[str]] = {}
    nodes = data.get("nodes") or data.get("sub_requirements") or data
    if isinstance(nodes, dict):
        for subreq_id, node in nodes.items():
            if isinstance(node, dict):
                raw = node.get("depends_on") or []
                deps[subreq_id] = list(raw) if isinstance(raw, list) else []
        return deps, warnings

    edges = data.get("edges")
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            subreq_id = edge.get("id") or edge.get("subreq_id")
            raw = edge.get("depends_on") or []
            if isinstance(subreq_id, str):
                deps[subreq_id] = list(raw) if isinstance(raw, list) else []
        return deps, warnings

    return deps, warnings


def legacy_participation_errors(req_root: Path) -> list[str]:
    """Reject removed routing fields and participation profiles."""
    def legacy_keys(value: object) -> set[str]:
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

    def has_legacy_profile(value: object) -> bool:
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


def dependencies_satisfied(
    subreq_id: str,
    sub_requirements: dict,
    deps: dict[str, list[str]],
) -> bool:
    for dep_id in deps.get(subreq_id, []):
        dep_entry = sub_requirements.get(dep_id)
        if not isinstance(dep_entry, dict):
            return False
        if dep_entry.get("status") not in {"merged", "archived"}:
            return False
    return True


def next_action_for_entry(
    entry: dict,
    ui_bearing: bool | None = None,
    subreq_dir: Path | None = None,
) -> str | None:
    """Derive the next abstract action from status and the two capability axes."""
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status) or status in TERMINAL_STATUSES:
        return None

    truth = ui_truth_mode(entry)
    mode = design_mode(entry)
    if truth not in UI_TRUTH_MODES or mode not in DESIGN_MODES:
        return None
    if subreq_dir is not None:
        artifact_errors = design_artifact_errors(entry, subreq_dir, status)
        # An unapproved light/full design is recoverable: dispatch the
        # solution-design action so it can create the missing artifact and
        # complete its review. Contradictory none-mode artifacts and forged
        # approvals remain fail-closed.
        recoverable_design_error = any(
            "hash does not match" in message
            or "review_mode" in message
            or "reviewed_design_sha256" in message
            or "reviewed_at" in message
            or "reviewed_by" in message
            for message in artifact_errors
        )
        if artifact_errors and not (
            mode in {"light", "full"}
            and (entry.get("design_approved") is False or recoverable_design_error)
        ):
            return None

    if status == "draft":
        return ACTION_BY_STATUS["draft"]

    if status in {"split_ready", "acceptance_frozen", "spec_ready"}:
        # The visual capability must finish before any solution/spec work.
        if status == "split_ready" and truth in UI_TRUTH_CAPABILITY_MODES:
            return "ui-truth-mapping"
        if status == "acceptance_frozen" and truth not in UI_TRUTH_CAPABILITY_MODES:
            return None
        if solution_design_pending(entry, subreq_dir):
            return "solution-design"
        if status == "spec_ready":
            return ACTION_BY_STATUS["spec_ready"]
        return "spec"

    if status == "plan_ready":
        if solution_design_pending(entry, subreq_dir):
            return "solution-design"
        return ACTION_BY_STATUS["plan_ready"]

    if status in {"tasks_ready", "in_dev"}:
        if solution_design_pending(entry, subreq_dir):
            return "solution-design"
        return ACTION_BY_STATUS[status]

    if status == "visual_acceptance_passed":
        if truth not in UI_TRUTH_CAPABILITY_MODES:
            return None
        if solution_design_pending(entry, subreq_dir):
            return "solution-design"
        return ACTION_BY_STATUS["visual_acceptance_passed"]

    if status == "merged":
        if solution_design_pending(entry, subreq_dir):
            return "solution-design"
        return ACTION_BY_STATUS["merged"]

    return None


def run_status_validator(
    status_path: Path,
    req_root: Path,
    validator_script: Path | None,
) -> list[str]:
    chosen = resolve_validator_script(req_root, validator_script=validator_script)
    if chosen is None:
        return []

    result = subprocess.run(
        [sys.executable, str(chosen), str(status_path), "--req-root", str(req_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout or "") + (result.stderr or "")
    return [line for line in output.splitlines() if line.strip()]


def reconcile(
    status_path: Path,
    req_root: Path,
    validator_script: Path | None = None,
) -> dict:
    errors: list[str] = []

    if not status_path.exists():
        return {
            "runtime_mode": "bootstrap",
            "checkpoint": None,
            "runnable": [],
            "blocked": [],
            "blocker_scopes": [],
            "next_action": "requirement-breakdown",
            "next_subreq": None,
            "errors": ["status.json missing"],
        }

    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "runtime_mode": "bootstrap",
            "checkpoint": None,
            "runnable": [],
            "blocked": [],
            "blocker_scopes": [],
            "next_action": "requirement-breakdown",
            "next_subreq": None,
            "errors": [f"cannot read status.json: {exc}"],
        }

    sub_requirements = status_data.get("sub_requirements")
    if not isinstance(sub_requirements, dict) or not sub_requirements:
        return {
            "runtime_mode": "bootstrap",
            "checkpoint": status_data.get("current_checkpoint"),
            "runnable": [],
            "blocked": [],
            "blocker_scopes": [],
            "next_action": "requirement-breakdown",
            "next_subreq": None,
            "errors": [],
        }

    validation_errors = run_status_validator(status_path, req_root, validator_script)
    errors.extend(validation_errors)
    legacy_errors = legacy_participation_errors(req_root)
    errors.extend(legacy_errors)
    metadata_invalid = bool(legacy_errors)

    deps, dep_warnings = load_dependency_graph(req_root)
    errors.extend(dep_warnings)
    recorded_checkpoint = status_data.get("current_checkpoint")
    runnable: list[str] = []
    blocked: list[str] = []
    blocker_scopes: list[str] = []
    actionable: list[tuple[str, str]] = []
    ui_waiting: list[str] = []
    ui_authorized: list[str] = []
    design_pending: list[tuple[str, str]] = []
    dev_waiting: list[str] = []
    archive_pending: list[str] = []
    downgraded: set[str] = set()
    invalid_mode_subreqs: set[str] = set()
    invalid_artifact_subreqs: set[str] = set()

    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not isinstance(status, str):
            continue

        # Validate mode fields before blocker/dependency short-circuits. A
        # blocked or waiting slice must not become a storage path for removed
        # bypass fields or an invalid capability combination.
        entry_mode_errors = mode_errors(
            entry,
            strict_design=status_data.get("_schema") == "1.1",
        )
        if (
            status_data.get("_schema", "legacy") in {"legacy", "1.0"}
            and status not in {"merged", "archived"}
            and ("state_flow_required" not in entry or "design_review" not in entry)
        ):
            entry_mode_errors.append(
                "active legacy status requires migration to schema 1.1"
            )
        if entry_mode_errors:
            invalid_mode_subreqs.add(subreq_id)
            errors.extend(f"[MODE] {subreq_id}: {message}" for message in entry_mode_errors)

        subreq_dir = req_root / "sub-requirements" / subreq_id
        artifact_errors = design_artifact_errors(entry, subreq_dir, status)
        if artifact_errors:
            invalid_artifact_subreqs.add(subreq_id)
            errors.extend(f"[DESIGN] {subreq_id}: {message}" for message in artifact_errors)

        if is_blocked(status):
            blocked.append(f"{subreq_id}:{status}")
            scope = entry.get("blocker_scope")
            if isinstance(scope, str) and scope:
                blocker_scopes.append(f"{subreq_id}:{scope}")
            continue

        if status in TERMINAL_STATUSES:
            continue

        if not dependencies_satisfied(subreq_id, sub_requirements, deps):
            continue

        if entry_mode_errors:
            continue
        truth = ui_truth_mode(entry)
        mode = design_mode(entry)
        ui_bearing = infer_ui_bearing(entry, subreq_dir)
        # A mode=none artifact is contradictory, so stop that slice instead
        # of routing it into the pipeline. Missing light/full artifacts remain
        # recoverable through the solution-design action.
        if artifact_errors and mode == "none":
            continue

        if status in DRIFT_CHECK_STATUSES:
            for message in spec_drift(subreq_dir):
                if status in DRIFT_DOWNGRADE_STATUSES:
                    errors.append(
                        f"[DRIFT] {subreq_id}: {message} — living spec changed; "
                        f"downgraded to spec_ready, regenerate plan/tasks "
                        f"(record superseded decisions in decisions.md first)"
                    )
                    downgraded.add(subreq_id)
                else:
                    errors.append(
                        f"[DRIFT] {subreq_id}: {message} — living spec changed "
                        f"after {status}; re-align the derived artifacts before merge"
                    )
            if subreq_id in downgraded:
                # Re-derive the action from spec_ready without touching status.json:
                # reconcile is a pure deriver, writing status is a skill-layer action.
                status = "spec_ready"
                entry = {**entry, "status": status}

        # A full solution design pauses for CP-DESIGN. Light mode remains
        # runnable so the action can write its short record and self-approve.
        if (
            mode == "full"
            and solution_design_pending(entry, subreq_dir)
            and status in DESIGN_GATE_STATUSES
            and not (status == "split_ready" and truth in UI_TRUTH_CAPABILITY_MODES)
        ):
            design_pending.append((subreq_id, "solution-design"))
            continue
        action = next_action_for_entry(entry, ui_bearing, subreq_dir)
        if action:
            if action == "archive":
                # merged -> archive is a pure housekeeping action; it must not
                # count as a "runnable" development task (so the runtime mode
                # resolves to `closing` rather than `resume`).
                archive_pending.append(subreq_id)
                runnable.append(f"{subreq_id}:{status}->{action}")
            elif action == "ui-truth-mapping":
                # Stage 2 writes production code. Require the explicit CP-UI
                # credential before exposing it as a runnable action.
                if recorded_checkpoint == "CP-UI":
                    ui_authorized.append(subreq_id)
                    runnable.append(f"{subreq_id}:{status}->{action}")
                    actionable.append((subreq_id, action))
                else:
                    ui_waiting.append(subreq_id)
            elif status == "tasks_ready" and action == "implement":
                # Development is gated by CP-001. Hold tasks_ready slices until
                # all_tasks_ready and a recorded CP-001 confirmation allow release.
                dev_waiting.append(subreq_id)
            else:
                runnable.append(f"{subreq_id}:{status}->{action}")
                actionable.append((subreq_id, action))

    executable = [
        sid
        for sid, entry in sub_requirements.items()
        if isinstance(entry, dict)
        and isinstance(entry.get("status"), str)
        and not is_blocked(entry["status"])
    ]
    all_archived = (
        not validation_errors
        and not metadata_invalid
        and not (invalid_mode_subreqs | invalid_artifact_subreqs)
        and all(
            isinstance(sub_requirements.get(sid), dict)
            and sub_requirements[sid].get("status") == "archived"
            for sid in executable
        )
    ) if executable else False

    # A drift-downgraded slice is no longer tasks_ready even though status.json
    # still says so — otherwise CP-001 would authorize development against a
    # stale plan/tasks pair.
    all_tasks_ready = (
        bool(executable)
        and not validation_errors
        and not metadata_invalid
        and not (invalid_mode_subreqs | invalid_artifact_subreqs)
        and not (downgraded & set(executable))
        and all(
            isinstance(sub_requirements.get(sid), dict)
            and sub_requirements[sid].get("status") == "tasks_ready"
            for sid in executable
        )
    )

    # CP-001 is valid only while every slice is tasks_ready, no solution-design
    # prerequisite is pending, and user confirmation is recorded. A stale
    # confirmation must not reauthorize implementation around a design gate.
    prerequisite_actionable = any(
        action != "implement" for _, action in actionable
    )
    dev_authorized = (
        recorded_checkpoint == "CP-001"
        and all_tasks_ready
        and not design_pending
        and not prerequisite_actionable
    )
    for subreq_id in dev_waiting:
        if dev_authorized:
            runnable.append(f"{subreq_id}:tasks_ready->implement")
            actionable.append((subreq_id, "implement"))

    checkpoint = recorded_checkpoint
    if all_archived and executable:
        runtime_mode = "completed"
        checkpoint = None
    elif archive_pending and not actionable:
        runtime_mode = "closing"
        checkpoint = "CP-ARCHIVE"
    elif checkpoint == "CP-002":
        runtime_mode = "blocker_recovery"
    elif ui_waiting and not actionable:
        runtime_mode = "confirm_ui"
        checkpoint = "CP-UI"
    elif design_pending and not actionable:
        runtime_mode = "confirm_solution_design"
        checkpoint = "CP-DESIGN"
    elif all_tasks_ready and not design_pending and not prerequisite_actionable:
        runtime_mode = "confirm_to_dev"
        checkpoint = "CP-001"
    elif not runnable and (
        blocked
        or invalid_mode_subreqs
        or invalid_artifact_subreqs
        or validation_errors
        or metadata_invalid
    ):
        runtime_mode = "blocker_recovery"
        checkpoint = checkpoint or "CP-002"
    else:
        runtime_mode = "resume"
        # A checkpoint is evidence only while its guard holds. A stale CP-001
        # after gate regression no longer authorizes implement; pending design
        # continues to surface CP-DESIGN without blocking other runnable items.
        if ui_waiting:
            checkpoint = "CP-UI"
        elif design_pending:
            checkpoint = "CP-DESIGN"
        elif ui_authorized:
            checkpoint = "CP-UI"
        else:
            checkpoint = None

    if runtime_mode == "completed":
        next_action = "none"
        next_subreq = None
    elif runtime_mode == "closing" and archive_pending:
        next_subreq, next_action = archive_pending[0], "archive"
    elif runtime_mode == "confirm_solution_design" and design_pending:
        next_subreq, next_action = design_pending[0]
    elif runtime_mode == "confirm_to_dev":
        next_subreq = next((sid for sid in executable if sub_requirements[sid].get("status") == "tasks_ready"), None)
        # Release implement only when status.json records user confirmation (CP-001).
        next_action = "implement" if recorded_checkpoint == "CP-001" else "none"
    elif runtime_mode == "confirm_ui":
        next_subreq = ui_waiting[0]
        next_action = "none"
    elif runtime_mode == "blocker_recovery":
        next_action = "none"
        if blocked:
            next_subreq = blocked[0].split(":", 1)[0]
        elif invalid_mode_subreqs:
            next_subreq = sorted(invalid_mode_subreqs)[0]
        elif invalid_artifact_subreqs:
            next_subreq = sorted(invalid_artifact_subreqs)[0]
        else:
            next_subreq = None
    elif actionable:
        next_subreq, next_action = actionable[0]
    else:
        next_action = "requirement-breakdown"
        next_subreq = next(iter(sub_requirements.keys()), None)

    return {
        "runtime_mode": runtime_mode,
        "checkpoint": checkpoint,
        "runnable": runnable,
        "blocked": blocked,
        "blocker_scopes": blocker_scopes,
        "next_action": next_action,
        "next_subreq": next_subreq,
        "errors": errors,
    }


def format_output(result: dict) -> str:
    lines = [
        f"RUNTIME_MODE={result['runtime_mode']}",
        f"CHECKPOINT={result['checkpoint']}",
        f"RUNNABLE={','.join(result['runnable']) if result['runnable'] else 'none'}",
        f"BLOCKED={','.join(result['blocked']) if result['blocked'] else 'none'}",
        f"BLOCKER_SCOPES={','.join(result['blocker_scopes']) if result['blocker_scopes'] else 'none'}",
        f"NEXT_ACTION={result['next_action']}",
        f"NEXT_SUBREQ={result['next_subreq']}",
    ]
    if result["errors"]:
        lines.append(f"ERRORS={'; '.join(result['errors'])}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("status", type=Path, help="Path to requirement-level status.json")
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
        help="Path to validate-delivery-status.py (optional)",
    )
    args = parser.parse_args()

    status_path = args.status.resolve()
    req_root = args.req_root.resolve() if args.req_root else status_path.parent.resolve()

    result = reconcile(status_path, req_root, args.validator)
    print(format_output(result))
    if not status_path.exists():
        return 0
    if result["runtime_mode"] == "completed":
        return 0
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
