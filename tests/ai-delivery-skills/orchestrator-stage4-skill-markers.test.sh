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
ZH_UI="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-ui-truth.md"
EN_SKILL="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
ZH_SKILL="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md"

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
forbid "$ZH" "\`figma-design-to-code\` 只在本阶段（或后续视觉修复 loop）使用" "ZH old TemPad-must-run wording"

require "$EN" "Do not run \`figma-design-to-code\` or call TemPad" "EN no TemPad ritual"
require "$EN" "the contract wins" "EN contract wins vs live TemPad"
require "$EN" "data-ui-sizing" "EN follow sizing annotation"
require "$EN" "not a runtime constant" "EN preview px ≠ runtime"

require "$ZH" "默认不要跑 \`figma-design-to-code\`，也不要调用 TemPad" "ZH no TemPad ritual"
require "$ZH" "以冻结契约为准" "ZH contract wins vs live TemPad"
require "$ZH" "data-ui-sizing" "ZH follow sizing annotation"
require "$ZH" "不是运行时常量" "ZH preview px ≠ runtime"

require "$EN_UI" "Stage 4 does not re-run it by default" "EN Stage 2 pointer"
require "$ZH_UI" "Stage 4 默认也不再跑" "ZH Stage 2 pointer"

require "$EN_SKILL" "do not re-query TemPad / run \`figma-design-to-code\` by default" "EN SKILL Stage 4"
require "$ZH_SKILL" "默认不要再查 TemPad / 不要跑 \`figma-design-to-code\`" "ZH SKILL Stage 4"

# Kit skills must stay framework-agnostic — no host-app size tokens or live-node anecdotes.
for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w|left: 35|x=46' "$f" >/dev/null; then
    fail "project-specific anecdote in $(basename "$f")"
  fi
done

echo "PASS: orchestrator Stage 4 skill markers"
