from __future__ import annotations

from typing import Any

from orchestration.cascade import cascade_changed, cascade_done


class CascadeIntegrator:
    def __init__(self, resolver: Any) -> None:
        self.resolver = resolver

    def serial_done(
        self,
        pipeline_id: str,
        node_id: str,
        pipeline_def: Any,
        state: Any,
    ) -> tuple[Any, list]:
        def _do() -> list:
            new_state, events = cascade_done(node_id, pipeline_def, state)
            return events

        deduped_events = self.resolver.cascade_serialize(
            pipeline_id, _do
        )
        ns_map = {}
        for nid, ns in state.node_states.items():
            ns_map[nid] = ns
        result_state, _ = cascade_done(node_id, pipeline_def, state)
        return result_state, deduped_events

    def serial_changed(
        self,
        pipeline_id: str,
        node_id: str,
        change_class: str,
        coupling_default: Any,
        pipeline_def: Any,
        state: Any,
    ) -> tuple[Any, list]:
        def _do() -> list:
            new_state, events = cascade_changed(
                node_id, change_class, coupling_default, pipeline_def, state
            )
            return events

        deduped_events = self.resolver.cascade_serialize(
            pipeline_id, _do
        )
        result_state, _ = cascade_changed(
            node_id, change_class, coupling_default, pipeline_def, state
        )
        return result_state, deduped_events
