from __future__ import annotations

from enum import Enum, IntEnum, StrEnum
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeStatus(StrEnum):
    BLOCKED = "blocked"
    READY = "ready"
    PENDING_REVIEW = "pending_review"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CHANGED = "changed"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    SKIPPED = "skipped"


class PipelineStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    MERGED = "merged"
    COMPLETED = "completed"


class DepPresence(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    IF_PRESENT = "if_present"


class DepStrictness(StrEnum):
    STRICT = "strict"
    ACCEPTS_DRAFT = "accepts_draft"


class DepCoupling(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    INFORMATIONAL = "informational"


class DepDeclaration(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    upstream: str
    presence: DepPresence = DepPresence.REQUIRED
    strictness: DepStrictness = DepStrictness.STRICT
    coupling: DepCoupling = DepCoupling.HARD
    scope: Optional[str] = None


class Provenance(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    commit_sha: str
    pr_id: str
    approver_ids: list[str] = []
    reviewer_ids: list[str] = []
    merged_at: str


class ArtifactRef(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    node_id: str
    artifact_type: str
    version: int = Field(ge=1)
    qualifier: str = "default"
    uri: str
    external: bool = False
    ref_hash: str
    trace_id: str
    provenance: Optional["Provenance"] = None


class Addendum(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: str
    version: int = Field(ge=1)
    change_class: Literal["must", "should", "informational"]
    incompatible_with: list[str] = []
    impact_claim: list[str] = []
    diff_hash: str
    author: str
    created_at: str


class ClassificationLevel(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class TokenType(StrEnum):
    BOT = "bot"
    HUMAN_SUBMIT = "human_submit"
    ADMIN = "admin"
    REVIEWER = "reviewer"


class RoleInstance(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    instance_id: str
    role: str
    human_override: bool = False
    approvers: list[str] = Field(min_length=1, max_length=2)
    clearance: ClassificationLevel = ClassificationLevel.INTERNAL

    def can_access(self, classification: ClassificationLevel) -> bool:
        return self.clearance >= classification


class NodeDef(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    node_id: str
    node_type: str
    role_assignments: list[str] = []
    deps: list[DepDeclaration] = []
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    requires_human_review: bool = False
    strictness_default: DepStrictness = DepStrictness.STRICT
    coupling_default: DepCoupling = DepCoupling.HARD
    optional: bool = False


class ChangeState(StrEnum):
    UNCHANGED = "unchanged"
    SOFT_PENDING = "soft_pending"
    SOFT_ACKED = "soft_acked"
    INCOMPATIBLE_PENDING = "incompatible_pending"
    INCOMPATIBLE_ACKED = "incompatible_acked"


class NodeState(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    node_id: str
    status: NodeStatus = NodeStatus.BLOCKED
    artifact_refs: list[ArtifactRef] = []
    downstream_acked_ids: list[str] = []
    addenda: list[Addendum] = []
    change_state: ChangeState = ChangeState.UNCHANGED
    pending_pr_count: int = 0
    locked_by: Optional[str] = None


class ParticipationProfile(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: str
    name: str
    roles_present: list[str]
    roles_absent: list[str] = []
    allow_non_product_root: bool = False
    allow_design_as_root: bool = False
    completion_mode: Literal[
        "core_nodes_done", "core_plus_noncritical_acceptance", "explicit_closure"
    ] = "core_nodes_done"
    core_node_types: list[str] = []
    optional_node_types: list[str] = []
    tech_debt_hotfix_mode: bool = False


class PipelineDefinition(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: str
    name: str
    template_id: Optional[str] = None
    nodes: list[NodeDef]
    profile: ParticipationProfile
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    root_product_node_id: Optional[str] = None


class PipelineState(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    pipeline_id: str
    version: int = 1
    status: PipelineStatus = PipelineStatus.ACTIVE
    created_at: str
    updated_at: str
    node_states: dict[str, NodeState] = {}
    cascade_pending: list[dict] = []
    profile_id: Optional[str] = None
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    completed_nodes_count: int = 0
    hash_chain_tip: Optional[str] = None
    checkpoint_id: Optional[str] = None
    _dep_cache: ClassVar[dict] = {}


ArtifactRef.model_rebuild()
