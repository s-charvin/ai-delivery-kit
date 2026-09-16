#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)

tracked=$(git -C "$ROOT" ls-files .ai-delivery)
if [[ -n "$tracked" ]]; then
  printf 'FAIL: kit source repository must not track bootstrap output under .ai-delivery:\n%s\n' "$tracked" >&2
  exit 1
fi

printf 'PASS: kit root does not track bootstrap output under .ai-delivery.\n'
