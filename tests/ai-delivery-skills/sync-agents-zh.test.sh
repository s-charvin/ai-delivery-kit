#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
SRC="$ROOT/.agents/skills"
DST="$ROOT/.agents-zh/skills"

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

# Non-localized assets must be byte-identical
for rel in \
  ai-delivery-orchestrator/agents/openai.yaml \
  ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  ai-delivery-orchestrator/templates/status-template.json \
  requirement-breakdown/agents/openai.yaml \
  ui-truth-mapping/agents/openai.yaml \
  ui-truth-mapping/templates/section-map-template.json \
  ui-truth-mapping/fixtures/section-map-good.json \
  ui-truth-mapping/fixtures/ui-acceptance-contract-good.yaml \
  ui-truth-mapping/fixtures/ui-acceptance-contract-bad.yaml
do
  require_identical "$rel"
done

# Localized skill entrypoints
for skill in ai-delivery-orchestrator requirement-breakdown ui-truth-mapping; do
  require_file "$SRC/$skill/SKILL.md"
  require_file "$DST/$skill/SKILL-zh.md"
done

# Localized templates
require_file "$SRC/requirement-breakdown/templates/requirement-slice-template.md"
require_file "$DST/requirement-breakdown/templates/requirement-slice-template-zh.md"

# Orchestrator reference parity (same filenames, zh tree translated)
for ref in handoff-table.md stage-breakdown.md stage-ui-truth.md stage-design-and-speckit.md stage-4-sdd-bridge.md stage-implementation.md blocker-catalog.md reconcile-rules.md; do
  require_file "$SRC/ai-delivery-orchestrator/references/$ref"
  require_file "$DST/ai-delivery-orchestrator/references/$ref"
  grep -q '[\u4e00-\u9fff]' "$DST/ai-delivery-orchestrator/references/$ref" \
    || fail "Expected Chinese content in zh reference: $ref"
done

# Orchestrator templates: todo localized, status identical
require_identical "ai-delivery-orchestrator/templates/status-template.json"
require_file "$SRC/ai-delivery-orchestrator/templates/todo-template.md"
require_file "$DST/ai-delivery-orchestrator/templates/todo-template.md"
grep -q '[\u4e00-\u9fff]' "$DST/ai-delivery-orchestrator/templates/todo-template.md" \
  || fail "Expected Chinese todo-template in .agents-zh"

# ui-truth yaml template exists in both (structure synced; comments localized)
require_file "$SRC/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml"
require_file "$DST/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml"

# zh tree must not advertise .agents-zh as a runtime command path
if grep -R -- '.agents-zh/skills/.*/scripts/' "$DST" >/dev/null 2>&1; then
  fail "Found forbidden runtime path .agents-zh/skills/.../scripts/ in zh mirror"
fi

print -- 'PASS: .agents and .agents-zh are structurally synced (non-locale identical, locale mirrored).'
