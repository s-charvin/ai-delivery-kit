from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from orchestration.models import (
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from orchestration.state_machine import Event

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crew.builder import build_crew_for_ready_nodes


def _deepcopy_state(state: PipelineState) -> PipelineState:
    return PipelineState.model_validate(state.model_dump())


EVENT_CREWAI_DISPATCHED = "CREWAI_DISPATCHED"
EVENT_NODE_DONE_VIA_CREW = "NODE_DONE_VIA_CREW"
EVENT_STUB_WARN = "CREW_STUB_WARN"


class CrewGraphBridge:
    def __init__(self, env: Any | None = None) -> None:
        self.env = env or {}
        self.last_crew_result: Any = None
        self.dispatched: list[dict] = []

    def dispatch_ready_nodes(
        self,
        pipeline_id: str,
        ready_nodes: list[tuple[str, str]],
        pipeline_def: PipelineDefinition | None = None,
        pipeline_state: PipelineState | None = None,
        instances: dict | None = None,
        mcp_tools_wrapper: Any | None = None,
    ) -> dict:
        if pipeline_def is None or pipeline_state is None or instances is None:
            return {
                "pipeline_state": pipeline_state,
                "events": [],
                "crew_result": None,
            }

        crew = build_crew_for_ready_nodes(
            ready_nodes=ready_nodes,
            pipeline_def=pipeline_def,
            pipeline_state=pipeline_state,
            instances=instances,
            mcp_tools_wrapper=mcp_tools_wrapper,
        )

        events: list[Event] = []
        try:
            result = crew.kickoff()
        except Exception as exc:
            # No production fallback to a test stub: a failed crew run is surfaced as a
            # warning event and the node statuses are left unchanged so the failure is
            # explicit rather than silently masked.
            events.append(
                Event(
                    type=EVENT_STUB_WARN,
                    payload={"pipeline_id": pipeline_id, "error": str(exc)},
                )
            )
            return {
                "pipeline_state": pipeline_state,
                "events": events,
                "crew_result": None,
                "crew": crew,
            }

        self.last_crew_result = result
        self.dispatched.append(
            {
                "pipeline_id": pipeline_id,
                "ready_nodes": list(ready_nodes),
                "result": getattr(result, "raw", str(result)),
            }
        )

        new_state = _deepcopy_state(pipeline_state)
        events = []

        now = datetime.now(timezone.utc).isoformat()
        new_state.updated_at = now

        node_map = {n.node_id: n for n in pipeline_def.nodes}

        for nid, instance_id in ready_nodes:
            events.append(
                Event(
                    type=EVENT_CREWAI_DISPATCHED,
                    payload={
                        "node_id": nid,
                        "instance_id": instance_id,
                        "pipeline_id": pipeline_id,
                    },
                )
            )
            ns = new_state.node_states.get(nid)
            if ns is not None:
                if ns.status in (
                    NodeStatus.READY,
                    NodeStatus.IN_PROGRESS,
                    NodeStatus.PENDING_REVIEW,
                    NodeStatus.REVIEW,
                ):
                    # DONE is recognized by the artifacts the crew actually produced
                    # (artifact_refs), not by parsing the crew result string.
                    if ns.artifact_refs:
                        ns.status = NodeStatus.DONE
                        events.append(
                            Event(
                                type=EVENT_NODE_DONE_VIA_CREW,
                                payload={
                                    "node_id": nid,
                                    "instance_id": instance_id,
                                },
                            )
                        )

        return {
            "pipeline_state": new_state,
            "events": events,
            "crew_result": result,
            "crew": crew,
        }


_GLOBAL_BRIDGE: CrewGraphBridge | None = None


def get_global_bridge(env: Any | None = None) -> CrewGraphBridge:
    global _GLOBAL_BRIDGE
    if _GLOBAL_BRIDGE is None:
        _GLOBAL_BRIDGE = CrewGraphBridge(env)
    return _GLOBAL_BRIDGE
