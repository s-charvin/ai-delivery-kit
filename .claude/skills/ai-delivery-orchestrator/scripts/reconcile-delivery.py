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

STATUS_ORDER = [
    "draft",
    "split_ready",
    "acceptance_frozen",
    "spec_ready",
    "plan_ready",
    "tasks_ready",
    "in_dev",
    "visual_acceptance_passed",
    "merged",
]

SKILL_BY_STATUS: dict[tuple[str, bool | None, bool], str] = {
    ("draft", None, False): "requirement-breakdown",
    ("split_ready", True, False): "ui-truth-mapping",
    ("split_ready", False, False): "superpowers:brainstorming",
    ("split_ready", False, True): "speckit-specify",
    ("acceptance_frozen", True, False): "superpowers:brainstorming",
    ("acceptance_frozen", True, True): "speckit-specify",
    ("spec_ready", None, True): "speckit-plan",
    ("plan_ready", None, True): "speckit-tasks",
    ("tasks_ready", None, True): "stage-4-implementation",
    ("in_dev", None, True): "subagent-driven-development",
    ("visual_acceptance_passed", None, True): "finishing-a-development-branch",
}


def is_blocked(status: str) -> bool:
    return status.startswith(BLOCKED_PREFIX)


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


def next_skill_for_entry(entry: dict, ui_bearing: bool) -> str | None:
    status = entry.get("status")
    if not isinstance(status, str) or is_blocked(status) or status in TERMINAL_STATUSES:
        return None

    design_approved = bool(entry.get("design_approved"))

    if status == "draft":
        return SKILL_BY_STATUS[("draft", None, False)]

    if status == "split_ready":
        if ui_bearing:
            return SKILL_BY_STATUS[("split_ready", True, False)]
        key = ("split_ready", False, design_approved)
        return SKILL_BY_STATUS[key]

    if status == "acceptance_frozen":
        key = ("acceptance_frozen", True, design_approved)
        return SKILL_BY_STATUS[key]

    if status in {"spec_ready", "plan_ready", "tasks_ready", "in_dev", "visual_acceptance_passed"}:
        if not design_approved and status not in {"in_dev", "visual_acceptance_passed"}:
            return "superpowers:brainstorming"
        for key_status in STATUS_ORDER:
            if key_status == status:
                for key, skill in SKILL_BY_STATUS.items():
                    if key[0] == status:
                        return skill
        return None

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
            "next_skill": "requirement-breakdown",
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
            "next_skill": "requirement-breakdown",
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
            "next_skill": "requirement-breakdown",
            "next_subreq": None,
            "errors": [],
        }

    validation_errors = run_status_validator(status_path, req_root, validator_script)
    errors.extend(validation_errors)

    deps = load_dependency_graph(req_root)
    runnable: list[str] = []
    blocked: list[str] = []
    actionable: list[tuple[str, str]] = []

    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not isinstance(status, str):
            continue

        if is_blocked(status):
            blocked.append(f"{subreq_id}:{status}")
            continue

        if status in TERMINAL_STATUSES:
            continue

        if not dependencies_satisfied(subreq_id, sub_requirements, deps):
            continue

        subreq_dir = req_root / "sub-requirements" / subreq_id
        ui_bearing = infer_ui_bearing(entry, subreq_dir)
        skill = next_skill_for_entry(entry, ui_bearing)
        if skill:
            runnable.append(f"{subreq_id}:{status}->{skill}")
            actionable.append((subreq_id, skill))

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

    checkpoint = status_data.get("current_checkpoint")
    stored_mode = status_data.get("runtime_mode")

    if all_merged and executable:
        runtime_mode = "completed"
    elif checkpoint == "CP-001":
        runtime_mode = "confirm_to_dev"
    elif checkpoint == "CP-002":
        runtime_mode = "blocker_recovery"
    elif not runnable and blocked and not actionable:
        runtime_mode = "blocker_recovery" if checkpoint == "CP-002" else stored_mode or "resume"
    else:
        runtime_mode = stored_mode if stored_mode in {
            "bootstrap",
            "resume",
            "confirm_to_dev",
            "blocker_recovery",
            "completed",
        } else "resume"

    if runtime_mode == "completed":
        next_skill = None
        next_subreq = None
    elif actionable:
        next_subreq, next_skill = actionable[0]
    elif blocked:
        next_skill = "blocker-recovery"
        next_subreq = blocked[0].split(":", 1)[0]
    else:
        next_skill = "requirement-breakdown"
        next_subreq = next(iter(sub_requirements.keys()), None)

    return {
        "runtime_mode": runtime_mode,
        "checkpoint": checkpoint,
        "runnable": runnable,
        "blocked": blocked,
        "next_skill": next_skill,
        "next_subreq": next_subreq,
        "errors": errors,
    }


def format_output(result: dict) -> str:
    lines = [
        f"RUNTIME_MODE={result['runtime_mode']}",
        f"CHECKPOINT={result['checkpoint']}",
        f"RUNNABLE={','.join(result['runnable']) if result['runnable'] else 'none'}",
        f"BLOCKED={','.join(result['blocked']) if result['blocked'] else 'none'}",
        f"NEXT_SKILL={result['next_skill']}",
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
