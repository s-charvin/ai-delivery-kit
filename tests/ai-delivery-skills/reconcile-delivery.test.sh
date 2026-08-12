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

require_next_action "$FIXTURE_ROOT/split-ready-ui/status.json" "ui-truth-mapping"

require_runtime_mode "$FIXTURE_ROOT/cp-design-pending/status.json" "confirm_design"
require_output_contains "$FIXTURE_ROOT/cp-design-pending/status.json" "CHECKPOINT=CP-DESIGN"
require_next_action "$FIXTURE_ROOT/cp-design-pending/status.json" "design"

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

print("dependency-graph load OK")
PY

print -- 'PASS: reconcile-delivery fixtures behave as expected.'
