#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)

fail() {
  print -u2 -- "[verify-ai-delivery-full-chain] $1"
  exit 1
}

resolve_admin_root() {
  if [[ -n "${AI_DELIVERY_ADMIN_ROOT:-}" && -d "${AI_DELIVERY_ADMIN_ROOT}" ]]; then
    print -- "${AI_DELIVERY_ADMIN_ROOT}"
    return 0
  fi

  local candidates=(
    "$ROOT/.worktrees/ai-delivery-admin/full-chain-consistency-repair"
    "$ROOT/../ai-delivery-admin"
    "/Users/charvin/Projects/ai-delivery-admin"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "$candidate" ]]; then
      print -- "$candidate"
      return 0
    fi
  done

  return 1
}

ADMIN_ROOT=$(resolve_admin_root) || fail "Unable to locate ai-delivery-admin repo. Set AI_DELIVERY_ADMIN_ROOT to continue."

print -- "[verify-ai-delivery-full-chain] validating project-local skills"
zsh "$ROOT/scripts/validate-project-ai-delivery-skills.sh"

print -- "[verify-ai-delivery-full-chain] validating Codex-side full-chain contracts"
zsh "$ROOT/scripts/validate-full-chain-repair-contracts.sh"

print -- "[verify-ai-delivery-full-chain] running ai-delivery-admin test suite from $ADMIN_ROOT"
(
  cd "$ADMIN_ROOT"
  npm test
)

print -- "PASS: ai-delivery full-chain verification succeeded."
