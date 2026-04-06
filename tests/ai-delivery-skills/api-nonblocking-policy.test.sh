#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

if [[ -d "$ROOT/.agents/skills/ai-delivery" ]]; then
  SKILL_ROOT="$ROOT/.agents/skills/ai-delivery"
else
  SKILL_ROOT="$ROOT/.agents/skills"
fi

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

require_not_contains() {
  local file=$1
  local needle=$2

  if grep -Fq -- "$needle" "$file"; then
    fail "Unexpected '$needle' in $file"
  fi
}

require_file "$SKILL_ROOT/api-contract-mapping/SKILL.md"
require_file "$SKILL_ROOT/requirement-breakdown/SKILL.md"
require_file "$SKILL_ROOT/ui-requirement-mapping/SKILL.md"
require_file "$SKILL_ROOT/ui-interaction-design/SKILL.md"

require_not_contains \
  "$SKILL_ROOT/api-contract-mapping/SKILL.md" \
  'If the user asked for API mapping but no trustworthy client-facing API contract source exists, block on `blocked_missing_api_contract`.'

require_contains \
  "$SKILL_ROOT/api-contract-mapping/SKILL.md" \
  "Missing or partial API contract material does not block early frontend stages by default."

require_contains \
  "$SKILL_ROOT/requirement-breakdown/SKILL.md" \
  "Do not let API incompleteness reduce a safe requirement slice."

require_contains \
  "$SKILL_ROOT/ui-requirement-mapping/SKILL.md" \
  "Do not require complete API mapping to finish UI mapping."

require_contains \
  "$SKILL_ROOT/ui-interaction-design/SKILL.md" \
  "Do not wait for request or response field finality to finish interaction design."

print -- "PASS: non-blocking API policy is documented across governed skill stages."
