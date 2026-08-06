from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
import uuid

from mcp.tracing import LANGFUSE_CLIENT


class ScopeMismatchError(Exception):
    def __init__(self, message: str, error_code: str = "E_TOKEN_SCOPE_MISMATCH") -> None:
        super().__init__(message)
        self.error_code = error_code
        self.code = error_code


ALR13_SPAN_TYPE = "ALR-13-CYCLE-DETECT"
ALR14_SPAN_TYPE = "ALR-14-SCOPE-MISMATCH"
ALR15_SPAN_TYPE = "ALR-15-COST-ANOMALY"


class BehaviorGuard:
    def __init__(self, cost_controller: Any | None = None) -> None:
        self._submit_sequence: dict[tuple[str, str], list[str]] = defaultdict(list)
        self._alr_spans: list[dict] = []
        self._cost_controller = cost_controller

    def _write_alr_span(
        self,
        span_type: str,
        trace_id: str,
        name: str,
        inputs: dict,
        reason: str,
    ) -> None:
        span = {
            "trace_id": trace_id or uuid.uuid4().hex,
            "span_id": uuid.uuid4().hex,
            "name": name,
            "span_type": span_type,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "inputs": inputs,
            "outputs": None,
            "error": reason,
            "metadata": {"audit_code": span_type},
        }
        self._alr_spans.append(span)
        try:
            LANGFUSE_CLIENT._write_wal(span)
        except Exception:
            pass

    def before_mcp_call(self, agent_id: str, node_id: str, tool_name: str) -> dict[str, Any]:
        key = (agent_id, node_id)
        seq = self._submit_sequence[key]
        if tool_name in ("submit_artifact", "approve_pr"):
            seq.append(tool_name)
        if len(seq) > 5:
            repeat_count = len(seq)
            trace_id = uuid.uuid4().hex
            self._write_alr_span(
                ALR13_SPAN_TYPE,
                trace_id,
                "ALR-13-cycle-detected",
                {
                    "agent_id": agent_id,
                    "node_id": node_id,
                    "tool_name": tool_name,
                    "repeat_sequence": list(seq),
                    "repeat_count": repeat_count,
                },
                f"Same (agent_id, node_id) submit sequence exceeds 5: count={repeat_count}",
            )
            return {"alarm": True, "repeat_count": repeat_count, "trace_id": trace_id, "span_type": ALR13_SPAN_TYPE}
        return {"alarm": False, "repeat_count": len(seq)}

    def check_scope(self, allowed_tools: list[str], tool_name: str, trace_id: str) -> None:
        if tool_name not in allowed_tools:
            self._write_alr_span(
                ALR14_SPAN_TYPE,
                trace_id,
                "ALR-14-scope-mismatch",
                {
                    "tool_name": tool_name,
                    "allowed_tools": list(allowed_tools),
                },
                f"Tool '{tool_name}' not in allowed scope {allowed_tools}",
            )
            msg = f"E_TOKEN_SCOPE_MISMATCH: Tool '{tool_name}' not in allowed scope {allowed_tools}"
            raise ScopeMismatchError(msg)

    def check_task_cost_anomaly(self, task_id: str, cost_usd: float) -> dict[str, Any]:
        if self._cost_controller is None:
            return {"anomaly": False}
        stats = self._cost_controller.get_task_cost_stats(task_id)
        if stats["count"] < 3:
            return {"anomaly": False, "stats": stats}
        threshold = stats["mean"] + 3 * stats["std"]
        anomaly = cost_usd > threshold
        if anomaly:
            trace_id = uuid.uuid4().hex
            self._write_alr_span(
                ALR15_SPAN_TYPE,
                trace_id,
                "ALR-15-cost-anomaly",
                {
                    "task_id": task_id,
                    "cost_usd": cost_usd,
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "threshold_3sigma": threshold,
                },
                f"Task cost {cost_usd} USD exceeds mean+3std ({threshold} USD)",
            )
            return {
                "anomaly": True,
                "cost_usd": cost_usd,
                "threshold": threshold,
                "stats": stats,
                "trace_id": trace_id,
                "span_type": ALR15_SPAN_TYPE,
            }
        return {"anomaly": False, "cost_usd": cost_usd, "threshold": threshold, "stats": stats}
