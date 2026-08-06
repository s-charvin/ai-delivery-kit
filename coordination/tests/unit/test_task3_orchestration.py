from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import PARTICIPATION_PROFILES, TRANSITION_MATRIX
from orchestration.cascade import cascade_addendum, cascade_changed, cascade_done
from orchestration.checkpoints import SQLiteCheckpointStorage
from orchestration.deps import compute_downstream, is_ready, resolve_effective_deps
from orchestration.materialize import is_pipeline_completed, materialize_pipeline
from orchestration.models import (
    Addendum,
    ArtifactRef,
    DepDeclaration,
    DepCoupling,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.pipeline_lifecycle import (
    cancel_pipeline,
    is_cancelled,
    pause_pipeline,
    resume_pipeline,
)
from orchestration.state_machine import (
    EVENT_ADD_ADDENDUM_MUST,
    EVENT_APPROVE_MERGE,
    EVENT_BREAKING_CHANGE,
    EVENT_DEPRECATE,
    EVENT_READY,
    EVENT_RESUBMIT,
    EVENT_SET_DRAFT,
    EVENT_SKIP_OPTIONAL,
    EVENT_START_REVIEW,
    EVENT_SUBMIT_ARTIFACT,
    Event,
    transition,
    transition_allowed,
)


def make_fs():
    n1 = NodeDef(
        node_id="n1",
        node_type="product_spec",
        role_assignments=["product"],
        deps=[],
    )
    n2 = NodeDef(
        node_id="n2",
        node_type="api_contract",
        role_assignments=["product", "server_impl"],
        deps=[
            DepDeclaration(
                upstream="n1",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n3 = NodeDef(
        node_id="n3",
        node_type="design_asset",
        role_assignments=["design"],
        deps=[
            DepDeclaration(
                upstream="n1",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n4 = NodeDef(
        node_id="n4",
        node_type="client_ui_impl",
        role_assignments=["client_ui"],
        deps=[
            DepDeclaration(
                upstream="n2",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n3",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
        ],
    )
    n5 = NodeDef(
        node_id="n5",
        node_type="server_impl",
        role_assignments=["server_impl"],
        deps=[
            DepDeclaration(
                upstream="n2",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n6 = NodeDef(
        node_id="n6",
        node_type="server_test",
        role_assignments=["server_test"],
        deps=[
            DepDeclaration(
                upstream="n5",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n7 = NodeDef(
        node_id="n7",
        node_type="delivery_gate",
        role_assignments=["ops"],
        deps=[
            DepDeclaration(
                upstream="n4",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n6",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n3",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
        ],
    )

    profile = PARTICIPATION_PROFILES["fullstack"].model_copy(deep=True)

    pipeline_def = PipelineDefinition(
        id="pipe-fs-001",
        name="fullstack-happy-path",
        nodes=[n1, n2, n3, n4, n5, n6, n7],
        profile=profile,
        root_product_node_id="n1",
    )

    return pipeline_def


def _make_state(def_: PipelineDefinition) -> PipelineState:
    node_states: dict[str, NodeState] = {}
    for n in def_.nodes:
        node_states[n.node_id] = NodeState(
            node_id=n.node_id, status=NodeStatus.BLOCKED
        )
    return PipelineState(
        pipeline_id=def_.id,
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        node_states=node_states,
    )


def test_tr3_1_state_machine():
    """TR-3.1 状态机 18 条合法转移 + 14 条非法."""

    valid_paths: list[tuple[NodeStatus, str, NodeStatus]] = [
        (NodeStatus.BLOCKED, EVENT_READY, NodeStatus.READY),
        (NodeStatus.READY, EVENT_SUBMIT_ARTIFACT, NodeStatus.PENDING_REVIEW),
        (NodeStatus.PENDING_REVIEW, EVENT_START_REVIEW, NodeStatus.REVIEW),
        (NodeStatus.REVIEW, EVENT_APPROVE_MERGE, NodeStatus.DONE),
        (NodeStatus.REVIEW, "REJECT_REVIEW", NodeStatus.READY),
        (NodeStatus.DONE, EVENT_BREAKING_CHANGE, NodeStatus.CHANGED),
        (NodeStatus.CHANGED, EVENT_RESUBMIT, NodeStatus.IN_PROGRESS),
        (NodeStatus.READY, EVENT_SET_DRAFT, NodeStatus.DRAFT),
        (NodeStatus.DRAFT, EVENT_SUBMIT_ARTIFACT, NodeStatus.PENDING_REVIEW),
        (NodeStatus.READY, EVENT_SKIP_OPTIONAL, NodeStatus.SKIPPED),
        (NodeStatus.DONE, EVENT_DEPRECATE, NodeStatus.DEPRECATED),
        (NodeStatus.CHANGED, EVENT_DEPRECATE, NodeStatus.DEPRECATED),
        (NodeStatus.READY, EVENT_DEPRECATE, NodeStatus.DEPRECATED),
        (NodeStatus.BLOCKED, EVENT_DEPRECATE, NodeStatus.DEPRECATED),
        (NodeStatus.DEPRECATED, "SUNSET", NodeStatus.SUNSET),
        (NodeStatus.DRAFT, EVENT_DEPRECATE, NodeStatus.DEPRECATED),
        (NodeStatus.PENDING_REVIEW, "CANCEL_SUBMIT", NodeStatus.READY),
    ]

    ok_count = 0
    for from_status, event_type, expected_to in valid_paths:
        evt = Event(type=event_type, payload={"node_id": "x"})
        result = transition(from_status, evt, ctx={"node_id": "x"})
        new_status, side_effects, err = result
        assert err is None, (
            f"Valid {from_status} --{event_type}--> should succeed, got err={err}"
        )
        assert new_status is not None, (
            f"Valid {from_status} --{event_type}--> unexpected new_status None"
        )
        assert new_status == expected_to, (
            f"Valid {from_status} --{event_type}--> expected {expected_to}, got {new_status}"
        )
        ok_count += 1

    invalid_cases: list[tuple[NodeStatus, str]] = [
        (NodeStatus.BLOCKED, EVENT_APPROVE_MERGE),
        (NodeStatus.READY, EVENT_BREAKING_CHANGE),
        (NodeStatus.DONE, EVENT_READY),
        (NodeStatus.DONE, EVENT_SUBMIT_ARTIFACT),
        (NodeStatus.PENDING_REVIEW, EVENT_APPROVE_MERGE),
        (NodeStatus.REVIEW, EVENT_READY),
        (NodeStatus.CHANGED, EVENT_SUBMIT_ARTIFACT),
        (NodeStatus.DRAFT, EVENT_APPROVE_MERGE),
        (NodeStatus.SKIPPED, EVENT_READY),
        (NodeStatus.SUNSET, EVENT_DEPRECATE),
        (NodeStatus.DEPRECATED, EVENT_RESUBMIT),
        (NodeStatus.IN_PROGRESS, EVENT_SKIP_OPTIONAL),
        (NodeStatus.BLOCKED, EVENT_SET_DRAFT),
        (NodeStatus.DONE, EVENT_SKIP_OPTIONAL),
    ]

    for status, etype in invalid_cases:
        evt = Event(type=etype, payload={})
        result = transition(status, evt, ctx={})
        new_status, side_effects, err = result
        assert err == "E_ILLEGAL_TRANSITION", (
            f"Invalid {status} --{etype}--> expected E_ILLEGAL_TRANSITION, got err={err}, new={new_status}"
        )
        assert new_status is None
        assert side_effects == []

    evt_add_must = Event(
        type=EVENT_ADD_ADDENDUM_MUST,
        payload={"downstream": ["n2", "n3"], "addendum_id": "a1"},
    )
    add_result = transition(NodeStatus.DONE, evt_add_must, ctx={})
    assert add_result[2] is None
    assert add_result[0] == NodeStatus.DONE
    assert len(add_result[1]) == 1
    assert add_result[1][0].payload.get("change_class") == "must"

    add_result_bad = transition(NodeStatus.READY, evt_add_must, ctx={})
    assert add_result_bad[2] == "E_ILLEGAL_TRANSITION"

    assert transition_allowed(NodeStatus.BLOCKED, NodeStatus.READY) is True
    assert transition_allowed(NodeStatus.DONE, NodeStatus.READY) is False


def test_tr3_2_cascade_tc01_tc04():
    """TR-3.2 TC-01 + TC-04 cascade_done + cascade_changed."""
    def_ = make_fs()
    state = _make_state(def_)

    state.node_states["n1"].status = NodeStatus.READY

    state1, evts1 = cascade_done("n1", def_, state)

    n1_status = (
        NodeStatus(state1.node_states["n1"].status)
        if isinstance(state1.node_states["n1"].status, str)
        else state1.node_states["n1"].status
    )
    assert n1_status == NodeStatus.DONE, f"n1 expected DONE, got {n1_status}"

    n2_status = (
        NodeStatus(state1.node_states["n2"].status)
        if isinstance(state1.node_states["n2"].status, str)
        else state1.node_states["n2"].status
    )
    n3_status = (
        NodeStatus(state1.node_states["n3"].status)
        if isinstance(state1.node_states["n3"].status, str)
        else state1.node_states["n3"].status
    )
    assert n2_status == NodeStatus.READY, (
        f"TC-01: n2 expected READY, got {n2_status}"
    )
    assert n3_status == NodeStatus.READY, (
        f"TC-01: n3 expected READY, got {n3_status}"
    )

    state2, evts2 = cascade_done("n2", def_, state1)
    n2_status2 = (
        NodeStatus(state2.node_states["n2"].status)
        if isinstance(state2.node_states["n2"].status, str)
        else state2.node_states["n2"].status
    )
    assert n2_status2 == NodeStatus.DONE

    n5_status = (
        NodeStatus(state2.node_states["n5"].status)
        if isinstance(state2.node_states["n5"].status, str)
        else state2.node_states["n5"].status
    )
    assert n5_status == NodeStatus.READY, (
        f"TC-03: n5 expected READY after n2 done, got {n5_status}"
    )

    n4_status = (
        NodeStatus(state2.node_states["n4"].status)
        if isinstance(state2.node_states["n4"].status, str)
        else state2.node_states["n4"].status
    )
    assert n4_status == NodeStatus.BLOCKED, (
        f"TC-03: n4 expected BLOCKED (n3 if_present not done), got {n4_status}"
    )
    assert is_ready("n4", def_, state2) is False

    fake_artifact = ArtifactRef(
        node_id="n5",
        artifact_type="ServerImpl",
        version=1,
        uri="/x",
        ref_hash="sha256:abc",
        trace_id="t1",
    )
    state2.node_states["n5"].artifact_refs = [fake_artifact]
    state2.node_states["n5"].status = NodeStatus.DONE

    state3, evts3 = cascade_changed(
        "n2", "breaking", DepCoupling.HARD, def_, state2
    )

    n2_status3 = (
        NodeStatus(state3.node_states["n2"].status)
        if isinstance(state3.node_states["n2"].status, str)
        else state3.node_states["n2"].status
    )
    assert n2_status3 == NodeStatus.CHANGED, (
        f"TC-04: n2 expected CHANGED after breaking, got {n2_status3}"
    )

    n5_status3 = (
        NodeStatus(state3.node_states["n5"].status)
        if isinstance(state3.node_states["n5"].status, str)
        else state3.node_states["n5"].status
    )
    assert n5_status3 in {NodeStatus.CHANGED, NodeStatus.BLOCKED}, (
        f"TC-04: n5 expected invalidated CHANGED/BLOCKED, got {n5_status3}"
    )
    assert state3.node_states["n5"].artifact_refs == [], (
        "TC-04: n5 artifact_refs should be cleared"
    )

    has_invalidate_evt = any(e.type == "NODE_INVALIDATED" for e in evts3)
    assert has_invalidate_evt, "TC-04: expected NODE_INVALIDATED event"


def test_tr3_3_materialize_server_only():
    """TR-3.3 TC-13 materialize server_only profile."""
    base_def = make_fs()
    server_profile = PARTICIPATION_PROFILES["server_only"].model_copy(deep=True)

    mat_def = materialize_pipeline(base_def, server_profile)

    node_ids = {n.node_id for n in mat_def.nodes}
    assert "n3" not in node_ids, "n3 (design) should be removed in server_only"
    assert "n4" not in node_ids, "n4 (client_ui) should be removed in server_only"
    assert "n1" in node_ids
    assert "n2" in node_ids
    assert "n5" in node_ids
    assert "n6" in node_ids
    assert "n7" in node_ids

    mat_state = _make_state(mat_def)
    for nid in ["n1", "n2", "n5", "n6", "n7"]:
        mat_state.node_states[nid].status = NodeStatus.DONE

    assert (
        is_pipeline_completed(mat_def, mat_state) is True
    ), "core_nodes_done模式下所有core done后应完成"

    mat_state.node_states["n5"].status = NodeStatus.READY
    assert (
        is_pipeline_completed(mat_def, mat_state) is False
    ), "缺少n5.done不应完成"


def test_tr3_4_no_design_client():
    """TR-3.4 TC-14 no_design_client + if_present 丢弃."""
    base_def = make_fs()
    no_design_profile = PARTICIPATION_PROFILES[
        "no_design_client"
    ].model_copy(deep=True)
    mat_def = materialize_pipeline(base_def, no_design_profile)

    node_ids = {n.node_id for n in mat_def.nodes}
    assert "n3" not in node_ids, "n3 (design) 应在 no_design_client 中被移除"

    n4_def = None
    for n in mat_def.nodes:
        if n.node_id == "n4":
            n4_def = n
            break
    assert n4_def is not None, "n4 应仍存在（client_ui 在 roles_present 中）"

    n4_dep_upstreams = {d.upstream for d in n4_def.deps}
    assert "n3" not in n4_dep_upstreams, (
        "n4 的 deps 中 n3 if_present 应被 dangling 裁剪"
    )

    mat_state = _make_state(mat_def)
    mat_state.node_states["n1"].status = NodeStatus.DONE
    mat_state.node_states["n2"].status = NodeStatus.DONE

    eff_deps = resolve_effective_deps("n4", mat_def, mat_state)
    eff_upstreams = {up for up, _ in eff_deps}
    assert "n3" not in eff_upstreams

    assert is_ready("n4", mat_def, mat_state) is True, (
        "R_DEPS_DONE: n2 done 后 n4 应 ready（n3 已被裁剪不算入）"
    )


def test_tr3_5_checkpoint_restart(tmp_path):
    """TR-3.5 checkpoint 重启恢复 100 次."""
    db = tmp_path / "cp.db"
    storage = SQLiteCheckpointStorage(str(db))
    pipeline_id = "pipe-restart-100"

    rng = random.Random(42)
    all_statuses = list(NodeStatus)
    base_time = "2025-06-01T00:00:00Z"

    for i in range(100):
        version = i + 1
        node_states: dict[str, NodeState] = {}
        for j in range(5):
            nid = f"n{j}"
            status = rng.choice(all_statuses)
            pending_pr = rng.randint(0, 3)
            locked_by = (
                f"bot-{rng.randint(0, 5)}" if rng.random() < 0.3 else None
            )
            change_state_options = [
                "unchanged",
                "soft_pending",
                "soft_acked",
                "incompatible_pending",
                "unchanged",
            ]
            change_state_val = rng.choice(change_state_options)
            downstream_count = rng.randint(0, 2)
            downstream_acked = [
                f"down{rng.randint(0, 10)}" for _ in range(downstream_count)
            ]
            ns = NodeState(
                node_id=nid,
                status=status,
                pending_pr_count=pending_pr,
                locked_by=locked_by,
                change_state=change_state_val,
                downstream_acked_ids=downstream_acked,
            )
            node_states[nid] = ns

        cascade_val = [{"i": i, "v": version}] if rng.random() < 0.5 else []
        state = PipelineState(
            pipeline_id=pipeline_id,
            version=version,
            status=rng.choice(list(PipelineStatus)),
            created_at=base_time,
            updated_at=base_time,
            node_states=node_states,
            cascade_pending=cascade_val,
            profile_id="profile-x",
            completed_nodes_count=rng.randint(0, 5),
        )

        cp_id = storage.save(pipeline_id, version, state)
        assert isinstance(cp_id, str) and len(cp_id) > 0

        loaded = storage.load_latest(pipeline_id)
        assert loaded is not None, f"iter {i}: load_latest returned None"

        original_json = json.dumps(state.model_dump(), sort_keys=True)
        loaded_json = json.dumps(loaded.model_dump(), sort_keys=True)
        assert original_json == loaded_json, (
            f"iter {i}: checkpoint roundtrip mismatch"
        )

    listing = storage.list(pipeline_id)
    assert len(listing) == 100


def test_tr3_6_pause_resume_cascade():
    """TR-3.6 pause/resume 级联."""
    def_ = make_fs()
    state = _make_state(def_)

    state.node_states["n1"].status = NodeStatus.READY
    s1, e1 = cascade_done("n1", def_, state)

    s_paused, ev_pause = pause_pipeline(s1, reason="emergency stop")
    s_paused_status = (
        PipelineStatus(s_paused.status)
        if isinstance(s_paused.status, str)
        else s_paused.status
    )
    assert s_paused_status == PipelineStatus.PAUSED
    assert len(s_paused.cascade_pending) >= 1
    has_pause_evt = any(e.type == "PIPELINE_PAUSED" for e in ev_pause)
    assert has_pause_evt

    s_resumed, ev_resume = resume_pipeline(def_, s_paused)
    s_resumed_status = (
        PipelineStatus(s_resumed.status)
        if isinstance(s_resumed.status, str)
        else s_resumed.status
    )
    assert s_resumed_status == PipelineStatus.ACTIVE
    assert s_resumed.cascade_pending == []
    has_resume_evt = any(e.type == "PIPELINE_RESUMED" for e in ev_resume)
    assert has_resume_evt

    n2_status = (
        NodeStatus(s_resumed.node_states["n2"].status)
        if isinstance(s_resumed.node_states["n2"].status, str)
        else s_resumed.node_states["n2"].status
    )
    n3_status = (
        NodeStatus(s_resumed.node_states["n3"].status)
        if isinstance(s_resumed.node_states["n3"].status, str)
        else s_resumed.node_states["n3"].status
    )
    assert n2_status == NodeStatus.READY, (
        f"pause/resume 后 n2 仍应 READY, got {n2_status}"
    )
    assert n3_status == NodeStatus.READY


def test_tr3_7_cascade_addendum_must():
    """TR-3.7 cascade_addendum must 级联."""
    def_ = make_fs()
    state = _make_state(def_)

    state.node_states["n1"].status = NodeStatus.DONE
    state.node_states["n2"].status = NodeStatus.DONE
    state.node_states["n5"].status = NodeStatus.DONE
    fake_artifact = ArtifactRef(
        node_id="n5",
        artifact_type="code",
        version=2,
        uri="/artifacts/n5/v2",
        ref_hash="sha256:abcdef",
        trace_id="trace-x",
    )
    state.node_states["n5"].artifact_refs = [fake_artifact]

    addendum = Addendum(
        id="add-001",
        version=1,
        change_class="must",
        incompatible_with=["n5"],
        impact_claim=["n5"],
        diff_hash="sha256:diffhash",
        author="bot-1",
        created_at="2025-06-01T10:00:00Z",
    )

    s2, evts = cascade_addendum("n2", addendum, def_, state)

    n2_addenda = s2.node_states["n2"].addenda
    assert len(n2_addenda) == 1, f"n2.addenda 期望长度 1, got {len(n2_addenda)}"
    assert n2_addenda[0].id == "add-001"

    n5_status = (
        NodeStatus(s2.node_states["n5"].status)
        if isinstance(s2.node_states["n5"].status, str)
        else s2.node_states["n5"].status
    )
    assert n5_status == NodeStatus.CHANGED, (
        f"must 级联: n5 应为 CHANGED, got {n5_status}"
    )
    assert s2.node_states["n5"].artifact_refs == [], (
        "must 级联: n5 artifact_refs 应清空"
    )

    has_must_ack = any(e.type == "ADDENDUM_MUST_ACK" for e in evts)
    assert has_must_ack, "期望 ADDENDUM_MUST_ACK 事件"
