#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

fail() {
  print -u2 -- "[validate-sources-test] $1"
  exit 1
}

resolve_project_asset_path() {
  local relative_path=$1
  local candidate

  for candidate in "$ROOT/$relative_path" "$ROOT/.ai-delivery/$relative_path"; do
    if [[ -f "$candidate" ]]; then
      print -- "$candidate"
      return 0
    fi
  done

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

VALIDATE_SCRIPT=$(resolve_project_asset_path "scripts/validate-project-ai-delivery-skills.sh")

if [[ -d "$ROOT/.agents/skills" ]]; then
  SKILL_ROOT="$ROOT/.agents/skills"
else
  SKILL_ROOT="$ROOT/.codex/skills/ai-delivery"
fi

zsh "$VALIDATE_SCRIPT"

require_file "$SKILL_ROOT/requirement-breakdown/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/requirement-breakdown/references/blocker-catalog.md"
require_file "$SKILL_ROOT/requirement-breakdown/references/logging-checklist.md"
require_file "$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/blocker-catalog.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/references/logging-checklist.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/templates/figma-mapping-template.md"
require_file "$SKILL_ROOT/ui-interaction-design/references/dual-truth-rules.md"
require_file "$SKILL_ROOT/ui-interaction-design/references/blocker-catalog.md"
require_file "$SKILL_ROOT/ui-interaction-design/references/logging-checklist.md"
require_file "$SKILL_ROOT/ui-interaction-design/templates/interaction-design-template.md"

require_not_contains "$SKILL_ROOT/requirement-breakdown/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-requirement-mapping/SKILL.md" '../common/'
require_not_contains "$SKILL_ROOT/ui-interaction-design/SKILL.md" '../common/'
