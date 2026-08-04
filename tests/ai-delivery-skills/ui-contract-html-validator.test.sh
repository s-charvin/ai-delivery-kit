#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOOD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-good.html"
BAD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"
VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"

fail() { echo "FAIL: $*" >&2; exit 1; }

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

python3 "$VALIDATOR" "$GOOD" >"$TMP_DIR/ui-contract-good.out" 2>&1 || {
  cat "$TMP_DIR/ui-contract-good.out" >&2
  fail "good fixture should validate"
}
grep -q '^OK:' "$TMP_DIR/ui-contract-good.out" || fail "good fixture must print OK"

if python3 "$VALIDATOR" "$BAD" >"$TMP_DIR/ui-contract-bad.out" 2>&1; then
  cat "$TMP_DIR/ui-contract-bad.out" >&2
  fail "bad fixture unexpectedly validated"
fi
grep -q 'INVALID:' "$TMP_DIR/ui-contract-bad.out" || fail "bad fixture must print INVALID"
grep -q 'META' "$TMP_DIR/ui-contract-bad.out" || fail "bad fixture should report metadata errors"
grep -q 'DUPLICATE_ID' "$TMP_DIR/ui-contract-bad.out" || fail "bad fixture should report duplicate IDs"
grep -q 'SOURCE_NODE' "$TMP_DIR/ui-contract-bad.out" || fail "bad fixture should report missing source nodes"
grep -q 'SYSTEM_UI' "$TMP_DIR/ui-contract-bad.out" || fail "bad fixture should reject system UI"

# Reject empty / whitespace-only data-ui-id attributes.
python3 - "$GOOD" "$TMP_DIR/empty-id.html" <<'PY'
from pathlib import Path
import sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
needle = '<h1 data-ui-id="profile-title"'
if needle not in raw:
    raise SystemExit("fixture missing expected h1 data-ui-id")
dst.write_text(raw.replace(needle, '<h1 data-ui-id="   "', 1), encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/empty-id.html" >"$TMP_DIR/empty-id.out" 2>&1; then
  cat "$TMP_DIR/empty-id.out" >&2
  fail "whitespace data-ui-id should fail validation"
fi
grep -q 'data-ui-id must be a non-empty string' "$TMP_DIR/empty-id.out" \
  || fail "whitespace data-ui-id must report empty/whitespace rejection"

echo "PASS: ui-contract-html-validator"
