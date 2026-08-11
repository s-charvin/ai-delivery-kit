from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Literal


class CostAggregator:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = Path(sqlite_path)
        if not self.sqlite_path.parent.exists():
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_events (
                id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                task_id TEXT,
                agent_id TEXT,
                pipeline_id TEXT,
                platform_id TEXT,
                cost_usd REAL NOT NULL DEFAULT 0,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                span_ref_id TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_task ON cost_events(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_agent ON cost_events(agent_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cost_pipeline ON cost_events(pipeline_id)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cost_ts ON cost_events(ts)")
        self._conn.commit()

    def record(
        self,
        task_id: str | None = None,
        agent_id: str | None = None,
        pipeline_id: str | None = None,
        platform_id: str | None = "default",
        cost_usd: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        span_ref_id: str | None = None,
        ts: float | None = None,
        **_: Any,
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO cost_events (
                id, ts, task_id, agent_id, pipeline_id, platform_id,
                cost_usd, tokens_in, tokens_out, span_ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                ts if ts is not None else time.time(),
                task_id,
                agent_id,
                pipeline_id,
                platform_id,
                float(cost_usd),
                int(tokens_in),
                int(tokens_out),
                span_ref_id,
            ),
        )
        self._conn.commit()

    def summary(
        self,
        group_by: Literal["task", "agent", "pipeline", "platform"],
        from_ts: float | None = None,
        to_ts: float | None = None,
        pipeline_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict:
        where_clauses: list[str] = ["1=1"]
        params: list[Any] = []
        if from_ts is not None:
            where_clauses.append("ts >= ?")
            params.append(float(from_ts))
        if to_ts is not None:
            where_clauses.append("ts <= ?")
            params.append(float(to_ts))
        if pipeline_id is not None:
            where_clauses.append("pipeline_id = ?")
            params.append(pipeline_id)
        if agent_id is not None:
            where_clauses.append("agent_id = ?")
            params.append(agent_id)

        where_sql = " AND ".join(where_clauses)

        group_column = {
            "task": "task_id",
            "agent": "agent_id",
            "pipeline": "pipeline_id",
            "platform": "platform_id",
        }[group_by]

        query = f"""
            SELECT
                {group_column} AS key,
                SUM(cost_usd) AS total_usd,
                SUM(tokens_in) AS total_tokens_in,
                SUM(tokens_out) AS total_tokens_out,
                COUNT(*) AS cnt
            FROM cost_events
            WHERE {where_sql}
            GROUP BY {group_column}
            ORDER BY total_usd DESC
        """

        cur = self._conn.cursor()
        cur.execute(query, params)
        rows_raw = cur.fetchall()
        rows: list[dict] = []
        total = 0.0
        for row in rows_raw:
            key = row["key"]
            if key is None:
                continue
            r = {
                group_by: key,
                "cost_usd": round(float(row["total_usd"] or 0.0), 6),
                "tokens_in": int(row["total_tokens_in"] or 0),
                "tokens_out": int(row["total_tokens_out"] or 0),
                "count": int(row["cnt"] or 0),
            }
            rows.append(r)
            total += r["cost_usd"]

        total = round(total, 6)
        return {"rows": rows, "total": total}

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def task_cost_stats(self, task_id: str) -> dict[str, float]:
        """Mean / std / count of recorded cost_usd for a task (ledger-backed)."""
        cur = self._conn.cursor()
        cur.execute("SELECT cost_usd FROM cost_events WHERE task_id = ?", (task_id,))
        costs = [float(r["cost_usd"]) for r in cur.fetchall()]
        if not costs:
            return {"mean": 0.0, "std": 0.0, "count": 0}
        n = len(costs)
        mean = sum(costs) / n
        var = sum((c - mean) ** 2 for c in costs) / n
        return {
            "mean": round(mean, 6),
            "std": round(var**0.5, 6),
            "count": n,
        }
