from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from orchestration.models import ClassificationLevel, RoleInstance


DEFAULT_ROLE_INSTANCES_YAML = (
    Path(__file__).resolve().parents[1] / "config" / "default_role_instances.yaml"
)

INSTANCE_METADATA: dict[str, dict[str, Any]] = {}


def _parse_clearance(value: Any) -> ClassificationLevel:
    if isinstance(value, ClassificationLevel):
        return value
    if isinstance(value, int):
        try:
            return ClassificationLevel(value)
        except ValueError:
            return ClassificationLevel.INTERNAL
    if isinstance(value, str):
        try:
            return ClassificationLevel[value.upper()]
        except KeyError:
            pass
        try:
            return ClassificationLevel(int(value))
        except (ValueError, TypeError):
            return ClassificationLevel.INTERNAL
    return ClassificationLevel.INTERNAL


def load_role_instances(yaml_path: Path) -> dict[str, RoleInstance]:
    yaml_path = Path(yaml_path)
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    instances_raw = data.get("instances", {})
    result: dict[str, RoleInstance] = {}

    for instance_id, spec in instances_raw.items():
        if not isinstance(spec, dict):
            continue
        role = spec.get("role", "")
        approvers = spec.get("approvers", ["bot-coord"]) or ["bot-coord"]
        if not approvers:
            approvers = ["bot-coord"]
        if len(approvers) > 2:
            approvers = approvers[:2]
        clearance_raw = spec.get("clearance", ClassificationLevel.INTERNAL)
        clearance = _parse_clearance(clearance_raw)
        human_override = bool(spec.get("human_override", False))

        ri = RoleInstance(
            instance_id=instance_id,
            role=role,
            human_override=human_override,
            approvers=approvers,
            clearance=clearance,
        )
        result[instance_id] = ri

        metadata = {
            "llm_config": spec.get("llm_config", {}),
            "allowed_node_types": spec.get("allowed_node_types", []),
            "allowed_external_repos": spec.get("allowed_external_repos", []),
        }
        INSTANCE_METADATA[instance_id] = metadata

    return result


def get_default_role_instances() -> dict[str, RoleInstance]:
    if DEFAULT_ROLE_INSTANCES_YAML.exists():
        return load_role_instances(DEFAULT_ROLE_INSTANCES_YAML)
    return {}


def get_instance_metadata(instance_id: str) -> dict[str, Any]:
    return INSTANCE_METADATA.get(instance_id, {})
