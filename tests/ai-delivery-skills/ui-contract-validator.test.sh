#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

fail() {
  echo "[ui-contract-validator-test] $1" >&2
  exit 1
}

if [[ -f "$ROOT/managedassets.go" ]]; then
  VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"
  STATUS_VALIDATOR="$ROOT/scripts/validate-delivery-status.py"
  GOOD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-good.html"
  BAD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"
else
  VALIDATOR="$ROOT/.ai-delivery/scripts/validate-ui-contract-html.py"
  STATUS_VALIDATOR="$ROOT/.ai-delivery/scripts/validate-delivery-status.py"
  GOOD="$ROOT/.ai-delivery/tests/ai-delivery-skills/fixtures/ui-contract-good.html"
  BAD="$ROOT/.ai-delivery/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"
fi

[[ -f "$VALIDATOR" ]] || fail "Missing HTML contract validator: $VALIDATOR"
[[ -f "$STATUS_VALIDATOR" ]] || fail "Missing status validator: $STATUS_VALIDATOR"
[[ -f "$GOOD" ]] || fail "Missing good fixture: $GOOD"
[[ -f "$BAD" ]] || fail "Missing bad fixture: $BAD"

python3 "$VALIDATOR" "$GOOD" >/dev/null || fail "Good HTML contract fixture should pass validation"

if python3 "$VALIDATOR" "$BAD" >/dev/null 2>&1; then
  fail "Bad HTML contract fixture should fail validation"
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Scenario 1: a status that expects a frozen contract (acceptance_frozen) with a
# valid v2 HTML contract present (one ui-contract.html per unit dir) must PASS.
mkdir -p "$TMP_DIR/frozen/sub-requirements/sr-login/profile-page"
cp "$GOOD" "$TMP_DIR/frozen/sub-requirements/sr-login/profile-page/ui-contract.html"

cat >"$TMP_DIR/frozen/status.json" <<'EOF'
{
  "requirement_id": "req-fixture",
  "updated_at": "2026-07-10T00:00:00Z",
  "sub_requirements": {
    "sr-login": {
      "status": "acceptance_frozen",
      "detail": null,
      "blocked_from_status": null,
      "blocker_scope": null,
      "resume_target_status": null,
      "notes": null
    }
  }
}
EOF

python3 "$STATUS_VALIDATOR" "$TMP_DIR/frozen/status.json" --req-root "$TMP_DIR/frozen" >/dev/null \
  || fail "Status validator should pass acceptance_frozen with a valid ui-contract.html present"

# Scenario 2: a delivered status (merged) whose ui-contract.html declares
# delivery.status=merged but is missing delivery.implemented must FAIL.
mkdir -p "$TMP_DIR/merged/sub-requirements/sr-login/profile-page"
sed -e 's/"status": "frozen"/"status": "merged"/' \
  "$GOOD" >"$TMP_DIR/merged/sub-requirements/sr-login/profile-page/ui-contract.html"
echo '# visual acceptance evidence' >"$TMP_DIR/merged/sub-requirements/sr-login/visual-acceptance.md"

cat >"$TMP_DIR/merged/status.json" <<'EOF'
{
  "requirement_id": "req-fixture",
  "updated_at": "2026-07-10T00:00:00Z",
  "sub_requirements": {
    "sr-login": {
      "status": "merged",
      "detail": null,
      "blocked_from_status": null,
      "blocker_scope": null,
      "resume_target_status": null,
      "notes": null
    }
  }
}
EOF

if python3 "$STATUS_VALIDATOR" "$TMP_DIR/merged/status.json" --req-root "$TMP_DIR/merged" >/dev/null 2>&1; then
  fail "Status validator should fail when a merged contract is missing delivery.implemented"
fi

# Scenario 3: a sub-requirement with no ui-contract.html anywhere must fail
# acceptance_frozen (no YAML or section-map fallback exists anymore).
mkdir -p "$TMP_DIR/missing/sub-requirements/sr-missing"
cat >"$TMP_DIR/missing/status.json" <<'EOF'
{
  "requirement_id": "req-fixture",
  "updated_at": "2026-07-10T00:00:00Z",
  "sub_requirements": {
    "sr-missing": {
      "status": "acceptance_frozen",
      "detail": null,
      "blocked_from_status": null,
      "blocker_scope": null,
      "resume_target_status": null,
      "notes": null
    }
  }
}
EOF

if python3 "$STATUS_VALIDATOR" "$TMP_DIR/missing/status.json" --req-root "$TMP_DIR/missing" >/dev/null 2>&1; then
  fail "Status validator should fail when acceptance_frozen has no ui-contract.html"
fi

echo 'PASS: ui contract validators enforce good/bad HTML fixtures and status gates.'
