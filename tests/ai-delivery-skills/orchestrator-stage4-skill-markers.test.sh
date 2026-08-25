#!/usr/bin/env bash
set -euo pipefail

# Pressure markers for Stage 4 visual-truth rules.
#
# Observed failures without these rules:
# 1. Agents re-called TemPad get_code/get_structure during implement because
#    stage-implementation said "Run figma-design-to-code only in this stage",
#    creating a second visual truth that can disagree with the frozen HTML.
# 2. Agents copied contract/get_code pixel widths as runtime constants
#    instead of fill + parent insets.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EN="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-implementation.md"
ZH="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-implementation.md"
EN_UI="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-ui-truth.md"
EN_SKILL="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
EN_BRIDGE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-4-sdd-bridge.md"
EN_DESIGN_STAGE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md"
EN_DESIGN_TEMPLATE="$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

require() {
  local file="$1" needle="$2" label="$3"
  [[ -f "$file" ]] || fail "Missing file: $file"
  grep -F -q -- "$needle" "$file" || fail "$label missing in $(basename "$file"): $needle"
}

forbid() {
  local file="$1" needle="$2" label="$3"
  [[ -f "$file" ]] || fail "Missing file: $file"
  if grep -F -q -- "$needle" "$file"; then
    fail "$label still present in $(basename "$file"): $needle"
  fi
}

# The old sentence is read as "you MUST run TemPad in Stage 4".
forbid "$EN" "Run \`figma-design-to-code\` only in this stage" "EN old TemPad-must-run wording"

require "$EN" "Do not run \`figma-design-to-code\` or call TemPad" "EN no TemPad ritual"
require "$EN" "the frozen component wins" "EN frozen component wins vs live TemPad"
require "$EN" "fill / hug / fixed" "EN follow sizing classification"
require "$EN" "not a runtime constant" "EN preview px ≠ runtime"
require "$EN" "stop and ask" "EN ask overflow at implement"
require "$EN" "snapshot \`w×h\` equality" "EN VA not snapshot px"
require "$EN" "execute every v2 scenario" "EN complete runtime scenario execution"
require "$EN" "preview hashes remain identical" "EN preview hash invalidation"
require "$EN" "reference/candidate/diff hashes" "EN deterministic image diff evidence"

require "$EN_UI" "Stage 4 does not re-run it by default" "EN Stage 2 pointer"
require "$EN_UI" "all ten coverage dimensions" "EN runtime coverage freeze gate"

require "$EN_SKILL" "do not re-query TemPad / run \`figma-design-to-code\` by default" "EN SKILL Stage 4"
require "$EN_SKILL" "structured \`visual-acceptance.json\`" "EN structured acceptance gate"
require "$EN_BRIDGE" "exactly one result for every indexed scenario id" "EN exact scenario acceptance"
require "$EN_DESIGN_STAGE" "every frozen unit/scenario id" "EN scenario-linked spec"
require "$EN_DESIGN_STAGE" "which task implements or verifies each scenario id" "EN scenario-linked plan"
require "$EN_DESIGN_STAGE" "complete scenario-to-test/acceptance coverage" "EN scenario-linked tasks"
require "$EN_DESIGN_TEMPLATE" "Unit and Scenario Traceability" "EN design traceability"
require "$EN_DESIGN_TEMPLATE" "State and Transition Model" "EN design state model"
require "$EN_DESIGN_TEMPLATE" "Runtime Boundaries" "EN design runtime boundaries"
require "$EN_DESIGN_TEMPLATE" "Performance/resource lifecycle" "EN design performance lifecycle"

# Kit skills must stay framework-agnostic — no host-app size tokens or live-node anecdotes.
for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w|left: 35|x=46' "$f" >/dev/null; then
    fail "project-specific anecdote in $(basename "$f")"
  fi
done

echo "PASS: orchestrator Stage 4 skill markers"
