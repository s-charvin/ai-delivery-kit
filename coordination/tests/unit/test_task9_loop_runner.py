from __future__ import annotations

from datetime import datetime, timezone

from orchestration.models import (
    NodeDef,
    NodeState,
    NodeStatus,
    ParticipationProfile,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.checkpoints import SQLiteCheckpointStorage
from monitoring.alerting import AlertManager

from orchestration.loop_runner import LoopRunner


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.t = start

    def ts(self) -> float:
        return self.t

    def iso(self) -> str:
        return datetime.fromtimestamp(self.t, tz=timezone.utc).isoformat()

    def advance(self, seconds: float) -> None:
        self.t += seconds


class FakeLock:
    def __init__(self) -> None:
        self.held: dict[str, bool] = {}

    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool:
        self.held[key] = True
        return True

    def release(self, key: str) -> None:
        self.held.pop(key, None)


class FakeCostAggregator:
    def __init__(self, total: float = 0.0) -> None:
        self._total = total

    def summary(self, group_by: str, pipeline_id: str | None = None, **_: object) -> dict:
        return {"rows": [], "total": self._total}


def _make_def() -> PipelineDefinition:
    node = NodeDef(node_id="n1", node_type="client_ui_impl")
    profile = ParticipationProfile(id="p", name="p", roles_present=["product"])
    return PipelineDefinition(
        id="pipe-1",
        name="t",
        nodes=[node],
        profile=profile,
        root_product_node_id="n1",
    )


def _make_state(status: NodeStatus = NodeStatus.READY, lease_expires_at=None) -> PipelineState:
    ns = NodeState(
        node_id="n1",
        status=status,
        artifact_refs=[],
        lease_expires_at=lease_expires_at,
    )
    return PipelineState(
        pipeline_id="pipe-1",
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        node_states={"n1": ns},
    )


def _fake_step_mark_done(step_name, pipeline_def, state, ctx):
    new_state = PipelineState.model_validate(state.model_dump())
    if step_name == "crewai_assign":
        nid = ctx.get("node_id")
        ns = new_state.node_states.get(nid)
        if ns is not None:
            ns.status = NodeStatus.DONE
    return new_state, [], None


def test_lease_expiry_requeues_node_and_fires_alr2(tmp_path):
    clock = FakeClock(start=1_000_000.0)
    # lease already expired (expires at start)
    state = _make_state(status=NodeStatus.IN_PROGRESS, lease_expires_at=clock.iso())
    lock = FakeLock()
    ckpt = SQLiteCheckpointStorage(str(tmp_path / "ckpt.db"))
    alerts = AlertManager(sqlite_path=tmp_path / "alerts.db")

    runner = LoopRunner(
        "pipe-1", _make_def(), state,
        lock=lock, checkpoint_storage=ckpt,
        cost_aggregator=FakeCostAggregator(0.0), alert_manager=alerts,
        now_ts=clock.ts, now_iso=clock.iso, step_fn=_fake_step_mark_done,
    )
    clock.advance(100)  # now far past the lease; clears supervision interval
    result = runner.run()

    # The dead IN_PROGRESS node was requeued (otherwise the loop would take 0 steps:
    # with only an IN_PROGRESS node and no cascade pending, _next_step yields None).
    assert result["steps"] >= 1
    # ALR-2 was raised by the supervision tick.
    fired = [a["alert_id"] for a in alerts.list_alerts()]
    assert "ALR-2" in fired


def test_cost_over_budget_pauses_and_fires_alr15(tmp_path):
    clock = FakeClock()
    state = _make_state(status=NodeStatus.READY)

    lock = FakeLock()
    ckpt = SQLiteCheckpointStorage(str(tmp_path / "ckpt.db"))
    alerts = AlertManager(sqlite_path=tmp_path / "alerts.db")

    runner = LoopRunner(
        "pipe-1", _make_def(), state,
        lock=lock, checkpoint_storage=ckpt,
        cost_aggregator=FakeCostAggregator(total=999.0), alert_manager=alerts,
        now_ts=clock.ts, now_iso=clock.iso, step_fn=_fake_step_mark_done,
    )
    result = runner.run()

    assert result["paused"] is True
    assert runner._state.status == PipelineStatus.PAUSED
    fired = [a["alert_id"] for a in alerts.list_alerts()]
    assert "ALR-15" in fired


def test_checkpoint_recovery_after_kill(tmp_path):
    clock = FakeClock()
    # Two nodes; runner A will only process one step then "die" (max_steps=1).
    defn = PipelineDefinition(
        id="pipe-1", name="t",
        nodes=[NodeDef(node_id="n1", node_type="client_ui_impl"),
               NodeDef(node_id="n2", node_type="server_impl")],
        profile=ParticipationProfile(id="p", name="p", roles_present=["product"]),
        root_product_node_id="n1",
    )
    st = PipelineState(
        pipeline_id="pipe-1", version=1, status=PipelineStatus.ACTIVE,
        created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z",
        node_states={
            "n1": NodeState(node_id="n1", status=NodeStatus.READY),
            "n2": NodeState(node_id="n2", status=NodeStatus.READY),
        },
    )
    ckpt = SQLiteCheckpointStorage(str(tmp_path / "ckpt.db"))
    alerts = AlertManager(sqlite_path=tmp_path / "alerts.db")
    lock = FakeLock()

    ra = LoopRunner(
        "pipe-1", defn, st, lock=lock, checkpoint_storage=ckpt,
        cost_aggregator=FakeCostAggregator(0.0), alert_manager=alerts,
        now_ts=clock.ts, now_iso=clock.iso, step_fn=_fake_step_mark_done,
        max_steps=1,
    )
    ra.run()  # processes n1 only, then "dies"

    # New runner B with the SAME checkpoint storage resumes from the snapshot.
    rb = LoopRunner(
        "pipe-1", defn, st, lock=lock, checkpoint_storage=ckpt,
        cost_aggregator=FakeCostAggregator(0.0), alert_manager=alerts,
        now_ts=clock.ts, now_iso=clock.iso, step_fn=_fake_step_mark_done,
    )
    # B must have recovered n1 already done from the checkpoint.
    assert rb._state.node_states["n1"].status == NodeStatus.DONE
    rb.run()
    assert rb._state.node_states["n2"].status == NodeStatus.DONE
