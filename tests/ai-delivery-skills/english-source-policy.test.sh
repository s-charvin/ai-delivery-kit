#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

if matches=$(git -C "$ROOT" grep -n -P '\p{Han}' -- . \
  ':(glob,exclude).agents-zh/**' \
  ':(glob,exclude)**/README*' \
  ':(glob,exclude)**/docs/**'); then
  printf '%s\n' "$matches" >&2
  printf '%s\n' '[english-source-policy.test] Han characters are allowed only in .agents-zh, README files, and docs.' >&2
  exit 1
fi

printf '%s\n' 'PASS: governed source files contain no Han characters outside allowed paths.'
