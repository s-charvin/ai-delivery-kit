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
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md \
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
  .agents/skills/ui-truth-mapping/references/framework-adapters/flutter/golden-preview-test.dart.example
do
  require_contains "$ROOT/$rel" "user's current conversation language"
done

require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'status-template.json'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'human-readable descriptive values'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'solution-design'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'ui_truth_mode'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'user_decision_required'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-4-sdd-bridge.md" 'visual-acceptance-template.json'
require_contains "$ROOT/.agents/skills/ui-truth-mapping/SKILL.md" 'ui-truth-index-template.json'
require_contains "$ROOT/.agents/skills/ui-truth-mapping/SKILL.md" 'confirmation.note'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/visual-acceptance-template.json" "user's current conversation language"
require_contains "$ROOT/.agents/skills/ui-truth-mapping/templates/ui-truth-index-template.json" "user's current conversation language"
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" 'Scenario ID'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" 'ui-truth-index.json'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" 'Solution Design'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" 'UI Scenario References'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" '"artifact_type":"design-contract"'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" '"layout_key":"solution_design"'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" '"canonical_path":"design.md"'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'Mermaid node, edge, and participant labels'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" 'Unexplained English prose or headings'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md" 'Before review, localize every human-readable heading'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md" 'Language boundary'
require_contains "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-state-flow-example.md" 'Language boundary'

unicode_text() {
  python3 -c 'print("".join(chr(int(codepoint, 16)) for codepoint in __import__("sys").argv[1].split()))' "$1"
}

ZH_LANGUAGE_BOUNDARY=$(unicode_text '8BED 8A00 8FB9 754C')
ZH_MERMAID_LABELS=$(unicode_text '004D 0065 0072 006D 0061 0069 0064 0020 8282 70B9 3001 8FDE 7EBF 548C 53C2 4E0E 8005 6807 7B7E')
ZH_ENGLISH_LEAK=$(unicode_text '672A 89E3 91CA 7684 82F1 6587 6B63 6587')
ZH_DESIGN_REVIEW=$(unicode_text '8BC4 5BA1 4E0E 0020 0043 0050 002D 0044 0045 0053 0049 0047 004E')
ZH_STATE_SUMMARY=$(unicode_text '7D27 51D1 72B6 6001 8868')
ZH_USER_DECISION=$(unicode_text '7528 6237 51B3 7B56')
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md" "$ZH_MERMAID_LABELS"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md" "$ZH_ENGLISH_LEAK"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md" "$ZH_DESIGN_REVIEW"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/templates/design-template.md" "$ZH_LANGUAGE_BOUNDARY"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/templates/design-template.md" "$ZH_STATE_SUMMARY"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/templates/design-template.md" "$ZH_USER_DECISION"
require_contains "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/templates/design-state-flow-example.md" "$ZH_LANGUAGE_BOUNDARY"

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
  .agents-zh/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md \
  .agents-zh/skills/requirement-breakdown/templates/requirement-slice-template-zh.md
do
  require_contains "$ROOT/$rel" 'ai-delivery-template-language'
done

echo "PASS: human-readable templates and direct use sites enforce conversation-language output."
