"""Bridge between ai-delivery-orchestrator status.json and coordination pipelines.

The skill layer owns spec-segment statuses (draft … tasks_ready, archived).
The coordination engine owns an execution view (in_dev / merged / blocked_*).
``load_requirement`` materialises sub-requirements as pipeline nodes;
``flush_back`` writes only execution-segment statuses back to status.json,
then runs reconcile so the skill layer re-derives next actions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.constants import PARTICIPATION_PROFILES
from orchestration.models import (
    DepDeclaration,
    DepPresence,
    NodeDef,
    NodeState,
    NodeStatus,
    ParticipationProfile,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)

# --- frozen bidirectional mapping (tested) ------------------------------------

SPEC_SEGMENT_STATUSES: frozenset[str] = frozenset(
    {
        "draft",
        "split_ready",
        "acceptance_frozen",
        "spec_ready",
        "plan_ready",
        "tasks_ready",
        "archived",
    }
)

EXECUTION_SEGMENT_STATUSES: frozenset[str] = frozenset(
    {
        "in_dev",
        "visual_acceptance_passed",
        "merged",
        "blocked_missing_requirement",
        "blocked_requirement_conflict",
        "blocked_dependency",
        "blocked_missing_design",
        "blocked_requirement_figma_conflict",
        "blocked_figma_conflict",
        "blocked_missing_state_code",
        "blocked_missing_visual_truth",
        "blocked_spec_mismatch",
        "blocked_dependency_slice",
        "blocked_merge_conflict",
        "blocked_verification_failure",
    }
)

SKILL_TO_NODE_STATUS: dict[str, NodeStatus] = {
    "draft": NodeStatus.BLOCKED,
    "split_ready": NodeStatus.BLOCKED,
    "acceptance_frozen": NodeStatus.BLOCKED,
    "spec_ready": NodeStatus.BLOCKED,
    "plan_ready": NodeStatus.BLOCKED,
    "tasks_ready": NodeStatus.READY,
    "in_dev": NodeStatus.IN_PROGRESS,
    "visual_acceptance_passed": NodeStatus.IN_PROGRESS,
    "merged": NodeStatus.DONE,
    "archived": NodeStatus.DONE,
    "blocked_missing_requirement": NodeStatus.BLOCKED,
    "blocked_requirement_conflict": NodeStatus.BLOCKED,
    "blocked_dependency": NodeStatus.BLOCKED,
    "blocked_missing_design": NodeStatus.BLOCKED,
    "blocked_requirement_figma_conflict": NodeStatus.BLOCKED,
    "blocked_figma_conflict": NodeStatus.BLOCKED,
    "blocked_missing_state_code": NodeStatus.BLOCKED,
    "blocked_missing_visual_truth": NodeStatus.BLOCKED,
    "blocked_spec_mismatch": NodeStatus.BLOCKED,
    "blocked_dependency_slice": NodeStatus.BLOCKED,
    "blocked_merge_conflict": NodeStatus.BLOCKED,
    "blocked_verification_failure": NodeStatus.BLOCKED,
}

NODE_TO_SKILL_STATUS: dict[NodeStatus, str] = {
    NodeStatus.IN_PROGRESS: "in_dev",
    NodeStatus.DONE: "merged",
}


@dataclass
class SkillBridgeContext:
    repo_root: Path
    req_root: Path
    req_id: str
    skill_status_by_node: dict[str, str] = field(default_factory=dict)


class SkillBridgeError(ValueError):
    """Raised when skill ↔ node mapping cannot be resolved."""


def is_blocked_skill_status(status: str) -> bool:
    return status.startswith("blocked_")


def skill_status_to_node_status(skill_status: str) -> NodeStatus:
    if skill_status not in SKILL_TO_NODE_STATUS:
        raise SkillBridgeError(f"unknown skill status: {skill_status!r}")
    return SKILL_TO_NODE_STATUS[skill_status]


def node_status_to_skill_status(
    node_status: NodeStatus,
    *,
    prior_skill_status: str | None = None,
) -> str | None:
    """Map a pipeline node status back to a skill status for flush_back.

    Returns ``None`` when the skill layer should keep the current status
    (spec segment or unmapped node states like READY/BLOCKED spec-phase).
    """
    if node_status == NodeStatus.BLOCKED and prior_skill_status:
        if is_blocked_skill_status(prior_skill_status):
            return prior_skill_status
        return None
    return NODE_TO_SKILL_STATUS.get(node_status)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _find_reconcile_script(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / ".agents" / "skills" / "ai-delivery-orchestrator" / "scripts" / "reconcile-delivery.py",
        repo_root / ".agents-zh" / "skills" / "ai-delivery-orchestrator" / "scripts" / "reconcile-delivery.py",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def _node_type_for_subreq(entry: dict[str, Any]) -> str:
    ui_bearing = entry.get("ui_bearing")
    if ui_bearing is True:
        return "client_ui_impl"
    return "server_impl"


def _load_dependency_graph(req_root: Path) -> dict[str, list[str]]:
    graph_path = req_root / "dependency-graph.json"
    if not graph_path.is_file():
        return {}
    data = _read_json(graph_path)
    deps: dict[str, list[str]] = {}
    for node in data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        sr_id = node.get("subreq_id")
        if not isinstance(sr_id, str):
            continue
        raw = node.get("depends_on", [])
        deps[sr_id] = [d for d in raw if isinstance(d, str)]
    return deps


def load_requirement(req_root: Path | str, *, repo_root: Path | str | None = None) -> tuple[
    PipelineDefinition,
    PipelineState,
    SkillBridgeContext,
]:
    """Load a requirement directory into a coordination pipeline view."""
    req_root = Path(req_root).resolve()
    if repo_root is None:
        repo_root = req_root.parent.parent.parent
    repo_root = Path(repo_root).resolve()

    status_path = req_root / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError(f"missing status.json: {status_path}")

    status_data = _read_json(status_path)
    req_id = status_data.get("requirement_id")
    if not isinstance(req_id, str) or not req_id:
        req_id = req_root.name

    subreqs = status_data.get("sub_requirements", {})
    if not isinstance(subreqs, dict) or not subreqs:
        raise SkillBridgeError(f"no sub_requirements in {status_path}")

    dep_graph = _load_dependency_graph(req_root)
    profile: ParticipationProfile = PARTICIPATION_PROFILES["fullstack"]
    nodes: list[NodeDef] = []
    node_states: dict[str, NodeState] = {}
    skill_status_by_node: dict[str, str] = {}

    for sr_id, entry in subreqs.items():
        if not isinstance(entry, dict):
            raise SkillBridgeError(f"invalid subreq entry for {sr_id!r}")
        skill_status = entry.get("status")
        if not isinstance(skill_status, str):
            raise SkillBridgeError(f"missing status for subreq {sr_id!r}")

        skill_status_by_node[sr_id] = skill_status
        node_status = skill_status_to_node_status(skill_status)
        upstreams = dep_graph.get(sr_id, [])
        deps = [
            DepDeclaration(upstream=u, presence=DepPresence.REQUIRED)
            for u in upstreams
        ]
        nodes.append(
            NodeDef(
                node_id=sr_id,
                node_type=_node_type_for_subreq(entry),
                deps=deps,
            )
        )
        node_states[sr_id] = NodeState(node_id=sr_id, status=node_status)

    pipeline_id = req_id
    now = _now_iso()
    pipeline_def = PipelineDefinition(
        id=pipeline_id,
        name=pipeline_id,
        nodes=nodes,
        profile=profile,
        root_product_node_id=nodes[0].node_id if nodes else None,
    )
    pipeline_state = PipelineState(
        pipeline_id=pipeline_id,
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        node_states=node_states,
        profile_id=profile.id,
    )
    ctx = SkillBridgeContext(
        repo_root=repo_root,
        req_root=req_root,
        req_id=req_id,
        skill_status_by_node=skill_status_by_node,
    )
    return pipeline_def, pipeline_state, ctx


def flush_back(
    state: PipelineState,
    ctx: SkillBridgeContext,
    *,
    run_reconcile: bool = True,
) -> dict[str, Any]:
    """Write execution-segment statuses from *state* back to status.json."""
    status_path = ctx.req_root / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError(f"missing status.json: {status_path}")

    data = _read_json(status_path)
    subreqs = data.get("sub_requirements", {})
    if not isinstance(subreqs, dict):
        raise SkillBridgeError("status.json sub_requirements is not an object")

    updated: list[str] = []
    skipped: list[str] = []

    for sr_id, ns in state.node_states.items():
        entry = subreqs.get(sr_id)
        if not isinstance(entry, dict):
            continue
        current_skill = entry.get("status")
        if not isinstance(current_skill, str):
            continue

        node_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        prior = ctx.skill_status_by_node.get(sr_id, current_skill)
        new_skill = node_status_to_skill_status(node_status, prior_skill_status=prior)

        if new_skill is None:
            skipped.append(sr_id)
            continue
        if new_skill not in EXECUTION_SEGMENT_STATUSES:
            skipped.append(sr_id)
            continue
        if new_skill == current_skill:
            skipped.append(sr_id)
            continue

        entry["status"] = new_skill
        ctx.skill_status_by_node[sr_id] = new_skill
        updated.append(sr_id)

    data["updated_at"] = _now_iso()
    _write_json(status_path, data)

    reconcile_output: str | None = None
    if run_reconcile and updated:
        reconcile_output = _run_reconcile(ctx)

    return {
        "updated_subreqs": updated,
        "skipped_subreqs": skipped,
        "reconcile_output": reconcile_output,
    }


def _run_reconcile(ctx: SkillBridgeContext) -> str | None:
    script = _find_reconcile_script(ctx.repo_root)
    if script is None:
        return None
    status_path = ctx.req_root / "status.json"
    proc = subprocess.run(
        [sys.executable, str(script), str(status_path), "--req-root", str(ctx.req_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "") + (proc.stderr or "")
