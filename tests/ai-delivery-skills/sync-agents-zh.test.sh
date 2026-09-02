#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
SRC="$ROOT/.agents/skills"
DST="$ROOT/.agents-zh/skills"
SYNC_SCRIPT="$ROOT/scripts/sync-agents-zh-nonlocale.sh"

fail() {
  print -u2 -- "[sync-agents-zh.test] $1"
  exit 1
}

require_identical() {
  local rel=$1
  local from="$SRC/$rel"
  local to="$DST/$rel"
  [[ -f "$from" ]] || fail "Missing source file: $rel"
  [[ -f "$to" ]] || fail "Missing zh mirror file: $rel"
  diff -q "$from" "$to" >/dev/null || fail "Non-localized file drift: $rel"
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_han_content() {
  local file=$1
  python3 -c 'import pathlib, sys; sys.exit(0 if any("\u4e00" <= char <= "\u9fff" for char in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")) else 1)' "$file" \
    || fail "Expected Chinese content: ${file#$ROOT/}"
}

require_no_han_content() {
  local file=$1
  if python3 -c 'import pathlib, sys; sys.exit(0 if any("\u4e00" <= char <= "\u9fff" for char in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")) else 1)' "$file"; then
    fail "Unexpected Chinese content: ${file#$ROOT/}"
  fi
}

# Non-localized assets must be byte-identical
for rel in \
  ai-delivery-orchestrator/agents/openai.yaml \
  ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  ai-delivery-orchestrator/scripts/layout.py \
  requirement-breakdown/agents/openai.yaml \
  ui-truth-mapping/agents/openai.yaml \
  ui-truth-mapping/templates/flutter-golden-preview-test.dart.example \
  ui-truth-mapping/templates/ui-truth-index-template.json
do
  require_identical "$rel"
done

require_file "$DST/ui-truth-mapping/templates/flutter-motion-preview-test.dart.example"
require_han_content "$DST/ui-truth-mapping/templates/flutter-motion-preview-test.dart.example"

# Localized skill entrypoints
for skill in ai-delivery-orchestrator requirement-breakdown ui-truth-mapping; do
  require_file "$SRC/$skill/SKILL.md"
  require_file "$DST/$skill/SKILL-zh.md"
  require_no_han_content "$SRC/$skill/SKILL.md"
  require_han_content "$DST/$skill/SKILL-zh.md"
done

for rel in ai-delivery-orchestrator/SKILL.md ai-delivery-orchestrator/templates/design-template.md ai-delivery-orchestrator/templates/status-template.json; do
  require_no_han_content "$SRC/$rel"
  grep -Fq 'ui_truth_mode' "$SRC/$rel" || grep -Fq 'solution-design' "$SRC/$rel" \
    || fail "Missing mode-aware solution-design marker: $rel"
done

for tree in "$SRC" "$DST"; do
  if grep -R -Fq 'ui_contract_exempt' "$tree/ai-delivery-orchestrator" \
      --exclude-dir='__pycache__' \
      --exclude='reconcile-delivery.py' \
      --exclude='*.pyc'; then
    fail "Deprecated ui_contract_exempt bypass remains outside the explicit rejection guard"
  fi
  if grep -R -Fq 'no_design_client' "$tree/ai-delivery-orchestrator" \
      --exclude-dir='__pycache__' \
      --exclude='reconcile-delivery.py' \
      --exclude='*.pyc'; then
    fail "Deprecated no_design_client profile remains outside the explicit rejection guard"
  fi
done
grep -Fq 'legacy field ui_contract_exempt is forbidden' \
  "$SRC/ai-delivery-orchestrator/scripts/reconcile-delivery.py" \
  || fail "Reconcile must reject ui_contract_exempt explicitly"
grep -Fq 'no_design_client participation profile is removed' \
  "$SRC/ai-delivery-orchestrator/scripts/reconcile-delivery.py" \
  || fail "Reconcile must reject no_design_client explicitly"

# Localized templates
require_file "$SRC/requirement-breakdown/templates/requirement-slice-template.md"
require_file "$DST/requirement-breakdown/templates/requirement-slice-template-zh.md"

# Orchestrator reference parity (same filenames, zh tree translated)
for ref in framework-adaptation.md workspace-policy.md handoff-table.md stage-breakdown.md stage-ui-truth.md stage-design-and-spec.md stage-4-sdd-bridge.md stage-implementation.md blocker-catalog.md reconcile-rules.md scenario-guidance.md retrospective-guidance.md; do
  require_file "$SRC/ai-delivery-orchestrator/references/$ref"
  require_file "$DST/ai-delivery-orchestrator/references/$ref"
  require_han_content "$DST/ai-delivery-orchestrator/references/$ref"
done
for framework in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
  require_file "$SRC/ai-delivery-orchestrator/references/frameworks/$framework"
  require_file "$DST/ai-delivery-orchestrator/references/frameworks/$framework"
  require_han_content "$DST/ai-delivery-orchestrator/references/frameworks/$framework"
done

# Human-readable orchestrator templates are localized in both trees.
for template in \
  delivery-report-template.md \
  design-template.md \
  status-template.json \
  todo-template.md \
  visual-acceptance-template.json \
  retrospective-template.md \
  retrospective-index-template.md \
  verification-template.md
do
  source_template="$SRC/ai-delivery-orchestrator/templates/$template"
  zh_template="$DST/ai-delivery-orchestrator/templates/$template"
  require_file "$source_template"
  require_file "$zh_template"
  require_no_han_content "$source_template"
  require_han_content "$zh_template"
  if grep -Fq -- "ai-delivery-orchestrator/templates/$template" "$SYNC_SCRIPT"; then
    fail "Localized template must not be copied as a non-localized asset: $template"
  fi
done

grep -Fq 'Scenario IDs' "$SRC/ai-delivery-orchestrator/templates/design-template.md" \
  || fail "English design template must reference scenario IDs"
grep -Fq $'\u573a\u666f' "$DST/ai-delivery-orchestrator/templates/design-template.md" \
  || fail "Chinese design template must localize scenario references"
for design_template in \
  "$SRC/ai-delivery-orchestrator/templates/design-template.md" \
  "$DST/ai-delivery-orchestrator/templates/design-template.md"
do
  grep -Fq '"artifact_type":"solution-design"' "$design_template" \
    || fail "Design template must declare solution-design artifact metadata: $design_template"
  grep -Fq '"layout_key":"solution_design"' "$design_template" \
    || fail "Design template must declare the solution_design layout key: $design_template"
  grep -Fq '"canonical_path":"design.md"' "$design_template" \
    || fail "Design template must preserve the canonical design.md path: $design_template"
done

# zh tree must not advertise .agents-zh as a runtime command path
if grep -R -- '.agents-zh/skills/.*/scripts/' "$DST" >/dev/null 2>&1; then
  fail "Found forbidden runtime path .agents-zh/skills/.../scripts/ in zh mirror"
fi

print -- 'PASS: .agents and .agents-zh are structurally synced (non-locale identical, locale mirrored).'
