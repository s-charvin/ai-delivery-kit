#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
EN_ROOT="$ROOT/.agents/skills/ai-delivery-orchestrator"
ZH_ROOT="$ROOT/.agents-zh/skills/ai-delivery-orchestrator"

fail() { echo "FAIL: $*" >&2; exit 1; }
require() {
  local file=$1 needle=$2
  grep -Fq -- "$needle" "$file" || fail "missing '$needle' in $file"
}
forbid() {
  local file=$1 pattern=$2
  if grep -Eq -- "$pattern" "$file"; then
    fail "forbidden legacy route '$pattern' remains in $file"
  fi
}

for root in "$EN_ROOT" "$ZH_ROOT"; do
  skill="$root/SKILL.md"
  [[ -f "$skill" ]] || skill="$root/SKILL-zh.md"
  require "$skill" 'design_ready'
  require "$skill" 'state_flow_required'
  require "$skill" 'user_decision_required'
  require "$skill" 'design_review'
  forbid "$skill" 'spec_ready|plan_ready|tasks_ready|CP-001|confirm_to_dev|design_mode|design_approved'

  for file in \
    references/stage-design-and-spec.md \
    references/stage-4-sdd-bridge.md \
    references/reconcile-rules.md \
    references/handoff-table.md \
    references/framework-adaptation.md \
    references/workspace-policy.md
  do
    forbid "$root/$file" 'spec_ready|plan_ready|tasks_ready|CP-001|confirm_to_dev|design_mode|design_approved'
  done

  for guide in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
    require "$root/references/frameworks/$guide" 'design.md'
    require "$root/references/frameworks/$guide" 'source_index.design'
    forbid "$root/references/frameworks/$guide" 'spec_ready|plan_ready|tasks_ready|CP-001|confirm_to_dev|design_mode|design_approved'
  done
done

EN_IMPL="$EN_ROOT/references/stage-implementation.md"
EN_UI="$EN_ROOT/references/stage-ui-truth.md"
EN_BRIDGE="$EN_ROOT/references/stage-4-sdd-bridge.md"
EN_DESIGN="$EN_ROOT/references/stage-design-and-spec.md"
EN_TEMPLATE="$EN_ROOT/templates/design-template.md"
EN_ADAPT="$EN_ROOT/references/framework-adaptation.md"

# Existing UI truth, resource, layout, and motion constraints remain intact.
require "$EN_IMPL" 'Do not re-query TemPad or official Figma as a pre-implement ritual'
require "$EN_IMPL" 'the frozen component wins'
require "$EN_IMPL" 'fill / hug / fixed'
require "$EN_IMPL" 'one independent motion acceptance record for every indexed unit'
require "$EN_IMPL" 'fabricated fixture content'
require "$EN_IMPL" 'git diff --cached --name-status'
require "$EN_UI" 'all ten coverage dimensions'
require "$EN_UI" 'Static preview confirmation and motion confirmation/waiver are separate gates'
require "$EN_UI" 'Do not assemble a synthetic page'
require "$EN_BRIDGE" 'exactly one result for every indexed scenario id'
require "$EN_BRIDGE" 'design_ready'
require "$EN_BRIDGE" 'progress.md'

# Stage 3 is one bounded design contract, with simple and complex state-flow forms.
require "$EN_DESIGN" 'single canonical `design.md`'
require "$EN_DESIGN" 'state_flow_required=false'
require "$EN_DESIGN" 'state_flow_required=true'
require "$EN_DESIGN" 'user_decision_required'
require "$EN_TEMPLATE" 'ai-delivery:behavior-contract:start'
require "$EN_TEMPLATE" 'ai-delivery:state-summary'
require "$EN_TEMPLATE" 'ai-delivery:user-decisions'
require "$EN_TEMPLATE" 'UI Scenario References'

# External frameworks supply methods without restoring their artifact pipelines.
require "$EN_ADAPT" 'Artifact containment protocol (required)'
require "$EN_ADAPT" 'Existing framework trees are read-only inputs'
require "$EN_ADAPT" 'source_index.design'
require "$EN_ADAPT" 'including ignored files'

for guide in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
  forbid "$EN_ROOT/references/frameworks/$guide" 'kind.?=.?(spec|plan|tasks)|layout key.?[[:space:]]*`?(spec|plan|tasks)'
done

echo 'PASS: unified Stage 3/4 and framework containment markers'
