#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
VALIDATOR="$ROOT/scripts/validate-delivery-status.py"

[[ -f "$VALIDATOR" ]] || {
  echo "FAIL: missing validator: $VALIDATOR" >&2
  exit 1
}

python3 - "$VALIDATOR" <<'PY'
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


validator = Path(sys.argv[1]).resolve()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory(prefix="ui-truth-index-validator.") as td:
    repo = Path(td) / "repo"
    req_root = repo / ".ai-delivery" / "requirements" / "REQ-UI"
    subreq = req_root / "sub-requirements" / "SR-001"
    contracts = subreq / "contracts"
    component = repo / "lib" / "profile_card.dart"
    golden_test = repo / "test" / "profile_card_golden_test.dart"
    default_preview = repo / "test" / "goldens" / "profile-card-default.png"
    loading_preview = repo / "test" / "goldens" / "profile-card-loading.png"
    index_path = contracts / "ui-truth-index.json"

    for path in (contracts, component.parent, golden_test.parent, default_preview.parent):
        path.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir()
    component.write_text("class ProfileCard {}\n", encoding="utf-8")
    golden_test.write_text("void main() {}\n", encoding="utf-8")
    default_preview.write_bytes(b"default-png")
    loading_preview.write_bytes(b"loading-png")

    status = {
        "requirement_id": "REQ-UI",
        "sub_requirements": {
            "SR-001": {
                "status": "spec_ready",
                "ui_bearing": True,
                "design_approved": True,
            }
        },
    }
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    valid_index = {
        "schema_version": 2,
        "design_source": {
            "file_key": "figma-file-key",
            "root_node": "12:34",
            "revision": "rev-2026-08-25",
            "captured_at": "2026-08-25T00:00:00Z",
        },
        "units": [
            {
                "unit_id": "profile-card",
                "type": "component",
                "stack": "flutter",
                "source_node": "12:40",
                "dependencies": [],
                "component_path": "lib/profile_card.dart",
                "component_sha256": sha256(component),
                "golden_test": "test/profile_card_golden_test.dart",
                "golden_test_sha256": sha256(golden_test),
                "profiles": [
                    {
                        "profile_id": "phone-portrait-light",
                        "surface": {
                            "kind": "viewport",
                            "width": 390,
                            "height": 844,
                            "device_pixel_ratio": 3,
                        },
                        "orientation": "portrait",
                        "theme": "light",
                        "locale": "en-US",
                        "text_scale": 1.0,
                        "reduced_motion": False,
                        "input_mode": "touch",
                    },
                    {
                        "profile_id": "phone-reduced-motion",
                        "surface": {
                            "kind": "viewport",
                            "width": 390,
                            "height": 844,
                            "device_pixel_ratio": 3,
                        },
                        "orientation": "portrait",
                        "theme": "light",
                        "locale": "en-US",
                        "text_scale": 1.0,
                        "reduced_motion": True,
                        "input_mode": "touch",
                    },
                ],
                "states": [
                    {
                        "state_id": "default",
                        "evidence_origin": "figma",
                        "source_ref": "figma:12:41",
                        "source_node": "12:41",
                    },
                    {
                        "state_id": "loading",
                        "evidence_origin": "requirement",
                        "source_ref": "requirement-slice.md#acceptance-signals",
                    },
                ],
                "scenarios": [
                    {
                        "scenario_id": "default-phone",
                        "state_id": "default",
                        "profile_id": "phone-portrait-light",
                        "dimensions": [
                            "state",
                            "layout",
                            "content",
                            "theme",
                            "accessibility",
                            "platform",
                        ],
                        "review_mode": "visual",
                        "evidence_origin": "figma",
                        "source_ref": "figma:12:41",
                        "preview_path": "test/goldens/profile-card-default.png",
                        "preview_sha256": sha256(default_preview),
                        "confirmation": {
                            "status": "confirmed",
                            "confirmed_at": "2026-08-25T00:10:00Z",
                            "confirmed_by": "user",
                            "reviewed_preview_sha256": sha256(default_preview),
                            "note": "Matches the approved design state.",
                        },
                    },
                    {
                        "scenario_id": "loading-phone",
                        "state_id": "loading",
                        "profile_id": "phone-portrait-light",
                        "dimensions": ["state", "interaction", "assets"],
                        "review_mode": "both",
                        "evidence_origin": "requirement",
                        "source_ref": "requirement-slice.md#acceptance-signals",
                        "preview_path": "test/goldens/profile-card-loading.png",
                        "preview_sha256": sha256(loading_preview),
                        "confirmation": {
                            "status": "confirmed",
                            "confirmed_at": "2026-08-25T00:11:00Z",
                            "confirmed_by": "user",
                            "reviewed_preview_sha256": sha256(loading_preview),
                            "note": "Loading behavior and its visual keyframe are approved.",
                        },
                    },
                    {
                        "scenario_id": "reduced-motion",
                        "state_id": "default",
                        "profile_id": "phone-reduced-motion",
                        "dimensions": ["motion"],
                        "review_mode": "behavior",
                        "evidence_origin": "project",
                        "source_ref": "docs/accessibility.md#reduced-motion",
                        "confirmation": {
                            "status": "confirmed",
                            "confirmed_at": "2026-08-25T00:12:00Z",
                            "confirmed_by": "user",
                            "note": "Reduced motion renders the readable end state.",
                        },
                    }
                ],
                "coverage": [
                    {
                        "dimension": "state",
                        "status": "covered",
                        "scenario_ids": ["default-phone", "loading-phone"],
                        "note": "Default and loading states are covered.",
                    },
                    {
                        "dimension": "layout",
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": "The supported phone viewport is covered.",
                    },
                    {
                        "dimension": "content",
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": "Content sizing is covered by the default scenario.",
                    },
                    {
                        "dimension": "interaction",
                        "status": "covered",
                        "scenario_ids": ["loading-phone"],
                        "note": "Loading interaction behavior is covered.",
                    },
                    {
                        "dimension": "motion",
                        "status": "covered",
                        "scenario_ids": ["reduced-motion"],
                        "note": "Reduced-motion behavior is covered.",
                    },
                    {
                        "dimension": "assets",
                        "status": "covered",
                        "scenario_ids": ["loading-phone"],
                        "note": "Loading asset behavior is covered.",
                    },
                    {
                        "dimension": "theme",
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": "The supported light theme is covered.",
                    },
                    {
                        "dimension": "accessibility",
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": "Semantic and contrast checks are covered.",
                    },
                    {
                        "dimension": "platform",
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": "The supported touch platform is covered.",
                    },
                    {
                        "dimension": "performance",
                        "status": "not_applicable",
                        "scenario_ids": [],
                        "note": "This static unit has no independent performance behavior.",
                    },
                ],
            }
        ],
    }

    def write_index(data: dict) -> None:
        index_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(validator),
                str(req_root / "status.json"),
                "--req-root",
                str(req_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def expect_pass(label: str, data: dict) -> None:
        write_index(data)
        result = run()
        require(result.returncode == 0, f"{label}: expected pass, got:\n{result.stderr}")

    def expect_fail(label: str, data: dict | None, needle: str) -> None:
        if data is None:
            index_path.unlink(missing_ok=True)
        else:
            write_index(data)
        result = run()
        output = result.stdout + result.stderr
        require(result.returncode != 0, f"{label}: validator unexpectedly passed")
        require(needle in output, f"{label}: missing {needle!r} in:\n{output}")

    # Schema v2 runtime coverage remains required at every explicit post-freeze UI status.
    expect_pass("valid runtime coverage spec_ready", valid_index)
    expect_fail("missing index at spec_ready", None, "requires contracts/ui-truth-index.json")

    wrong_schema = copy.deepcopy(valid_index)
    wrong_schema["schema_version"] = 1
    expect_fail("wrong schema version", wrong_schema, "schema_version must equal 2")

    missing_design_revision = copy.deepcopy(valid_index)
    del missing_design_revision["design_source"]["revision"]
    expect_fail("missing design revision", missing_design_revision, "design_source.revision is required")

    escaped = copy.deepcopy(valid_index)
    outside = repo.parent / "outside.dart"
    outside.write_text("outside\n", encoding="utf-8")
    escaped["units"][0]["component_path"] = "../outside.dart"
    escaped["units"][0]["component_sha256"] = sha256(outside)
    expect_fail("dot-dot path escape", escaped, "component_path must stay within repository root")

    symlinked = copy.deepcopy(valid_index)
    symlink = repo / "lib" / "escaped.dart"
    symlink.symlink_to(outside)
    symlinked["units"][0]["component_path"] = "lib/escaped.dart"
    symlinked["units"][0]["component_sha256"] = sha256(outside)
    expect_fail("symlink path escape", symlinked, "component_path resolves outside repository root")

    invalid_stack = copy.deepcopy(valid_index)
    invalid_stack["units"][0]["stack"] = "fluter"
    expect_fail("invalid stack", invalid_stack, "stack must be one of")

    invalid_unit = copy.deepcopy(valid_index)
    invalid_unit["units"][0]["unit_id"] = "Profile Card"
    expect_fail("invalid unit id", invalid_unit, "unit_id must be kebab-case")

    duplicate_units = copy.deepcopy(valid_index)
    duplicate_units["units"].append(copy.deepcopy(duplicate_units["units"][0]))
    expect_fail("duplicate unit id", duplicate_units, "duplicate unit_id")

    duplicate_states = copy.deepcopy(valid_index)
    duplicate_states["units"][0]["states"][1]["state_id"] = "default"
    expect_fail("duplicate state id", duplicate_states, "duplicate state_id")

    invalid_origin = copy.deepcopy(valid_index)
    invalid_origin["units"][0]["states"][1]["evidence_origin"] = "inferred"
    expect_fail("invalid evidence origin", invalid_origin, "evidence_origin must be one of")

    figma_without_node = copy.deepcopy(valid_index)
    del figma_without_node["units"][0]["states"][0]["source_node"]
    expect_fail("figma state without node", figma_without_node, "source_node is required for figma evidence")

    runtime_without_ref = copy.deepcopy(valid_index)
    del runtime_without_ref["units"][0]["states"][1]["source_ref"]
    expect_fail("runtime state without source", runtime_without_ref, "source_ref is required")

    unknown_profile = copy.deepcopy(valid_index)
    unknown_profile["units"][0]["scenarios"][0]["profile_id"] = "missing-profile"
    expect_fail("unknown profile", unknown_profile, "references unknown profile missing-profile")

    unknown_state = copy.deepcopy(valid_index)
    unknown_state["units"][0]["scenarios"][0]["state_id"] = "missing-state"
    expect_fail("unknown state", unknown_state, "references unknown state missing-state")

    duplicate_scenarios = copy.deepcopy(valid_index)
    duplicate_scenarios["units"][0]["scenarios"].append(
        copy.deepcopy(duplicate_scenarios["units"][0]["scenarios"][0])
    )
    expect_fail("duplicate scenario", duplicate_scenarios, "duplicate scenario_id")

    missing_coverage = copy.deepcopy(valid_index)
    missing_coverage["units"][0]["coverage"] = [
        row for row in missing_coverage["units"][0]["coverage"]
        if row["dimension"] != "performance"
    ]
    expect_fail("missing coverage dimension", missing_coverage, "missing coverage dimension: performance")

    unresolved_coverage = copy.deepcopy(valid_index)
    unresolved_coverage["units"][0]["coverage"][0]["status"] = "unresolved"
    expect_fail("unresolved coverage", unresolved_coverage, "coverage status must be one of")

    invalid_not_applicable = copy.deepcopy(valid_index)
    invalid_not_applicable["units"][0]["coverage"][-1]["note"] = ""
    expect_fail("not applicable without note", invalid_not_applicable, "not_applicable coverage requires a note")

    invalid_preview = copy.deepcopy(valid_index)
    text_preview = repo / "test" / "goldens" / "profile-card-default.txt"
    text_preview.write_text("not a preview", encoding="utf-8")
    invalid_preview["units"][0]["scenarios"][0]["preview_path"] = (
        "test/goldens/profile-card-default.txt"
    )
    invalid_preview["units"][0]["scenarios"][0]["preview_sha256"] = sha256(text_preview)
    invalid_preview["units"][0]["scenarios"][0]["confirmation"][
        "reviewed_preview_sha256"
    ] = sha256(text_preview)
    expect_fail("invalid Flutter preview type", invalid_preview, "preview_path must end with .png")

    drifted = copy.deepcopy(valid_index)
    component.write_text("class ProfileCard { final bool changed = true; }\n", encoding="utf-8")
    expect_fail("component hash drift", drifted, "component_sha256 mismatch")
    component.write_text("class ProfileCard {}\n", encoding="utf-8")

    missing_confirmation = copy.deepcopy(valid_index)
    del missing_confirmation["units"][0]["scenarios"][0]["confirmation"]
    expect_fail("missing confirmation", missing_confirmation, "confirmation must be an object")

    waiver_without_note = copy.deepcopy(valid_index)
    waiver_without_note["units"][0]["scenarios"][1]["confirmation"]["status"] = "waived"
    waiver_without_note["units"][0]["scenarios"][1]["confirmation"]["note"] = ""
    expect_fail("waiver without note", waiver_without_note, "waiver note is required")

    stale_confirmation = copy.deepcopy(valid_index)
    stale_confirmation["units"][0]["scenarios"][0]["confirmation"][
        "reviewed_preview_sha256"
    ] = "0" * 64
    expect_fail("stale preview confirmation", stale_confirmation, "reviewed_preview_sha256 must match preview_sha256")

    unknown_dependency = copy.deepcopy(valid_index)
    unknown_dependency["units"][0]["dependencies"] = ["missing-unit"]
    expect_fail("unknown dependency", unknown_dependency, "unknown dependency missing-unit")

print("PASS: ui-truth-index v2 rejects incomplete runtime coverage and stale visual evidence.")
PY
