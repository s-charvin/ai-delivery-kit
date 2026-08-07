#!/usr/bin/env python3
"""Reconcile requirement delivery state and emit next orchestrator action."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TERMINAL_STATUSES = frozenset({"merged"})
BLOCKED_PREFIX = "blocked_"
DESIGN_PENDING_STATUSES = frozenset({"split_ready", "acceptance_frozen"})

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
}


def is_blocked(status: str) -> bool:
    return status.startswith(BLOCKED_PREFIX)


def find_contracts(subreq_dir: Path) -> list[Path]:
    """Find every ui-contract.html under a sub-requirement (one per unit)."""
    if not subreq_dir.is_dir():
        return []
    return sorted(subreq_dir.rglob("ui-contract.html"))


def has_ui_artifacts(subreq_dir: Path) -> bool:
    return bool(find_contracts(subreq_dir))


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


def needs_design_approval(entry: dict, ui_bearing: bool) -> bool:
    if bool(entry.get("design_approved")):
        return False
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status):
        return False
    if status == "split_ready" and not ui_bearing:
        return True
    if status == "acceptance_frozen" and ui_bearing:
        return True
    return False


def load_dependency_graph(req_root: Path) -> dict[str, list[str]]:
    graph_path = req_root / "dependency-graph.json"
    if not graph_path.exists():
        return {}

    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    deps: dict[str, list[str]] = {}
    nodes = data.get("nodes") or data.get("sub_requirements") or data
    if isinstance(nodes, dict):
        for subreq_id, node in nodes.items():
            if isinstance(node, dict):
                raw = node.get("depends_on") or []
                deps[subreq_id] = list(raw) if isinstance(raw, list) else []
        return deps

    edges = data.get("edges")
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            subreq_id = edge.get("id") or edge.get("subreq_id")
            raw = edge.get("depends_on") or []
            if isinstance(subreq_id, str):
                deps[subreq_id] = list(raw) if isinstance(raw, list) else []
        return deps

    subreq_dirs = req_root / "sub-requirements"
    if subreq_dirs.is_dir():
        for child in sorted(subreq_dirs.iterdir()):
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


def dependencies_satisfied(
    subreq_id: str,
    sub_requirements: dict,
    deps: dict[str, list[str]],
) -> bool:
    for dep_id in deps.get(subreq_id, []):
        dep_entry = sub_requirements.get(dep_id)
        if not isinstance(dep_entry, dict):
            return False
        if dep_entry.get("status") != "merged":
            return False
    return True


def next_action_for_entry(entry: dict, ui_bearing: bool) -> str | None:
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status) or status in TERMINAL_STATUSES:
        return None

    design_approved = bool(entry.get("design_approved"))

    if status == "draft":
        return ACTION_BY_STATUS[("draft", None, False)]

    if status == "split_ready":
        if ui_bearing:
            return ACTION_BY_STATUS[("split_ready", True, False)]
        return ACTION_BY_STATUS[("split_ready", False, design_approved)]

    if status == "acceptance_frozen":
        return ACTION_BY_STATUS[("acceptance_frozen", True, design_approved)]

    if status in {"spec_ready", "plan_ready", "tasks_ready", "in_dev", "visual_acceptance_passed"}:
        if not design_approved and status not in {"in_dev", "visual_acceptance_passed"}:
            return "design"
        return ACTION_BY_STATUS.get((status, None, True))

    return None


def run_status_validator(
    status_path: Path,
    req_root: Path,
    validator_script: Path | None,
) -> list[str]:
    kit_root = Path(__file__).resolve().parents[4]
    candidates = [
        validator_script,
        kit_root / "scripts" / "validate-delivery-status.py",
        Path("scripts/validate-delivery-status.py"),
        Path(".ai-delivery/scripts/validate-delivery-status.py"),
    ]
    chosen = next((p.resolve() for p in candidates if p is not None and p.exists()), None)
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

    deps = load_dependency_graph(req_root)
    recorded_checkpoint = status_data.get("current_checkpoint")
    runnable: list[str] = []
    blocked: list[str] = []
    blocker_scopes: list[str] = []
    actionable: list[tuple[str, str]] = []
    design_pending: list[tuple[str, str]] = []
    dev_waiting: list[str] = []

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

        if needs_design_approval(entry, ui_bearing):
            design_pending.append((subreq_id, "design"))
            continue

        action = next_action_for_entry(entry, ui_bearing)
        if action:
            if status == "tasks_ready":
                # 进入开发必须经过 CP-001 门禁：tasks_ready 子需求先等待，
                # 待 all_tasks_ready 与已记录的 CP-001 确认后再放行。
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
    all_merged = all(
        isinstance(sub_requirements.get(sid), dict)
        and sub_requirements[sid].get("status") == "merged"
        for sid in executable
    ) if executable else False

    all_tasks_ready = bool(executable) and all(
        isinstance(sub_requirements.get(sid), dict)
        and sub_requirements[sid].get("status") == "tasks_ready"
        for sid in executable
    )

    # CP-001 凭证仅在“全部 tasks_ready 且用户确认已记录”时有效；
    # 回退后残留的旧确认不得再次授权 implement。
    dev_authorized = recorded_checkpoint == "CP-001" and all_tasks_ready
    for subreq_id in dev_waiting:
        if dev_authorized:
            runnable.append(f"{subreq_id}:tasks_ready->implement")
            actionable.append((subreq_id, "implement"))

    checkpoint = recorded_checkpoint

    if all_merged and executable:
        runtime_mode = "completed"
        checkpoint = None
    elif checkpoint == "CP-002":
        runtime_mode = "blocker_recovery"
    elif all_tasks_ready:
        runtime_mode = "confirm_to_dev"
        checkpoint = "CP-001"
    elif design_pending and not actionable:
        runtime_mode = "confirm_design"
        checkpoint = "CP-DESIGN"
    elif not runnable and blocked:
        runtime_mode = "blocker_recovery"
        checkpoint = checkpoint or "CP-002"
    else:
        runtime_mode = "resume"
        # 检查点只是守卫满足时的凭证：门禁回退后残留的 CP-001 不再
        # 授权 implement；设计待批则继续以 CP-DESIGN 提示，不阻塞其他
        # 无依赖的可运行项。
        checkpoint = "CP-DESIGN" if design_pending else None

    if runtime_mode == "completed":
        next_action = "none"
        next_subreq = None
    elif runtime_mode == "confirm_design" and design_pending:
        next_subreq, next_action = design_pending[0]
    elif runtime_mode == "confirm_to_dev":
        next_subreq = next((sid for sid in executable if sub_requirements[sid].get("status") == "tasks_ready"), None)
        # 仅当用户确认已记录在 status.json（CP-001）时才放行 implement。
        next_action = "implement" if recorded_checkpoint == "CP-001" else "none"
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
