#!/usr/bin/env bash
# layout.py 单测：验证统一产物布局解析器的路径解析与 hash 规范化。
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAYOUT_PY="$KIT_ROOT/.agents/skills/ai-delivery-orchestrator/scripts/layout.py"

if [ ! -f "$LAYOUT_PY" ]; then
  echo "FAIL: layout.py not found at $LAYOUT_PY" >&2
  exit 1
fi

python3 "$LAYOUT_PY" --selftest
