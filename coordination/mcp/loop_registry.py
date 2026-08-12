"""In-process registry for autonomous LoopRunner instances (MCP tools)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from orchestration.checkpoints import SQLiteCheckpointStorage
from orchestration.loop_runner import LoopRunner
from orchestration.locks import ThreadingLockImpl
from orchestration.models import NodeStatus, PipelineState
from orchestration.skill_bridge import SkillBridgeContext, flush_back, load_requirement
from monitoring.alerting import AlertManager
from monitoring.cost import CostAggregator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LoopHandle:
    pipeline_id: str
    runner: LoopRunner
    bridge_ctx: SkillBridgeContext
    thread: threading.Thread | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    overbudget_approved: bool = False


class LoopRegistry:
    def __init__(self, *, data_dir: Path | str | None = None) -> None:
        base = Path(data_dir) if data_dir is not None else Path(".coordination-loop")
        base.mkdir(parents=True, exist_ok=True)
        self._data_dir = base
        self._handles: dict[str, LoopHandle] = {}
        self._control: dict[str, str | None] = {}
        self._lock = threading.RLock()
        self._cost = CostAggregator(base / "cost.db")
        self._alerts = AlertManager(sqlite_path=base / "alerts.db")
        self._checkpoint = SQLiteCheckpointStorage(str(base / "checkpoints.db"))
        self._thread_lock = ThreadingLockImpl()

    def _control_provider(self, pipeline_id: str) -> Callable[[], str | None]:
        def _read() -> str | None:
            with self._lock:
                return self._control.get(pipeline_id)

        return _read

    def start(
        self,
        req_root: str,
        *,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        req_path = Path(req_root).resolve()
        repo = Path(repo_root).resolve() if repo_root else req_path.parent.parent.parent

        pipeline_def, initial_state, bridge_ctx = load_requirement(req_path, repo_root=repo)
        pipeline_id = pipeline_def.id

        with self._lock:
            if pipeline_id in self._handles:
                handle = self._handles[pipeline_id]
                if handle.thread and handle.thread.is_alive():
                    return {"pipeline_id": pipeline_id, "already_running": True}
            self._control[pipeline_id] = None

        runner = LoopRunner(
            pipeline_id,
            pipeline_def,
            initial_state,
            lock=self._thread_lock,
            checkpoint_storage=self._checkpoint,
            cost_aggregator=self._cost,
            alert_manager=self._alerts,
            control_provider=self._control_provider(pipeline_id),
        )

        handle = LoopHandle(
            pipeline_id=pipeline_id,
            runner=runner,
            bridge_ctx=bridge_ctx,
        )

        def _run() -> None:
            try:
                handle.result = runner.run()
                flush_back(runner._state, bridge_ctx)
            except Exception as exc:  # pragma: no cover - surfaced via loop_status
                handle.error = str(exc)

        thread = threading.Thread(target=_run, name=f"loop-{pipeline_id}", daemon=True)
        handle.thread = thread

        with self._lock:
            self._handles[pipeline_id] = handle
        thread.start()
        return {"pipeline_id": pipeline_id, "started": True}

    def stop(self, pipeline_id: str) -> dict[str, Any]:
        with self._lock:
            self._control[pipeline_id] = "cancel"
            handle = self._handles.get(pipeline_id)
        if handle is None:
            return {"pipeline_id": pipeline_id, "found": False}
        if handle.thread:
            handle.thread.join(timeout=30.0)
        return {"pipeline_id": pipeline_id, "stopped": True}

    def status(self, pipeline_id: str) -> dict[str, Any]:
        with self._lock:
            handle = self._handles.get(pipeline_id)
        if handle is None:
            return {"pipeline_id": pipeline_id, "found": False}
        alive = bool(handle.thread and handle.thread.is_alive())
        state: PipelineState = handle.runner._state
        nodes = {
            nid: (ns.status.value if isinstance(ns.status, NodeStatus) else str(ns.status))
            for nid, ns in state.node_states.items()
        }
        return {
            "pipeline_id": pipeline_id,
            "running": alive,
            "paused": handle.runner._paused,
            "cancelled": handle.runner._cancelled,
            "pipeline_status": state.status.value if hasattr(state.status, "value") else str(state.status),
            "nodes": nodes,
            "result": handle.result,
            "error": handle.error,
            "overbudget_approved": handle.overbudget_approved,
        }

    def stall_report(self, pipeline_id: str) -> dict[str, Any]:
        alerts = self._alerts.list_alerts(trace_id=pipeline_id)
        stalled = [a for a in alerts if a.get("alert_id") in {"ALR-1", "ALR-2", "ALR-4", "ALR-15"}]
        return {"pipeline_id": pipeline_id, "stall_alerts": stalled}

    def intervene(
        self,
        pipeline_id: str,
        action: str,
        *,
        actor: str = "human",
        node_id: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        allowed = {
            "pause",
            "resume",
            "cancel",
            "retry_node",
            "skip_node",
            "approve_overbudget",
        }
        if action not in allowed:
            raise ValueError(f"unsupported intervene action: {action!r}")

        with self._lock:
            handle = self._handles.get(pipeline_id)
            if handle is None:
                return {"pipeline_id": pipeline_id, "found": False}

            audit_entry = {
                "at": _now_iso(),
                "actor": actor,
                "action": action,
                "node_id": node_id,
                "reason": reason,
            }
            handle.audit_log.append(audit_entry)

            if action == "pause":
                self._control[pipeline_id] = "pause"
                handle.runner._paused = True
            elif action == "resume":
                if not reason.strip():
                    raise ValueError("resume requires a non-empty audit reason")
                self._control[pipeline_id] = "resume"
                handle.runner._paused = False
            elif action == "cancel":
                self._control[pipeline_id] = "cancel"
            elif action == "approve_overbudget":
                if not reason.strip():
                    raise ValueError("approve_overbudget requires a non-empty audit reason")
                handle.overbudget_approved = True
                # Lift the ceiling so the runner can continue after human approval.
                spent = handle.runner._pipeline_cost_usd()
                handle.runner.cost_budget_usd = max(
                    handle.runner.cost_budget_usd, spent + 1.0
                )
                handle.runner._paused = False
                self._control[pipeline_id] = "resume"
            elif action == "retry_node":
                if not node_id:
                    raise ValueError("retry_node requires node_id")
                ns = handle.runner._state.node_states.get(node_id)
                if ns is None:
                    raise ValueError(f"unknown node_id: {node_id}")
                ns.status = NodeStatus.READY
                ns.heartbeat_at = None
                ns.lease_expires_at = None
                handle.runner._paused = False
                self._control[pipeline_id] = "resume"
            elif action == "skip_node":
                if not node_id:
                    raise ValueError("skip_node requires node_id")
                ns = handle.runner._state.node_states.get(node_id)
                if ns is None:
                    raise ValueError(f"unknown node_id: {node_id}")
                ns.status = NodeStatus.SKIPPED

        flush_back(handle.runner._state, handle.bridge_ctx)
        return {
            "pipeline_id": pipeline_id,
            "action": action,
            "audit": audit_entry,
            "status": self.status(pipeline_id),
        }


_registry: LoopRegistry | None = None


def get_loop_registry() -> LoopRegistry:
    global _registry
    if _registry is None:
        _registry = LoopRegistry()
    return _registry
