#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

fail() {
  echo "[artifact-language-policy.test] $1" >&2
  exit 1
}

require_contains() {
  local file=$1
  local needle=$2
  [[ -f "$file" ]] || fail "missing file: ${file#$ROOT/}"
  grep -Fq -- "$needle" "$file" \
    || fail "missing '$needle' in ${file#$ROOT/}"
}

for rel in \
  .agents/skills/ai-delivery-orchestrator/templates/delivery-report-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/design-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/todo-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/verification-template.md \
  .agents/skills/requirement-breakdown/templates/requirement-slice-template.md
do
  require_contains "$ROOT/$rel" 'ai-delivery-template-language'
  require_contains "$ROOT/$rel" "user's current conversation language"
done

for rel in \
  AGENTS.md \
  .agents/skills/ai-delivery-orchestrator/SKILL.md \
  .agents/skills/requirement-breakdown/SKILL.md \
  .agents/skills/ui-truth-mapping/SKILL.md \
  .agents/skills/ai-delivery-orchestrator/references/stage-breakdown.md \
  .agents/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md \
  .agents/skills/ai-delivery-orchestrator/references/stage-implementation.md \
  .agents/skills/ui-truth-mapping/templates/flutter-golden-preview-test.dart.example
do
  require_contains "$ROOT/$rel" "user's current conversation language"
done

require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'status-template.json'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'human-readable descriptive values'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-4-sdd-bridge.md" 'visual-acceptance-template.json'
require_contains "$ROOT/.agents/skills/ui-truth-mapping/SKILL.md" 'ui-truth-index-template.json'
require_contains "$ROOT/.agents/skills/ui-truth-mapping/SKILL.md" 'confirmation.note'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/visual-acceptance-template.json" "user's current conversation language"
require_contains "$ROOT/.agents/skills/ui-truth-mapping/templates/ui-truth-index-template.json" "user's current conversation language"

for marker in \
  ai-delivery-verification:review-rounds \
  ai-delivery-verification:commands-results \
  ai-delivery-verification:sign-off
do
  require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/verification-template.md" "$marker"
  require_contains "$ROOT/scripts/validate-delivery-status.py" "$marker"
done
if grep -Fq 'required_sections' "$ROOT/scripts/validate-delivery-status.py"; then
  fail "verification validation must not depend on localized section headings"
fi

for rel in \
  .agents-zh/skills/ai-delivery-orchestrator/templates/delivery-report-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/design-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/todo-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/verification-template.md \
  .agents-zh/skills/requirement-breakdown/templates/requirement-slice-template-zh.md
do
  require_contains "$ROOT/$rel" 'ai-delivery-template-language'
done

echo "PASS: human-readable templates and direct use sites enforce conversation-language output."
