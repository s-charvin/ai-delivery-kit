from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from mcp.tracing import LANGFUSE_WAL_DIR, LANGFUSE_CLIENT


class CostController:
    """Pure policy evaluator for cost thresholds.

    The running totals previously kept here (per-task tokens, per-agent / pipeline /
    platform daily USD) were a second, in-memory copy of what the persistent ledger
    (monitoring.cost.CostAggregator) already tracks. This class no longer accumulates
    anything: callers supply the current accumulated value (typically read from the
    ledger) and the controller only evaluates it against THRESHOLDS and emits an
    observability span when a threshold is crossed.
    """

    THRESHOLDS: dict[str, dict[str, Any]] = {
        "task": {"tokens": 20_000, "retries": 3, "action": "needs_human"},
        "agent": {"usd_per_day": 10.0, "action": "queue"},
        "pipeline": {"usd": 100.0, "action": "pause_pipeline"},
        "platform": {"usd_per_day": 4000.0, "action": "switch_cheap_model"},
    }

    def __init__(self, cost_aggregator: Any | None = None) -> None:
        # No internal accumulators. Optionally wired to the ledger for stat lookups.
        self._aggregator = cost_aggregator

    def _write_cost_span(
        self, name: str, level: str, payload: dict, trace_id: str | None = None
    ) -> None:
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
        try:
            LANGFUSE_CLIENT._write_wal(span)
        except Exception:
            pass

    def evaluate_task_tokens(self, accum_tokens: int) -> dict[str, Any]:
        threshold = self.THRESHOLDS["task"]["tokens"]
        needs_human = accum_tokens >= threshold
        if needs_human:
            self._write_cost_span(
                "TASK-TOKEN-THRESHOLD-TRIGGERED",
                "task",
                {"accum_tokens": accum_tokens, "threshold": threshold},
            )
        return {
            "needs_human": needs_human,
            "accum_tokens": accum_tokens,
            "threshold": threshold,
        }

    def evaluate_agent_usd_daily(self, accum_usd: float) -> dict[str, Any]:
        threshold = self.THRESHOLDS["agent"]["usd_per_day"]
        action = self.THRESHOLDS["agent"]["action"] if accum_usd >= threshold else None
        if action:
            self._write_cost_span(
                "AGENT-DAILY-THRESHOLD-TRIGGERED",
                "agent",
                {"accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def evaluate_pipeline_usd(self, accum_usd: float) -> dict[str, Any]:
        threshold = self.THRESHOLDS["pipeline"]["usd"]
        action = self.THRESHOLDS["pipeline"]["action"] if accum_usd >= threshold else None
        if action:
            self._write_cost_span(
                "PIPELINE-THRESHOLD-TRIGGERED",
                "pipeline",
                {"accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def evaluate_platform_usd_daily(self, accum_usd: float) -> dict[str, Any]:
        threshold = self.THRESHOLDS["platform"]["usd_per_day"]
        action = (
            self.THRESHOLDS["platform"]["action"] if accum_usd >= threshold else None
        )
        if action:
            self._write_cost_span(
                "PLATFORM-DAILY-THRESHOLD-TRIGGERED",
                "platform",
                {"accum_usd": accum_usd, "threshold": threshold},
            )
        return {"action": action, "accum_usd": accum_usd, "threshold": threshold}

    def get_task_cost_stats(self, task_id: str) -> dict[str, float]:
        """Delegate to the ledger when wired; otherwise report empty stats."""
        if self._aggregator is None:
            return {"mean": 0.0, "std": 0.0, "count": 0}
        return self._aggregator.task_cost_stats(task_id)

    def cost_summary(self, group_by: str = "pipeline") -> dict[str, Any]:
        if self._aggregator is None:
            return {"group_by": group_by, "items": {}, "total": 0.0}
        return self._aggregator.summary(group_by)
