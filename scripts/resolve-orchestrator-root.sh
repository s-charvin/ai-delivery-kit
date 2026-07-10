#!/bin/zsh
# Resolve orchestrator skill root for script invocations.
# Prefers .agents/skills/ai-delivery-orchestrator; falls back to skill-relative path.

set -euo pipefail

resolve_from_cwd() {
  local cwd=${1:-$(pwd -P)}
  if [[ -d "$cwd/.agents/skills/ai-delivery-orchestrator" ]]; then
    print -- "$cwd/.agents/skills/ai-delivery-orchestrator"
    return 0
  fi
  if [[ -d "$cwd/.ai-delivery" && -d "$cwd/.agents/skills/ai-delivery-orchestrator" ]]; then
    print -- "$cwd/.agents/skills/ai-delivery-orchestrator"
    return 0
  fi
  return 1
}

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
KIT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

if resolve_from_cwd "$KIT_ROOT"; then
  exit 0
fi

# Fallback: relative to this script when running from kit repo scripts/
if [[ -d "$KIT_ROOT/.agents/skills/ai-delivery-orchestrator" ]]; then
  print -- "$KIT_ROOT/.agents/skills/ai-delivery-orchestrator"
  exit 0
fi

print -u2 -- "orchestrator root not found; expected .agents/skills/ai-delivery-orchestrator"
exit 1
