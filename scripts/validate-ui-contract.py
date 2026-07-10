#!/usr/bin/env python3
"""Validate ui-acceptance-contract.yaml against ui-truth-mapping template rules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment bootstrap
    print(
        "ERROR: PyYAML is required. Install with: python3 -m pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)

REQUIRED_TOP_LEVEL = ("version", "contract_id", "states", "regions")
FORBIDDEN_KEYS = frozenset(
    {
        "visual_truth",
        "code-baseline",
        "layout_note",
        "implementation_reference",
        "policy",
        "screen_states",
    }
)
ANCHOR_DIRECTIONS = ("start", "end", "top", "bottom")
PADDING_DIRECTIONS = ("top", "right", "bottom", "left")
PLACEHOLDER_PATTERN = re.compile(r"^<[^>]+>$")
CONTENT_SLOTS = ("text", "icon", "image")


class ValidationError(Exception):
    def __init__(self, rule_id: str, message: str) -> None:
        self.rule_id = rule_id
        self.message = message
        super().__init__(f"[{rule_id}] {message}")


class ContractValidator:
    def __init__(self, contract_path: Path, section_map_path: Path | None = None) -> None:
        self.contract_path = contract_path
        self.section_map_path = section_map_path
        self.errors: list[ValidationError] = []

    def add_error(self, rule_id: str, message: str) -> None:
        self.errors.append(ValidationError(rule_id, message))

    def load_yaml(self) -> dict[str, Any] | None:
        try:
            raw = self.contract_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.add_error("IO", f"cannot read contract: {exc}")
            return None

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            self.add_error("YAML", f"invalid YAML: {exc}")
            return None

        if not isinstance(data, dict):
            self.add_error("STRUCT", "contract root must be a mapping")
            return None
        return data

    def collect_forbidden_keys(self, node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                current = f"{path}.{key}" if path else key
                if key in FORBIDDEN_KEYS:
                    self.add_error("ANTI", f"forbidden field '{key}' at {current}")
                if key == "requirement_id" and not path:
                    self.add_error("ANTI", "forbidden flat-format field 'requirement_id' at root")
                if key == "screen" and isinstance(value, dict) and "visual_truth" in value:
                    self.add_error("ANTI", "forbidden flat format screen.visual_truth")
                self.collect_forbidden_keys(value, current)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                self.collect_forbidden_keys(item, f"{path}[{index}]")

    def validate_top_level(self, data: dict[str, Any]) -> None:
        for key in REQUIRED_TOP_LEVEL:
            if key not in data:
                self.add_error("STRUCT", f"missing required top-level field '{key}'")

        if "requirement_id" in data:
            self.add_error("ANTI", "forbidden flat-format field 'requirement_id' at root")

        contract_id = data.get("contract_id")
        if isinstance(contract_id, str) and PLACEHOLDER_PATTERN.match(contract_id.strip()):
            self.add_error("PLACEHOLDER", f"contract_id still placeholder: {contract_id}")

        states = data.get("states")
        if states is not None and not isinstance(states, list):
            self.add_error("S3", "states must be a list")
        elif isinstance(states, list):
            if not states:
                self.add_error("S3", "states must not be empty")
            for index, state in enumerate(states):
                if not isinstance(state, dict):
                    self.add_error("S3", f"states[{index}] must be a mapping")
                    continue
                if not state.get("id"):
                    self.add_error("S3", f"states[{index}] missing id")
                source_node = state.get("source_node")
                if not source_node:
                    self.add_error("S3", f"states[{index}] missing source_node")
                elif isinstance(source_node, str) and PLACEHOLDER_PATTERN.match(source_node.strip()):
                    self.add_error("PLACEHOLDER", f"states[{index}].source_node still placeholder")

        regions = data.get("regions")
        if regions is not None and not isinstance(regions, list):
            self.add_error("STRUCT", "regions must be a list")
        elif isinstance(regions, list):
            if not regions:
                self.add_error("S1", "regions must not be empty")
            for index, region in enumerate(regions):
                if isinstance(region, dict):
                    self.validate_component(region, f"regions[{index}]", is_region=True)
                else:
                    self.add_error("S1", f"regions[{index}] must be a mapping")

    def validate_anchor(self, component: dict[str, Any], path: str) -> None:
        anchor = component.get("anchor")
        if anchor is None:
            self.add_error("L1", f"{path} missing anchor")
            return
        if not isinstance(anchor, list):
            self.add_error("L1", f"{path}.anchor must be a list")
            return

        seen: set[str] = set()
        for index, entry in enumerate(anchor):
            if not isinstance(entry, dict):
                self.add_error("L1", f"{path}.anchor[{index}] must be a mapping")
                continue
            direction = entry.get("direction")
            if not direction:
                self.add_error("L1", f"{path}.anchor[{index}] missing direction")
                continue
            if direction not in ANCHOR_DIRECTIONS:
                self.add_error("L1", f"{path}.anchor[{index}] invalid direction '{direction}'")
                continue
            seen.add(direction)
            for field in ("to", "direction", "offset"):
                value = entry.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    self.add_error("L1", f"{path}.anchor[{index}] missing {field}")
            offset = entry.get("offset")
            if offset == "auto" and not entry.get("note"):
                self.add_error("L1", f"{path}.anchor[{index}] offset auto requires note")

        for direction in ANCHOR_DIRECTIONS:
            if direction not in seen:
                self.add_error("L1", f"{path}.anchor missing direction '{direction}'")

    def validate_padding(self, component: dict[str, Any], path: str) -> None:
        box = component.get("box")
        if not isinstance(box, dict):
            self.add_error("L2", f"{path} missing box for padding validation")
            return
        padding = box.get("padding")
        if not isinstance(padding, dict):
            self.add_error("L2", f"{path}.box.padding must be a mapping")
            return
        for direction in PADDING_DIRECTIONS:
            if direction not in padding or padding[direction] is None:
                self.add_error("L2", f"{path}.box.padding missing '{direction}'")

    def content_slot_count(self, component: dict[str, Any]) -> int:
        count = 0
        if component.get("text") not in (None, ""):
            count += 1
        icon = component.get("icon")
        if isinstance(icon, dict) and icon.get("src") not in (None, ""):
            count += 1
        image = component.get("image")
        if isinstance(image, dict) and image.get("src") not in (None, ""):
            count += 1
        return count

    def validate_component(self, component: dict[str, Any], path: str, is_region: bool = False) -> None:
        if not component.get("id"):
            self.add_error("S1", f"{path} missing id")
        if not component.get("source_node"):
            self.add_error("S4", f"{path} missing source_node")
        self.validate_anchor(component, path)
        self.validate_padding(component, path)

        children = component.get("children", [])
        if children is None:
            children = []
        if not isinstance(children, list):
            self.add_error("S1", f"{path}.children must be a list")
            return

        is_leaf = len(children) == 0
        if is_leaf and not is_region:
            slots = self.content_slot_count(component)
            if slots != 1:
                self.add_error(
                    "C1",
                    f"{path} leaf must populate exactly one content slot (text/icon/image), found {slots}",
                )

        for index, child in enumerate(children):
            if isinstance(child, dict):
                self.validate_component(child, f"{path}.children[{index}]")
            else:
                self.add_error("S1", f"{path}.children[{index}] must be a mapping")

    def validate_section_map_alignment(self, data: dict[str, Any]) -> None:
        if self.section_map_path is None or not self.section_map_path.exists():
            return
        try:
            section_map = yaml.safe_load(self.section_map_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            self.add_error("S3", f"cannot read section-map.json: {exc}")
            return

        if not isinstance(section_map, dict):
            self.add_error("S3", "section-map root must be a mapping")
            return

        frame_nodes: set[str] = set()
        for unit in section_map.get("units", []) or []:
            if not isinstance(unit, dict):
                continue
            for frame in unit.get("frames", []) or []:
                if isinstance(frame, dict):
                    node = frame.get("source_node")
                    if isinstance(node, str) and node.strip():
                        frame_nodes.add(node.strip())

        contract_nodes: set[str] = set()
        for state in data.get("states", []) or []:
            if isinstance(state, dict):
                node = state.get("source_node")
                if isinstance(node, str) and node.strip():
                    contract_nodes.add(node.strip())

        if frame_nodes and contract_nodes != frame_nodes:
            missing = sorted(frame_nodes - contract_nodes)
            extra = sorted(contract_nodes - frame_nodes)
            if missing:
                self.add_error("S3", f"states missing section-map frames: {', '.join(missing)}")
            if extra:
                self.add_error("S3", f"states include frames not in section-map: {', '.join(extra)}")

    def validate(self) -> bool:
        data = self.load_yaml()
        if data is None:
            return False

        self.collect_forbidden_keys(data)
        self.validate_top_level(data)
        if isinstance(data, dict):
            self.validate_section_map_alignment(data)
        return not self.errors


def resolve_section_map(contract_path: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    candidate = contract_path.parent / "section-map.json"
    return candidate if candidate.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path, help="Path to ui-acceptance-contract.yaml")
    parser.add_argument(
        "--section-map",
        type=Path,
        default=None,
        help="Optional section-map.json for frame alignment checks",
    )
    args = parser.parse_args()

    if not args.contract.exists():
        print(f"ERROR: contract not found: {args.contract}", file=sys.stderr)
        return 1

    section_map = resolve_section_map(args.contract, args.section_map)
    validator = ContractValidator(args.contract, section_map)
    ok = validator.validate()

    if ok:
        print(f"OK: {args.contract}")
        return 0

    for error in validator.errors:
        print(f"FAIL {error.rule_id}: {error.message}", file=sys.stderr)
    print(f"INVALID: {args.contract} ({len(validator.errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
