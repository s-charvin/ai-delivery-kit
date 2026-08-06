from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from config.constants import TRANSITION_MATRIX, VALID_TRANSITIONS
from orchestration.models import NodeStatus


class Event(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    type: str
    payload: dict[str, Any] = {}
    trace_id: str | None = None


EVENT_READY = "READY"
EVENT_SUBMIT_ARTIFACT = "SUBMIT_ARTIFACT"
EVENT_START_REVIEW = "START_REVIEW"
EVENT_APPROVE_MERGE = "APPROVE_MERGE"
EVENT_REJECT_REVIEW = "REJECT_REVIEW"
EVENT_BREAKING_CHANGE = "BREAKING_CHANGE"
EVENT_REASSIGN = "REASSIGN"
EVENT_SOFT_SUBMIT = "SOFT_SUBMIT"
EVENT_CANCEL_SUBMIT = "CANCEL_SUBMIT"
EVENT_SKIP_OPTIONAL = "SKIP_OPTIONAL"

EVENT_ADD_ADDENDUM_MUST = "ADD_ADDENDUM_MUST"
EVENT_ADD_ADDENDUM_SHOULD = "ADD_ADDENDUM_SHOULD"
EVENT_ADD_ADDENDUM_INFO = "ADD_ADDENDUM_INFO"

EVENT_DEPRECATE = "DEPRECATE"
EVENT_SET_DRAFT = "SET_DRAFT"
EVENT_RESUBMIT = "RESUBMIT"

EVENT_PIPELINE_STARTED = "PIPELINE_STARTED"
EVENT_NODE_READY = "NODE_READY"
EVENT_NODE_DONE = "NODE_DONE"
EVENT_NODE_INVALIDATED = "NODE_INVALIDATED"
EVENT_NODE_SKIPPED = "NODE_SKIPPED"
EVENT_NODE_DEPRECATED = "NODE_DEPRECATED"
EVENT_SOFT_DRAFT_PUBLISHED = "SOFT_DRAFT_PUBLISHED"
EVENT_DOWNSTREAM_SOFT_ACK = "DOWNSTREAM_SOFT_ACK"
EVENT_NOTIFY = "NOTIFY"
EVENT_ADDENDUM_NOTIFY = "ADDENDUM_NOTIFY"
EVENT_ADDENDUM_MUST_ACK = "ADDENDUM_MUST_ACK"
EVENT_ADDENDUM_SHOULD_NOTIFY = "ADDENDUM_SHOULD_NOTIFY"
EVENT_ADDENDUM_INFO_NOTIFY = "ADDENDUM_INFO_NOTIFY"
EVENT_PIPELINE_PAUSED = "PIPELINE_PAUSED"
EVENT_PIPELINE_RESUMED = "PIPELINE_RESUMED"
EVENT_PIPELINE_CANCELLED = "PIPELINE_CANCELLED"
EVENT_STUB_CREWAI_ASSIGN = "STUB_CREWAI_ASSIGN"
EVENT_STUB_APPROVAL = "STUB_APPROVAL"
EVENT_STUB_WARN = "STUB_WARN"


def transition(
    current: NodeStatus,
    event: Event,
    ctx: dict[str, Any] | None = None,
) -> tuple[NodeStatus | None, list[Event], str | None]:
    ctx = ctx or {}

    if event.type in (
        EVENT_ADD_ADDENDUM_MUST,
        EVENT_ADD_ADDENDUM_SHOULD,
        EVENT_ADD_ADDENDUM_INFO,
    ):
        if current != NodeStatus.DONE:
            return None, [], "E_ILLEGAL_TRANSITION"
        change_class_map = {
            EVENT_ADD_ADDENDUM_MUST: "must",
            EVENT_ADD_ADDENDUM_SHOULD: "should",
            EVENT_ADD_ADDENDUM_INFO: "informational",
        }
        cc = change_class_map[event.type]
        downstream = event.payload.get("downstream", [])
        side_effects = [
            Event(
                type=EVENT_ADDENDUM_NOTIFY,
                payload={
                    "change_class": cc,
                    "downstream": downstream,
                    "addendum_id": event.payload.get("addendum_id"),
                },
                trace_id=event.trace_id,
            )
        ]
        return current, side_effects, None

    new_status: NodeStatus | None = None
    side_effects: list[Event] = []

    et = event.type

    if et == EVENT_READY:
        if current == NodeStatus.BLOCKED:
            new_status = NodeStatus.READY
    elif et == EVENT_SUBMIT_ARTIFACT:
        if current == NodeStatus.READY:
            new_status = NodeStatus.PENDING_REVIEW
        elif current == NodeStatus.DRAFT:
            new_status = NodeStatus.PENDING_REVIEW
    elif et == EVENT_SOFT_SUBMIT:
        if current == NodeStatus.READY:
            new_status = NodeStatus.PENDING_REVIEW
    elif et == EVENT_START_REVIEW:
        if current == NodeStatus.PENDING_REVIEW:
            new_status = NodeStatus.REVIEW
    elif et == EVENT_APPROVE_MERGE:
        if current == NodeStatus.REVIEW:
            new_status = NodeStatus.DONE
            side_effects.append(
                Event(
                    type=EVENT_NODE_DONE,
                    payload={"node_id": ctx.get("node_id")},
                    trace_id=event.trace_id,
                )
            )
    elif et == EVENT_REJECT_REVIEW or et == "REJECT_REVIEW":
        if current == NodeStatus.REVIEW:
            new_status = NodeStatus.READY
    elif et == EVENT_CANCEL_SUBMIT or et == "CANCEL_SUBMIT":
        if current == NodeStatus.PENDING_REVIEW:
            new_status = NodeStatus.READY
    elif et == EVENT_BREAKING_CHANGE:
        if current == NodeStatus.DONE:
            new_status = NodeStatus.CHANGED
    elif et == EVENT_RESUBMIT:
        if current == NodeStatus.CHANGED:
            new_status = NodeStatus.IN_PROGRESS
    elif et == EVENT_SET_DRAFT:
        if current == NodeStatus.READY:
            new_status = NodeStatus.DRAFT
    elif et == EVENT_SKIP_OPTIONAL:
        if current == NodeStatus.READY:
            new_status = NodeStatus.SKIPPED
            side_effects.append(
                Event(
                    type=EVENT_NODE_SKIPPED,
                    payload={"node_id": ctx.get("node_id")},
                    trace_id=event.trace_id,
                )
            )
    elif et == EVENT_DEPRECATE:
        if current in (
            NodeStatus.DONE,
            NodeStatus.CHANGED,
            NodeStatus.READY,
            NodeStatus.BLOCKED,
            NodeStatus.DRAFT,
        ):
            new_status = NodeStatus.DEPRECATED
            side_effects.append(
                Event(
                    type=EVENT_NODE_DEPRECATED,
                    payload={"node_id": ctx.get("node_id")},
                    trace_id=event.trace_id,
                )
            )
    elif et == "SUNSET":
        if current == NodeStatus.DEPRECATED:
            new_status = NodeStatus.SUNSET
    elif et == EVENT_REASSIGN:
        return current, [], None

    if new_status is None:
        return None, [], "E_ILLEGAL_TRANSITION"

    matrix_ok = TRANSITION_MATRIX.get(current.value, {}).get(new_status.value, False)
    event_override_ok = et in {
        EVENT_CANCEL_SUBMIT,
        "REJECT_REVIEW",
        EVENT_RESUBMIT,
        "T9_SUBMIT",
        "IN_PROGRESS_SUBMIT",
    }
    if not matrix_ok and not event_override_ok:
        if et == EVENT_CANCEL_SUBMIT and current == NodeStatus.PENDING_REVIEW and new_status == NodeStatus.READY:
            pass
        else:
            return None, [], "E_ILLEGAL_TRANSITION"

    return new_status, side_effects, None


def transition_allowed(from_: NodeStatus, to_: NodeStatus) -> bool:
    return TRANSITION_MATRIX.get(from_.value, {}).get(to_.value, False)
