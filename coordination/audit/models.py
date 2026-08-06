from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict

from orchestration.models import ClassificationLevel, NodeStatus


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: Optional[int] = None
    pipeline_id: str
    node_id: Optional[str] = None
    action: str
    actor: str
    payload: dict = {}
    created_at: str
    prev_hash: str
    hash: str
    trace_id: str
    ip: Optional[str] = None
    session_token_hint: Optional[str] = None
    classification_before: Optional[ClassificationLevel] = None
    classification_after: Optional[ClassificationLevel] = None
    change_class: Optional[str] = None
    status_before: Optional[NodeStatus] = None
    status_after: Optional[NodeStatus] = None
    integrity_check_passed: bool = True


class CrossPipelineRefType(StrEnum):
    DEP = "dep"
    CONSUMER = "consumer"
    MERGE_RESULT = "merge_result"
    SPLIT_SOURCE = "split_source"


class CrossPipelineReference(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    source_pipeline_id: str
    target_pipeline_id: str
    source_node_id: str
    target_node_id: str
    ref_type: CrossPipelineRefType
    created_at: str
