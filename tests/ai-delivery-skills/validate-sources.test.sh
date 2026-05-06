#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

MANAGED_ASSET_ROOT=""
SKILL_ROOT=""

fail() {
  print -u2 -- "[validate-sources-test] $1"
  exit 1
}

resolve_project_asset_path() {
  local relative_path=$1
  local candidate="$MANAGED_ASSET_ROOT/$relative_path"

  if [[ -f "$candidate" ]]; then
    print -- "$candidate"
    return 0
  fi

  fail "Missing managed asset: $relative_path"
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_not_contains() {
  local file=$1
  local needle=$2
  if grep -Fq -- "$needle" "$file"; then
    fail "Unexpected '$needle' in $file"
  fi
}

if [[ -f "$ROOT/managedassets.go" ]]; then
  MANAGED_ASSET_ROOT="$ROOT"
else
  MANAGED_ASSET_ROOT="$ROOT/.ai-delivery"
fi

SKILL_ROOT="$ROOT/.agents/skills"

VALIDATE_SCRIPT=$(resolve_project_asset_path "scripts/validate-project-ai-delivery-skills.sh")

zsh "$VALIDATE_SCRIPT"

[[ -d "$SKILL_ROOT" ]] || fail "Missing source skill root: $SKILL_ROOT"

require_file "$SKILL_ROOT/requirement-breakdown/SKILL.md"
require_file "$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
require_file "$SKILL_ROOT/ui-truth-mapping/SKILL.md"
require_file "$SKILL_ROOT/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml"
require_file "$SKILL_ROOT/ui-truth-mapping/templates/section-map-template.json"
require_file "$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md"
require_file "$SKILL_ROOT/ai-delivery-orchestrator/templates/status-template.json"

require_not_contains "$SKILL_ROOT/requirement-breakdown/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-truth-mapping/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md" '../common/'
