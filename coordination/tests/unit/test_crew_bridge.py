from __future__ import annotations

from orchestration.models import (
    ArtifactRef,
    NodeDef,
    NodeState,
    NodeStatus,
    ParticipationProfile,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)

from crew.bridge import (
    EVENT_CREWAI_DISPATCHED,
    EVENT_NODE_DONE_VIA_CREW,
    EVENT_STUB_WARN,
    CrewGraphBridge,
)


def _make_pipeline(node_status: NodeStatus, artifact_refs=None):
    node = NodeDef(node_id="n1", node_type="client_ui_impl")
    profile = ParticipationProfile(id="p", name="p", roles_present=["product"])
    pipeline_def = PipelineDefinition(
        id="pipe-1",
        name="t",
        nodes=[node],
        profile=profile,
        root_product_node_id="n1",
    )
    ns = NodeState(
        node_id="n1",
        status=node_status,
        artifact_refs=artifact_refs or [],
    )
    state = PipelineState(
        pipeline_id="pipe-1",
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        node_states={"n1": ns},
    )
    return pipeline_def, state


def _fake_crew(result_raw: str = "submit_artifact done"):
    class _Crew:
        def kickoff(self):
            return type("R", (), {"raw": result_raw})()

    return _Crew


def test_bridge_marks_done_when_artifact_refs_present(monkeypatch):
    """DONE is driven by produced artifacts, not by parsing the crew result string."""
    monkeypatch.setattr(
        "crew.bridge.build_crew_for_ready_nodes", lambda **k: _fake_crew()()
    )
    refs = [
        ArtifactRef(
            node_id="n1",
            artifact_type="ui",
            version=1,
            uri="file://x",
            ref_hash="h",
            trace_id="t",
        )
    ]
    pipeline_def, state = _make_pipeline(NodeStatus.READY, artifact_refs=refs)
    out = CrewGraphBridge().dispatch_ready_nodes(
        "pipe-1", [("n1", "i1")], pipeline_def, state, {"n1": object()}
    )

    assert any(e.type == EVENT_CREWAI_DISPATCHED for e in out["events"])
    assert any(e.type == EVENT_NODE_DONE_VIA_CREW for e in out["events"])
    assert all(e.type != EVENT_STUB_WARN for e in out["events"])
    assert out["pipeline_state"].node_states["n1"].status == NodeStatus.DONE


def test_bridge_no_string_parsing_does_not_fake_done(monkeypatch):
    """Even if the crew result string hints submit/approve, no artifact_refs => not DONE."""
    monkeypatch.setattr(
        "crew.bridge.build_crew_for_ready_nodes", lambda **k: _fake_crew()()
    )
    pipeline_def, state = _make_pipeline(NodeStatus.READY)  # no artifact_refs
    out = CrewGraphBridge().dispatch_ready_nodes(
        "pipe-1", [("n1", "i1")], pipeline_def, state, {"n1": object()}
    )

    assert out["pipeline_state"].node_states["n1"].status == NodeStatus.READY
    assert all(e.type != EVENT_NODE_DONE_VIA_CREW for e in out["events"])


def test_bridge_no_production_stub_fallback(monkeypatch):
    """A crew failure surfaces a warning and leaves node statuses unchanged."""

    class _BoomCrew:
        def kickoff(self):
            raise RuntimeError("crew exploded")

    monkeypatch.setattr(
        "crew.bridge.build_crew_for_ready_nodes", lambda **k: _BoomCrew()
    )
    pipeline_def, state = _make_pipeline(NodeStatus.READY)
    out = CrewGraphBridge().dispatch_ready_nodes(
        "pipe-1", [("n1", "i1")], pipeline_def, state, {"n1": object()}
    )

    assert any(e.type == EVENT_STUB_WARN for e in out["events"])
    assert out["crew_result"] is None
    # state is returned unchanged (no silent DONE)
    assert out["pipeline_state"].node_states["n1"].status == NodeStatus.READY
    assert all(e.type != EVENT_NODE_DONE_VIA_CREW for e in out["events"])
