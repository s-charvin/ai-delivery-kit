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

REQ_SKILL="$SKILL_ROOT/requirement-breakdown/SKILL.md"
REQ_TEMPLATE="$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
UI_SKILL="$SKILL_ROOT/ui-truth-mapping/SKILL.md"
UI_EXAMPLE="$SKILL_ROOT/ui-truth-mapping/templates/flutter-golden-preview-test.dart.example"
UI_INDEX_TEMPLATE="$SKILL_ROOT/ui-truth-mapping/templates/ui-truth-index-template.json"

require_file "$REQ_SKILL"
require_file "$REQ_TEMPLATE"
require_file "$UI_SKILL"
require_file "$UI_EXAMPLE"
require_file "$UI_INDEX_TEMPLATE"

require_contains "$REQ_SKILL" 'source_ref'
require_contains "$REQ_TEMPLATE" 'source_ref'

require_contains "$UI_SKILL" 'requirement-slice'
require_contains "$UI_SKILL" 'ui-contract.html'
require_contains "$UI_SKILL" 'Incremental patch'
require_contains "$UI_SKILL" 'implementation lookup'
require_contains "$UI_SKILL" 'Do not invent visual truth'
require_contains "$UI_SKILL" 'fill detection rule'
require_contains "$UI_SKILL" 'Paint compositing / mask scan'
require_contains "$UI_SKILL" 'not a second visible wash'
require_contains "$UI_SKILL" 'ui-truth-index.json'
require_contains "$UI_SKILL" '--update-goldens'
require_contains "$UI_SKILL" 'CP-UI'
require_contains "$UI_SKILL" 'same slice worktree'
require_contains "$UI_SKILL" 'SHA-256'
require_contains "$UI_SKILL" 'Runtime Coverage Plan'
require_contains "$UI_SKILL" '`state`'
require_contains "$UI_SKILL" '`layout`'
require_contains "$UI_SKILL" '`content`'
require_contains "$UI_SKILL" '`interaction`'
require_contains "$UI_SKILL" '`motion`'
require_contains "$UI_SKILL" '`assets`'
require_contains "$UI_SKILL" '`theme`'
require_contains "$UI_SKILL" '`accessibility`'
require_contains "$UI_SKILL" '`platform`'
require_contains "$UI_SKILL" '`performance`'
require_contains "$UI_SKILL" 'figma` / `requirement` / `project` / `user-decision'
require_contains "$UI_SKILL" 'There is no HTML validator and no v1 compatibility path'
require_contains "$UI_INDEX_TEMPLATE" '"schema_version": 2'
require_contains "$UI_INDEX_TEMPLATE" '"profiles"'
require_contains "$UI_INDEX_TEMPLATE" '"scenarios"'
require_contains "$UI_INDEX_TEMPLATE" '"coverage"'
require_contains "$UI_INDEX_TEMPLATE" '"reviewed_preview_sha256"'

require_contains "$UI_EXAMPLE" 'matchesGoldenFile'
require_contains "$UI_EXAMPLE" 'RepaintBoundary'
require_contains "$UI_EXAMPLE" '--update-goldens'
require_contains "$UI_EXAMPLE" 'PNG canvas'
require_contains "$UI_EXAMPLE" 'state-switcher'
require_contains "$UI_EXAMPLE" 'ValueKey'
require_contains "$UI_EXAMPLE" 'pumpAndSettle()'
require_contains "$UI_EXAMPLE" 'explicit, named keyframe duration'

echo "PASS: composition guardrails are documented and validated across breakdown and mapping."
