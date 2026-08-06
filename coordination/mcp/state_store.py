from __future__ import annotations

from typing import Optional

from orchestration.models import PipelineDefinition, PipelineState


class PipelineStateStore:
    def __init__(self) -> None:
        self.pipelines: dict[str, PipelineDefinition] = {}
        self.states: dict[str, PipelineState] = {}
        self.pending_prs: dict[str, str] = {}
        self.pending_sync: dict[str, list[dict]] = {}

    def register(self, defn: PipelineDefinition, state: PipelineState) -> None:
        pid = defn.id
        self.pipelines[pid] = defn
        self.states[pid] = state
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


STORE = PipelineStateStore()
