from __future__ import annotations

from repo.hub import PRTemplateInvalidError

PR_REQUIRED_FIELDS: list[str] = [
    "node_id",
    "instance_id",
    "pipeline_id",
    "deps",
    "classification",
    "artifact_type",
    "version",
    "qualifier",
    "change_class",
    "modification_declaration",
    "trace_id",
    "role_signature",
]


def validate_pr_template(template: dict) -> list[str]:
    missing = [f for f in PR_REQUIRED_FIELDS if f not in template]
    return missing


def ensure_pr_template_valid(template: dict) -> None:
    missing = validate_pr_template(template)
    if missing:
        raise PRTemplateInvalidError(missing_fields=missing)
