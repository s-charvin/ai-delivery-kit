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

# Context chrome carrying truth annotations must fail SCOPE.
python3 - "$GOOD" "$TMP_DIR/context-truth.html" <<'PY'
from pathlib import Path
import sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
needle = '<template data-ui-state="idle">'
if needle not in raw:
    raise SystemExit("fixture missing idle template")
inject = (
    '<template data-ui-state="idle">'
    '<div data-ui-scope="context" data-ui-id="ctx-nav" data-ui-kind="navigation" '
    'data-figma-node="1:999">context chrome must not be truth-annotated</div>'
)
dst.write_text(raw.replace(needle, inject, 1), encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/context-truth.html" >"$TMP_DIR/context-truth.out" 2>&1; then
  cat "$TMP_DIR/context-truth.out" >&2
  fail "truth-annotated context chrome should fail validation"
fi
grep -q 'data-ui-scope="context" must not carry' "$TMP_DIR/context-truth.out" \
  || fail "truth-annotated context must report SCOPE context-not-truth"

# Empty non-default state template must fail PREVIEW (every state must preview).
python3 - "$GOOD" "$TMP_DIR/empty-alt.html" <<'PY'
from pathlib import Path
import re, sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
raw = re.sub(
    r'<template data-ui-state="empty">.*?</template>',
    '<template data-ui-state="empty"></template>',
    raw,
    count=1,
    flags=re.DOTALL,
)
dst.write_text(raw, encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/empty-alt.html" >"$TMP_DIR/empty-alt.out" 2>&1; then
  cat "$TMP_DIR/empty-alt.out" >&2
  fail "empty non-default state template should fail validation"
fi
grep -q 'state template "empty"' "$TMP_DIR/empty-alt.out" \
  || fail "empty non-default state must report PREVIEW state-content"

# in_scope node id not frozen in DOM must fail SCOPE (coverage cross-check).
python3 - "$GOOD" "$TMP_DIR/scope-coverage.html" <<'PY'
from pathlib import Path
import sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
old = "1:201 profile header; 1:202 title; 1:203 idle note; 1:301–1:302 empty state."
new = "9:999 phantom node that is not frozen anywhere in the DOM."
if old not in raw:
    raise SystemExit("fixture missing expected in_scope dd text")
dst.write_text(raw.replace(old, new, 1), encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/scope-coverage.html" >"$TMP_DIR/scope-coverage.out" 2>&1; then
  cat "$TMP_DIR/scope-coverage.out" >&2
  fail "in_scope node not frozen in DOM should fail validation"
fi
grep -q 'in_scope node "9:999" is not frozen' "$TMP_DIR/scope-coverage.out" \
  || fail "unfrozen in_scope node must report SCOPE coverage"

# Non-kebab-case state id must fail STATE (preview selector would break).
python3 - "$GOOD" "$TMP_DIR/bad-state-id.html" <<'PY'
from pathlib import Path
import sys
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
raw = raw.replace('"id": "empty"', '"id": "EmptyState"', 1)
raw = raw.replace('data-ui-state="empty"', 'data-ui-state="EmptyState"', 1)
dst.write_text(raw, encoding="utf-8")
PY
if python3 "$VALIDATOR" "$TMP_DIR/bad-state-id.html" >"$TMP_DIR/bad-state-id.out" 2>&1; then
  cat "$TMP_DIR/bad-state-id.out" >&2
  fail "non-kebab-case state id should fail validation"
fi
grep -q 'kebab-case lowercase ASCII' "$TMP_DIR/bad-state-id.out" \
  || fail "non-kebab-case state id must report STATE format"

echo "PASS: ui-contract-html-validator"
