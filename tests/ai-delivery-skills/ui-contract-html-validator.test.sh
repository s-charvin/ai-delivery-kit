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

# Empty default <template> must fail PREVIEW (would hydrate blank).
python3 - "$GOOD" "$TMP_DIR/empty-default.html" <<'PY'
from pathlib import Path
import re, sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
raw = re.sub(
    r'<template data-ui-state="idle">.*?</template>',
    '<template data-ui-state="idle"></template>',
    raw,
    count=1,
    flags=re.DOTALL,
)
dst.write_text(raw, encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/empty-default.html" >"$TMP_DIR/empty-default.out" 2>&1; then
  cat "$TMP_DIR/empty-default.out" >&2
  fail "empty default state template should fail validation"
fi
grep -q 'PREVIEW' "$TMP_DIR/empty-default.out" \
  || fail "empty default template must report PREVIEW"

# Missing scope inventory must fail SCOPE.
python3 - "$GOOD" "$TMP_DIR/no-scope.html" <<'PY'
from pathlib import Path
import sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
raw = raw.replace('data-ui-scope="in_scope"', 'data-ui-scope="other"')
dst.write_text(raw, encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/no-scope.html" >"$TMP_DIR/no-scope.out" 2>&1; then
  cat "$TMP_DIR/no-scope.out" >&2
  fail "missing in_scope inventory should fail validation"
fi
grep -q 'SCOPE' "$TMP_DIR/no-scope.out" \
  || fail "missing in_scope must report SCOPE"

echo "PASS: ui-contract-html-validator"
