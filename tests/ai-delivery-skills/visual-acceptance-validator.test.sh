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


# Minimal real GIF payload; the validator must reject extension-only fakes.
TWO_FRAME_GIF = bytes.fromhex(
    "47494638396101000100810000ff000000000000000000000021ff0b"
    "4e45545343415045322e30030100000021f904000a0000002c000000"
    "0001000100000804000104040021f904010a0001002c000000000100"
    "0100810000ff000000000000000000080400010404003b"
)


with tempfile.TemporaryDirectory(prefix="visual-acceptance-validator.") as td:
    repo = Path(td) / "repo"
    req_root = repo / ".ai-delivery" / "requirements" / "REQ-UI"
    subreq = req_root / "sub-requirements" / "SR-001"
    contracts = subreq / "contracts"
    component = repo / "lib" / "profile_card.dart"
    host_component = repo / "lib" / "profile_page.dart"
    golden_test = repo / "test" / "profile_card_golden_test.dart"
    runtime_test = repo / "integration_test" / "profile_page_test.dart"
    runtime_capture = repo / "integration_test" / "screenshots" / "profile" / "profile-page.png"
    assertion_report = repo / "integration_test" / "screenshots" / "profile" / "profile-page.assertions.json"
    preview = repo / "test" / "goldens" / "profile-card-default.png"
    motion_preview = repo / "test" / "motion" / "profile-card-default.gif"
    unrelated_preview = repo / "test" / "goldens" / "unrelated.png"
    index_path = contracts / "ui-truth-index.json"
    acceptance_path = subreq / "visual-acceptance.json"

    for path in (contracts, component.parent, golden_test.parent, preview.parent, motion_preview.parent, runtime_test.parent, runtime_capture.parent):
        path.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir()
    component.write_text("class ProfileCard {}\n", encoding="utf-8")
    host_component.write_text("class ProfilePage {}\n", encoding="utf-8")
    golden_test.write_text("void main() {}\n", encoding="utf-8")
    runtime_test.write_text("void main() {}\n", encoding="utf-8")
    runtime_capture.write_bytes(b"runtime-capture-png")
    assertion_report.write_text(
        json.dumps({"passed": ["profile-card-visible"]}) + "\n",
        encoding="utf-8",
    )
    preview.write_bytes(b"default-png")
    motion_preview.write_bytes(TWO_FRAME_GIF)
    unrelated_preview.write_bytes(b"unrelated-png")
    (subreq / "design.md").write_text(
        "# Solution Design\n\n"
        "Scenario IDs: default-phone\n",
        encoding="utf-8",
    )

    status = {
        "_schema": "1.1",
        "requirement_id": "REQ-UI",
        "sub_requirements": {
            "SR-001": {
                "status": "visual_acceptance_passed",
                "ui_bearing": True,
                "ui_truth_mode": "figma",
                "design_mode": "full",
                "state_flow_required": False,
                "design_approved": True,
                "design_review": {
                    "review_mode": "human",
                    "reviewed_design_sha256": sha256(subreq / "design.md"),
                    "reviewed_at": "2026-09-09T00:00:00Z",
                    "reviewed_by": "fixture-user",
                },
            }
        },
    }
    (req_root / "status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    dimensions = [
        "state",
        "layout",
        "content",
        "interaction",
        "motion",
        "assets",
        "theme",
        "accessibility",
        "platform",
        "performance",
    ]
    index = {
        "schema_version": 3,
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
                    }
                ],
                "states": [
                    {
                        "state_id": "default",
                        "evidence_origin": "figma",
                        "source_ref": "figma:12:41",
                        "source_node": "12:41",
                    }
                ],
                "scenarios": [
                    {
                        "scenario_id": "default-phone",
                        "evidence_scope": "component-only",
                        "scope_decision": {
                            "reason": "The component has a deterministic native preview.",
                            "host_capture_supported": False,
                            "uncovered_risk": "Host composition is outside this scenario's acceptance claim.",
                        },
                        "state_id": "default",
                        "profile_id": "phone-portrait-light",
                        "dimensions": dimensions,
                        "review_mode": "both",
                        "evidence_origin": "figma",
                        "source_ref": "figma:12:41",
                        "preview_path": "test/goldens/profile-card-default.png",
                        "preview_sha256": sha256(preview),
                        "confirmation": {
                            "status": "confirmed",
                            "confirmed_at": "2026-08-25T00:10:00Z",
                            "confirmed_by": "user",
                            "reviewed_preview_sha256": sha256(preview),
                            "note": "The preview is approved.",
                        },
                    }
                ],
                "coverage": [
                    {
                        "dimension": dimension,
                        "status": "covered",
                        "scenario_ids": ["default-phone"],
                        "note": f"{dimension} is covered by the default scenario.",
                    }
                    for dimension in dimensions
                ],
            }
        ],
    }
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    valid_acceptance = {
        "schema_version": 2,
        "ui_truth_index_sha256": sha256(index_path),
        "generated_at": "2026-08-25T01:00:00Z",
        "scenarios": [
            {
                "scenario_id": "default-phone",
                "result": "passed",
                "evidence": [
                    {
                        "kind": "preview",
                        "path": "test/goldens/profile-card-default.png",
                        "sha256": sha256(preview),
                        "command": "flutter test test/profile_card_golden_test.dart",
                        "summary": "The deterministic golden passed.",
                    },
                    {
                        "kind": "manual",
                        "reviewed_by": "reviewer",
                        "reviewed_at": "2026-08-25T01:00:00Z",
                        "summary": "Keyboard and semantics behavior passed review.",
                    },
                ],
                "note": "Visual and behavior evidence are complete.",
            }
        ],
        "motion_acceptance": [
            {
                "unit_id": "profile-card",
                "result": "passed",
                "evidence": [
                    {
                        "kind": "motion",
                        "path": "test/motion/profile-card-default.gif",
                        "sha256": sha256(motion_preview),
                        "command": "record-motion",
                        "summary": "The deterministic motion recording passed.",
                    }
                ],
                "note": "Motion acceptance is independent from the golden frame.",
            }
        ],
    }

    def write_acceptance(data: dict) -> None:
        acceptance_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def run() -> subprocess.CompletedProcess[str]:
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
        write_acceptance(data)
        result = run()
        require(result.returncode == 0, f"{label}: expected pass, got:\n{result.stderr}")

    def expect_fail(label: str, data: dict | None, needle: str) -> None:
        if data is None:
            acceptance_path.unlink(missing_ok=True)
        else:
            write_acceptance(data)
        result = run()
        output = result.stdout + result.stderr
        require(result.returncode != 0, f"{label}: validator unexpectedly passed")
        require(needle in output, f"{label}: missing {needle!r} in:\n{output}")

    expect_pass("valid structured visual acceptance", valid_acceptance)
    expect_fail("missing acceptance", None, "requires visual-acceptance.json")

    host_index = copy.deepcopy(index)
    host_scenario = host_index["units"][0]["scenarios"][0]
    host_scenario["evidence_scope"] = "host-runtime"
    host_scenario["scope_decision"] = {
        "reason": "The production host requires a runtime renderer.",
        "host_capture_supported": True,
        "uncovered_risk": None,
    }
    host_scenario["host_binding"] = {
        "host_component_path": "lib/profile_page.dart",
        "host_component_sha256": sha256(host_component),
        "entrypoint_ref": "ProfilePage",
        "capture_boundary_ref": "profile-page-viewport",
        "evidence_root": "integration_test/screenshots/profile",
        "required_landmarks": ["profile-card"],
        "spatial_constraints": [
            {
                "constraint_id": "profile-card-visible",
                "kind": "visible",
                "subject_ref": "profile-card",
                "source_ref": "figma:12:41",
            }
        ],
    }
    index_path.write_text(json.dumps(host_index, indent=2) + "\n", encoding="utf-8")
    runtime_acceptance = copy.deepcopy(valid_acceptance)
    runtime_acceptance["ui_truth_index_sha256"] = sha256(index_path)
    runtime_acceptance["scenarios"][0]["evidence"][0] = {
        "kind": "runtime-capture",
        "path": "integration_test/screenshots/profile/profile-page.png",
        "sha256": sha256(runtime_capture),
        "test_path": "integration_test/profile_page_test.dart",
        "test_sha256": sha256(runtime_test),
        "assertion_report_path": "integration_test/screenshots/profile/profile-page.assertions.json",
        "assertion_report_sha256": sha256(assertion_report),
        "command": "run-runtime-capture",
        "host_component_path": "lib/profile_page.dart",
        "entrypoint_ref": "ProfilePage",
        "capture_boundary_ref": "profile-page-viewport",
        "verified_landmarks": ["profile-card"],
        "verified_constraints": ["profile-card-visible"],
        "reviewed_by": "user",
        "reviewed_at": "2026-08-25T01:00:00Z",
        "reviewed_capture_sha256": sha256(runtime_capture),
        "summary": "The production runtime host passed visual review.",
    }
    expect_pass("valid runtime host capture", runtime_acceptance)

    missing_runtime_capture = copy.deepcopy(runtime_acceptance)
    missing_runtime_capture["scenarios"][0]["evidence"] = [
        missing_runtime_capture["scenarios"][0]["evidence"][1]
    ]
    expect_fail(
        "host scope requires runtime capture",
        missing_runtime_capture,
        "requires runtime-capture evidence",
    )

    governed_capture = copy.deepcopy(runtime_acceptance)
    governed_path = subreq / "evidence" / "profile-page.png"
    governed_path.parent.mkdir(parents=True, exist_ok=True)
    governed_path.write_bytes(b"governed-capture")
    governed_capture["scenarios"][0]["evidence"][0]["path"] = str(
        governed_path.relative_to(repo)
    )
    governed_capture["scenarios"][0]["evidence"][0]["sha256"] = sha256(
        governed_path
    )
    governed_capture["scenarios"][0]["evidence"][0][
        "reviewed_capture_sha256"
    ] = sha256(governed_path)
    expect_fail(
        "runtime capture cannot live in governance tree",
        governed_capture,
        "runtime capture must stay outside .ai-delivery",
    )

    missing_landmark = copy.deepcopy(runtime_acceptance)
    missing_landmark["scenarios"][0]["evidence"][0]["verified_landmarks"] = []
    expect_fail(
        "runtime capture must verify landmarks",
        missing_landmark,
        "missing required landmark profile-card",
    )

    manual_visual_claim = copy.deepcopy(runtime_acceptance)
    manual_visual_claim["scenarios"][0]["evidence"] = [
        {
            "kind": "manual",
            "reviewed_by": "reviewer",
            "reviewed_at": "2026-08-25T01:00:00Z",
            "summary": "The screenshot filename is profile-page.png.",
        }
    ]
    expect_fail(
        "manual text cannot prove host visual",
        manual_visual_claim,
        "requires runtime-capture evidence",
    )

    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    valid_acceptance["ui_truth_index_sha256"] = sha256(index_path)

    missing_motion_acceptance = copy.deepcopy(valid_acceptance)
    del missing_motion_acceptance["motion_acceptance"]
    expect_fail(
        "missing motion acceptance",
        missing_motion_acceptance,
        "motion_acceptance must be an array",
    )

    mismatched_motion_evidence = copy.deepcopy(valid_acceptance)
    mismatched_motion_evidence["motion_acceptance"][0]["evidence"][0]["path"] = (
        "test/motion/other-unit.gif"
    )
    expect_fail(
        "motion evidence from another unit",
        mismatched_motion_evidence,
        "motion evidence must match motion_decision preview_path",
    )

    wrong_schema = copy.deepcopy(valid_acceptance)
    wrong_schema["schema_version"] = 1
    expect_fail("wrong schema", wrong_schema, "schema_version must equal 2")

    stale_index = copy.deepcopy(valid_acceptance)
    stale_index["ui_truth_index_sha256"] = "0" * 64
    expect_fail("stale index binding", stale_index, "ui_truth_index_sha256 mismatch")

    missing_scenario = copy.deepcopy(valid_acceptance)
    missing_scenario["scenarios"] = []
    expect_fail("missing scenario", missing_scenario, "missing scenario result: default-phone")

    unknown_scenario = copy.deepcopy(valid_acceptance)
    unknown_scenario["scenarios"][0]["scenario_id"] = "unknown-scenario"
    expect_fail("unknown scenario", unknown_scenario, "references unknown scenario unknown-scenario")

    failed_result = copy.deepcopy(valid_acceptance)
    failed_result["scenarios"][0]["result"] = "failed"
    expect_fail("failed result", failed_result, "result must be one of")

    missing_behavior = copy.deepcopy(valid_acceptance)
    missing_behavior["scenarios"][0]["evidence"] = [
        missing_behavior["scenarios"][0]["evidence"][0]
    ]
    expect_fail("missing behavior evidence", missing_behavior, "requires test or manual evidence")

    forged_path = copy.deepcopy(valid_acceptance)
    forged_path["scenarios"][0]["evidence"][0]["path"] = "../outside.png"
    expect_fail("forged path", forged_path, "must stay within repository root")

    drifted_evidence = copy.deepcopy(valid_acceptance)
    drifted_evidence["scenarios"][0]["evidence"][0]["sha256"] = "0" * 64
    expect_fail("evidence drift", drifted_evidence, "sha256 mismatch")

    mismatched_preview = copy.deepcopy(valid_acceptance)
    mismatched_preview["scenarios"][0]["evidence"][0]["path"] = (
        "test/goldens/unrelated.png"
    )
    mismatched_preview["scenarios"][0]["evidence"][0]["sha256"] = sha256(
        unrelated_preview
    )
    expect_fail(
        "preview from another scenario",
        mismatched_preview,
        "preview evidence must match the indexed scenario preview",
    )

    non_finite_threshold = copy.deepcopy(valid_acceptance)
    non_finite_threshold["scenarios"][0]["evidence"][0] = {
        "kind": "image-diff",
        "reference_path": "test/goldens/profile-card-default.png",
        "reference_sha256": sha256(preview),
        "candidate_path": "test/goldens/profile-card-default.png",
        "candidate_sha256": sha256(preview),
        "diff_path": "test/goldens/profile-card-default.png",
        "diff_sha256": sha256(preview),
        "metric": "pixel-ratio",
        "threshold": float("nan"),
        "actual": 0,
        "command": "compare-goldens",
        "summary": "The comparison is not valid with a non-finite threshold.",
    }
    expect_fail(
        "non-finite image threshold",
        non_finite_threshold,
        "threshold must be a non-negative number",
    )

    waiver_without_note = copy.deepcopy(valid_acceptance)
    waiver_without_note["scenarios"][0] = {
        "scenario_id": "default-phone",
        "result": "waived",
        "evidence": [],
        "waived_by": "user",
        "waived_at": "2026-08-25T01:00:00Z",
        "note": "",
    }
    expect_fail("waiver without note", waiver_without_note, "waiver note is required")

    static_index = copy.deepcopy(index)
    static_index["units"][0]["motion_decision"] = {
        "decision": "static",
        "verification_mode": "not_applicable",
        "confirmation": {
            "status": "confirmed",
            "confirmed_at": "2026-08-25T00:09:00Z",
            "confirmed_by": "user",
            "note": "The unit is intentionally static and has no motion.",
        },
    }
    index_path.write_text(json.dumps(static_index, indent=2) + "\n", encoding="utf-8")
    static_acceptance = copy.deepcopy(valid_acceptance)
    static_acceptance["ui_truth_index_sha256"] = sha256(index_path)
    static_acceptance["motion_acceptance"] = [
        {
            "unit_id": "profile-card",
            "result": "passed",
            "evidence": [
                {
                    "kind": "manual",
                    "reviewed_by": "reviewer",
                    "reviewed_at": "2026-08-25T01:00:00Z",
                    "summary": "The unit remains static under the supported profile.",
                }
            ],
            "note": "Static/no-motion acceptance is complete.",
        }
    ]
    expect_pass("static no-motion acceptance", static_acceptance)

    static_without_motion_evidence = copy.deepcopy(static_acceptance)
    static_without_motion_evidence["motion_acceptance"][0]["evidence"] = []
    expect_fail(
        "static no-motion acceptance without evidence",
        static_without_motion_evidence,
        "static/no-motion acceptance requires test or manual evidence",
    )

    static_preview_as_test_evidence = copy.deepcopy(static_acceptance)
    static_preview_as_test_evidence["motion_acceptance"][0]["evidence"] = [
        {
            "kind": "test",
            "path": "test/goldens/profile-card-default.png",
            "sha256": sha256(preview),
            "command": "flutter test",
            "summary": "The static golden was incorrectly used as motion evidence.",
        }
    ]
    expect_fail(
        "static golden cannot be motion test evidence",
        static_preview_as_test_evidence,
        "must reference a test/report artifact, not a preview file",
    )

    static_motion_waived = copy.deepcopy(static_acceptance)
    static_motion_waived["motion_acceptance"][0].update(
        {
            "result": "waived",
            "waived_by": "user",
            "waived_at": "2026-08-25T01:00:00Z",
            "note": "No motion exists.",
        }
    )
    expect_fail(
        "static no-motion acceptance cannot be waived",
        static_motion_waived,
        "static/no-motion acceptance cannot be waived",
    )

    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    def write_status(*, status_name: str, ui_bearing: bool, ui_truth_mode: str, design_mode: str) -> None:
        status["sub_requirements"]["SR-001"].update(
            {
                "status": status_name,
                "ui_bearing": ui_bearing,
                "ui_truth_mode": ui_truth_mode,
                "design_mode": design_mode,
                "design_approved": design_mode != "none",
            }
        )
        (req_root / "status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8"
        )

    def expect_without_acceptance(label: str, *, status_name: str, ui_bearing: bool, ui_truth_mode: str, design_mode: str) -> None:
        write_status(
            status_name=status_name,
            ui_bearing=ui_bearing,
            ui_truth_mode=ui_truth_mode,
            design_mode=design_mode,
        )
        acceptance_path.unlink(missing_ok=True)
        index_path.unlink(missing_ok=True)
        if design_mode == "none":
            (subreq / "design.md").unlink(missing_ok=True)
        else:
            (subreq / "design.md").write_text(
                "# Solution Design\n\nExisting behavior change.\n",
                encoding="utf-8",
            )
        result = run()
        require(result.returncode == 0, f"{label}: expected pass, got:\n{result.stderr}")

    expect_without_acceptance(
        "none skips visual acceptance",
        status_name="spec_ready",
        ui_bearing=False,
        ui_truth_mode="none",
        design_mode="none",
    )
    expect_without_acceptance(
        "existing skips visual acceptance",
        status_name="spec_ready",
        ui_bearing=True,
        ui_truth_mode="existing",
        design_mode="light",
    )

    # A runtime baseline has no Figma claim, but it still needs deterministic
    # visual evidence once its status reaches visual acceptance.
    write_status(
        status_name="visual_acceptance_passed",
        ui_bearing=True,
        ui_truth_mode="runtime-baseline",
        design_mode="light",
    )
    runtime_index = copy.deepcopy(index)
    runtime_index["ui_truth_mode"] = "runtime-baseline"
    runtime_index["design_source"] = {
        "evidence_origin": "requirement",
        "source_ref": "requirement-slice.md#ui-baseline",
        "captured_at": "2026-08-25T00:00:00Z",
    }
    for unit in runtime_index["units"]:
        for state in unit.get("states", []):
            if state.get("evidence_origin") == "figma":
                state["evidence_origin"] = "requirement"
                state["source_ref"] = "requirement-slice.md#ui-baseline"
                state.pop("source_node", None)
        for scenario in unit.get("scenarios", []):
            if scenario.get("evidence_origin") == "figma":
                scenario["evidence_origin"] = "requirement"
                scenario["source_ref"] = "requirement-slice.md#ui-baseline"
    index_path.write_text(json.dumps(runtime_index, indent=2) + "\n", encoding="utf-8")
    expect_fail(
        "runtime baseline missing acceptance",
        None,
        "requires visual-acceptance.json",
    )

    write_status(
        status_name="visual_acceptance_passed",
        ui_bearing=True,
        ui_truth_mode="figma",
        design_mode="full",
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (subreq / "design.md").write_text(
        "# Solution Design\n\nScenario IDs: default-phone\n",
        encoding="utf-8",
    )
    expect_pass("restore Figma acceptance after mode matrix", valid_acceptance)

print("PASS: structured visual acceptance rejects missing, stale, partial, and forged evidence.")
PY
