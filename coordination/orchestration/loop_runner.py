from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from orchestration.graph import run_graph_step
from orchestration.models import (
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.checkpoints import CheckpointStorage

from config.constants import (
    LOOP_HEARTBEAT_INTERVAL_S,
    LOOP_LEASE_TTL_S,
    LOOP_SUPERVISION_INTERVAL_S,
    LOOP_MAX_STEPS,
    LOOP_COST_BUDGET_USD,
    LOOP_SLO_TOTAL_DURATION_S,
    LOOP_SLO_NODE_DURATION_S,
    LOOP_SLO_UPSTREAM_WAIT_S,
)
from monitoring.alerting import AlertManager


def _now_ts() -> float:
    return time.time()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_after(epoch: float, delta_s: int) -> str:
    return datetime.fromtimestamp(epoch + delta_s, tz=timezone.utc).isoformat()


def _lease_expired(ns: NodeState, now_ts: float) -> bool:
    if ns.lease_expires_at is None:
        return False
    try:
        exp = datetime.fromisoformat(ns.lease_expires_at).timestamp()
    except Exception:
        return False
    return now_ts >= exp


# Minimal contract the runner needs from a distributed lock. Mirrors
# orchestration/locks.py DistributedLock.
class _LockProtocol:
    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool:  # pragma: no cover
        raise NotImplementedError

    def release(self, key: str) -> None:  # pragma: no cover
        raise NotImplementedError


class LoopRunner:
    """Autonomous, safe loop executor for a single pipeline.

    Wraps ``orchestration.graph.run_graph_step`` in a supervised loop:
      * each step is checkpointed to SQLite (crash recovery),
      * an in-process lock guarantees a single runner per pipeline,
      * IN_PROGRESS nodes get a heartbeat/lease set and renewed each step,
      * a supervision tick requeues nodes whose lease expired (dead-runner
        detection) and raises the dormant alerting rules (ALR-1/2/4),
      * cost over the pipeline budget pauses the loop and raises ALR-15.

    The loop never auto-merges and always routes to a human on review /
    budget / stall — matching the "review must be clean, never auto-merge" rule.
    """

    def __init__(
        self,
        pipeline_id: str,
        pipeline_def: PipelineDefinition,
        initial_state: PipelineState,
        *,
        lock: _LockProtocol,
        checkpoint_storage: CheckpointStorage,
        cost_aggregator: Any,
        alert_manager: AlertManager,
        now_ts: Callable[[], float] = _now_ts,
        now_iso: Callable[[], str] = _now_iso,
        control_provider: Callable[[], Optional[str]] = lambda: None,
        step_fn: Callable[..., Any] | None = None,
        heartbeat_interval_s: int = LOOP_HEARTBEAT_INTERVAL_S,
        lease_ttl_s: int = LOOP_LEASE_TTL_S,
        supervision_interval_s: int = LOOP_SUPERVISION_INTERVAL_S,
        max_steps: int = LOOP_MAX_STEPS,
        cost_budget_usd: float = LOOP_COST_BUDGET_USD,
    ) -> None:
        self.pipeline_id = pipeline_id
        self.pipeline_def = pipeline_def
        self.lock = lock
        self.checkpoint_storage = checkpoint_storage
        self.cost_aggregator = cost_aggregator
        self.alert_manager = alert_manager
        self.now_ts = now_ts
        self.now_iso = now_iso
        self.control_provider = control_provider
        self.step_fn = step_fn or run_graph_step
        self.heartbeat_interval_s = heartbeat_interval_s
        self.lease_ttl_s = lease_ttl_s
        self.supervision_interval_s = supervision_interval_s
        self.max_steps = max_steps
        self.cost_budget_usd = cost_budget_usd

        # Resume from the latest checkpoint if one exists (kill -9 recovery).
        self._state: PipelineState = self._load_latest() or initial_state
        self._version = self._max_version() + 1
        self._paused = False
        self._cancelled = False
        self._requeued: set[str] = set()
        # Run a supervision tick on the first loop iteration (immediate health check).
        self._last_supervision_ts = self.now_ts() - self.supervision_interval_s - 1
        self._start_ts = self.now_ts()
        self._stall_event_written = False

    # ---- checkpoint helpers -------------------------------------------------
    def _max_version(self) -> int:
        try:
            rows = self.checkpoint_storage.list(self.pipeline_id)
            return max((r["version"] for r in rows), default=0)
        except Exception:
            return 0

    def _load_latest(self) -> PipelineState | None:
        try:
            return self.checkpoint_storage.load_latest(self.pipeline_id)
        except Exception:
            return None

    def _save_checkpoint(self) -> None:
        self.checkpoint_storage.save(self.pipeline_id, self._version, self._state)
        self._version += 1

    # ---- cost ---------------------------------------------------------------
    def _pipeline_cost_usd(self) -> float:
        try:
            return float(
                self.cost_aggregator.summary("pipeline", pipeline_id=self.pipeline_id)["total"]
            )
        except Exception:
            return 0.0

    def _over_budget(self) -> bool:
        return self._pipeline_cost_usd() > self.cost_budget_usd

    # ---- lease --------------------------------------------------------------
    def _renew_leases(self) -> None:
        now = self.now_ts()
        iso = self.now_iso()
        for ns in self._state.node_states.values():
            if ns.status == NodeStatus.IN_PROGRESS:
                ns.heartbeat_at = iso
                ns.lease_expires_at = _iso_after(now, self.lease_ttl_s)

    # ---- scheduling ---------------------------------------------------------
    def _next_step(self) -> tuple[str, dict] | None:
        state = self._state
        # 1) a READY node -> dispatch it through the crew bridge.
        for nid, ns in state.node_states.items():
            if ns.status == NodeStatus.READY:
                return (
                    "crewai_assign",
                    {
                        "node_id": nid,
                        "ready_nodes": [(nid, nid)],
                        "pipeline_def": self.pipeline_def,
                        "instances": {},
                    },
                )
        # 2) pending cascade work -> propagate downstream.
        for ns in state.node_states.values():
            if ns.status in (
                NodeStatus.PENDING_REVIEW,
                NodeStatus.REVIEW,
                NodeStatus.CHANGED,
            ):
                return ("cascade_done", {})
        return None

    # ---- supervision (dead-runner + stall detection) -------------------------
    def _supervise(self) -> None:
        now = self.now_ts()
        if now - self._last_supervision_ts < self.supervision_interval_s:
            return
        self._last_supervision_ts = now

        for nid, ns in list(self._state.node_states.items()):
            if ns.status == NodeStatus.IN_PROGRESS and _lease_expired(ns, now):
                if nid in self._requeued:
                    # Already requeued once and still dead -> pause + stall audit.
                    self._pause(f"lease expired twice on node {nid}")
                    self._write_stall_event(nid, "lease_expired_persistent")
                    continue
                # First expiry: requeue once for another attempt.
                ns.status = NodeStatus.READY
                ns.heartbeat_at = None
                ns.lease_expires_at = None
                self._requeued.add(nid)
                self.alert_manager.fire(
                    "ALR-2",
                    trace_id=self.pipeline_id,
                    node_id=nid,
                    reason="lease_expired_requeue",
                )

        # ALR-1: total pipeline duration over SLO.
        if now - self._start_ts > LOOP_SLO_TOTAL_DURATION_S:
            self.alert_manager.fire(
                "ALR-1", trace_id=self.pipeline_id, duration_s=int(now - self._start_ts)
            )
        # ALR-4: upstream wait (a BLOCKED node with no progress for too long).
        for ns in self._state.node_states.values():
            if ns.status == NodeStatus.BLOCKED and (
                now - self._start_ts > LOOP_SLO_UPSTREAM_WAIT_S
            ):
                self.alert_manager.fire(
                    "ALR-4", trace_id=self.pipeline_id, node_id=ns.node_id
                )
                break

    def _write_stall_event(self, node_id: str, reason: str) -> None:
        if self._stall_event_written:
            return
        self._stall_event_written = True
        self.alert_manager.fire(
            "ALR-2",
            trace_id=self.pipeline_id,
            node_id=node_id,
            reason=f"stall:{reason}",
            stage="audit",
        )

    # ---- pause / cancel -----------------------------------------------------
    def _pause(self, reason: str) -> None:
        self._paused = True
        try:
            self._state.status = PipelineStatus.PAUSED
        except Exception:
            pass
        self.alert_manager.fire(
            "ALR-15", trace_id=self.pipeline_id, reason=reason, action="pause"
        )

    # ---- main loop ----------------------------------------------------------
    def run(self) -> dict:
        if not self.lock.acquire(self.pipeline_id, timeout_sec=5.0):
            raise RuntimeError(f"could not acquire loop lock for {self.pipeline_id}")
        try:
            steps = 0
            events: list[dict] = []
            self._save_checkpoint()  # baseline for crash recovery
            while steps < self.max_steps:
                cmd = self.control_provider()
                if cmd == "cancel":
                    self._cancelled = True
                    break
                if cmd == "resume":
                    self._paused = False
                if self._paused:
                    break

                self._supervise()
                if self._paused or self._cancelled:
                    break

                nxt = self._next_step()
                if nxt is None:
                    break
                step_name, ctx = nxt
                new_state, step_events, err = self.step_fn(
                    step_name, self.pipeline_def, self._state, ctx
                )
                if err:
                    self.alert_manager.fire(
                        "ALR-15",
                        trace_id=self.pipeline_id,
                        step=step_name,
                        error=str(err),
                        action="step_error_pause",
                    )
                    self._pause(f"step {step_name} errored: {err}")
                    break
                self._state = new_state
                events.extend(
                    {"type": e.type, "payload": e.payload} for e in step_events
                )
                self._renew_leases()
                steps += 1
                self._save_checkpoint()

                if self._over_budget():
                    self._pause("cost over budget")
                    break

            return {
                "pipeline_id": self.pipeline_id,
                "steps": steps,
                "paused": self._paused,
                "cancelled": self._cancelled,
                "status": self._state.status,
                "events": events,
            }
        finally:
            self.lock.release(self.pipeline_id)
