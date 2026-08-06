from __future__ import annotations

import sqlite3
import uuid
from typing import Protocol, runtime_checkable

from orchestration.models import PipelineState


@runtime_checkable
class CheckpointStorage(Protocol):
    def save(self, pipeline_id: str, version: int, state: PipelineState) -> str: ...

    def load_latest(self, pipeline_id: str) -> PipelineState | None: ...

    def list(self, pipeline_id: str) -> list[dict]: ...


class SQLiteCheckpointStorage(CheckpointStorage):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_pipeline ON checkpoints(pipeline_id, version DESC)"
            )
            conn.commit()
        finally:
            conn.close()

    def save(self, pipeline_id: str, version: int, state: PipelineState) -> str:
        id_ = str(uuid.uuid4())
        state_json = state.model_dump_json()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO checkpoints (id, pipeline_id, version, state_json) VALUES (?, ?, ?, ?)",
                (id_, pipeline_id, version, state_json),
            )
            conn.commit()
        finally:
            conn.close()
        return id_

    def load_latest(self, pipeline_id: str) -> PipelineState | None:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT state_json FROM checkpoints WHERE pipeline_id = ? ORDER BY version DESC LIMIT 1",
                (pipeline_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            state_json = row["state_json"]
            return PipelineState.model_validate_json(state_json)
        finally:
            conn.close()

    def list(self, pipeline_id: str) -> list[dict]:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT id, version, created_at FROM checkpoints WHERE pipeline_id = ? ORDER BY version DESC",
                (pipeline_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "version": r["version"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        finally:
            conn.close()
