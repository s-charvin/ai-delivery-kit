from __future__ import annotations

from typing import Literal

from orchestration.deps import compute_downstream, is_ready
from orchestration.models import (
    Addendum,
    ChangeState,
    DepCoupling,
    DepDeclaration,
    DepStrictness,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
)
from orchestration.state_machine import (
    EVENT_ADDENDUM_INFO_NOTIFY,
    EVENT_ADDENDUM_MUST_ACK,
    EVENT_ADDENDUM_SHOULD_NOTIFY,
    EVENT_DOWNSTREAM_SOFT_ACK,
    EVENT_NODE_DONE,
    EVENT_NODE_INVALIDATED,
    EVENT_NODE_READY,
    EVENT_NOTIFY,
    Event,
    transition,
)


def _deepcopy_state(state: PipelineState) -> PipelineState:
    return PipelineState.model_validate(state.model_dump())


def _find_dep_decl(
    upstream_id: str,
    downstream_node: NodeDef,
) -> DepDeclaration | None:
    for d in downstream_node.deps:
        if d.upstream == upstream_id:
            return d
    return None


def _do_transition_step(
    ns: NodeState,
    event_type: str,
    node_id: str,
) -> tuple[bool, list[Event]]:
    current_status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )
    evt = Event(type=event_type, payload={"node_id": node_id})
    new_s, side_effects, err = transition(
        current_status, evt, ctx={"node_id": node_id}
    )
    if err is not None or new_s is None:
        return False, []
    ns.status = new_s
    return True, side_effects


def cascade_done(
    node_id: str,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    ns = new_state.node_states.get(node_id)
    if ns is None:
        return new_state, events

    current_status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )

    if current_status != NodeStatus.DONE:
        plan: list[str] = []
        if current_status == NodeStatus.BLOCKED:
            plan = ["READY", "SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
        elif current_status == NodeStatus.READY:
            plan = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
        elif current_status == NodeStatus.DRAFT:
            plan = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
        elif current_status == NodeStatus.PENDING_REVIEW:
            plan = ["START_REVIEW", "APPROVE_MERGE"]
        elif current_status == NodeStatus.REVIEW:
            plan = ["APPROVE_MERGE"]
        elif current_status == NodeStatus.CHANGED:
            plan = ["RESUBMIT", "SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
        elif current_status == NodeStatus.IN_PROGRESS:
            plan = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]

        for step in plan:
            ok, se = _do_transition_step(ns, step, node_id)
            events.extend(se)
            if not ok:
                break

    final_status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )
    if final_status == NodeStatus.DONE:
        has_done_event = any(e.type == EVENT_NODE_DONE for e in events)
        if not has_done_event:
            events.append(
                Event(type=EVENT_NODE_DONE, payload={"node_id": node_id})
            )

    downstream_ids = compute_downstream(node_id, pipeline_def)
    for down_id in downstream_ids:
        down_ns = new_state.node_states.get(down_id)
        if down_ns is None:
            continue
        down_status = (
            NodeStatus(down_ns.status)
            if isinstance(down_ns.status, str)
            else down_ns.status
        )
        if down_status == NodeStatus.BLOCKED and is_ready(
            down_id, pipeline_def, new_state
        ):
            ok, se = _do_transition_step(down_ns, "READY", down_id)
            if ok:
                events.extend(se)
                has_ready = any(e.type == EVENT_NODE_READY for e in events)
                if not has_ready or True:
                    events.append(
                        Event(
                            type=EVENT_NODE_READY,
                            payload={"node_id": down_id},
                        )
                    )

    return new_state, events


def cascade_changed(
    node_id: str,
    change_class: Literal["compatible", "breaking"],
    coupling_default: DepCoupling,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    ns = new_state.node_states.get(node_id)
    if ns is None:
        return new_state, events

    current_status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )
    if current_status == NodeStatus.DONE:
        t = transition(
            current_status,
            Event(
                type="BREAKING_CHANGE",
                payload={"node_id": node_id, "change_class": change_class},
            ),
            ctx={"node_id": node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
            events.extend(t[1])

    downstream_ids = compute_downstream(node_id, pipeline_def)
    node_map: dict[str, NodeDef] = {n.node_id: n for n in pipeline_def.nodes}

    for down_id in downstream_ids:
        down_ns = new_state.node_states.get(down_id)
        if down_ns is None:
            continue
        down_node = node_map.get(down_id)
        if down_node is None:
            continue
        dep_decl = _find_dep_decl(node_id, down_node)
        if dep_decl is None:
            continue

        coupling = (
            DepCoupling(dep_decl.coupling)
            if isinstance(dep_decl.coupling, str)
            else dep_decl.coupling
        )
        strictness = (
            DepStrictness(dep_decl.strictness)
            if isinstance(dep_decl.strictness, str)
            else dep_decl.strictness
        )

        down_status = (
            NodeStatus(down_ns.status)
            if isinstance(down_ns.status, str)
            else down_ns.status
        )

        if coupling == DepCoupling.HARD and strictness == DepStrictness.STRICT:
            if down_status in {
                NodeStatus.DONE,
                NodeStatus.READY,
                NodeStatus.PENDING_REVIEW,
                NodeStatus.IN_PROGRESS,
                NodeStatus.REVIEW,
                NodeStatus.CHANGED,
                NodeStatus.DRAFT,
            }:
                if down_status == NodeStatus.DONE:
                    down_ns.artifact_refs = []
                    events.append(
                        Event(
                            type=EVENT_NODE_INVALIDATED,
                            payload={
                                "node_id": down_id,
                                "reason": f"upstream {node_id} changed",
                            },
                        )
                    )
                    t = transition(
                        down_status,
                        Event(
                            type="BREAKING_CHANGE",
                            payload={"node_id": down_id},
                        ),
                        ctx={"node_id": down_id},
                    )
                    if t[0] is not None:
                        down_ns.status = t[0]
                        events.extend(t[1])
                    else:
                        down_ns.status = NodeStatus.CHANGED
                else:
                    down_ns.status = NodeStatus.BLOCKED
        elif coupling == DepCoupling.SOFT and strictness == DepStrictness.STRICT:
            down_ns.change_state = ChangeState.SOFT_PENDING
            events.append(
                Event(
                    type=EVENT_DOWNSTREAM_SOFT_ACK,
                    payload={
                        "downstream_id": down_id,
                        "upstream_id": node_id,
                        "change_class": change_class,
                    },
                )
            )
        else:
            events.append(
                Event(
                    type=EVENT_NOTIFY,
                    payload={
                        "target_id": down_id,
                        "upstream_id": node_id,
                        "change_class": change_class,
                    },
                )
            )

    return new_state, events


def cascade_addendum(
    node_id: str,
    addendum: Addendum,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> tuple[PipelineState, list[Event]]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    ns = new_state.node_states.get(node_id)
    if ns is None:
        return new_state, events

    ns.addenda = ns.addenda + [addendum]

    cc = addendum.change_class

    if cc == "must":
        for down_id in addendum.incompatible_with:
            down_ns = new_state.node_states.get(down_id)
            if down_ns is None:
                continue
            down_status = (
                NodeStatus(down_ns.status)
                if isinstance(down_ns.status, str)
                else down_ns.status
            )
            if down_status == NodeStatus.DONE:
                down_ns.artifact_refs = []
                t = transition(
                    down_status,
                    Event(
                        type="BREAKING_CHANGE",
                        payload={
                            "node_id": down_id,
                            "addendum_id": addendum.id,
                        },
                    ),
                    ctx={"node_id": down_id},
                )
                if t[0] is not None:
                    down_ns.status = t[0]
                    events.extend(t[1])
                else:
                    down_ns.status = NodeStatus.CHANGED
            events.append(
                Event(
                    type=EVENT_ADDENDUM_MUST_ACK,
                    payload={
                        "downstream_id": down_id,
                        "addendum_id": addendum.id,
                        "upstream_id": node_id,
                    },
                )
            )
    elif cc == "should":
        events.append(
            Event(
                type=EVENT_ADDENDUM_SHOULD_NOTIFY,
                payload={
                    "addendum_id": addendum.id,
                    "upstream_id": node_id,
                    "impact": addendum.impact_claim,
                },
            )
        )
    else:
        events.append(
            Event(
                type=EVENT_ADDENDUM_INFO_NOTIFY,
                payload={
                    "addendum_id": addendum.id,
                    "upstream_id": node_id,
                    "impact": addendum.impact_claim,
                },
            )
        )

    return new_state, events
