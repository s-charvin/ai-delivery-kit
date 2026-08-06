from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import uuid

from mcp.tracing import LANGFUSE_WAL_DIR, LANGFUSE_CLIENT


class CostController:
    THRESHOLDS: dict[str, dict[str, Any]] = {
        "task": {"tokens": 20_000, "retries": 3, "action": "needs_human"},
        "agent": {"usd_per_day": 10.0, "action": "queue"},
        "pipeline": {"usd": 100.0, "action": "pause_pipeline"},
        "platform": {"usd_per_day": 4000.0, "action": "switch_cheap_model"},
    }

    def __init__(self) -> None:
        self._task_token_accum: dict[str, int] = defaultdict(int)
        self._task_retries: dict[str, int] = defaultdict(int)
        self._agent_daily_usd: dict[str, float] = defaultdict(float)
        self._pipeline_usd: dict[str, float] = defaultdict(float)
        self._platform_daily_usd: float = 0.0
        self._history: dict[str, list[float]] = defaultdict(list)
        self._spans: list[dict] = []

    def _write_cost_span(self, name: str, level: str, payload: dict, trace_id: str | None = None) -> None:
        span = {
            "trace_id": trace_id or uuid.uuid4().hex,
            "span_id": uuid.uuid4().hex,
            "name": name,
            "span_type": "cost",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "inputs": {"level": level, **payload},
            "outputs": None,
            "error": None,
            "metadata": {"audit_code": "COST"},
        }
        self._spans.append(span)
        try:
            LANGFUSE_CLIENT._write_wal(span)
        except Exception:
            pass

    def on_task_token_count(
        self,
        task_id: str,
        delta_tokens: int,
        accum: int | None = None,
        pipeline: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        if accum is None:
            self._task_token_accum[task_id] += delta_tokens
            accum = self._task_token_accum[task_id]
        else:
            self._task_token_accum[task_id] = accum

        threshold = self.THRESHOLDS["task"]["tokens"]
        needs_human = accum >= threshold
        reset_retry = False
        if needs_human:
            self._write_cost_span(
                "TASK-TOKEN-THRESHOLD-TRIGGERED",
                "task",
                {"task_id": task_id, "accum": accum, "threshold": threshold, "pipeline": pipeline, "agent": agent},
            )
        return {
            "needs_human": needs_human,
            "reset_retry": reset_retry,
            "accum_tokens": accum,
            "delta_tokens": delta_tokens,
        }

    def on_agent_usd_daily(self, agent_id: str, accum_usd: float) -> dict[str, Any]:
        self._agent_daily_usd[agent_id] = accum_usd
        threshold = self.THRESHOLDS["agent"]["usd_per_day"]
        action = None
        if accum_usd >= threshold:
            action = self.THRESHOLDS["agent"]["action"]
            self._write_cost_span(
                "AGENT-DAILY-THRESHOLD-TRIGGERED",
                "agent",
                {"agent_id": agent_id, "accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def on_pipeline_usd(self, pid: str, accum_usd: float) -> dict[str, Any]:
        self._pipeline_usd[pid] = accum_usd
        threshold = self.THRESHOLDS["pipeline"]["usd"]
        action = None
        if accum_usd >= threshold:
            action = self.THRESHOLDS["pipeline"]["action"]
            self._write_cost_span(
                "PIPELINE-THRESHOLD-TRIGGERED",
                "pipeline",
                {"pipeline_id": pid, "accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def on_platform_usd_daily(self, accum_usd: float) -> dict[str, Any]:
        self._platform_daily_usd = accum_usd
        threshold = self.THRESHOLDS["platform"]["usd_per_day"]
        action = None
        if accum_usd >= threshold:
            action = self.THRESHOLDS["platform"]["action"]
            self._write_cost_span(
                "PLATFORM-DAILY-THRESHOLD-TRIGGERED",
                "platform",
                {"accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def record_task_cost(self, task_id: str, cost_usd: float) -> None:
        self._history[task_id].append(cost_usd)

    def cost_summary(self, group_by: str = "pipeline") -> dict[str, Any]:
        if group_by == "pipeline":
            return {
                "group_by": "pipeline",
                "items": {pid: {"usd": usd} for pid, usd in self._pipeline_usd.items()},
                "total_usd": sum(self._pipeline_usd.values()),
            }
        elif group_by == "agent":
            return {
                "group_by": "agent",
                "items": {aid: {"usd_daily": usd} for aid, usd in self._agent_daily_usd.items()},
                "total_usd_daily": sum(self._agent_daily_usd.values()),
            }
        elif group_by == "task":
            return {
                "group_by": "task",
                "items": {tid: {"tokens": tok} for tid, tok in self._task_token_accum.items()},
                "total_tokens": sum(self._task_token_accum.values()),
            }
        elif group_by == "platform":
            return {
                "group_by": "platform",
                "usd_daily": self._platform_daily_usd,
                "threshold": self.THRESHOLDS["platform"]["usd_per_day"],
            }
        return {"group_by": group_by, "items": {}}

    def get_task_cost_stats(self, task_id: str) -> dict[str, float]:
        costs = self._history.get(task_id, [])
        if not costs:
            return {"mean": 0.0, "std": 0.0, "count": 0}
        n = len(costs)
        mean = sum(costs) / n
        var = sum((c - mean) ** 2 for c in costs) / n if n > 0 else 0.0
        std = var ** 0.5
        return {"mean": mean, "std": std, "count": n}
