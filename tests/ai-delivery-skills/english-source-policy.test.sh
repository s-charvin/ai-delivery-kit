#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

for rel in \
  .agents/skills/ai-delivery-orchestrator/references/retrospective-guidance.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md
do
  [[ -f "$ROOT/$rel" ]] || { printf '%s\n' "[english-source-policy.test] missing $rel" >&2; exit 1; }
done

if matches=$(git -C "$ROOT" grep -n -P '\p{Han}' -- . \
  ':(glob,exclude).agents-zh/**' \
  ':(glob,exclude)**/README*' \
  ':(glob,exclude)**/docs/**'); then
  printf '%s\n' "$matches" >&2
  printf '%s\n' '[english-source-policy.test] Han characters are allowed only in .agents-zh, README files, and docs.' >&2
  exit 1
fi

printf '%s\n' 'PASS: governed source files contain no Han characters outside allowed paths.'
