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


# Minimal real GIF payloads keep this validator test independent of Pillow or
# any other image package while exercising the motion-file checks.
TWO_FRAME_GIF = bytes.fromhex(
    "47494638396101000100810000ff000000000000000000000021ff0b"
    "4e45545343415045322e30030100000021f904000a0000002c000000"
    "0001000100000804000104040021f904010a0001002c000000000100"
    "0100810000ff000000000000000000080400010404003b"
)
ONE_FRAME_GIF = bytes.fromhex(
    "47494638376101000100810000ff00000000000000000000002c0000"
    "00000100010000080400010404003b"
)


with tempfile.TemporaryDirectory(prefix="ui-truth-index-validator.") as td:
    repo = Path(td) / "repo"
    req_root = repo / ".ai-delivery" / "requirements" / "REQ-UI"
    subreq = req_root / "sub-requirements" / "SR-001"
    contracts = subreq / "contracts"
    component = repo / "lib" / "profile_card.dart"
    golden_test = repo / "test" / "profile_card_golden_test.dart"
    default_preview = repo / "test" / "goldens" / "profile-card-default.png"
    loading_preview = repo / "test" / "goldens" / "profile-card-loading.png"
    motion_preview = repo / "test" / "motion" / "profile-card-default.gif"
    index_path = contracts / "ui-truth-index.json"

    for path in (contracts, component.parent, golden_test.parent, default_preview.parent, motion_preview.parent):
        path.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir()
    component.write_text("class ProfileCard {}\n", encoding="utf-8")
    golden_test.write_text("void main() {}\n", encoding="utf-8")
    default_preview.write_bytes(b"default-png")
    loading_preview.write_bytes(b"loading-png")
    motion_preview.write_bytes(TWO_FRAME_GIF)
    (subreq / "design.md").write_text(
        "# Solution Design\n\n"
        "| Unit ID | Scenario ID | Responsibility | Verification |\n"
        "| profile-card | default-phone | Render the approved default state | golden |\n"
        "| profile-card | loading-phone | Render loading feedback | behavior test |\n"
        "| profile-card | reduced-motion | Honor reduced motion | semantics test |\n",
        encoding="utf-8",
    )

    status = {
        "_schema": "1.1",
        "requirement_id": "REQ-UI",
        "sub_requirements": {
            "SR-001": {
                "status": "spec_ready",
                "ui_bearing": True,
                "ui_truth_mode": "figma",
                "design_mode": "full",
                "state_flow_required": False,
                "design_approved": True,
                "design_review": {
                    "review_mode": "none",
                    "reviewed_design_sha256": None,
                    "reviewed_at": None,
                    "reviewed_by": None,
                },
            }
        },
    }
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    valid_index = {
        "schema_version": 2,
        "ui_truth_mode": "figma",
        "design_source": {
            "evidence_origin": "figma",
            "source_ref": "figma:file-key@rev-2026-08-25",
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
                "motion_decision": {
                    "decision": "animated",
                    "verification_mode": "runtime",
                    "preview_path": "test/motion/profile-card-default.gif",
                    "preview_sha256": sha256(motion_preview),
                    "confirmation": {
                        "status": "confirmed",
                        "confirmed_at": "2026-08-25T00:09:00Z",
                        "confirmed_by": "user",
                        "reviewed_preview_sha256": sha256(motion_preview),
                        "note": "The motion contract is separately approved.",
                    },
                },
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

    def sync_design_review() -> None:
        entry = status["sub_requirements"]["SR-001"]
        design_path = subreq / "design.md"
        if entry.get("design_approved") is True and design_path.is_file():
            entry["design_review"] = {
                "review_mode": "human" if entry.get("design_mode") == "full" else "self",
                "reviewed_design_sha256": sha256(design_path),
                "reviewed_at": "2026-09-09T00:00:00Z",
                "reviewed_by": "fixture-user",
            }
        else:
            entry["design_review"] = {
                "review_mode": "none",
                "reviewed_design_sha256": None,
                "reviewed_at": None,
                "reviewed_by": None,
            }

    def run() -> subprocess.CompletedProcess[str]:
        sync_design_review()
        (req_root / "status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8"
        )
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

    unsupported_motion_preview = copy.deepcopy(valid_index)
    mp4_preview = repo / "test" / "motion" / "profile-card-default.mp4"
    mp4_preview.write_bytes(b"motion-mp4")
    unsupported_motion_preview["units"][0]["motion_decision"]["preview_path"] = (
        "test/motion/profile-card-default.mp4"
    )
    unsupported_motion_preview["units"][0]["motion_decision"]["preview_sha256"] = sha256(
        mp4_preview
    )
    unsupported_motion_preview["units"][0]["motion_decision"]["confirmation"][
        "reviewed_preview_sha256"
    ] = sha256(mp4_preview)
    expect_fail(
        "unsupported motion preview type",
        unsupported_motion_preview,
        "motion_decision.preview_path must end with .gif",
    )

    malformed_motion_preview = copy.deepcopy(valid_index)
    motion_preview.write_bytes(b"not-a-gif")
    malformed_motion_preview["units"][0]["motion_decision"]["preview_sha256"] = sha256(
        motion_preview
    )
    malformed_motion_preview["units"][0]["motion_decision"]["confirmation"][
        "reviewed_preview_sha256"
    ] = sha256(motion_preview)
    expect_fail(
        "malformed GIF payload",
        malformed_motion_preview,
        "motion_decision.preview_path must be a valid GIF",
    )

    one_frame_motion_preview = copy.deepcopy(valid_index)
    motion_preview.write_bytes(ONE_FRAME_GIF)
    one_frame_motion_preview["units"][0]["motion_decision"]["preview_sha256"] = sha256(
        motion_preview
    )
    one_frame_motion_preview["units"][0]["motion_decision"]["confirmation"][
        "reviewed_preview_sha256"
    ] = sha256(motion_preview)
    expect_fail(
        "single-frame GIF payload",
        one_frame_motion_preview,
        "motion_decision.preview_path must contain at least two GIF frames",
    )

    motion_preview.write_bytes(TWO_FRAME_GIF)

    drifted = copy.deepcopy(valid_index)
    component.write_text("class ProfileCard { final bool changed = true; }\n", encoding="utf-8")
    expect_fail("component hash drift", drifted, "component_sha256 mismatch")
    component.write_text("class ProfileCard {}\n", encoding="utf-8")

    missing_confirmation = copy.deepcopy(valid_index)
    del missing_confirmation["units"][0]["scenarios"][0]["confirmation"]
    expect_fail("missing confirmation", missing_confirmation, "confirmation must be an object")

    missing_motion_decision = copy.deepcopy(valid_index)
    del missing_motion_decision["units"][0]["motion_decision"]
    expect_fail("missing motion decision", missing_motion_decision, "motion_decision must be an object")

    static_motion_without_decision_note = copy.deepcopy(valid_index)
    static_motion_without_decision_note["units"][0]["motion_decision"] = {
        "decision": "static",
        "verification_mode": "not_applicable",
        "confirmation": {
            "status": "confirmed",
            "confirmed_at": "2026-08-25T00:09:00Z",
            "confirmed_by": "user",
            "note": "",
        },
    }
    expect_fail(
        "static motion decision without note",
        static_motion_without_decision_note,
        "motion_decision confirmation.note is required",
    )

    static_motion_decision = copy.deepcopy(valid_index)
    static_motion_decision["units"][0]["motion_decision"] = {
        "decision": "static",
        "verification_mode": "not_applicable",
        "confirmation": {
            "status": "confirmed",
            "confirmed_at": "2026-08-25T00:09:00Z",
            "confirmed_by": "user",
            "note": "The unit is intentionally static and has no motion.",
        },
    }
    expect_pass("explicit static no-motion decision", static_motion_decision)

    static_motion_waived = copy.deepcopy(static_motion_decision)
    static_motion_waived["units"][0]["motion_decision"]["confirmation"]["status"] = "waived"
    expect_fail(
        "static motion decision cannot be waived",
        static_motion_waived,
        "static motion_decision requires confirmation.status=confirmed",
    )

    animated_without_preview_reason = copy.deepcopy(valid_index)
    animated_without_preview_reason["units"][0]["motion_decision"].pop("preview_path")
    animated_without_preview_reason["units"][0]["motion_decision"].pop("preview_sha256")
    animated_without_preview_reason["units"][0]["motion_decision"]["confirmation"].pop(
        "reviewed_preview_sha256"
    )
    expect_fail(
        "animated motion without preview reason",
        animated_without_preview_reason,
        "without a preview requires preview_unavailable_reason",
    )

    animated_without_preview = copy.deepcopy(animated_without_preview_reason)
    animated_without_preview["units"][0]["motion_decision"][
        "preview_unavailable_reason"
    ] = "The host test stack cannot record deterministic motion output."
    expect_pass("animated motion with deferred preview", animated_without_preview)

    animated_preview_with_unavailable_reason = copy.deepcopy(valid_index)
    animated_preview_with_unavailable_reason["units"][0]["motion_decision"][
        "preview_unavailable_reason"
    ] = "The host could not record motion."
    expect_fail(
        "animated motion preview contradicts unavailable reason",
        animated_preview_with_unavailable_reason,
        "with a preview must not declare preview_unavailable_reason",
    )

    animated_without_motion_scenario = copy.deepcopy(valid_index)
    animated_without_motion_scenario["units"][0]["scenarios"][2]["dimensions"].remove(
        "motion"
    )
    animated_without_motion_scenario["units"][0]["coverage"][4] = {
        "dimension": "motion",
        "status": "not_applicable",
        "scenario_ids": [],
        "note": "No motion scenario was provided.",
    }
    expect_fail(
        "animated motion without motion scenario",
        animated_without_motion_scenario,
        "animated motion_decision requires a motion scenario",
    )

    stale_motion_confirmation = copy.deepcopy(valid_index)
    stale_motion_confirmation["units"][0]["motion_decision"]["confirmation"][
        "reviewed_preview_sha256"
    ] = "0" * 64
    expect_fail(
        "stale motion preview confirmation",
        stale_motion_confirmation,
        "motion_decision confirmation.reviewed_preview_sha256 must match preview_sha256",
    )

    animated_without_runtime_verification = copy.deepcopy(valid_index)
    animated_without_runtime_verification["units"][0]["motion_decision"][
        "verification_mode"
    ] = "not_applicable"
    expect_fail(
        "animated motion without runtime verification",
        animated_without_runtime_verification,
        "animated motion_decision requires a runtime verification mode",
    )

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

    # The UI truth capability is selected explicitly by mode. Non-visual
    # slices do not need an index, while figma slices do.
    def set_mode(*, ui_bearing: bool, ui_truth_mode: str, design_mode: str) -> None:
        status["sub_requirements"]["SR-001"].update(
            {
                "ui_bearing": ui_bearing,
                "ui_truth_mode": ui_truth_mode,
                "design_mode": design_mode,
                "design_approved": design_mode != "none",
            }
        )
        (req_root / "status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8"
        )

    def expect_mode_pass(label: str, *, ui_bearing: bool, ui_truth_mode: str, design_mode: str) -> None:
        set_mode(
            ui_bearing=ui_bearing,
            ui_truth_mode=ui_truth_mode,
            design_mode=design_mode,
        )
        index_path.unlink(missing_ok=True)
        if design_mode == "none":
            (subreq / "design.md").unlink(missing_ok=True)
        else:
            (subreq / "design.md").write_text(
                "# Solution Design\n\nExisting component behavior change.\n",
                encoding="utf-8",
            )
        result = run()
        require(result.returncode == 0, f"{label}: expected pass, got:\n{result.stderr}")

    def expect_mode_fail(
        label: str,
        *,
        ui_bearing: bool,
        ui_truth_mode: str,
        design_mode: str,
        needle: str,
        design_approved: bool = False,
        design_text: str = "# Solution Design\n",
    ) -> None:
        set_mode(
            ui_bearing=ui_bearing,
            ui_truth_mode=ui_truth_mode,
            design_mode=design_mode,
        )
        status["sub_requirements"]["SR-001"]["design_approved"] = design_approved
        (req_root / "status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8"
        )
        index_path.unlink(missing_ok=True)
        (subreq / "design.md").write_text(design_text, encoding="utf-8")
        result = run()
        output = result.stdout + result.stderr
        require(result.returncode != 0, f"{label}: validator unexpectedly passed")
        require(needle in output, f"{label}: missing {needle!r} in:\n{output}")

    # none and existing are capability-free and intentionally accept no index.
    expect_mode_pass(
        "ui_truth_mode=none without index",
        ui_bearing=False,
        ui_truth_mode="none",
        design_mode="none",
    )
    expect_mode_pass(
        "ui_truth_mode=existing without index",
        ui_bearing=True,
        ui_truth_mode="existing",
        design_mode="light",
    )
    # A no-design slice cannot retain an approval bit or a stale design file.
    set_mode(ui_bearing=False, ui_truth_mode="none", design_mode="none")
    status["sub_requirements"]["SR-001"]["design_approved"] = True
    (subreq / "design.md").unlink(missing_ok=True)
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    result = run()
    require(result.returncode != 0, "design_mode=none approval flag unexpectedly passed")
    require(
        "cannot set design_approved=true" in result.stdout + result.stderr,
        "design_mode=none approval error was not reported",
    )
    status["sub_requirements"]["SR-001"]["design_approved"] = False

    # Approval cannot be forged before the canonical design artifact exists.
    set_mode(ui_bearing=True, ui_truth_mode="existing", design_mode="light")
    status["sub_requirements"]["SR-001"]["design_approved"] = True
    (subreq / "design.md").unlink(missing_ok=True)
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    result = run()
    require(result.returncode != 0, "approved design without design.md unexpectedly passed")
    require(
        "design_approved=true requires design.md" in result.stdout + result.stderr,
        "missing design artifact was not tied to approval",
    )
    status["sub_requirements"]["SR-001"]["design_approved"] = False

    expect_mode_fail(
        "design_mode=none forbids design artifact",
        ui_bearing=False,
        ui_truth_mode="none",
        design_mode="none",
        needle="must not produce design.md",
    )
    expect_mode_fail(
        "design_mode=light requires approval after spec",
        ui_bearing=False,
        ui_truth_mode="none",
        design_mode="light",
        needle="requires design_approved=true",
    )

    # Restore the governed Figma fixture for the remaining checks.
    set_mode(ui_bearing=True, ui_truth_mode="figma", design_mode="full")
    status["sub_requirements"]["SR-001"]["design_approved"] = True
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    (subreq / "design.md").write_text(
        "# Solution Design\n\n"
        "Scenario IDs: default-phone loading-phone reduced-motion\n",
        encoding="utf-8",
    )
    expect_pass("ui_truth_mode=figma with index", valid_index)

    runtime_baseline = copy.deepcopy(valid_index)
    runtime_baseline["ui_truth_mode"] = "runtime-baseline"
    runtime_baseline["design_source"] = {
        "evidence_origin": "requirement",
        "source_ref": "requirement-slice.md#ui-baseline",
        "captured_at": "2026-08-25T00:00:00Z",
    }
    for unit in runtime_baseline["units"]:
        for state in unit.get("states", []):
            if state.get("evidence_origin") == "figma":
                state["evidence_origin"] = "requirement"
                state["source_ref"] = "requirement-slice.md#ui-baseline"
                state.pop("source_node", None)
        for scenario in unit.get("scenarios", []):
            if scenario.get("evidence_origin") == "figma":
                scenario["evidence_origin"] = "requirement"
                scenario["source_ref"] = "requirement-slice.md#ui-baseline"
    set_mode(
        ui_bearing=True,
        ui_truth_mode="runtime-baseline",
        design_mode="light",
    )
    runtime_with_figma_source = copy.deepcopy(valid_index)
    runtime_with_figma_source["ui_truth_mode"] = "runtime-baseline"
    expect_fail(
        "runtime-baseline rejects Figma-only design source",
        runtime_with_figma_source,
        "cannot use figma design_source",
    )
    expect_pass("runtime-baseline with deterministic index", runtime_baseline)

    mismatch = copy.deepcopy(valid_index)
    set_mode(ui_bearing=False, ui_truth_mode="figma", design_mode="full")
    expect_fail("ui_bearing/mode mismatch", mismatch, "ui_bearing")

    mismatch_none = copy.deepcopy(valid_index)
    set_mode(ui_bearing=True, ui_truth_mode="none", design_mode="none")
    expect_fail("ui-bearing true with no UI truth", mismatch_none, "ui_bearing")

    unknown_ui_mode = copy.deepcopy(valid_index)
    set_mode(ui_bearing=True, ui_truth_mode="invented", design_mode="full")
    expect_fail("unknown ui truth mode", unknown_ui_mode, "ui_truth_mode")

    unknown_design_mode = copy.deepcopy(valid_index)
    set_mode(ui_bearing=True, ui_truth_mode="figma", design_mode="partial")
    expect_fail("unknown design mode", unknown_design_mode, "design_mode")

    legacy_bypass = copy.deepcopy(valid_index)
    set_mode(ui_bearing=True, ui_truth_mode="existing", design_mode="light")
    status["sub_requirements"]["SR-001"]["ui_contract_exempt"] = True
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    expect_fail("deprecated ui contract bypass", legacy_bypass, "ui_contract_exempt")
    del status["sub_requirements"]["SR-001"]["ui_contract_exempt"]

    legacy_participation = copy.deepcopy(valid_index)
    status["sub_requirements"]["SR-001"]["no_design_client"] = True
    (repo / ".ai-delivery" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".ai-delivery" / "meta" / "project-binding.json").write_text(
        json.dumps({"coordination": {"participation": "no_design_client"}}),
        encoding="utf-8",
    )
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    expect_fail("deprecated participation profile", legacy_participation, "no_design_client")
    del status["sub_requirements"]["SR-001"]["no_design_client"]
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    # Every indexed visual scenario must be referenced by solution design; a
    # missing reference is a stale design artifact, not a harmless omission.
    (repo / ".ai-delivery" / "meta" / "project-binding.json").unlink(missing_ok=True)
    set_mode(ui_bearing=True, ui_truth_mode="figma", design_mode="full")
    (subreq / "design.md").write_text(
        "# Solution Design\n\n"
        "Scenario IDs: default-phone-extra loading-phone-extra reduced-motion-extra\n",
        encoding="utf-8",
    )
    expect_fail(
        "design requires exact scenario references",
        valid_index,
        "must reference indexed scenario_id default-phone",
    )

print("PASS: ui-truth-index v2 rejects incomplete runtime coverage and stale visual evidence.")
PY
