from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALERTS: dict[str, dict] = {
    "ALR-1": {
        "name": "Pipeline 完成时长超时 SLO 90min 1h",
        "severity": "warn",
        "rule": "duration_seconds > 3600",
    },
    "ALR-2": {
        "name": "Node 单产物 > 1h",
        "severity": "warn",
        "rule": "node_duration_s > 3600",
    },
    "ALR-3": {
        "name": "Ready 队列积压 > 5",
        "severity": "warn",
        "rule": "ready_count > 5",
    },
    "ALR-4": {
        "name": "Dep 上游超时 > 45min",
        "severity": "warn",
        "rule": "upstream_wait > 2700",
    },
    "ALR-5": {
        "name": "Review 自动拒绝率 > 30%",
        "severity": "warn",
        "rule": "auto_reject_pct > 30",
    },
    "ALR-6": {
        "name": "PR 重开率 > 20%",
        "severity": "warn",
        "rule": "pr_reopen_rate > 20",
    },
    "ALR-7": {
        "name": "Hash 链缺口",
        "severity": "critical",
        "rule": "hash_chain_broken",
    },
    "ALR-8": {
        "name": "审计 WORM 写入失败",
        "severity": "critical",
        "rule": "worm_insert_fail",
    },
    "ALR-9": {
        "name": "Langfuse 发送失败率 > 10%",
        "severity": "warn",
        "rule": "langfuse_fail_rate > 10",
    },
    "ALR-10": {
        "name": "Hub 仓响应 P95 > 10s",
        "severity": "warn",
        "rule": "hub_p95_ms > 10000",
    },
    "ALR-11": {
        "name": "Vault 不可达",
        "severity": "critical",
        "rule": "vault_down",
    },
    "ALR-12": {
        "name": "外部依赖健康 3 fail",
        "severity": "critical",
        "rule": "ext_health_3_fail",
    },
    "ALR-13": {
        "name": "Agent 行为循环",
        "severity": "warn",
        "rule": "cycle_seq > 5",
    },
    "ALR-14": {
        "name": "越权访问拦截",
        "severity": "critical",
        "rule": "scope_mismatch",
    },
    "ALR-15": {
        "name": "成本异常",
        "severity": "critical",
        "rule": "cost_over_3sigma or tier_threshold_triggered",
    },
}


class AlertManager:
    def __init__(
        self,
        sqlite_path: Path | None = None,
        worm_storage: Any | None = None,
        channels: list[str] | None = None,
    ) -> None:
        self.channels = channels or ["console", "audit_event"]
        self.worm_storage = worm_storage
        if sqlite_path is None:
            sqlite_path = Path("data/alerts.db")
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                name TEXT NOT NULL,
                rule TEXT,
                trace_id TEXT,
                extra TEXT,
                ts REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_alert_id ON alerts(alert_id)")
        self._conn.commit()

    def _write_audit_event(self, alert_row: dict) -> None:
        if self.worm_storage is None:
            return
        try:
            from audit.worm_storage import AuditLogEntry

            entry = AuditLogEntry(
                prev_hash="",
                action="alert_fired",
                actor="alert_manager",
                payload={
                    "alert_id": alert_row["alert_id"],
                    "severity": alert_row["severity"],
                    "name": alert_row["name"],
                    "trace_id": alert_row.get("trace_id"),
                    "extra": alert_row.get("extra_raw"),
                },
                hash="",
                created_at=alert_row["created_at"],
                trace_id=alert_row.get("trace_id"),
            )
            self.worm_storage.insert(entry)
        except Exception:
            pass

    def fire(
        self,
        alert_id: str,
        trace_id: str | None = None,
        **extra: Any,
    ) -> dict:
        spec = ALERTS.get(alert_id, {"name": alert_id, "severity": "warn", "rule": ""})
        row_id = uuid.uuid4().hex
        ts_now = time.time()
        created_at = datetime.now(timezone.utc).isoformat()
        name = spec.get("name", alert_id)
        severity = spec.get("severity", "warn")
        rule = spec.get("rule", "")
        extra_json = json.dumps(extra, sort_keys=True, ensure_ascii=False)
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO alerts (
                id, alert_id, severity, name, rule, trace_id, extra, ts, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                alert_id,
                severity,
                name,
                rule,
                trace_id,
                extra_json,
                ts_now,
                created_at,
            ),
        )
        self._conn.commit()
        row = {
            "id": row_id,
            "alert_id": alert_id,
            "severity": severity,
            "name": name,
            "rule": rule,
            "trace_id": trace_id,
            "extra": extra,
            "extra_raw": extra_json,
            "ts": ts_now,
            "created_at": created_at,
        }
        if "console" in self.channels:
            print(
                f"[ALERT][{severity.upper()}] {alert_id} {name} | trace={trace_id} | extra={extra}"
            )
        if "audit_event" in self.channels:
            self._write_audit_event(row)
        return row

    def list_alerts(
        self,
        severity: str | None = None,
        since_ts: float | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        where: list[str] = ["1=1"]
        params: list[Any] = []
        if severity is not None:
            where.append("severity = ?")
            params.append(severity)
        if since_ts is not None:
            where.append("ts >= ?")
            params.append(float(since_ts))
        sql = (
            "SELECT * FROM alerts WHERE "
            + " AND ".join(where)
            + " ORDER BY ts DESC LIMIT ? OFFSET ?"
        )
        params.extend([int(limit), int(offset)])
        cur = self._conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        result: list[dict] = []
        for r in rows:
            extra_dict: dict = {}
            try:
                if r["extra"]:
                    extra_dict = json.loads(r["extra"])
            except Exception:
                extra_dict = {}
            result.append(
                {
                    "id": r["id"],
                    "alert_id": r["alert_id"],
                    "severity": r["severity"],
                    "name": r["name"],
                    "rule": r["rule"] or "",
                    "trace_id": r["trace_id"],
                    "extra": extra_dict,
                    "ts": float(r["ts"]),
                    "created_at": r["created_at"],
                }
            )
        return result

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
