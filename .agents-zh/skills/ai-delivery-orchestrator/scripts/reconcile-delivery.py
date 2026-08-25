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
from layout import resolve_validator_script, spec_drift, load_participation_profile  # noqa: E402

TERMINAL_STATUSES = frozenset({"archived"})
BLOCKED_PREFIX = "blocked_"
DESIGN_PENDING_STATUSES = frozenset({"split_ready", "acceptance_frozen"})

# spec-kit living-spec persistence: once derived artifacts exist, a changed
# spec.md makes plan/tasks stale. Report from plan_ready onwards; only send the
# pipeline back where nothing has been implemented yet (downgrade set) —
# forcing a downgrade mid-development would discard real work instead.
DRIFT_CHECK_STATUSES = frozenset(
    {"plan_ready", "tasks_ready", "in_dev", "visual_acceptance_passed"}
)
DRIFT_DOWNGRADE_STATUSES = frozenset({"plan_ready", "tasks_ready"})

# Participation profiles without a standing design/Figma resource (coordination
# participation-profiles.yaml: no_design_client).
PROFILES_WITHOUT_DESIGN = frozenset({"no_design_client"})

# Abstract stage actions only. Framework-specific tooling is resolved at
# runtime via references/framework-adaptation.md — reconcile stays a pure
# state machine and never hard-codes third-party skill names.
ACTION_BY_STATUS: dict[tuple[str, bool | None, bool], str] = {
    ("draft", None, False): "requirement-breakdown",
    ("split_ready", True, False): "ui-truth-mapping",
    ("split_ready", False, False): "design",
    ("split_ready", False, True): "spec",
    ("acceptance_frozen", True, False): "design",
    ("acceptance_frozen", True, True): "spec",
    ("spec_ready", None, True): "plan",
    ("plan_ready", None, True): "tasks",
    ("tasks_ready", None, True): "implement",
    ("in_dev", None, True): "implement",
    ("visual_acceptance_passed", None, True): "finish",
    ("merged", None, True): "archive",
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


def infer_ui_bearing(entry: dict, subreq_dir: Path) -> bool:
    ui_bearing = entry.get("ui_bearing")
    if ui_bearing is True:
        return True
    if ui_bearing is False:
        return False
    if has_ui_artifacts(subreq_dir):
        return True
    status = entry.get("status", "")
    if status in {"acceptance_frozen", "visual_acceptance_passed"}:
        return True
    return False


def needs_design_approval(entry: dict, ui_bearing: bool, participation: str) -> bool:
    if bool(entry.get("design_approved")):
        return False
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status):
        return False
    if participation in PROFILES_WITHOUT_DESIGN:
        if status == "split_ready" and not ui_bearing:
            return False
        if status == "acceptance_frozen" and ui_bearing:
            return False
    if status == "split_ready" and not ui_bearing:
        return True
    if status == "acceptance_frozen" and ui_bearing:
        return True
    return False


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


def next_action_for_entry(entry: dict, ui_bearing: bool, participation: str) -> str | None:
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status) or status in TERMINAL_STATUSES:
        return None

    design_approved = bool(entry.get("design_approved"))

    if status == "draft":
        return ACTION_BY_STATUS[("draft", None, False)]

    if status == "split_ready":
        if ui_bearing:
            if participation in PROFILES_WITHOUT_DESIGN:
                if entry.get("ui_contract_exempt"):
                    return ACTION_BY_STATUS[("split_ready", False, design_approved)]
                return "design"
            return ACTION_BY_STATUS[("split_ready", True, False)]
        if participation in PROFILES_WITHOUT_DESIGN:
            return "spec"
        return ACTION_BY_STATUS[("split_ready", False, design_approved)]

    if status == "acceptance_frozen":
        return ACTION_BY_STATUS[("acceptance_frozen", True, design_approved)]

    if status in {"spec_ready", "plan_ready", "tasks_ready", "in_dev", "visual_acceptance_passed", "merged"}:
        if (
            not design_approved
            and status not in {"in_dev", "visual_acceptance_passed", "merged"}
            and not (participation in PROFILES_WITHOUT_DESIGN and not ui_bearing)
        ):
            return "design"
        return ACTION_BY_STATUS.get((status, None, True))

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

    participation = load_participation_profile(req_root)
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

    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not isinstance(status, str):
            continue

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

        subreq_dir = req_root / "sub-requirements" / subreq_id
        ui_bearing = infer_ui_bearing(entry, subreq_dir)

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

        if needs_design_approval(entry, ui_bearing, participation):
            design_pending.append((subreq_id, "design"))
            continue

        action = next_action_for_entry(entry, ui_bearing, participation)
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
            elif status == "tasks_ready":
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
    all_archived = all(
        isinstance(sub_requirements.get(sid), dict)
        and sub_requirements[sid].get("status") == "archived"
        for sid in executable
    ) if executable else False

    # A drift-downgraded slice is no longer tasks_ready even though status.json
    # still says so — otherwise CP-001 would authorize development against a
    # stale plan/tasks pair.
    all_tasks_ready = (
        bool(executable)
        and not (downgraded & set(executable))
        and all(
            isinstance(sub_requirements.get(sid), dict)
            and sub_requirements[sid].get("status") == "tasks_ready"
            for sid in executable
        )
    )

    # CP-001 is valid only while every slice is tasks_ready and user confirmation
    # is recorded. A stale confirmation after rollback must not reauthorize implement.
    dev_authorized = recorded_checkpoint == "CP-001" and all_tasks_ready
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
    elif all_tasks_ready:
        runtime_mode = "confirm_to_dev"
        checkpoint = "CP-001"
    elif ui_waiting and not actionable:
        runtime_mode = "confirm_ui"
        checkpoint = "CP-UI"
    elif design_pending and not actionable:
        runtime_mode = "confirm_design"
        checkpoint = "CP-DESIGN"
    elif not runnable and blocked:
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
    elif runtime_mode == "confirm_design" and design_pending:
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
        next_subreq = blocked[0].split(":", 1)[0] if blocked else None
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
