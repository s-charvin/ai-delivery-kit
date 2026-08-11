#!/usr/bin/env bash
# superpowers verification discipline: `merged` requires verification.md hard
# evidence on new-layout sub-requirements, and legacy-layout repos stay clean.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-delivery-status.py"

fail() {
  printf '[verification-gate.test] %s\n' "$1" >&2
  exit 1
}

[ -f "$VALIDATOR" ] || fail "Missing validator: $VALIDATOR"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

write_status() {
  local req_root="$1" subreq_id="$2" subreq_status="$3"
  cat >"$req_root/status.json" <<EOF
{
  "requirement_id": "REQ-VERIFY",
  "sub_requirements": {
    "$subreq_id": { "status": "$subreq_status", "ui_bearing": false }
  }
}
EOF
}

run_validator() {
  python3 "$VALIDATOR" "$1/status.json" --req-root "$1" 2>&1
}

# --- Case 1: new layout at merged without verification.md -> rejected --------
NEW_ROOT="$WORK/new"
NEW_SR="$NEW_ROOT/sub-requirements/SR-001"
mkdir -p "$NEW_SR/spec"
echo '# spec' >"$NEW_SR/spec/spec.md"
echo '# plan' >"$NEW_SR/spec/plan.md"
echo '# tasks' >"$NEW_SR/spec/tasks.md"
echo '# design' >"$NEW_SR/design.md"
write_status "$NEW_ROOT" "SR-001" "merged"

if output="$(run_validator "$NEW_ROOT")"; then
  fail "merged without verification.md must fail, got: $output"
fi
grep -q 'requires verification.md' <<<"$output" \
  || fail "Expected a verification.md gate error, got: $output"

# --- Case 2: verification.md present but missing a required section ----------
cat >"$NEW_SR/verification.md" <<'EOF'
# 验证记录

## 评审轮次记录
- 第 1 轮：clean

## 验证命令与结果
- `make test` -> 通过
EOF

if output="$(run_validator "$NEW_ROOT")"; then
  fail "verification.md missing the sign-off section must fail, got: $output"
fi
grep -q 'missing required section' <<<"$output" \
  || fail "Expected a missing-section error, got: $output"

# --- Case 3: complete verification.md -> accepted ----------------------------
cat >>"$NEW_SR/verification.md" <<'EOF'

## 签署
- 验证人：orchestrator
EOF

output="$(run_validator "$NEW_ROOT")" \
  || fail "complete verification.md should validate clean, got: $output"

# --- Case 4: legacy layout at merged stays clean (backward compatibility) ----
OLD_ROOT="$WORK/old"
OLD_SR="$OLD_ROOT/sub-requirements/SR-001"
mkdir -p "$OLD_SR"
echo '# spec' >"$OLD_SR/spec.md"
echo '# tasks' >"$OLD_SR/tasks.md"
write_status "$OLD_ROOT" "SR-001" "merged"

output="$(run_validator "$OLD_ROOT")" \
  || fail "legacy-layout merged must stay clean, got: $output"

echo 'PASS: verification.md gate enforced on new layout, legacy layout unaffected.'
