#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
export KIT_ROOT="$ROOT"

python3 - <<'PY'
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(os.environ["KIT_ROOT"])
scripts = root / ".agents/skills/ai-delivery-orchestrator/scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load("design_contract", scripts / "design_contract.py")
reconcile = load("reconcile", scripts / "reconcile-delivery.py")
example = root / ".agents/skills/ai-delivery-orchestrator/templates/design-state-flow-example.md"
design_text = example.read_text(encoding="utf-8")


def review(path: Path, *, mode: str = "self"):
    return {
        "review_mode": mode,
        "reviewed_design_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "reviewed_at": "2026-09-16T12:00:00Z",
        "reviewed_by": "user" if mode == "human" else "agent",
    }


def entry(*, status="design_ready", user_decision_required=False, mode="self"):
    return {
        "status": status,
        "ui_bearing": True,
        "ui_truth_mode": "existing",
        "state_flow_required": True,
        "user_decision_required": user_decision_required,
        "design_review": {
            "review_mode": mode,
            "reviewed_design_sha256": None,
            "reviewed_at": None,
            "reviewed_by": None,
        },
    }


with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    sub = req / "sub-requirements" / "SR-001"
    sub.mkdir(parents=True)
    design = sub / "design.md"
    design.write_text(design_text, encoding="utf-8")

    # Complex state flow is documentation depth, not a human gate.
    current = entry()
    current["design_review"] = review(design)
    assert contract.validate_design_entry(
        current, sub, status="design_ready", legacy_allowed=False
    ) == []

    status_path = req / "status.json"
    status_path.write_text(
        json.dumps({"_schema": "2.0", "sub_requirements": {"SR-001": current}}),
        encoding="utf-8",
    )

    # A changed self-reviewed design reopens solution-design without CP-DESIGN.
    design.write_text(
        design_text.replace("stateDiagram-v2", "flowchart TD", 1),
        encoding="utf-8",
    )
    errors = contract.validate_design_entry(
        current, sub, status="design_ready", legacy_allowed=False
    )
    assert any("hash does not match" in item for item in errors), errors
    reconciled = reconcile.reconcile(
        status_path,
        req,
        validator_script=root / "scripts/validate-delivery-status.py",
    )
    assert reconciled["next_action"] == "solution-design", reconciled
    assert reconciled["runtime_mode"] == "resume", reconciled
    assert reconciled["checkpoint"] is None, reconciled

    current["design_review"] = review(design)
    errors = contract.validate_design_entry(
        current, sub, status="design_ready", legacy_allowed=False
    )
    assert any(
        "state-flow contract requires a Mermaid stateDiagram-v2" in item
        for item in errors
    ), errors

    # Review mode follows user authority, not state-flow complexity.
    wrong_mode = {**current, "design_review": review(design, mode="human")}
    errors = contract.validate_design_entry(
        wrong_mode, sub, status="design_ready", legacy_allowed=False
    )
    assert any("requires design_review.review_mode=self" in item for item in errors), errors

    duplicate = design_text.replace(
        "| T-005 | Submitting | CancelIntent | command cancellable | invalidate active id | Editing | CancelCommand(id) | Cancelled(id) |",
        "| T-005 | Submitting | CancelIntent | duplicate | duplicate | Editing | none | none |\n| T-005 | Submitting | CancelIntent | command cancellable | invalidate active id | Editing | CancelCommand(id) | Cancelled(id) |",
    )
    design.write_text(duplicate, encoding="utf-8")
    errors = contract.validate_design_document(design, state_flow_required=True)
    assert any("duplicate IDs" in item for item in errors), errors

    orphan = design_text.replace(
        "Submitting --> Submitted: T-003 success",
        "Submitting --> Submitted: T-003 success\n  Submitted --> Editing: T-999 illegal",
    )
    design.write_text(orphan, encoding="utf-8")
    errors = contract.validate_design_document(design, state_flow_required=True)
    assert any("unknown transition IDs" in item for item in errors), errors

    # Scaffold placeholders are not a valid completed behavior contract.
    template = root / ".agents/skills/ai-delivery-orchestrator/templates/design-template.md"
    placeholder_errors = contract.validate_behavior_contract(
        template,
        user_decision_required=False,
    )
    assert any("placeholder" in item for item in placeholder_errors), placeholder_errors

    # Historical terminal records remain readable without invented evidence.
    archived = {
        "status": "archived",
        "ui_bearing": True,
        "ui_truth_mode": "existing",
        "design_mode": "full",
        "design_approved": True,
    }
    assert contract.validate_design_entry(
        archived, sub, status="archived", legacy_allowed=True
    ) == []

    active_legacy = {
        "status": "spec_ready",
        "ui_bearing": True,
        "ui_truth_mode": "existing",
        "design_mode": "full",
        "design_approved": True,
    }
    status_path.write_text(
        json.dumps({"_schema": "1.1", "sub_requirements": {"SR-001": active_legacy}}),
        encoding="utf-8",
    )
    output = subprocess.run(
        [
            "python3",
            str(root / "scripts/validate-delivery-status.py"),
            str(status_path),
            "--req-root",
            str(req),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert output.returncode != 0
    assert "requires migration to schema 2.0" in output.stderr, output.stderr

print("PASS: design state-flow contract")
PY
