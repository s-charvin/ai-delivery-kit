#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

fail() {
  print -u2 -- "[ui-contract-validator-test] $1"
  exit 1
}

require_python_yaml() {
  python3 -c 'import yaml' 2>/dev/null || {
    python3 -m pip install pyyaml -q || pip3 install pyyaml -q || fail "PyYAML is required for validator tests"
  }
}

if [[ -f "$ROOT/managedassets.go" ]]; then
  VALIDATOR="$ROOT/scripts/validate-ui-contract.py"
  STATUS_VALIDATOR="$ROOT/scripts/validate-delivery-status.py"
else
  VALIDATOR="$ROOT/.ai-delivery/scripts/validate-ui-contract.py"
  STATUS_VALIDATOR="$ROOT/.ai-delivery/scripts/validate-delivery-status.py"
fi
GOOD="$ROOT/.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-good.yaml"
BAD="$ROOT/.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-bad.yaml"
SECTION_MAP="$ROOT/.agents/skills/ui-truth-mapping/fixtures/section-map-good.json"

[[ -f "$VALIDATOR" ]] || fail "Missing validator: $VALIDATOR"
[[ -f "$STATUS_VALIDATOR" ]] || fail "Missing status validator: $STATUS_VALIDATOR"
[[ -f "$GOOD" ]] || fail "Missing good fixture: $GOOD"
[[ -f "$BAD" ]] || fail "Missing bad fixture: $BAD"

require_python_yaml

python3 "$VALIDATOR" "$GOOD" --section-map "$SECTION_MAP" >/dev/null || fail "Good fixture should pass validation"

if python3 "$VALIDATOR" "$BAD" >/dev/null 2>&1; then
  fail "Bad fixture should fail validation"
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/sub-requirements/sr-login"
cp "$GOOD" "$TMP_DIR/sub-requirements/sr-login/ui-acceptance-contract.yaml"
cp "$SECTION_MAP" "$TMP_DIR/sub-requirements/sr-login/section-map.json"
echo '# visual acceptance evidence' >"$TMP_DIR/sub-requirements/sr-login/visual-acceptance.md"

cat >"$TMP_DIR/status.json" <<'EOF'
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

python3 "$STATUS_VALIDATOR" "$TMP_DIR/status.json" --req-root "$TMP_DIR" >/dev/null || fail "Status validator should pass for merged + valid contract"

mkdir -p "$TMP_DIR/sub-requirements/sr-missing"
cat >"$TMP_DIR/status.json" <<'EOF'
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

if python3 "$STATUS_VALIDATOR" "$TMP_DIR/status.json" --req-root "$TMP_DIR" >/dev/null 2>&1; then
  fail "Status validator should fail when acceptance_frozen has no contract"
fi

print -- 'PASS: ui contract validators enforce good/bad fixtures and status gates.'
