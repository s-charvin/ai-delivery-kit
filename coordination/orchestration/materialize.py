from __future__ import annotations

from orchestration.models import (
    DepDeclaration,
    DepPresence,
    NodeDef,
    NodeStatus,
    ParticipationProfile,
    PipelineDefinition,
    PipelineState,
)
from config.constants import ROLE_MAP


def node_type_role_mapping(node_type: str) -> list[str]:
    return ROLE_MAP.get(node_type, [])


def materialize_pipeline(
    base_def: PipelineDefinition,
    profile: ParticipationProfile,
) -> PipelineDefinition:
    roles_absent = set(profile.roles_absent)

    kept_nodes: list[NodeDef] = []
    removed_ids: set[str] = set()

    for n in base_def.nodes:
        roles = set(node_type_role_mapping(n.node_type))
        if roles & roles_absent:
            removed_ids.add(n.node_id)
        else:
            kept_nodes.append(n.model_copy(deep=True))

    final_nodes: list[NodeDef] = []
    for n in kept_nodes:
        new_deps: list[DepDeclaration] = []
        for dep in n.deps:
            if dep.upstream in removed_ids:
                presence = (
                    DepPresence(dep.presence)
                    if isinstance(dep.presence, str)
                    else dep.presence
                )
                if presence == DepPresence.REQUIRED:
                    raise ValueError(
                        f"Dangling required dep after materialize: "
                        f"node {n.node_id} -> upstream {dep.upstream}"
                    )
                continue
            new_deps.append(dep.model_copy(deep=True))
        n.deps = new_deps
        final_nodes.append(n)

    optional_types = set(profile.optional_node_types)
    for n in final_nodes:
        if n.node_type in optional_types:
            n.optional = True

    return PipelineDefinition(
        id=base_def.id,
        name=base_def.name,
        template_id=base_def.template_id,
        nodes=final_nodes,
        profile=profile,
        classification=base_def.classification,
        root_product_node_id=(
            base_def.root_product_node_id
            if base_def.root_product_node_id not in removed_ids
            else None
        ),
    )


def is_pipeline_completed(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> bool:
    profile = pipeline_def.profile
    if profile.completion_mode != "core_nodes_done":
        return False

    core_types = set(profile.core_node_types)
    core_nodes = [n for n in pipeline_def.nodes if n.node_type in core_types]

    for n in core_nodes:
        ns = state.node_states.get(n.node_id)
        if ns is None:
            return False

        status = (
            NodeStatus(ns.status)
            if isinstance(ns.status, str)
            else ns.status
        )

        if n.optional:
            if status in {
                NodeStatus.DONE,
                NodeStatus.SKIPPED,
                NodeStatus.DEPRECATED,
            }:
                continue
            return False
        else:
            if status != NodeStatus.DONE:
                return False

    return True
