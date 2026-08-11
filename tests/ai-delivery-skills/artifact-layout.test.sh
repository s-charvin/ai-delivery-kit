#!/bin/zsh
# validate-artifact-layout.py selftest: layout-contract resolution + backward compat.
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VALIDATOR="$KIT_ROOT/scripts/validate-artifact-layout.py"

[[ -f "$VALIDATOR" ]] || { print -u2 "FAIL: validator not found at $VALIDATOR"; exit 1 }

python3 "$VALIDATOR" --selftest
