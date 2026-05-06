#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

SKILL_ROOT="$ROOT/.agents/skills"

fail() {
  print -u2 -- "[ui-composition-guardrails-test] $1"
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

REQ_SKILL="$SKILL_ROOT/requirement-breakdown/SKILL.md"
REQ_TEMPLATE="$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
UI_SKILL="$SKILL_ROOT/ui-truth-mapping/SKILL.md"
UI_TEMPLATE="$SKILL_ROOT/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml"
SEC_TEMPLATE="$SKILL_ROOT/ui-truth-mapping/templates/section-map-template.json"

require_file "$REQ_SKILL"
require_file "$REQ_TEMPLATE"
require_file "$UI_SKILL"
require_file "$UI_TEMPLATE"
require_file "$SEC_TEMPLATE"

# Scenario 1: route-level shell and child composition must preserve truth.
require_contains "$REQ_SKILL" 'source_ref'
require_contains "$REQ_TEMPLATE" 'source_ref'
require_contains "$UI_SKILL" 'requirement-slice'
require_contains "$UI_SKILL" 'section-map.json'
require_contains "$UI_SKILL" 'Do not invent visual truth'

# Scenario 2: component tree must not be empty for visible blocks.
require_contains "$UI_SKILL" 'children: []'
require_contains "$UI_SKILL" 'Do not accept `children: []`'
require_contains "$UI_SKILL" 'Do not ship empty `font`'
require_contains "$UI_SKILL" 'Do not ship empty `icon`'

print -- "PASS: composition guardrails are documented and validated across breakdown and mapping."
