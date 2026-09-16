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
spec = importlib.util.spec_from_file_location("human_gate_reconcile", script)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def contract(*, decision=False) -> str:
    decision_row = "| D-001 | Choose retry behavior | automatic or manual | unresolved |" if decision else "not_applicable"
    return f"""# Design Contract
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## Scope
One bounded behavior.
<!-- ai-delivery:behavior-contract:behavior -->
## Behavior
| ID | Given | When | Then |
|---|---|---|---|
| B-001 | input | submit | result |
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
{decision_row}
"""


def entry(status, *, ui="none", user_decision=False, state_flow=False):
    return {
        "status": status,
        "ui_bearing": ui != "none",
        "ui_truth_mode": ui,
        "state_flow_required": state_flow,
        "user_decision_required": user_decision,
        "design_review": {
            "review_mode": "none",
            "reviewed_design_sha256": None,
            "reviewed_at": None,
            "reviewed_by": None,
        },
        "blocker_scope": None,
        "resume_target_status": None,
        "notes": None,
    }


def write_design(req, subreq_id, text):
    sub = req / "sub-requirements" / subreq_id
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / "design.md"
    path.write_text(text, encoding="utf-8")
    return path


def bind(value, path, mode):
    value["design_review"] = {
        "review_mode": mode,
        "reviewed_design_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "reviewed_at": "2026-09-16T12:00:00Z",
        "reviewed_by": "user" if mode == "human" else "agent",
    }


def run(req, values, checkpoint=None, schema="2.0", validator=False):
    status = req / "status.json"
    status.write_text(
        json.dumps(
            {
                "_schema": schema,
                "current_checkpoint": checkpoint,
                "sub_requirements": values,
            }
        ),
        encoding="utf-8",
    )
    validator_path = root / "scripts/validate-delivery-status.py" if validator else req / "missing-validator.py"
    return mod.reconcile(status, req, validator_script=validator_path)


# A forged design-ready status without a current design review cannot implement.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    result = run(req, {"SR-001": entry("design_ready")})
    assert result["next_action"] == "none", result
    assert result["runtime_mode"] == "blocker_recovery", result

# A removed CP-001 credential cannot create or block authority. Current design does.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    path = write_design(req, "SR-001", contract())
    ready = entry("design_ready")
    bind(ready, path, "self")
    result = run(req, {"SR-001": ready}, checkpoint="CP-001")
    assert result["next_action"] == "implement", result
    assert result["checkpoint"] is None, result

# A real user decision requires human review; forged self-review does not pass.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    path = write_design(req, "SR-001", contract(decision=True))
    pending = entry("design_ready", user_decision=True)
    bind(pending, path, "self")
    result = run(req, {"SR-001": pending})
    assert result["runtime_mode"] == "confirm_solution_design", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "solution-design", result

# The pending decision remains visible but cannot block an independent ready slice.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    ready_path = write_design(req, "SR-002", contract())
    ready = entry("design_ready")
    bind(ready, ready_path, "self")
    waiting = entry("split_ready", user_decision=True)
    result = run(req, {"SR-001": waiting, "SR-002": ready})
    assert result["runtime_mode"] == "resume", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "implement", result
    assert result["next_subreq"] == "SR-002", result

# Complex state-flow depth is self-reviewable when no user decision exists.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    example = (root / ".agents/skills/ai-delivery-orchestrator/templates/design-state-flow-example.md").read_text(encoding="utf-8")
    path = write_design(req, "SR-001", example)
    ready = entry("design_ready", state_flow=True)
    bind(ready, path, "self")
    result = run(req, {"SR-001": ready})
    assert result["next_action"] == "implement", result
    assert result["checkpoint"] is None, result

# Slice-local failure does not block a ready sibling.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    path = write_design(req, "SR-002", contract())
    ready = entry("design_ready")
    bind(ready, path, "self")
    blocked = entry("blocked_verification_failure")
    blocked["blocker_scope"] = "slice_local"
    blocked["resume_target_status"] = "in_dev"
    result = run(req, {"SR-001": blocked, "SR-002": ready})
    assert result["runtime_mode"] == "resume", result
    assert result["next_action"] == "implement", result
    assert result["blocker_scopes"] == ["SR-001:slice_local"], result

# UI truth remains capability-gated; existing UI does not enter CP-UI.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    result = run(req, {"SR-001": entry("split_ready", ui="figma")})
    assert result["runtime_mode"] == "confirm_ui", result
    assert result["checkpoint"] == "CP-UI", result
    assert result["next_action"] == "none", result
    result = run(req, {"SR-001": entry("split_ready", ui="existing")})
    assert result["next_action"] == "solution-design", result
    assert result["checkpoint"] is None, result

# Active legacy schemas cannot use the removed route as a compatibility branch.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    legacy = {
        "status": "tasks_ready",
        "ui_bearing": False,
        "ui_truth_mode": "none",
        "design_mode": "full",
        "design_approved": True,
    }
    result = run(req, {"SR-001": legacy}, schema="1.1")
    assert result["runtime_mode"] == "blocker_recovery", result
    assert any("migration to schema 2.0" in item for item in result["errors"]), result

# UI acceptance cannot be forged by advancing only the status string.
with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    path = write_design(req, "SR-001", contract())
    forged = entry("visual_acceptance_passed", ui="figma")
    bind(forged, path, "self")
    result = run(req, {"SR-001": forged}, validator=True)
    assert result["runtime_mode"] == "blocker_recovery", result
    assert any("visual-acceptance" in item for item in result["errors"]), result

print("PASS: human gate pressure scenarios")
PY
