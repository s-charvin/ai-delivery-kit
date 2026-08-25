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


with tempfile.TemporaryDirectory(prefix="visual-acceptance-validator.") as td:
    repo = Path(td) / "repo"
    req_root = repo / ".ai-delivery" / "requirements" / "REQ-UI"
    subreq = req_root / "sub-requirements" / "SR-001"
    contracts = subreq / "contracts"
    component = repo / "lib" / "profile_card.dart"
    golden_test = repo / "test" / "profile_card_golden_test.dart"
    preview = repo / "test" / "goldens" / "profile-card-default.png"
    unrelated_preview = repo / "test" / "goldens" / "unrelated.png"
    index_path = contracts / "ui-truth-index.json"
    acceptance_path = subreq / "visual-acceptance.json"

    for path in (contracts, component.parent, golden_test.parent, preview.parent):
        path.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir()
    component.write_text("class ProfileCard {}\n", encoding="utf-8")
    golden_test.write_text("void main() {}\n", encoding="utf-8")
    preview.write_bytes(b"default-png")
    unrelated_preview.write_bytes(b"unrelated-png")

    status = {
        "requirement_id": "REQ-UI",
        "sub_requirements": {
            "SR-001": {
                "status": "visual_acceptance_passed",
                "ui_bearing": True,
                "design_approved": True,
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
        "schema_version": 1,
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
    }

    def write_acceptance(data: dict) -> None:
        acceptance_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

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

    wrong_schema = copy.deepcopy(valid_acceptance)
    wrong_schema["schema_version"] = 2
    expect_fail("wrong schema", wrong_schema, "schema_version must equal 1")

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

print("PASS: structured visual acceptance rejects missing, stale, partial, and forged evidence.")
PY
