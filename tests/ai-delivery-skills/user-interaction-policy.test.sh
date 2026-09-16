#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
ORCHESTRATOR="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
UI_TRUTH="$ROOT/.agents/skills/ui-truth-mapping/SKILL.md"

require() {
  local file=$1
  local pattern=$2
  local label=$3
  if ! grep -Eq "$pattern" "$file"; then
    printf 'FAIL: missing %s in %s\n' "$label" "$file" >&2
    exit 1
  fi
}

require "$ORCHESTRATOR" 'request_user_input' 'native user-choice UI preference'
require "$ORCHESTRATOR" 'current (turn|runtime|mode).*(available|permitted)|(available|permitted).*current (turn|runtime|mode)' 'current-runtime availability guard'
require "$ORCHESTRATOR" 'batch|group' 'batched user decisions'
require "$ORCHESTRATOR" 'structured chat' 'structured-chat fallback'
require "$ORCHESTRATOR" 'permission approval|permission prompt' 'permission UI boundary'
require "$ORCHESTRATOR" 'fake|fabricat|manufactur|unrelated elevated' 'forbidden fake escalation'
require "$ORCHESTRATOR" 'silence.*(approval|confirmation)|omitted.*(approval|confirmation)' 'no implicit approval'
require "$UI_TRUTH" 'request_user_input' 'UI truth native choice routing'
require "$UI_TRUTH" 'structured chat' 'UI truth structured-chat fallback'

printf 'PASS: user interaction policy\n'
