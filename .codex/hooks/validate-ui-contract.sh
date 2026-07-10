#!/bin/bash
# Codex adapter: delegates to the shared UI contract gate.
# Wired via .codex/hooks.json PostToolUse (Edit|Write|apply_patch).
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
SHARED="$ROOT/.ai-delivery/scripts/hooks/validate-ui-contract.sh"
if [[ ! -f "$SHARED" ]]; then
  SHARED="$ROOT/scripts/hooks/validate-ui-contract.sh"
fi
exec bash "$SHARED"
