#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOOD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-good.html"
BAD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"
VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"

fail() { echo "FAIL: $*" >&2; exit 1; }

python3 "$VALIDATOR" "$GOOD" >"$TMPDIR/ui-contract-good.out" 2>&1 || {
  cat "$TMPDIR/ui-contract-good.out" >&2
  fail "good fixture should validate"
}
grep -q '^OK:' "$TMPDIR/ui-contract-good.out" || fail "good fixture must print OK"

if python3 "$VALIDATOR" "$BAD" >"$TMPDIR/ui-contract-bad.out" 2>&1; then
  cat "$TMPDIR/ui-contract-bad.out" >&2
  fail "bad fixture unexpectedly validated"
fi
grep -q 'INVALID:' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture must print INVALID"
grep -q 'META' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report metadata errors"
grep -q 'DUPLICATE_ID' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report duplicate IDs"
grep -q 'SOURCE_NODE' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report missing source nodes"
grep -q 'SYSTEM_UI' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should reject system UI"

echo "PASS: ui-contract-html-validator"
