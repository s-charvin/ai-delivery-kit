from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from orchestration.models import ClassificationLevel, DepDeclaration


class ReviewGates(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    coverage_min: float = 0.0
    requires_human: bool = False
    lint_required: bool = True
    test_required: bool = True
    security_scan: bool = True


class ModificationRules(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    allowed_change_class: list[str] = ["compatible", "addendum", "breaking"]
    enforce_addendum_only: bool = False


class FormatSpec(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    spec: str
    content_schema_url: Optional[str] = None


class OutputGuides(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    max_len_bytes: int = 10_000_000
    forbidden_tokens: list[str] = []


class CompletenessContract(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    json_paths: list[str]
    mode: Literal["and", "or"] = "and"
    threshold: float = 1.0


class SkillDefinition(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    for_node_types: list[str] = []
    required_fields: list[str] = []
    optional_fields: list[str] = []
    deps: list[DepDeclaration] = []
    completeness_contract: Optional[CompletenessContract] = None
    format: FormatSpec
    modification_rules: ModificationRules = ModificationRules()
    output_guides: OutputGuides = OutputGuides()
    review_gates: ReviewGates = ReviewGates()
    metadata: dict = {}


class ArtifactConstraints(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    node_type: str
    required_fields_present: bool
    max_len_bytes_ok: bool
    format_supported: bool
    skill_matches: bool

    @property
    def all_ok(self) -> bool:
        return (
            self.required_fields_present
            and self.max_len_bytes_ok
            and self.format_supported
            and self.skill_matches
        )


class ModificationDeclaration(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    change_class: Optional[Literal["compatible", "addendum", "breaking"]] = None
    incompatibility_claimed: list[str] = []
    impact_claimed_downstream: list[str] = []
    addendum_lines_only: bool = True


class ArtifactResubmitMeta(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    resubmit_of_artifact_hash: str
    resubmit_reason: str
    diff_to_previous: str
    classification_change_from: Optional[ClassificationLevel] = None
    classification_change_to: Optional[ClassificationLevel] = None
