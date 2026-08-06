from __future__ import annotations

from typing import Any

from orchestration.cascade import cascade_addendum, cascade_changed, cascade_done
from orchestration.deps import compute_downstream, is_ready
from orchestration.gate_policy import get_gate_policy_store
from orchestration.models import (
    Addendum,
    DepCoupling,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.state_machine import (
    EVENT_NODE_DONE,
    EVENT_NODE_DEPRECATED,
    EVENT_NODE_INVALIDATED,
    EVENT_NODE_READY,
    EVENT_NODE_SKIPPED,
    EVENT_NOTIFY,
    EVENT_PIPELINE_STARTED,
    EVENT_SOFT_DRAFT_PUBLISHED,
    EVENT_STUB_APPROVAL,
    EVENT_STUB_CREWAI_ASSIGN,
    EVENT_STUB_WARN,
    Event,
    transition,
)


def _step_crewai_assign(
    state: PipelineState,
    pipeline_def: PipelineDefinition,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    from crew.bridge import get_global_bridge

    bridge = get_global_bridge()
    ready_nodes = ctx.get("ready_nodes")
    pipeline_id = state.pipeline_id
    instances = ctx.get("instances", {})
    mcp_tools_wrapper = ctx.get("mcp_tools_wrapper")

    if not ready_nodes or not pipeline_def or not instances:
        return _step_stub_impl(
            state,
            EVENT_STUB_CREWAI_ASSIGN,
            {"step": "crewai_assign", "reason": "missing ready_nodes/pipeline_def/instances"},
        )

    result = bridge.dispatch_ready_nodes(
        pipeline_id=pipeline_id,
        ready_nodes=ready_nodes,
        pipeline_def=pipeline_def,
        pipeline_state=state,
        instances=instances,
        mcp_tools_wrapper=mcp_tools_wrapper,
    )
    new_state = result["pipeline_state"] if result.get("pipeline_state") is not None else _deepcopy_state(state)
    events = result.get("events", [])
    return new_state, events, None


def _step_stub_impl(
    state: PipelineState,
    event_type: str,
    payload: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    return _deepcopy_state(state), [Event(type=event_type, payload=payload)], None


def _deepcopy_state(state: PipelineState) -> PipelineState:
    return PipelineState.model_validate(state.model_dump())


def run_graph_step(
    step_name: str,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    if step_name == "bootstrap":
        return _step_bootstrap(pipeline_def, state, ctx)
    elif step_name == "cascade_done":
        return _step_cascade_done(pipeline_def, state, ctx)
    elif step_name == "invalidate":
        return _step_invalidate(pipeline_def, state, ctx)
    elif step_name == "draft_publish":
        return _step_draft_publish(pipeline_def, state, ctx)
    elif step_name == "addendum":
        return _step_addendum(pipeline_def, state, ctx)
    elif step_name == "skip_finalize":
        return _step_skip_finalize(pipeline_def, state, ctx)
    elif step_name == "external_health":
        return _step_external_health(pipeline_def, state, ctx)
    elif step_name == "wait":
        return _deepcopy_state(state), [], None
    elif step_name == "dispatch_router":
        return _step_dispatch_router(pipeline_def, state, ctx)
    elif step_name == "crewai_assign":
        pipeline_def = ctx.get("pipeline_def")
        return _step_crewai_assign(state, pipeline_def, ctx)
    elif step_name == "approval_node":
        return _step_stub(
            state,
            EVENT_STUB_APPROVAL,
            {"step": "approval_node", "node_id": ctx.get("node_id")},
        )
    elif step_name == "gate":
        return _step_gate(pipeline_def, state, ctx)
    elif step_name == "notify":
        return _step_notify(pipeline_def, state, ctx)
    elif step_name == "switch":
        return _step_switch(pipeline_def, state, ctx)
    else:
        return (
            _deepcopy_state(state),
            [
                Event(
                    type=EVENT_STUB_WARN,
                    payload={
                        "step_name": step_name,
                        "reason": "Unknown step, noop",
                    },
                )
            ],
            None,
        )


def _step_stub(
    state: PipelineState,
    event_type: str,
    payload: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    return _deepcopy_state(state), [Event(type=event_type, payload=payload)], None


def _step_bootstrap(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    root_id = pipeline_def.root_product_node_id
    if root_id is None:
        for n in pipeline_def.nodes:
            if n.node_type == "product_spec":
                root_id = n.node_id
                break
        if root_id is None and pipeline_def.nodes:
            root_id = pipeline_def.nodes[0].node_id

    for n in pipeline_def.nodes:
        if n.node_id not in new_state.node_states:
            ns = NodeState(node_id=n.node_id, status=NodeStatus.BLOCKED)
            new_state.node_states[n.node_id] = ns

    if root_id is not None and root_id in new_state.node_states:
        ns = new_state.node_states[root_id]
        current_status = (
            NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        )
        if current_status == NodeStatus.BLOCKED:
            t = transition(
                current_status,
                Event(type="READY", payload={"node_id": root_id}),
                ctx={"node_id": root_id},
            )
            if t[0] is not None:
                ns.status = t[0]
                events.extend(t[1])
                events.append(
                    Event(type=EVENT_NODE_READY, payload={"node_id": root_id})
                )

    events.append(
        Event(
            type=EVENT_PIPELINE_STARTED,
            payload={
                "pipeline_id": state.pipeline_id,
                "root_node_id": root_id,
            },
        )
    )

    return new_state, events, None


def _step_cascade_done(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    new_state = _deepcopy_state(state)
    all_events: list[Event] = []

    changed = True
    max_iter = 10
    iter_count = 0
    while changed and iter_count < max_iter:
        changed = False
        iter_count += 1
        for n in pipeline_def.nodes:
            ns = new_state.node_states.get(n.node_id)
            if ns is None:
                continue
            status = (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            if status == NodeStatus.BLOCKED and is_ready(
                n.node_id, pipeline_def, new_state
            ):
                t = transition(
                    status,
                    Event(type="READY", payload={"node_id": n.node_id}),
                    ctx={"node_id": n.node_id},
                )
                if t[0] is not None:
                    ns.status = t[0]
                    all_events.extend(t[1])
                    all_events.append(
                        Event(
                            type=EVENT_NODE_READY,
                            payload={"node_id": n.node_id},
                        )
                    )
                    changed = True

    return new_state, all_events, None


def _step_invalidate(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("changed_node_id") or ctx.get("node_id")
    if node_id is None:
        return _deepcopy_state(state), [], None
    change_class = ctx.get("change_class", "compatible")
    coupling_default = DepCoupling(
        ctx.get("coupling_default", DepCoupling.HARD.value)
    )
    if isinstance(change_class, str):
        cc = "compatible" if change_class == "compatible" else "breaking"
    else:
        cc = "compatible"
    new_state, events = cascade_changed(
        node_id, cc, coupling_default, pipeline_def, state
    )
    return new_state, events, None


def _step_draft_publish(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("node_id")
    if node_id is None:
        return _deepcopy_state(state), [], None
    new_state = _deepcopy_state(state)
    events: list[Event] = []
    ns = new_state.node_states.get(node_id)
    if ns is None:
        return new_state, events, None
    status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )
    if status == NodeStatus.READY:
        t = transition(
            status,
            Event(type="SET_DRAFT", payload={"node_id": node_id}),
            ctx={"node_id": node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
            events.extend(t[1])
    events.append(
        Event(
            type=EVENT_SOFT_DRAFT_PUBLISHED,
            payload={"node_id": node_id},
        )
    )
    return new_state, events, None


def _step_addendum(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("node_id")
    addendum_data = ctx.get("addendum")
    if node_id is None or addendum_data is None:
        return _deepcopy_state(state), [], None
    if isinstance(addendum_data, dict):
        addendum = Addendum(**addendum_data)
    else:
        addendum = addendum_data
    new_state, events = cascade_addendum(
        node_id, addendum, pipeline_def, state
    )
    return new_state, events, None


def _step_skip_finalize(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []
    core_types = set(pipeline_def.profile.core_node_types)

    for n in pipeline_def.nodes:
        if n.node_type in core_types:
            continue
        if not n.optional:
            continue
        ns = new_state.node_states.get(n.node_id)
        if ns is None:
            continue
        status = (
            NodeStatus(ns.status)
            if isinstance(ns.status, str)
            else ns.status
        )
        if status in {NodeStatus.BLOCKED, NodeStatus.READY}:
            t = transition(
                status,
                Event(type="SKIP_OPTIONAL", payload={"node_id": n.node_id}),
                ctx={"node_id": n.node_id},
            )
            if t[0] is not None:
                ns.status = t[0]
                events.extend(t[1])
                has_skip = any(e.type == EVENT_NODE_SKIPPED for e in events)
                if not has_skip:
                    events.append(
                        Event(
                            type=EVENT_NODE_SKIPPED,
                            payload={"node_id": n.node_id},
                        )
                    )

    return new_state, events, None


def _step_external_health(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    new_state = _deepcopy_state(state)
    events: list[Event] = []
    deprecated_nodes = ctx.get("deprecated_nodes", [])
    for node_id in deprecated_nodes:
        ns = new_state.node_states.get(node_id)
        if ns is None:
            continue
        status = (
            NodeStatus(ns.status)
            if isinstance(ns.status, str)
            else ns.status
        )
        if status == NodeStatus.DONE:
            t = transition(
                status,
                Event(type="DEPRECATE", payload={"node_id": node_id}),
                ctx={"node_id": node_id},
            )
            if t[0] is not None:
                ns.status = t[0]
                events.extend(t[1])
                has_dep = any(e.type == EVENT_NODE_DEPRECATED for e in events)
                if not has_dep:
                    events.append(
                        Event(
                            type=EVENT_NODE_DEPRECATED,
                            payload={"node_id": node_id},
                        )
                    )
    return new_state, events, None


def _step_dispatch_router(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("node_id")
    if node_id is None:
        return _deepcopy_state(state), [], None
    new_state = _deepcopy_state(state)
    ns = new_state.node_states.get(node_id)
    if ns is None:
        return new_state, [], None
    status = (
        NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    )
    events: list[Event] = []
    if status == NodeStatus.READY:
        t = transition(
            status,
            Event(type="SUBMIT_ARTIFACT", payload={"node_id": node_id}),
            ctx={"node_id": node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
            events.extend(t[1])
    return new_state, events, None


def _find_upstream_product_node(
    node_id: str,
    pipeline_def: PipelineDefinition,
    state: PipelineState,
) -> str | None:
    node_map: dict[str, NodeDef] = {n.node_id: n for n in pipeline_def.nodes}
    visited: set[str] = set()
    queue: list[str] = [node_id]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        current_def = node_map.get(current)
        current_ns = state.node_states.get(current)
        if current_def is None or current_ns is None:
            continue
        ns_status = (
            NodeStatus(current_ns.status)
            if isinstance(current_ns.status, str)
            else current_ns.status
        )
        if current_ns.artifact_refs and ns_status == NodeStatus.DONE:
            return current
        for dep in current_def.deps:
            up_id = dep.upstream
            if up_id not in visited:
                queue.append(up_id)
    for n in pipeline_def.nodes:
        if n.node_id in state.node_states:
            ns = state.node_states[n.node_id]
            if ns.artifact_refs:
                return n.node_id
    return None


def _step_gate(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    gate_node_id = ctx.get("node_id") or ctx.get("gate_node_id")
    if gate_node_id is None:
        return _deepcopy_state(state), [], "missing gate_node_id"
    pipeline_id = state.pipeline_id
    coverage_report_pct = ctx.get("coverage_report_pct")
    lint_passed = ctx.get("lint_passed", True)
    test_passed = ctx.get("test_passed", True)
    security_scan_passed = ctx.get("security_scan_passed", True)

    gate_store = get_gate_policy_store()
    passed, failed_rules = gate_store.evaluate(
        pipeline_id,
        gate_node_id,
        coverage_report_pct=coverage_report_pct,
        lint_passed=lint_passed,
        test_passed=test_passed,
        security_scan_passed=security_scan_passed,
    )

    new_state = _deepcopy_state(state)
    events: list[Event] = []

    gate_ns = new_state.node_states.get(gate_node_id)
    if gate_ns is None:
        gate_ns = NodeState(node_id=gate_node_id, status=NodeStatus.BLOCKED)
        new_state.node_states[gate_node_id] = gate_ns

    if passed:
        cur_status = (
            NodeStatus(gate_ns.status)
            if isinstance(gate_ns.status, str)
            else gate_ns.status
        )
        if cur_status == NodeStatus.BLOCKED and is_ready(gate_node_id, pipeline_def, new_state):
            t = transition(
                cur_status,
                Event(type="READY", payload={"node_id": gate_node_id}),
                ctx={"node_id": gate_node_id},
            )
            if t[0] is not None:
                gate_ns.status = t[0]
                events.extend(t[1])
        cur_status2 = (
            NodeStatus(gate_ns.status)
            if isinstance(gate_ns.status, str)
            else gate_ns.status
        )
        if cur_status2 in {NodeStatus.READY, NodeStatus.IN_PROGRESS}:
            plan = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
            for step in plan:
                ok, se = _do_transition_step_local(gate_ns, step, gate_node_id)
                events.extend(se)
                if not ok:
                    break
        final_status = (
            NodeStatus(gate_ns.status)
            if isinstance(gate_ns.status, str)
            else gate_ns.status
        )
        if final_status == NodeStatus.DONE:
            has_done = any(e.type == EVENT_NODE_DONE for e in events)
            if not has_done:
                events.append(Event(type=EVENT_NODE_DONE, payload={"node_id": gate_node_id}))
            downstream_ids = compute_downstream(gate_node_id, pipeline_def)
            for down_id in downstream_ids:
                down_ns = new_state.node_states.get(down_id)
                if down_ns is None:
                    continue
                down_status = (
                    NodeStatus(down_ns.status)
                    if isinstance(down_ns.status, str)
                    else down_ns.status
                )
                if down_status == NodeStatus.BLOCKED and is_ready(down_id, pipeline_def, new_state):
                    ok, se = _do_transition_step_local(down_ns, "READY", down_id)
                    if ok:
                        events.extend(se)
                        events.append(Event(type=EVENT_NODE_READY, payload={"node_id": down_id}))
    else:
        up_product = _find_upstream_product_node(gate_node_id, pipeline_def, new_state)
        if up_product is not None:
            up_ns = new_state.node_states.get(up_product)
            if up_ns is not None:
                up_status = (
                    NodeStatus(up_ns.status)
                    if isinstance(up_ns.status, str)
                    else up_ns.status
                )
                if up_status == NodeStatus.DONE:
                    up_ns.artifact_refs = []
                    events.append(
                        Event(
                            type=EVENT_NODE_INVALIDATED,
                            payload={
                                "node_id": up_product,
                                "reason": f"gate policy failed: {failed_rules}",
                            },
                        )
                    )
                    up_ns.status = NodeStatus.IN_PROGRESS
        events.append(
            Event(
                type="NOTIFY_GATE_FAIL",
                payload={
                    "gate_node_id": gate_node_id,
                    "failed_rules": failed_rules,
                    "upstream_in_progress": up_product,
                },
            )
        )

    return new_state, events, None


def _do_transition_step_local(
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


def _step_notify(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("node_id")
    cross_refs = ctx.get("cross_pipeline_refs", [])
    webhook_url = ctx.get("webhook_url")
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    consumers: list[str] = []
    for ref in cross_refs:
        try:
            ref_type = getattr(ref, "ref_type", None) or (ref.get("ref_type") if isinstance(ref, dict) else None)
            if ref_type in ("consumer", "CONSUMER"):
                tgt = getattr(ref, "target_node_id", None) or (ref.get("target_node_id") if isinstance(ref, dict) else None)
                if tgt:
                    consumers.append(tgt)
        except Exception:
            pass

    if node_id is not None:
        downstream = compute_downstream(node_id, pipeline_def)
        for d in downstream:
            if d not in consumers:
                consumers.append(d)

    for consumer_id in consumers:
        events.append(
            Event(
                type="CONSUMER_NOTIFY",
                payload={
                    "source_node_id": node_id,
                    "consumer_id": consumer_id,
                    "pipeline_id": state.pipeline_id,
                },
            )
        )
        events.append(
            Event(
                type=EVENT_NOTIFY,
                payload={
                    "target_id": consumer_id,
                    "source_id": node_id,
                },
            )
        )

    if webhook_url:
        try:
            import httpx
            try:
                httpx.post(
                    webhook_url,
                    json={
                        "pipeline_id": state.pipeline_id,
                        "node_id": node_id,
                        "consumers": consumers,
                    },
                    timeout=2.0,
                )
            except Exception:
                pass
        except ImportError:
            pass

    return new_state, events, None


def _step_switch(
    pipeline_def: PipelineDefinition,
    state: PipelineState,
    ctx: dict[str, Any],
) -> tuple[PipelineState, list[Event], str | None]:
    node_id = ctx.get("node_id")
    switch_decision = ctx.get("switch_decision") or ctx.get("approval_result")
    new_state = _deepcopy_state(state)
    events: list[Event] = []

    if node_id is None:
        return new_state, events, "missing node_id"

    control_ns = new_state.node_states.get(node_id)
    if control_ns is None:
        control_ns = NodeState(node_id=node_id, status=NodeStatus.BLOCKED)
        new_state.node_states[node_id] = control_ns

    if switch_decision == "approve":
        cur_status = (
            NodeStatus(control_ns.status)
            if isinstance(control_ns.status, str)
            else control_ns.status
        )
        if cur_status == NodeStatus.BLOCKED and is_ready(node_id, pipeline_def, new_state):
            t = transition(
                cur_status,
                Event(type="READY", payload={"node_id": node_id}),
                ctx={"node_id": node_id},
            )
            if t[0] is not None:
                control_ns.status = t[0]
                events.extend(t[1])
        cur_status2 = (
            NodeStatus(control_ns.status)
            if isinstance(control_ns.status, str)
            else control_ns.status
        )
        if cur_status2 in {NodeStatus.READY, NodeStatus.REVIEW}:
            plan = ["START_REVIEW", "APPROVE_MERGE"]
            for step in plan:
                ok, se = _do_transition_step_local(control_ns, step, node_id)
                events.extend(se)
                if not ok:
                    break
        final_status = (
            NodeStatus(control_ns.status)
            if isinstance(control_ns.status, str)
            else control_ns.status
        )
        if final_status == NodeStatus.DONE:
            has_done = any(e.type == EVENT_NODE_DONE for e in events)
            if not has_done:
                events.append(Event(type=EVENT_NODE_DONE, payload={"node_id": node_id}))
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
                if down_status == NodeStatus.BLOCKED and is_ready(down_id, pipeline_def, new_state):
                    ok, se = _do_transition_step_local(down_ns, "READY", down_id)
                    if ok:
                        events.extend(se)
                        events.append(Event(type=EVENT_NODE_READY, payload={"node_id": down_id}))
    elif switch_decision == "reject":
        cur_status = (
            NodeStatus(control_ns.status)
            if isinstance(control_ns.status, str)
            else control_ns.status
        )
        if cur_status in {NodeStatus.REVIEW, NodeStatus.PENDING_REVIEW, NodeStatus.READY}:
            t = transition(
                cur_status,
                Event(type="REJECT_REVIEW", payload={"node_id": node_id, "reason": ctx.get("reason", "switch reject")}),
                ctx={"node_id": node_id},
            )
            if t[0] is not None:
                control_ns.status = t[0]
                events.extend(t[1])
            else:
                control_ns.status = NodeStatus.READY
        up_product = _find_upstream_product_node(node_id, pipeline_def, new_state)
        if up_product is not None:
            up_ns = new_state.node_states.get(up_product)
            if up_ns is not None:
                up_status = (
                    NodeStatus(up_ns.status)
                    if isinstance(up_ns.status, str)
                    else up_ns.status
                )
                if up_status == NodeStatus.DONE:
                    up_ns.artifact_refs = []
                    events.append(
                        Event(
                            type="CODE_ROLLBACK_NEEDED",
                            payload={
                                "node_id": up_product,
                                "reason": f"approval control node {node_id} rejected",
                            },
                        )
                    )
                    t = transition(
                        up_status,
                        Event(type="BREAKING_CHANGE", payload={"node_id": up_product}),
                        ctx={"node_id": up_product},
                    )
                    if t[0] is not None:
                        up_ns.status = t[0]
                        events.extend(t[1])
                    else:
                        up_ns.status = NodeStatus.CHANGED

    return new_state, events, None
