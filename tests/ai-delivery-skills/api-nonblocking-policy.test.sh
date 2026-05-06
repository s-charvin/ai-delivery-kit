#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

SKILL_ROOT="$ROOT/.agents/skills"

fail() {
  print -u2 -- "[api-nonblocking-policy-test] $1"
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_contains() {
  local file=$1
  local needle=$2

  if ! grep -Fq -- "$needle" "$file"; then
    fail "Expected '$needle' in $file"
  fi
}

require_file "$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md"
require_file "$SKILL_ROOT/requirement-breakdown/SKILL.md"
require_file "$SKILL_ROOT/ui-truth-mapping/SKILL.md"

require_contains \
  "$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md" \
  "API docs are passed directly to implementation"

require_contains \
  "$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md" \
  "integration_deferred"

require_contains \
  "$SKILL_ROOT/ui-truth-mapping/SKILL.md" \
  "Do not invent visual truth"

require_contains \
  "$SKILL_ROOT/requirement-breakdown/SKILL.md" \
  "Do not invent product truth"

print -- "PASS: non-blocking API policy is documented across governed skill stages."
