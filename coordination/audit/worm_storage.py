from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from utils.hashing import audit_entry_hash


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    prev_hash: str
    action: str
    actor: str
    payload: dict
    hash: str
    created_at: str
    id: int | None = None
    pipeline_id: str | None = None
    node_id: str | None = None
    trace_id: str | None = None
    pr_id: str | None = None
    commit_sha: str | None = None
    artifact_ref: str | None = None
    classification: int | None = None
    note: str | None = None


class WormStorage:
    def __init__(self, sqlite_path: Path):
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
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT,
                node_id TEXT,
                pr_id TEXT,
                action TEXT,
                actor TEXT,
                payload TEXT,
                created_at TEXT,
                prev_hash TEXT,
                hash TEXT UNIQUE,
                trace_id TEXT,
                commit_sha TEXT,
                artifact_ref TEXT,
                classification INTEGER,
                note TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_pipeline ON audit_log(pipeline_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_node ON audit_log(node_id)"
        )
        self._conn.commit()

    @property
    def tip_hash(self) -> str:
        cur = self._conn.cursor()
        cur.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row is None:
            return ""
        return row["hash"] or ""

    def insert(self, entry: AuditLogEntry) -> AuditLogEntry:
        entry.prev_hash = self.tip_hash
        entry.hash = audit_entry_hash(
            entry.prev_hash, entry.action, entry.actor, entry.payload
        )
        if not entry.created_at:
            entry.created_at = datetime.now(timezone.utc).isoformat()

        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log (
                pipeline_id, node_id, pr_id, action, actor, payload,
                created_at, prev_hash, hash, trace_id, commit_sha,
                artifact_ref, classification, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.pipeline_id,
                entry.node_id,
                entry.pr_id,
                entry.action,
                entry.actor,
                json.dumps(entry.payload, sort_keys=True, ensure_ascii=False),
                entry.created_at,
                entry.prev_hash,
                entry.hash,
                entry.trace_id,
                entry.commit_sha,
                entry.artifact_ref,
                entry.classification,
                entry.note,
            ),
        )
        self._conn.commit()
        entry.id = cur.lastrowid
        return entry

    def list(
        self,
        pipeline_id: str | None = None,
        node_id: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list[Any] = []
        if pipeline_id is not None:
            query += " AND pipeline_id = ?"
            params.append(pipeline_id)
        if node_id is not None:
            query += " AND node_id = ?"
            params.append(node_id)
        query += " ORDER BY id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = self._conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        entries: list[AuditLogEntry] = []
        for row in rows:
            payload_dict: dict = {}
            try:
                payload_raw = row["payload"]
                if payload_raw:
                    payload_dict = json.loads(payload_raw)
            except Exception:
                payload_dict = {}
            entry = AuditLogEntry(
                id=row["id"],
                pipeline_id=row["pipeline_id"],
                node_id=row["node_id"],
                pr_id=row["pr_id"],
                action=row["action"],
                actor=row["actor"],
                payload=payload_dict,
                created_at=row["created_at"] or "",
                prev_hash=row["prev_hash"] or "",
                hash=row["hash"] or "",
                trace_id=row["trace_id"],
                commit_sha=row["commit_sha"],
                artifact_ref=row["artifact_ref"],
                classification=row["classification"],
                note=row["note"],
            )
            entries.append(entry)
        return entries

    def _raw_connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
