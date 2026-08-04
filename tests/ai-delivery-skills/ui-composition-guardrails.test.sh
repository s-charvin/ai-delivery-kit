#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

SKILL_ROOT="$ROOT/.agents/skills"

fail() {
  echo "[ui-composition-guardrails-test] $1" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_contains() {
  local file=$1
  local needle=$2

  if ! grep -Fq -- "$needle" "$file"; then
    fail "Expected '$needle' in $file"
  fi
}

require_not_contains() {
  local file=$1
  local needle=$2

  if grep -Fq -- "$needle" "$file"; then
    fail "Did not expect '$needle' in $file"
  fi
}

REQ_SKILL="$SKILL_ROOT/requirement-breakdown/SKILL.md"
REQ_TEMPLATE="$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
UI_SKILL="$SKILL_ROOT/ui-truth-mapping/SKILL.md"
UI_TEMPLATE="$SKILL_ROOT/ui-truth-mapping/templates/ui-contract-template.html"

require_file "$REQ_SKILL"
require_file "$REQ_TEMPLATE"
require_file "$UI_SKILL"
require_file "$UI_TEMPLATE"

# Scenario 1: requirement-breakdown truth linkage must be preserved.
require_contains "$REQ_SKILL" 'source_ref'
require_contains "$REQ_TEMPLATE" 'source_ref'

# Scenario 2: ui-truth-mapping speaks HTML contract v2 (single-file truth).
require_contains "$UI_SKILL" 'requirement-slice'
require_contains "$UI_SKILL" 'ui-contract.html'
require_contains "$UI_SKILL" 'ui-contract-template.html'
require_contains "$UI_SKILL" 'incremental patch'
require_contains "$UI_SKILL" 'implementation lookup'
require_contains "$UI_SKILL" 'Do not invent visual truth'

# Scenario 3: the HTML contract template carries the required schema v2
# anchors — metadata script, unit root, and the collapsible review panel.
require_contains "$UI_TEMPLATE" 'id="ui-contract-meta"'
require_contains "$UI_TEMPLATE" '<main data-ui-contract'
require_contains "$UI_TEMPLATE" 'data-ui-unit-id'
require_contains "$UI_TEMPLATE" 'data-ui-review-panel'

echo "PASS: composition guardrails are documented and validated across breakdown and mapping."
