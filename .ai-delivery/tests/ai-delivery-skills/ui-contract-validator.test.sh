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

# Scenario 2: status.json=merged while ui-contract.html meta is still frozen
# with implemented:null (raise-status-only shortcut) must FAIL — independent of
# HTML meta.delivery.status. Do NOT rewrite meta to merged here.
mkdir -p "$TMP_DIR/merged/sub-requirements/sr-login/profile-page"
cp "$GOOD" "$TMP_DIR/merged/sub-requirements/sr-login/profile-page/ui-contract.html"
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
  fail "Status validator should fail when status.json=merged but meta remains frozen/implemented:null"
fi

# Scenario 2b: merged + complete delivery.implemented backfill must PASS.
mkdir -p "$TMP_DIR/merged-ok/sub-requirements/sr-login/profile-page"
python3 - "$GOOD" "$TMP_DIR/merged-ok/sub-requirements/sr-login/profile-page/ui-contract.html" <<'PY'
import json, re, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_text(encoding="utf-8")
match = re.search(
    r'(<script[^>]*id=["\']ui-contract-meta["\'][^>]*>)(.*?)(</script>)',
    raw,
    re.DOTALL,
)
assert match, "fixture missing #ui-contract-meta"
meta = json.loads(match.group(2))
meta["delivery"] = {
    "status": "merged",
    "implemented": {
        "type": "code",
        "target": "src/profile/ProfilePage.tsx",
        "requirement": "fixture-subreq-1",
        "version": "1",
        "status": "merged",
    },
}
dst.write_text(match.group(1) + "\n  " + json.dumps(meta, indent=2) + "\n  " + match.group(3) + raw[match.end():], encoding="utf-8")
PY
echo '# visual acceptance evidence' >"$TMP_DIR/merged-ok/sub-requirements/sr-login/visual-acceptance.md"
cat >"$TMP_DIR/merged-ok/status.json" <<'EOF'
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

python3 "$STATUS_VALIDATOR" "$TMP_DIR/merged-ok/status.json" --req-root "$TMP_DIR/merged-ok" >/dev/null \
  || fail "Status validator should pass merged when delivery.implemented is complete"

# Scenario 3: a sub-requirement with no ui-contract.html anywhere must fail
# acceptance_frozen.
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

# Scenario 4: dangling ui-contract.html pointers in the requirement directory.
# Active pointers must resolve to an existing contract; a historical
# "superseded" note line is exempt.
mkdir -p "$TMP_DIR/pointers/sub-requirements/sr-login/profile-page"
cp "$GOOD" "$TMP_DIR/pointers/sub-requirements/sr-login/profile-page/ui-contract.html"
cat >"$TMP_DIR/pointers/status.json" <<'EOF'
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

# 4a: valid pointer + historical note about a removed contract -> PASS.
cat >"$TMP_DIR/pointers/sub-requirements/sr-login/visual-acceptance.md" <<'EOF'
# visual acceptance evidence
Contract: sub-requirements/sr-login/profile-page/ui-contract.html
History: sub-requirements/sr-login/old-states/ui-contract.html superseded by profile-page
EOF

python3 "$STATUS_VALIDATOR" "$TMP_DIR/pointers/status.json" --req-root "$TMP_DIR/pointers" >/dev/null \
  || fail "Status validator should pass when pointers resolve and removed paths are marked superseded"

# 4b: an ACTIVE pointer to a removed contract must FAIL.
cat >>"$TMP_DIR/pointers/sub-requirements/sr-login/visual-acceptance.md" <<'EOF'
Contract: sub-requirements/sr-login/removed-unit/ui-contract.html
EOF

if python3 "$STATUS_VALIDATOR" "$TMP_DIR/pointers/status.json" --req-root "$TMP_DIR/pointers" >/dev/null 2>&1; then
  fail "Status validator should fail on a dangling active ui-contract.html pointer"
fi

echo 'PASS: ui contract validators enforce good/bad HTML fixtures, status gates, and dangling-pointer sweeps.'
