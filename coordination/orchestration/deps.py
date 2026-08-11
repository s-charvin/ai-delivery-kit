from __future__ import annotations

from orchestration.models import (
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
)
from config.constants import ROLE_MAP


def _node_type_to_roles(node_type: str) -> list[str]:
    return ROLE_MAP.get(node_type, [])


def resolve_effective_deps(
    node_id: str,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> list[tuple[str, DepDeclaration]]:
    node_map: dict[str, NodeDef] = {n.node_id: n for n in pipeline_def.nodes}
    node = node_map.get(node_id)
    if node is None:
        return []

    roles_absent = set(pipeline_def.profile.roles_absent)
    result: list[tuple[str, DepDeclaration]] = []

    for dep in node.deps:
        up_id = dep.upstream
        presence = DepPresence(dep.presence) if isinstance(dep.presence, str) else dep.presence

        up_node = node_map.get(up_id)
        if up_node is None:
            if presence == DepPresence.IF_PRESENT:
                continue
            if presence == DepPresence.OPTIONAL:
                continue
            result.append((up_id, dep))
            continue

        up_roles = set(_node_type_to_roles(up_node.node_type))
        if up_roles & roles_absent:
            continue

        if presence == DepPresence.IF_PRESENT:
            result.append((up_id, dep))
        elif presence == DepPresence.REQUIRED:
            result.append((up_id, dep))
        elif presence == DepPresence.OPTIONAL:
            result.append((up_id, dep))

    return result


def is_ready(
    node_id: str,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> bool:
    node_states = state.node_states
    ns = node_states.get(node_id)
    if ns is None:
        return False

    current_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    if current_status in {
        NodeStatus.DONE,
        NodeStatus.DEPRECATED,
        NodeStatus.SUNSET,
        NodeStatus.SKIPPED,
    }:
        return False

    effective_deps = resolve_effective_deps(node_id, pipeline_def, state)

    for up_id, decl in effective_deps:
        up_state = node_states.get(up_id)
        if up_state is None:
            return False

        up_status = (
            NodeStatus(up_state.status)
            if isinstance(up_state.status, str)
            else up_state.status
        )
        presence = (
            DepPresence(decl.presence)
            if isinstance(decl.presence, str)
            else decl.presence
        )
        strictness = (
            DepStrictness(decl.strictness)
            if isinstance(decl.strictness, str)
            else decl.strictness
        )

        if presence == DepPresence.OPTIONAL and up_status in {
            NodeStatus.DEPRECATED,
            NodeStatus.SUNSET,
            NodeStatus.SKIPPED,
            NodeStatus.BLOCKED,
        }:
            continue

        if up_status in {
            NodeStatus.DEPRECATED,
            NodeStatus.SUNSET,
            NodeStatus.SKIPPED,
        } and presence in {DepPresence.REQUIRED, DepPresence.IF_PRESENT}:
            return False

        up_ok: bool
        if strictness == DepStrictness.STRICT:
            up_ok = up_status == NodeStatus.DONE
        else:
            up_ok = up_status in {NodeStatus.DONE, NodeStatus.DRAFT}

        if presence == DepPresence.OPTIONAL and up_status in {
            NodeStatus.DEPRECATED,
            NodeStatus.SUNSET,
            NodeStatus.SKIPPED,
            NodeStatus.BLOCKED,
        }:
            pass
        else:
            if not up_ok:
                return False

    return True


def compute_downstream(
    node_id: str,
    pipeline_def: PipelineDefinition,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for n in pipeline_def.nodes:
        for dep in n.deps:
            if dep.upstream == node_id:
                if n.node_id not in seen:
                    seen.add(n.node_id)
                    result.append(n.node_id)
                break
    return result
