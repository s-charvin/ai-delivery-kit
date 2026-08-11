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
        # Compute the cascade exactly once; capture the resulting state in the
        # closure so the returned state and the emitted events come from the same
        # derivation (previously cascade_done was called a second time here, which
        # both wasted work and risked divergence if cascade ever became stateful).
        captured: dict[str, Any] = {}

        def _do() -> list:
            new_state, events = cascade_done(node_id, pipeline_def, state)
            captured["state"] = new_state
            return events

        deduped_events = self.resolver.cascade_serialize(pipeline_id, _do)
        return captured["state"], deduped_events

    def serial_changed(
        self,
        pipeline_id: str,
        node_id: str,
        change_class: str,
        coupling_default: Any,
        pipeline_def: Any,
        state: Any,
    ) -> tuple[Any, list]:
        captured: dict[str, Any] = {}

        def _do() -> list:
            new_state, events = cascade_changed(
                node_id, change_class, coupling_default, pipeline_def, state
            )
            captured["state"] = new_state
            return events

        deduped_events = self.resolver.cascade_serialize(pipeline_id, _do)
        return captured["state"], deduped_events
