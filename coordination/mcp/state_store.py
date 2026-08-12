from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from orchestration.models import PipelineDefinition, PipelineState

# SQLite is the durable backing store; the in-memory dicts below are a *volatile
# cache* warmed from SQLite on init (load_latest). On every mutating call we
# write through to SQLite so a process restart can recover the latest pipeline
# definitions and states.
#
# Operational queues (pending_prs / pending_sync) are intentionally kept
# in-memory only — they are short-lived and not part of the durable snapshot.
_DEFAULT_DB_PATH = Path("data") / "pipeline_state.db"


class PipelineStateStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_tables()

        # Volatile caches (SQLite is the source of truth).
        self.pipelines: dict[str, PipelineDefinition] = {}
        self.states: dict[str, PipelineState] = {}
        self.pending_prs: dict[str, str] = {}
        self.pending_sync: dict[str, list[dict]] = {}

        self.load_latest()

    # ---- durable backing (SQLite) ------------------------------------------
    def _ensure_tables(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS pipeline_def ("
            "  pipeline_id TEXT PRIMARY KEY,"
            "  def_json TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS pipeline_state ("
            "  pipeline_id TEXT PRIMARY KEY,"
            "  state_json TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def load_latest(self) -> None:
        """Warm the in-memory caches from SQLite.

        Called on init so a restarted process recovers the last persisted
        definitions and states instead of starting empty.
        """
        cur = self._conn.cursor()
        cur.execute("SELECT pipeline_id, def_json FROM pipeline_def")
        for row in cur.fetchall():
            self.pipelines[row["pipeline_id"]] = PipelineDefinition.model_validate_json(
                row["def_json"]
            )
        cur.execute("SELECT pipeline_id, state_json FROM pipeline_state")
        for row in cur.fetchall():
            self.states[row["pipeline_id"]] = PipelineState.model_validate_json(
                row["state_json"]
            )

    def _write_def(self, pid: str, defn: PipelineDefinition) -> None:
        self._conn.execute(
            "INSERT INTO pipeline_def (pipeline_id, def_json) VALUES (?, ?) "
            "ON CONFLICT(pipeline_id) DO UPDATE SET def_json=excluded.def_json",
            (pid, defn.model_dump_json()),
        )
        self._conn.commit()

    def _write_state(self, pid: str, state: PipelineState) -> None:
        self._conn.execute(
            "INSERT INTO pipeline_state (pipeline_id, state_json, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(pipeline_id) DO UPDATE SET "
            "state_json=excluded.state_json, updated_at=excluded.updated_at",
            (pid, state.model_dump_json(), state.updated_at),
        )
        self._conn.commit()

    # ---- public API (signatures unchanged) --------------------------------
    def register(self, defn: PipelineDefinition, state: PipelineState) -> None:
        pid = defn.id
        self.pipelines[pid] = defn
        self.states[pid] = state
        self._write_def(pid, defn)
        self._write_state(pid, state)
        if pid not in self.pending_sync:
            self.pending_sync[pid] = []

    def get_def(self, pid: str) -> PipelineDefinition:
        if pid not in self.pipelines:
            raise KeyError(f"Pipeline definition not found: {pid}")
        return self.pipelines[pid]

    def get_state(self, pid: str) -> PipelineState:
        if pid not in self.states:
            raise KeyError(f"Pipeline state not found: {pid}")
        return self.states[pid]

    def set_state(self, pid: str, state: PipelineState) -> None:
        self.states[pid] = state
        self._write_state(pid, state)

    def set_pending_pr(self, node_id: str, pr_id: str) -> None:
        self.pending_prs[node_id] = pr_id

    def get_pending_pr(self, node_id: str) -> Optional[str]:
        return self.pending_prs.get(node_id)

    def add_pending_sync(self, pipeline_id: str, record: dict) -> None:
        if pipeline_id not in self.pending_sync:
            self.pending_sync[pipeline_id] = []
        self.pending_sync[pipeline_id].append(record)

    def get_pending_sync_list(self, pipeline_id: str | None = None) -> list[dict]:
        if pipeline_id is None:
            all_records: list[dict] = []
            for pid, recs in self.pending_sync.items():
                for r in recs:
                    all_records.append({**r, "pipeline_id": pid})
            return all_records
        return list(self.pending_sync.get(pipeline_id, []))

    def clear_pending_sync(self, pipeline_id: str) -> None:
        self.pending_sync[pipeline_id] = []

    def clear_all(self) -> None:
        self.pipelines.clear()
        self.states.clear()
        self.pending_prs.clear()
        self.pending_sync.clear()
        try:
            self._conn.execute("DELETE FROM pipeline_def")
            self._conn.execute("DELETE FROM pipeline_state")
            self._conn.commit()
        except Exception:
            pass


STORE = PipelineStateStore()
