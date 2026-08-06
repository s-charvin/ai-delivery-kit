from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from orchestration.models import (
    DepDeclaration,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.state_machine import (
    EVENT_PIPELINE_CANCELLED,
    EVENT_PIPELINE_PAUSED,
    EVENT_PIPELINE_RESUMED,
    Event,
    transition,
)


class CrossPipelineReference(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    ref_type: Literal["merge_result", "split_result"]
    source_pipeline_id: str
    source_node_id: str
    target_pipeline_id: str
    target_node_id: str


def _deepcopy_state(state: PipelineState) -> PipelineState:
    return PipelineState.model_validate(state.model_dump())


def _deepcopy_def(def_: PipelineDefinition) -> PipelineDefinition:
    return PipelineDefinition.model_validate(def_.model_dump())


def is_cancelled(state: PipelineState) -> bool:
    status = (
        PipelineStatus(state.status)
        if isinstance(state.status, str)
        else state.status
    )
    return status == PipelineStatus.CANCELLED


def pause_pipeline(
    state: PipelineState,
    reason: str,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    status = (
        PipelineStatus(new_state.status)
        if isinstance(new_state.status, str)
        else new_state.status
    )
    if status == PipelineStatus.ACTIVE:
        new_state.status = PipelineStatus.PAUSED
        pending = new_state.cascade_pending or []
        pending.append(
            {
                "type": "pause_record",
                "reason": reason,
                "pipeline_id": state.pipeline_id,
            }
        )
        new_state.cascade_pending = pending
        events.append(
            Event(
                type=EVENT_PIPELINE_PAUSED,
                payload={
                    "pipeline_id": state.pipeline_id,
                    "reason": reason,
                },
            )
        )

    return new_state, events


def resume_pipeline(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    status = (
        PipelineStatus(new_state.status)
        if isinstance(new_state.status, str)
        else new_state.status
    )
    if status == PipelineStatus.PAUSED:
        new_state.status = PipelineStatus.ACTIVE
        new_state.cascade_pending = []
        events.append(
            Event(
                type=EVENT_PIPELINE_RESUMED,
                payload={"pipeline_id": state.pipeline_id},
            )
        )

    return new_state, events


def cancel_pipeline(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    reason: str,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    status = (
        PipelineStatus(new_state.status)
        if isinstance(new_state.status, str)
        else new_state.status
    )
    if status in {PipelineStatus.ACTIVE, PipelineStatus.PAUSED}:
        new_state.status = PipelineStatus.CANCELLED

        cancelable_statuses = {
            NodeStatus.IN_PROGRESS,
            NodeStatus.PENDING_REVIEW,
            NodeStatus.READY,
            NodeStatus.DRAFT,
        }

        for nid, ns in new_state.node_states.items():
            ns_status = (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            if ns_status in cancelable_statuses:
                t = transition(
                    ns_status,
                    Event(type="DEPRECATE", payload={"node_id": nid}),
                    ctx={"node_id": nid},
                )
                if t[0] is not None:
                    ns.status = t[0]
            if ns.locked_by is not None:
                ns.locked_by = None

        events.append(
            Event(
                type=EVENT_PIPELINE_CANCELLED,
                payload={
                    "pipeline_id": state.pipeline_id,
                    "reason": reason,
                },
            )
        )

    return new_state, events


def merge_pipelines(
    def_a: PipelineDefinition,
    state_a: PipelineState,
    def_b: PipelineDefinition,
    state_b: PipelineState,
) -> tuple[PipelineDefinition, PipelineState, list[CrossPipelineReference]]:
    merged_def_a = _deepcopy_def(def_a)
    merged_def_b = _deepcopy_def(def_b)
    merged_state_a = _deepcopy_state(state_a)
    merged_state_b = _deepcopy_state(state_b)

    prefix_b = "B__"
    id_map_b: dict[str, str] = {}

    for n in merged_def_b.nodes:
        old_id = n.node_id
        new_id = prefix_b + old_id
        id_map_b[old_id] = new_id
        n.node_id = new_id
        for dep in n.deps:
            if dep.upstream in id_map_b:
                dep.upstream = id_map_b[dep.upstream]

    if merged_def_b.root_product_node_id is not None:
        merged_def_b.root_product_node_id = (
            prefix_b + merged_def_b.root_product_node_id
        )

    old_states_b = dict(merged_state_b.node_states)
    merged_state_b.node_states = {}
    for old_id, ns in old_states_b.items():
        new_id = id_map_b.get(old_id, prefix_b + old_id)
        ns.node_id = new_id
        merged_state_b.node_states[new_id] = ns

    merged_def = PipelineDefinition(
        id=f"MERGED_{def_a.id}_{def_b.id}",
        name=f"Merged: {def_a.name} + {def_b.name}",
        template_id=def_a.template_id or def_b.template_id,
        nodes=list(merged_def_a.nodes) + list(merged_def_b.nodes),
        profile=merged_def_a.profile,
        classification=merged_def_a.classification,
        root_product_node_id=merged_def_a.root_product_node_id,
    )

    merged_node_states = dict(merged_state_a.node_states)
    merged_node_states.update(merged_state_b.node_states)

    merged_state = PipelineState(
        pipeline_id=f"MERGED_{state_a.pipeline_id}_{state_b.pipeline_id}",
        version=max(state_a.version, state_b.version) + 1,
        status=PipelineStatus.ACTIVE,
        created_at=state_a.created_at,
        updated_at=state_b.updated_at,
        node_states=merged_node_states,
        cascade_pending=[],
        profile_id=state_a.profile_id or state_b.profile_id,
        classification=state_a.classification,
        completed_nodes_count=state_a.completed_nodes_count
        + state_b.completed_nodes_count,
    )

    refs: list[CrossPipelineReference] = []
    for n in def_a.nodes:
        refs.append(
            CrossPipelineReference(
                ref_type="merge_result",
                source_pipeline_id=def_a.id,
                source_node_id=n.node_id,
                target_pipeline_id=merged_def.id,
                target_node_id=n.node_id,
            )
        )
    for n in def_b.nodes:
        refs.append(
            CrossPipelineReference(
                ref_type="merge_result",
                source_pipeline_id=def_b.id,
                source_node_id=n.node_id,
                target_pipeline_id=merged_def.id,
                target_node_id=id_map_b.get(n.node_id, prefix_b + n.node_id),
            )
        )

    return merged_def, merged_state, refs


def split_pipeline(
    base_def: PipelineDefinition,
    base_state: PipelineState,
    subset_node_ids: list[str],
) -> tuple[
    PipelineDefinition,
    PipelineState,
    PipelineDefinition,
    PipelineState,
    list[CrossPipelineReference],
]:
    subset_set = set(subset_node_ids)

    subset_nodes: list[NodeDef] = []
    rest_nodes: list[NodeDef] = []
    for n in base_def.nodes:
        if n.node_id in subset_set:
            subset_nodes.append(n.model_copy(deep=True))
        else:
            rest_nodes.append(n.model_copy(deep=True))

    subset_states: dict[str, NodeState] = {}
    rest_states: dict[str, NodeState] = {}
    for nid, ns in base_state.node_states.items():
        if nid in subset_set:
            subset_states[nid] = ns.model_copy(deep=True)
        else:
            rest_states[nid] = ns.model_copy(deep=True)

    subset_def = PipelineDefinition(
        id=f"SPLIT_SUB_{base_def.id}",
        name=f"Subset of {base_def.name}",
        template_id=base_def.template_id,
        nodes=subset_nodes,
        profile=base_def.profile,
        classification=base_def.classification,
        root_product_node_id=(
            base_def.root_product_node_id
            if base_def.root_product_node_id in subset_set
            else None
        ),
    )

    rest_def = PipelineDefinition(
        id=f"SPLIT_REST_{base_def.id}",
        name=f"Rest of {base_def.name}",
        template_id=base_def.template_id,
        nodes=rest_nodes,
        profile=base_def.profile,
        classification=base_def.classification,
        root_product_node_id=(
            base_def.root_product_node_id
            if base_def.root_product_node_id not in subset_set
            else None
        ),
    )

    subset_state = PipelineState(
        pipeline_id=f"SPLIT_SUB_{base_state.pipeline_id}",
        version=base_state.version + 1,
        status=PipelineStatus.ACTIVE,
        created_at=base_state.created_at,
        updated_at=base_state.updated_at,
        node_states=subset_states,
        cascade_pending=[],
        profile_id=base_state.profile_id,
        classification=base_state.classification,
        completed_nodes_count=sum(
            1
            for ns in subset_states.values()
            if (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            == NodeStatus.DONE
        ),
    )

    rest_state = PipelineState(
        pipeline_id=f"SPLIT_REST_{base_state.pipeline_id}",
        version=base_state.version + 1,
        status=PipelineStatus.ACTIVE,
        created_at=base_state.created_at,
        updated_at=base_state.updated_at,
        node_states=rest_states,
        cascade_pending=[],
        profile_id=base_state.profile_id,
        classification=base_state.classification,
        completed_nodes_count=sum(
            1
            for ns in rest_states.values()
            if (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            == NodeStatus.DONE
        ),
    )

    refs: list[CrossPipelineReference] = []
    for nid in subset_node_ids:
        refs.append(
            CrossPipelineReference(
                ref_type="split_result",
                source_pipeline_id=base_def.id,
                source_node_id=nid,
                target_pipeline_id=subset_def.id,
                target_node_id=nid,
            )
        )
    for n in rest_def.nodes:
        refs.append(
            CrossPipelineReference(
                ref_type="split_result",
                source_pipeline_id=base_def.id,
                source_node_id=n.node_id,
                target_pipeline_id=rest_def.id,
                target_node_id=n.node_id,
            )
        )

    return subset_def, subset_state, rest_def, rest_state, refs
