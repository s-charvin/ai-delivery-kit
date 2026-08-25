#!/usr/bin/env bash
# Tests path resolution and hash normalization in the unified artifact layout resolver.
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAYOUT_PY="$KIT_ROOT/.agents/skills/ai-delivery-orchestrator/scripts/layout.py"

if [ ! -f "$LAYOUT_PY" ]; then
  echo "FAIL: layout.py not found at $LAYOUT_PY" >&2
  exit 1
fi

python3 "$LAYOUT_PY" --selftest
