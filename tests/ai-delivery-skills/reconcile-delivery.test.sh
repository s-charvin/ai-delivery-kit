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

  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")")
  echo "$output" | grep -q "RUNTIME_MODE=$expected_mode" \
    || fail "Expected RUNTIME_MODE=$expected_mode for $status_file, got:\n$output"
}

require_next_action() {
  local status_file=$1
  local expected_action=$2
  local output

  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")")
  echo "$output" | grep -q "NEXT_ACTION=$expected_action" \
    || fail "Expected NEXT_ACTION=$expected_action for $status_file, got:\n$output"
}

require_output_contains() {
  local status_file=$1
  local expected_line=$2
  local output

  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")")
  echo "$output" | grep -q "$expected_line" \
    || fail "Expected output to contain '$expected_line' for $status_file, got:\n$output"
}

[[ -f "$RECONCILE" ]] || fail "Missing reconcile script: $RECONCILE"
[[ -d "$FIXTURE_ROOT" ]] || fail "Missing fixtures: $FIXTURE_ROOT"

require_runtime_mode "$FIXTURE_ROOT/bootstrap-missing/status.json" "bootstrap"
require_runtime_mode "$FIXTURE_ROOT/all-merged/status.json" "completed"
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

print -- 'PASS: reconcile-delivery fixtures behave as expected.'
