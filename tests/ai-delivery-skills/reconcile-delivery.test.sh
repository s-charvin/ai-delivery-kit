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

require_next_skill() {
  local status_file=$1
  local expected_skill=$2
  local output

  output=$(python3 "$RECONCILE" "$status_file" --req-root "$(dirname "$status_file")")
  echo "$output" | grep -q "NEXT_SKILL=$expected_skill" \
    || fail "Expected NEXT_SKILL=$expected_skill for $status_file, got:\n$output"
}

[[ -f "$RECONCILE" ]] || fail "Missing reconcile script: $RECONCILE"
[[ -d "$FIXTURE_ROOT" ]] || fail "Missing fixtures: $FIXTURE_ROOT"

require_runtime_mode "$FIXTURE_ROOT/bootstrap-missing/status.json" "bootstrap"
require_runtime_mode "$FIXTURE_ROOT/all-merged/status.json" "completed"
require_next_skill "$FIXTURE_ROOT/split-ready-ui/status.json" "ui-truth-mapping"
require_next_skill "$FIXTURE_ROOT/blocked-design/status.json" "blocker-recovery"

print -- 'PASS: reconcile-delivery fixtures behave as expected.'
