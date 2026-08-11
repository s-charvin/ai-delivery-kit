#!/usr/bin/env bash
# validate-artifact-layout.py selftest: layout-contract resolution, backward
# compatibility, living-spec drift detection and archive immutability.
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VALIDATOR="$KIT_ROOT/scripts/validate-artifact-layout.py"

if [ ! -f "$VALIDATOR" ]; then
  echo "FAIL: validator not found at $VALIDATOR" >&2
  exit 1
fi

python3 "$VALIDATOR" --selftest
