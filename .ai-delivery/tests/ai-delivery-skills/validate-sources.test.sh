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

if [[ -d "$ROOT/.agents/skills/ai-delivery" ]]; then
  MANAGED_ASSET_ROOT="$ROOT"
  SKILL_ROOT="$ROOT/.agents/skills/ai-delivery"
else
  MANAGED_ASSET_ROOT="$ROOT/.ai-delivery"
  SKILL_ROOT="$ROOT/.agents/skills"
fi

VALIDATE_SCRIPT=$(resolve_project_asset_path "scripts/validate-project-ai-delivery-skills.sh")

zsh "$VALIDATE_SCRIPT"

[[ -d "$SKILL_ROOT" ]] || fail "Missing source skill root: $SKILL_ROOT"
if [[ "$ROOT" == "/Users/charvin/Projects/spec-dev/Codex" ]]; then
  [[ ! -e "$ROOT/.codex/skills" ]] || fail "Source skill root should not remain under .codex/skills"
fi

require_file "$SKILL_ROOT/requirement-breakdown/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/requirement-breakdown/references/blocker-catalog.md"
require_file "$SKILL_ROOT/requirement-breakdown/references/logging-checklist.md"
require_file "$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
require_file "$SKILL_ROOT/api-contract-mapping/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/api-contract-mapping/references/blocker-catalog.md"
require_file "$SKILL_ROOT/api-contract-mapping/references/logging-checklist.md"
require_file "$SKILL_ROOT/api-contract-mapping/templates/api-contract-mapping-template.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/blocker-catalog.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/logging-checklist.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/templates/figma-mapping-template.md"
require_file "$SKILL_ROOT/ui-acceptance-contract/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/ui-acceptance-contract/references/blocker-catalog.md"
require_file "$SKILL_ROOT/ui-acceptance-contract/references/logging-checklist.md"
require_file "$SKILL_ROOT/ui-acceptance-contract/templates/ui-acceptance-contract-template.yaml"
require_file "$SKILL_ROOT/ui-interaction-design/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/ui-interaction-design/references/blocker-catalog.md"
require_file "$SKILL_ROOT/ui-interaction-design/references/logging-checklist.md"
require_file "$SKILL_ROOT/ui-interaction-design/templates/interaction-design-template.md"

require_not_contains "$SKILL_ROOT/requirement-breakdown/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/api-contract-mapping/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-requirement-mapping/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-acceptance-contract/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-interaction-design/SKILL.md" '../common/'
require_file "$SKILL_ROOT/ai-delivery-orchestrator/references/reconcile-rules.md"

zsh "$SCRIPT_DIR/api-nonblocking-policy.test.sh"
