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
script = root / ".agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py"
spec = importlib.util.spec_from_file_location("reconcile_delivery_test", script)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def design_text() -> str:
    return """# Design Contract
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## Scope
One bounded change.
<!-- ai-delivery:behavior-contract:behavior -->
## Behavior
| ID | Given | When | Then |
|---|---|---|---|
| B-001 | input | event | result |
<!-- ai-delivery:behavior-contract:acceptance -->
## Acceptance
| ID | Outcome | Evidence |
|---|---|---|
| AC-001 | result is observable | focused test |
<!-- ai-delivery:behavior-contract:traceability -->
## Traceability
| Behavior | Requirement | UI | Acceptance |
|---|---|---|---|
| B-001 | REQ-001 | not_applicable | AC-001 |
<!-- ai-delivery:behavior-contract:end -->
<!-- ai-delivery:user-decisions -->
## User decisions
not_applicable
"""


def entry(status: str, *, ui="none", user_decision=False) -> dict:
    return {
        "status": status,
        "ui_bearing": ui != "none",
        "ui_truth_mode": ui,
        "state_flow_required": False,
        "user_decision_required": user_decision,
        "design_review": {
            "review_mode": "none",
            "reviewed_design_sha256": None,
            "reviewed_at": None,
            "reviewed_by": None,
        },
        "notes": None,
    }


def make_ready(req: Path, subreq_id: str = "SR-001") -> dict:
    sub = req / "sub-requirements" / subreq_id
    sub.mkdir(parents=True, exist_ok=True)
    design = sub / "design.md"
    design.write_text(design_text(), encoding="utf-8")
    value = entry("design_ready")
    value["design_review"] = {
        "review_mode": "self",
        "reviewed_design_sha256": hashlib.sha256(design.read_bytes()).hexdigest(),
        "reviewed_at": "2026-09-16T12:00:00Z",
        "reviewed_by": "agent",
    }
    return value


def reconcile(req: Path, values: dict, *, checkpoint=None, schema="2.0") -> dict:
    path = req / "status.json"
    path.write_text(
        json.dumps(
            {
                "_schema": schema,
                "current_checkpoint": checkpoint,
                "sub_requirements": values,
            }
        ),
        encoding="utf-8",
    )
    return mod.reconcile(path, req, validator_script=req / "missing-validator.py")


# Legacy terminal histories remain readable and closable without invented design evidence.
fixture_root = root / "tests/ai-delivery-skills/fixtures/reconcile-delivery"
for name, mode, action in (
    ("all-merged", "closing", "archive"),
    ("merged-pending-archive", "closing", "archive"),
    ("all-archived", "completed", "none"),
):
    status = fixture_root / name / "status.json"
    result = mod.reconcile(status, status.parent)
    assert result["runtime_mode"] == mode, result
    assert result["next_action"] == action, result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    result = mod.reconcile(req / "missing.json", req)
    assert result["runtime_mode"] == "bootstrap", result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    pending_ui = entry("split_ready", ui="runtime-baseline")
    result = reconcile(req, {"SR-001": pending_ui})
    assert result["runtime_mode"] == "confirm_ui", result
    assert result["checkpoint"] == "CP-UI", result
    assert result["next_action"] == "none", result
    result = reconcile(req, {"SR-001": pending_ui}, checkpoint="CP-UI")
    assert result["next_action"] == "ui-truth-mapping", result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    pending = entry("split_ready", user_decision=True)
    result = reconcile(req, {"SR-001": pending})
    assert result["runtime_mode"] == "confirm_solution_design", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "solution-design", result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    ready = make_ready(req, "SR-001")
    waiting = entry("split_ready", user_decision=True)
    result = reconcile(req, {"SR-001": ready, "SR-002": waiting})
    assert result["runtime_mode"] == "resume", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "implement", result
    assert result["next_subreq"] == "SR-001", result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    ready = make_ready(req, "SR-001")
    status_path = req / "status.json"
    reconcile(req, {"SR-001": ready}, checkpoint="CP-001")
    result = mod.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["next_action"] == "implement", result
    assert result["checkpoint"] is None, result

    design = req / "sub-requirements/SR-001/design.md"
    design.write_text(design.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    result = mod.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["next_action"] == "solution-design", result
    assert result["checkpoint"] is None, result

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    legacy = {
        "status": "spec_ready",
        "ui_bearing": False,
        "ui_truth_mode": "none",
        "design_mode": "full",
        "design_approved": True,
    }
    result = reconcile(req, {"SR-001": legacy}, schema="1.1")
    assert result["runtime_mode"] == "blocker_recovery", result
    assert any("migration to schema 2.0" in item for item in result["errors"]), result

# Dependency graph is authoritative; per-slice dependency.json is legacy fallback.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    (req / "sub-requirements/SR-B").mkdir(parents=True)
    (req / "dependency-graph.json").write_text(
        json.dumps({"nodes": {"SR-A": {"depends_on": []}, "SR-B": {"depends_on": ["SR-A"]}}}),
        encoding="utf-8",
    )
    (req / "sub-requirements/SR-B/dependency.json").write_text(
        json.dumps({"depends_on": ["SR-MISSING"]}), encoding="utf-8"
    )
    deps, warnings = mod.load_dependency_graph(req)
    assert deps["SR-B"] == ["SR-A"], deps
    assert not any("legacy" in item for item in warnings), warnings

print("PASS: reconcile-delivery unified route")
PY
