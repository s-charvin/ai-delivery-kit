#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
RECONCILE="$ROOT/.agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py"
FIXTURE_ROOT="$SCRIPT_DIR/fixtures/reconcile-delivery"

fail() {
  print -u2 -- "[reconcile-delivery.test] $1"
  exit 1
}

require_runtime_mode() {
  local status_file=$1
  local expected_mode=$2
  local output

  # reconcile may exit non-zero when a fixture legitimately carries GATE errors
  # (e.g. a merged ui-bearing subreq missing visual-acceptance artifacts). Those
  # errors never affect RUNTIME_MODE derivation, which is what we assert here, so
  # tolerate the non-zero exit via `|| true`.
  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")") || true
  echo "$output" | grep -q "RUNTIME_MODE=$expected_mode" \
    || fail "Expected RUNTIME_MODE=$expected_mode for $status_file, got:\n$output"
}

require_next_action() {
  local status_file=$1
  local expected_action=$2
  local output

  # reconcile may exit non-zero when a fixture legitimately carries GATE errors
  # (e.g. a merged ui-bearing subreq missing visual-acceptance artifacts). Those
  # errors never affect RUNTIME_MODE derivation, which is what we assert here, so
  # tolerate the non-zero exit via `|| true`.
  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")") || true
  echo "$output" | grep -q "NEXT_ACTION=$expected_action" \
    || fail "Expected NEXT_ACTION=$expected_action for $status_file, got:\n$output"
}

require_output_contains() {
  local status_file=$1
  local expected_line=$2
  local output

  # reconcile may exit non-zero when a fixture legitimately carries GATE errors
  # (e.g. a merged ui-bearing subreq missing visual-acceptance artifacts). Those
  # errors never affect RUNTIME_MODE derivation, which is what we assert here, so
  # tolerate the non-zero exit via `|| true`.
  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")") || true
  echo "$output" | grep -q "$expected_line" \
    || fail "Expected output to contain '$expected_line' for $status_file, got:\n$output"
}

[[ -f "$RECONCILE" ]] || fail "Missing reconcile script: $RECONCILE"
[[ -d "$FIXTURE_ROOT" ]] || fail "Missing fixtures: $FIXTURE_ROOT"

require_runtime_mode "$FIXTURE_ROOT/bootstrap-missing/status.json" "bootstrap"

# all-merged: every subreq is `merged` but none archived yet -> the requirement
# is "pending archive": runtime_mode resolves to closing (not completed).
require_runtime_mode "$FIXTURE_ROOT/all-merged/status.json" "closing"
require_output_contains "$FIXTURE_ROOT/all-merged/status.json" "CHECKPOINT=CP-ARCHIVE"
require_next_action "$FIXTURE_ROOT/all-merged/status.json" "archive"

# merged-pending-archive: same merged-but-not-archived shape, explicit fixture.
require_runtime_mode "$FIXTURE_ROOT/merged-pending-archive/status.json" "closing"
require_output_contains "$FIXTURE_ROOT/merged-pending-archive/status.json" "CHECKPOINT=CP-ARCHIVE"
require_next_action "$FIXTURE_ROOT/merged-pending-archive/status.json" "archive"

# all-archived: every subreq is `archived` -> terminal completion.
require_runtime_mode "$FIXTURE_ROOT/all-archived/status.json" "completed"
require_next_action "$FIXTURE_ROOT/all-archived/status.json" "none"

require_runtime_mode "$FIXTURE_ROOT/split-ready-ui/status.json" "confirm_ui"
require_output_contains "$FIXTURE_ROOT/split-ready-ui/status.json" "CHECKPOINT=CP-UI"
require_next_action "$FIXTURE_ROOT/split-ready-ui/status.json" "none"

require_runtime_mode "$FIXTURE_ROOT/cp-ui-confirmed/status.json" "resume"
require_output_contains "$FIXTURE_ROOT/cp-ui-confirmed/status.json" "CHECKPOINT=CP-UI"
require_next_action "$FIXTURE_ROOT/cp-ui-confirmed/status.json" "ui-truth-mapping"

# Capability-gated UI truth modes: a runtime baseline still requires CP-UI,
# while an existing frozen surface goes directly to solution design.
require_runtime_mode "$FIXTURE_ROOT/runtime-baseline-ui/status.json" "confirm_ui"
require_output_contains "$FIXTURE_ROOT/runtime-baseline-ui/status.json" "CHECKPOINT=CP-UI"
require_next_action "$FIXTURE_ROOT/existing-ui/status.json" "solution-design"

# Design mode none skips solution-design entirely; light emits the lightweight
# solution-design action without introducing a CP-DESIGN human gate.
require_next_action "$FIXTURE_ROOT/no-ui-design-none/status.json" "spec"
require_next_action "$FIXTURE_ROOT/no-ui-design-light/status.json" "solution-design"
light_output=$(python3 "$RECONCILE" "$FIXTURE_ROOT/no-ui-design-light/status.json" --req-root "$FIXTURE_ROOT/no-ui-design-light" 2>&1) || true
if echo "$light_output" | grep -Eq "CHECKPOINT=CP-DESIGN|RUNTIME_MODE=confirm_solution_design"; then
  fail "design_mode=light unexpectedly introduced CP-DESIGN: $light_output"
fi

# Legacy bypass fields and participation profiles are rejected instead of
# silently selecting a compatibility route.
legacy_output=$(python3 "$RECONCILE" "$FIXTURE_ROOT/legacy-ui-fields-rejected/status.json" --req-root "$FIXTURE_ROOT/legacy-ui-fields-rejected" 2>&1) || true
echo "$legacy_output" | grep -Eq "ui_contract_exempt|no_design_client|unsupported|legacy" \
  || fail "legacy bypass fixture was not rejected: $legacy_output"
legacy_output=$(python3 "$RECONCILE" "$FIXTURE_ROOT/legacy-participation-rejected/status.json" --req-root "$FIXTURE_ROOT/legacy-participation-rejected" 2>&1) || true
echo "$legacy_output" | grep -Eq "no_design_client|unsupported|legacy" \
  || fail "legacy participation fixture was not rejected: $legacy_output"

require_runtime_mode "$FIXTURE_ROOT/cp-design-pending/status.json" "confirm_solution_design"
require_output_contains "$FIXTURE_ROOT/cp-design-pending/status.json" "CHECKPOINT=CP-DESIGN"
require_next_action "$FIXTURE_ROOT/cp-design-pending/status.json" "solution-design"

require_runtime_mode "$FIXTURE_ROOT/confirm-to-dev/status.json" "confirm_to_dev"
require_next_action "$FIXTURE_ROOT/confirm-to-dev/status.json" "implement"

require_runtime_mode "$FIXTURE_ROOT/tasks-ready-ui/status.json" "confirm_to_dev"
require_output_contains "$FIXTURE_ROOT/tasks-ready-ui/status.json" "CHECKPOINT=CP-001"

require_runtime_mode "$FIXTURE_ROOT/blocked-design/status.json" "blocker_recovery"
require_next_action "$FIXTURE_ROOT/blocked-design/status.json" "none"
require_output_contains "$FIXTURE_ROOT/blocked-design/status.json" "BLOCKER_SCOPES=add-friend:slice_local"

# Graph-only vs legacy dependency loading (unit-level via load_dependency_graph).
python3 - "$RECONCILE" <<'PY' || fail "dependency-graph load assertions failed"
import importlib.util, json, sys, tempfile
from pathlib import Path

script = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("reconcile_delivery", script)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
# layout.py lives alongside reconcile-delivery.py
sys.path.insert(0, str(script.parent))
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "sub-requirements" / "SR-B").mkdir(parents=True)
    (root / "dependency-graph.json").write_text(
        json.dumps({"nodes": {"SR-A": {"depends_on": []}, "SR-B": {"depends_on": ["SR-A"]}}})
    )
    (root / "sub-requirements" / "SR-B" / "dependency.json").write_text(
        json.dumps({"depends_on": ["SR-MISSING"]})
    )
    deps, warns = mod.load_dependency_graph(root)
    assert deps.get("SR-B") == ["SR-A"], deps
    assert not any("legacy" in w for w in warns), warns

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "sub-requirements" / "SR-B").mkdir(parents=True)
    (root / "sub-requirements" / "SR-B" / "dependency.json").write_text(
        json.dumps({"depends_on": ["SR-A"]})
    )
    deps, warns = mod.load_dependency_graph(root)
    assert deps.get("SR-B") == ["SR-A"], deps
    assert any("[WARN] legacy dependency.json" in w for w in warns), warns

# Mode rejection is intrinsic to reconcile, even when a caller does not seed a
# validator script. Blocked slices still expose the blocker, but cannot hide an
# invalid capability mode or a removed bypass field.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "sub-requirements" / "SR-001").mkdir(parents=True)
    status = {
        "sub_requirements": {
            "SR-001": {
                "status": "blocked_dependency",
                "ui_bearing": False,
                "ui_truth_mode": "invalid",
                "design_mode": "none",
                "design_approved": False,
                "ui_contract_exempt": True,
            }
        }
    }
    status_path = root / "status.json"
    status_path.write_text(json.dumps(status))
    result = mod.reconcile(status_path, root, validator_script=root / "missing-validator.py")
    joined = "\n".join(result["errors"])
    assert "ui_truth_mode" in joined and "ui_contract_exempt" in joined, joined

    binding = root / ".ai-delivery" / "meta"
    binding.mkdir(parents=True)
    (binding / "project-binding.json").write_text(
        json.dumps({"ui_contract_exempt": True})
    )
    result = mod.reconcile(status_path, root, validator_script=root / "missing-validator.py")
    assert any("project-binding" in error for error in result["errors"]), result

# A full design regression remains CP-DESIGN-gated at every later runnable
# status. CP-001, finish, and archive must not outrank the missing approval.
for late_status in ("tasks_ready", "in_dev", "visual_acceptance_passed", "merged"):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sub-requirements" / "SR-001").mkdir(parents=True)
        figma_status = late_status == "visual_acceptance_passed"
        status_path = root / "status.json"
        status_path.write_text(
            json.dumps(
                {
                    "_schema": "1.1",
                    "sub_requirements": {
                        "SR-001": {
                            "status": late_status,
                            "ui_bearing": figma_status,
                            "ui_truth_mode": "figma" if figma_status else "none",
                            "design_mode": "full",
                            "design_approved": False,
                            "state_flow_required": False,
                            "design_review": {
                                "review_mode": "none",
                                "reviewed_design_sha256": None,
                                "reviewed_at": None,
                                "reviewed_by": None,
                            },
                        }
                    }
                }
            )
        )
        result = mod.reconcile(
            status_path, root, validator_script=root / "missing-validator.py"
        )
        assert result["runtime_mode"] == "confirm_solution_design", result
        assert result["checkpoint"] == "CP-DESIGN", result
        assert result["next_action"] == "solution-design", result

# A stale CP-001 cannot release an otherwise ready slice while a sibling full
# design gate is unresolved.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    first = root / "sub-requirements" / "SR-001"
    second = root / "sub-requirements" / "SR-002"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "design.md").write_text("# Solution Design\n")
    status_path = root / "status.json"
    status_path.write_text(
        json.dumps(
                {
                    "_schema": "1.1",
                    "current_checkpoint": "CP-001",
                "sub_requirements": {
                    "SR-001": {
                        "status": "tasks_ready",
                        "ui_bearing": False,
                        "ui_truth_mode": "none",
                        "design_mode": "full",
                        "design_approved": False,
                        "state_flow_required": False,
                        "design_review": {
                            "review_mode": "none",
                            "reviewed_design_sha256": None,
                            "reviewed_at": None,
                            "reviewed_by": None,
                        },
                    },
                    "SR-002": {
                        "status": "tasks_ready",
                        "ui_bearing": False,
                        "ui_truth_mode": "none",
                        "design_mode": "full",
                        "design_approved": False,
                        "state_flow_required": False,
                        "design_review": {
                            "review_mode": "none",
                            "reviewed_design_sha256": None,
                            "reviewed_at": None,
                            "reviewed_by": None,
                        },
                    },
                },
            }
        )
    )
    result = mod.reconcile(
        status_path, root, validator_script=root / "missing-validator.py"
    )
    assert result["runtime_mode"] == "confirm_solution_design", result
    assert result["checkpoint"] == "CP-DESIGN", result
    assert result["next_action"] == "solution-design", result
    assert not any("->implement" in item for item in result["runnable"]), result

# A terminal status with a missing solution-design artifact is invalid and
# cannot be reported as completed merely because every status string says
# `archived`.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "sub-requirements" / "SR-001").mkdir(parents=True)
    status_path = root / "status.json"
    status_path.write_text(
        json.dumps(
            {
                "sub_requirements": {
                    "SR-001": {
                        "status": "archived",
                        "ui_bearing": False,
                        "ui_truth_mode": "none",
                        "design_mode": "full",
                        "design_approved": False,
                    }
                }
            }
        )
    )
    result = mod.reconcile(
        status_path, root, validator_script=root / "missing-validator.py"
    )
    assert result["runtime_mode"] == "blocker_recovery", result
    assert result["next_action"] == "none", result

print("dependency-graph load OK")
PY

echo 'PASS: reconcile-delivery fixtures behave as expected.'
