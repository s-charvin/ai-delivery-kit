#!/usr/bin/env python3
"""Validate an HTML UI contract (schema v2) against ui-truth-mapping rules.

Uses only the Python standard library: ``html.parser`` for DOM parsing and
``json`` for the embedded metadata payload.
"""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator

VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

VALID_UNIT_TYPES = frozenset({"page", "modal", "shared-component"})
FORBIDDEN_KINDS = frozenset({"status-bar", "system-navigation", "soft-keyboard", "device-chrome"})
DELIVERY_STATUSES_REQUIRING_IMPLEMENTED = frozenset({"implemented", "merged"})
DELIVERY_IMPLEMENTED_FIELDS = ("type", "target", "requirement", "version", "status")


class ValidationError(Exception):
    def __init__(self, rule_id: str, message: str) -> None:
        self.rule_id = rule_id
        self.message = message
        super().__init__(f"[{rule_id}] {message}")


class Node:
    __slots__ = ("tag", "attrs", "parent", "children", "text")

    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], parent: "Node | None") -> None:
        self.tag = tag
        self.attrs: dict[str, str | None] = dict(attrs)
        self.parent = parent
        self.children: list["Node"] = []
        self.text: list[str] = []

    def has(self, name: str) -> bool:
        return name in self.attrs

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)


class TreeBuilder(HTMLParser):
    """Builds a minimal DOM tree from HTML using only stdlib html.parser."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", [], None)
        self._stack: list[Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, attrs, self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, attrs, self._stack[-1])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return
        # Stray end tag with no matching open tag: ignore leniently.

    def handle_data(self, data: str) -> None:
        if self._stack[-1] is not self.root:
            self._stack[-1].text.append(data)


def walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from walk(child)


def text_content(node: Node | None) -> str:
    if node is None:
        return ""
    parts = list(node.text)
    for child in node.children:
        parts.append(text_content(child))
    return "".join(parts).strip()


def is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class ContractValidator:
    def __init__(self, contract_path: Path) -> None:
        self.contract_path = contract_path
        self.errors: list[ValidationError] = []
        self.root: Node | None = None
        self.meta: dict[str, Any] | None = None

    def add_error(self, rule_id: str, message: str) -> None:
        self.errors.append(ValidationError(rule_id, message))

    def load_html(self) -> bool:
        try:
            raw = self.contract_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.add_error("HTML", f"cannot read contract: {exc}")
            return False

        builder = TreeBuilder()
        try:
            builder.feed(raw)
            builder.close()
        except Exception as exc:  # noqa: BLE001 - surface as a validation issue, not a crash
            self.add_error("HTML", f"failed to parse HTML: {exc}")
            return False

        self.root = builder.root
        return True

    def load_meta(self) -> None:
        assert self.root is not None
        scripts = [
            node
            for node in walk(self.root)
            if node.tag == "script" and node.get("id") == "ui-contract-meta"
        ]

        if not scripts:
            self.add_error(
                "META",
                'missing required <script id="ui-contract-meta" type="application/json"> element',
            )
            return
        if len(scripts) > 1:
            self.add_error(
                "META",
                f'multiple <script id="ui-contract-meta"> elements found ({len(scripts)}); '
                "exactly one root unit is allowed",
            )
            return

        script = scripts[0]
        script_type = script.get("type")
        if script_type != "application/json":
            self.add_error(
                "META",
                f'script#ui-contract-meta must have type="application/json" (found "{script_type}")',
            )
            return

        raw_json = "".join(script.text)
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            self.add_error("META", f"invalid JSON in ui-contract-meta script: {exc}")
            return

        if not isinstance(data, dict):
            self.add_error("META", "ui-contract-meta JSON root must be an object")
            return

        self.meta = data

    def validate_meta_fields(self) -> None:
        meta = self.meta
        if meta is None:
            return

        schema_version = meta.get("schema_version")
        if not (is_int(schema_version) and schema_version == 2):
            self.add_error(
                "META", f"schema_version must be 2 (found {schema_version!r})"
            )

        if not is_nonempty_str(meta.get("contract_id")):
            self.add_error("META", "contract_id is required and must be a non-empty string")

        source = meta.get("source")
        if not isinstance(source, dict):
            self.add_error("META", "source is required and must be an object")
            source = {}
        for field in ("requirement", "design_file", "root_node"):
            if not is_nonempty_str(source.get(field)):
                self.add_error("META", f"source.{field} is required and must be a non-empty string")

        self.validate_unit_fields(meta.get("unit"))
        self.validate_states_fields(meta.get("states"))
        self.validate_delivery_fields(meta.get("delivery"))

    def validate_unit_fields(self, unit: Any) -> None:
        if not isinstance(unit, dict):
            self.add_error("UNIT", "unit is required and must be an object")
            return

        if not is_nonempty_str(unit.get("id")):
            self.add_error("UNIT", "unit.id is required and must be a non-empty string")

        unit_type = unit.get("type")
        if unit_type not in VALID_UNIT_TYPES:
            self.add_error(
                "UNIT",
                f"unit.type must be one of {sorted(VALID_UNIT_TYPES)} (found {unit_type!r})",
            )

        if not is_nonempty_str(unit.get("source_node")):
            self.add_error("SOURCE_NODE", "unit.source_node is required and must be a non-empty string")

        requirements = unit.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            self.add_error("UNIT", "unit.requirements is required and must be a non-empty array")

    def validate_states_fields(self, states: Any) -> None:
        if not isinstance(states, list) or not states:
            self.add_error("STATE", "states is required and must be a non-empty array")
            return

        seen_ids: set[str] = set()
        has_default = False
        for index, state in enumerate(states):
            if not isinstance(state, dict):
                self.add_error("STATE", f"states[{index}] must be an object")
                continue
            state_id = state.get("id")
            if not is_nonempty_str(state_id):
                self.add_error("STATE", f"states[{index}].id is required and must be a non-empty string")
            elif state_id in seen_ids:
                self.add_error("STATE", f'duplicate state id "{state_id}" in states')
            else:
                seen_ids.add(state_id)

            if not is_nonempty_str(state.get("source_node")):
                self.add_error(
                    "SOURCE_NODE",
                    f'state "{state_id}" is missing a non-empty source_node',
                )

            if state.get("default") is True:
                has_default = True

        if not has_default:
            self.add_error("STATE", "at least one state must be marked default: true")

    def validate_delivery_fields(self, delivery: Any) -> None:
        if not isinstance(delivery, dict):
            self.add_error("DELIVERY", "delivery is required and must be an object")
            return

        status = delivery.get("status")
        if not is_nonempty_str(status):
            self.add_error("DELIVERY", "delivery.status is required and must be a non-empty string")
            return

        if status in DELIVERY_STATUSES_REQUIRING_IMPLEMENTED:
            implemented = delivery.get("implemented")
            if not isinstance(implemented, dict):
                self.add_error(
                    "DELIVERY",
                    f'delivery.implemented is required and must be an object when delivery.status is "{status}"',
                )
                return
            for field in DELIVERY_IMPLEMENTED_FIELDS:
                if not is_nonempty_str(implemented.get(field)):
                    self.add_error(
                        "DELIVERY",
                        f'delivery.implemented.{field} is required when delivery.status is "{status}"',
                    )
        # status == "frozen" (or any other declared status): implemented may be null/absent.

    def validate_dom(self) -> None:
        assert self.root is not None
        root = self.root

        mains = [
            node for node in walk(root) if node.tag == "main" and node.has("data-ui-contract")
        ]
        if not mains:
            self.add_error("HTML", 'missing required <main data-ui-contract> root element')
        elif len(mains) > 1:
            self.add_error(
                "HTML",
                f"multiple <main data-ui-contract> root elements found ({len(mains)}); "
                "only one root unit is allowed",
            )
        else:
            self.validate_main_matches_unit(mains[0])

        self.validate_ui_ids(root)
        self.validate_forbidden_kinds(root)
        self.validate_states_in_dom(root)
        self.validate_evidence(root)
        self.validate_assets(root)

    def validate_main_matches_unit(self, main: Node) -> None:
        meta = self.meta
        if not isinstance(meta, dict):
            return
        unit = meta.get("unit")
        if not isinstance(unit, dict):
            return

        expected_id = unit.get("id")
        actual_id = main.get("data-ui-unit-id")
        if is_nonempty_str(expected_id) and actual_id != expected_id:
            self.add_error(
                "UNIT",
                f'main data-ui-unit-id "{actual_id}" does not match meta.unit.id "{expected_id}"',
            )

        expected_type = unit.get("type")
        actual_type = main.get("data-ui-unit-type")
        if is_nonempty_str(expected_type) and actual_type != expected_type:
            self.add_error(
                "UNIT",
                f'main data-ui-unit-type "{actual_type}" does not match meta.unit.type "{expected_type}"',
            )

    def validate_ui_ids(self, root: Node) -> None:
        seen_ids: set[str] = set()
        for node in walk(root):
            if not node.has("data-ui-id"):
                continue
            ui_id = node.get("data-ui-id")
            if not is_nonempty_str(ui_id):
                self.add_error(
                    "HTML",
                    "data-ui-id must be a non-empty string (empty or whitespace rejected)",
                )
                continue
            if ui_id in seen_ids:
                self.add_error("DUPLICATE_ID", f'duplicate data-ui-id "{ui_id}" found')
            else:
                seen_ids.add(ui_id)

            if not is_nonempty_str(node.get("data-figma-node")):
                self.add_error(
                    "SOURCE_NODE",
                    f'element with data-ui-id "{ui_id}" is missing required data-figma-node',
                )

            if not is_nonempty_str(node.get("data-ui-kind")):
                self.add_error(
                    "HTML",
                    f'element with data-ui-id "{ui_id}" is missing required data-ui-kind',
                )

    def validate_forbidden_kinds(self, root: Node) -> None:
        for node in walk(root):
            kind = node.get("data-ui-kind")
            if kind in FORBIDDEN_KINDS:
                ui_id = node.get("data-ui-id")
                descriptor = f'data-ui-id "{ui_id}"' if ui_id else f"<{node.tag}>"
                self.add_error(
                    "SYSTEM_UI",
                    f'element ({descriptor}) uses forbidden system UI kind "{kind}"; '
                    "system chrome must not be modeled as contract content",
                )

    def validate_states_in_dom(self, root: Node) -> None:
        meta = self.meta
        known_state_ids: set[str] | None = None
        if isinstance(meta, dict):
            states = meta.get("states")
            if isinstance(states, list):
                known_state_ids = {
                    state.get("id")
                    for state in states
                    if isinstance(state, dict) and is_nonempty_str(state.get("id"))
                }

        for node in walk(root):
            if node.tag != "template" or not node.has("data-ui-state"):
                continue
            state_id = node.get("data-ui-state")
            if known_state_ids is not None and state_id not in known_state_ids:
                self.add_error(
                    "STATE",
                    f'template state "{state_id}" is not declared in meta.states',
                )

    def validate_evidence(self, root: Node) -> None:
        panels = [node for node in walk(root) if node.has("data-ui-review-panel")]

        notes: dict[str, str] = {}
        for panel in panels:
            for node in walk(panel):
                if node.tag != "dt" or not node.has("data-ui-evidence-for"):
                    continue
                target = node.get("data-ui-evidence-for") or ""
                dd_node = None
                if node.parent is not None:
                    siblings = node.parent.children
                    idx = siblings.index(node)
                    for sibling in siblings[idx + 1 :]:
                        if sibling.tag == "dd":
                            dd_node = sibling
                            break
                        if sibling.tag == "dt":
                            break
                notes[target] = text_content(dd_node)

        for node in walk(root):
            if node.get("data-evidence") != "inferred":
                continue
            ui_id = node.get("data-ui-id") or ""
            note = notes.get(ui_id, "")
            if not note:
                self.add_error(
                    "DELIVERY",
                    f'element with data-ui-id "{ui_id}" has data-evidence="inferred" but no evidence '
                    "note was found in [data-ui-review-panel]",
                )

    def validate_assets(self, root: Node) -> None:
        for node in walk(root):
            if not node.has("data-src"):
                continue
            if not is_nonempty_str(node.get("data-ui-asset")):
                src = node.get("data-src")
                self.add_error(
                    "ASSET",
                    f'element with data-src "{src}" is missing required data-ui-asset metadata',
                )

    def run(self) -> bool:
        if not self.load_html():
            return not self.errors
        self.load_meta()
        self.validate_meta_fields()
        self.validate_dom()
        return not self.errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path, help="Path to the HTML UI contract file")
    args = parser.parse_args()

    if not args.contract.exists():
        print(f"ERROR: contract not found: {args.contract}", file=sys.stderr)
        return 1

    validator = ContractValidator(args.contract)
    ok = validator.run()

    if ok:
        print(f"OK: {args.contract}")
        return 0

    for error in validator.errors:
        print(f"FAIL {error.rule_id}: {error.message}", file=sys.stderr)
    print(f"INVALID: {args.contract} ({len(validator.errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
