#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
export KIT_ROOT="$ROOT"

python3 - <<'PY'
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

root = Path(os.environ["KIT_ROOT"])
scripts = root / ".agents/skills/ai-delivery-orchestrator/scripts"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load("unified_design_contract", scripts / "design_contract.py")
reconcile = load("unified_reconcile", scripts / "reconcile-delivery.py")


def write_design(path: Path) -> None:
    path.write_text(
        """<!-- ai-delivery-meta: {\"version\":3,\"artifact_type\":\"design-contract\",\"layout_key\":\"solution_design\",\"canonical_path\":\"design.md\"} -->
# Design Contract

<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## Scope
Bounded behavior change with no unresolved product decision.

<!-- ai-delivery:behavior-contract:behavior -->
## Behavior
| ID | Given | When | Then | Boundaries |
|---|---|---|---|---|
| B-001 | valid input | submit | save once | invalid input is rejected |

<!-- ai-delivery:behavior-contract:acceptance -->
## Acceptance
| ID | Verifiable outcome | Evidence |
|---|---|---|
| AC-001 | B-001 is satisfied | focused test command |

<!-- ai-delivery:behavior-contract:traceability -->
## Traceability
| Behavior | Requirement | UI scenario | Acceptance |
|---|---|---|---|
| B-001 | REQ-001 | not_applicable | AC-001 |
<!-- ai-delivery:behavior-contract:end -->

<!-- ai-delivery:user-decisions -->
## User Decisions
None.

## Solution
Reuse the existing module boundary and verification command.
""",
        encoding="utf-8",
    )


def review(path: Path, mode: str) -> dict:
    return {
        "review_mode": mode,
        "reviewed_design_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "reviewed_at": "2026-09-16T12:00:00Z",
        "reviewed_by": "user" if mode == "human" else "agent",
    }


def entry(*, status: str, user_decision_required: bool, review_mode: str = "none", state_flow_required: bool = False) -> dict:
    return {
        "status": status,
        "ui_bearing": False,
        "ui_truth_mode": "none",
        "state_flow_required": state_flow_required,
        "user_decision_required": user_decision_required,
        "design_review": {
            "review_mode": review_mode,
            "reviewed_design_sha256": None,
            "reviewed_at": None,
            "reviewed_by": None,
        },
        "notes": None,
    }


with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    sub = req / "sub-requirements" / "SR-001"
    sub.mkdir(parents=True)
    design = sub / "design.md"
    write_design(design)

    # A self-reviewed design is the only planning artifact required before
    # implementation. There is no CP-001 or spec/plan/tasks intermediate state.
    ready = entry(status="design_ready", user_decision_required=False, review_mode="self")
    ready["design_review"] = review(design, "self")
    status_path = req / "status.json"
    status_path.write_text(
        json.dumps({"_schema": "2.0", "sub_requirements": {"SR-001": ready}}),
        encoding="utf-8",
    )
    result = reconcile.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["runtime_mode"] == "resume", result
    assert result["checkpoint"] is None, result
    assert result["next_action"] == "implement", result
    assert result["next_subreq"] == "SR-001", result

    # A real unresolved user decision introduces CP-DESIGN. The checkpoint is
    # about that decision, not the size of the document or state machine.
    pending = entry(status="split_ready", user_decision_required=True)
    status_path.write_text(
        json.dumps({"_schema": "2.0", "sub_requirements": {"SR-001": pending}}),
        encoding="utf-8",
    )
    result = reconcile.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["runtime_mode"] == "confirm_solution_design", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "solution-design", result

    # The field classifies the current design's authority requirement. It stays
    # true after approval; the valid hash-bound human review closes the pending
    # checkpoint and permits implementation.
    design.write_text(
        design.read_text(encoding="utf-8").replace(
            "None.",
            "| D-001 | Choose the supported behavior | Keep or reject | Keep |",
        ),
        encoding="utf-8",
    )
    approved = entry(status="design_ready", user_decision_required=True)
    approved["design_review"] = review(design, "human")
    status_path.write_text(
        json.dumps({"_schema": "2.0", "sub_requirements": {"SR-001": approved}}),
        encoding="utf-8",
    )
    result = reconcile.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["runtime_mode"] == "resume", result
    assert result["checkpoint"] is None, result
    assert result["next_action"] == "implement", result

    # Complex state-flow documentation may still be self-reviewed when it has
    # no product decision for the user. Complexity and authority are separate.
    complex_self_review = entry(
        status="design_ready",
        user_decision_required=False,
        review_mode="self",
        state_flow_required=True,
    )
    complex_self_review["design_review"] = review(design, "self")
    assert not any(
        "human" in message or "CP-DESIGN" in message
        for message in reconcile.mode_errors(complex_self_review, strict_design=True)
    )

with tempfile.TemporaryDirectory() as td:
    req = Path(td)
    first = req / "sub-requirements" / "SR-001"
    second = req / "sub-requirements" / "SR-002"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    write_design(first / "design.md")
    ready = entry(status="design_ready", user_decision_required=False, review_mode="self")
    ready["design_review"] = review(first / "design.md", "self")
    waiting = entry(status="split_ready", user_decision_required=True)
    status_path = req / "status.json"
    status_path.write_text(
        json.dumps(
            {
                "_schema": "2.0",
                "sub_requirements": {"SR-001": ready, "SR-002": waiting},
            }
        ),
        encoding="utf-8",
    )
    result = reconcile.reconcile(status_path, req, validator_script=req / "missing-validator.py")
    assert result["runtime_mode"] == "resume", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "implement", result
    assert result["next_subreq"] == "SR-001", result
    assert "CP-001" not in json.dumps(result), result

print("PASS: unified design-to-implementation route")
PY

SKILL="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
STAGE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md"
BREAKDOWN="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-breakdown.md"
POLICY="$ROOT/.ai-delivery/meta/workflow-policy.json"

grep -Fq 'design_ready → in_dev' "$SKILL"
grep -Fq 'single canonical `design.md`' "$STAGE"
grep -Fq 'it is not the pending-review state' "$STAGE"
grep -Fq 'It remains `true` for that' "$STAGE"
grep -Fq '"human_checkpoint_condition": "user_decision_required_and_no_valid_human_review"' "$POLICY"

if grep -Fq 'clear the flag' "$BREAKDOWN"; then
  echo "FAIL: user_decision_required must not be cleared after human approval" >&2
  exit 1
fi

if grep -Eq 'spec_ready|plan_ready|tasks_ready|CP-001' "$SKILL" "$STAGE"; then
  echo "FAIL: the unified route still advertises removed spec/plan/tasks or CP-001 gates" >&2
  exit 1
fi

echo "PASS: unified route markers"
