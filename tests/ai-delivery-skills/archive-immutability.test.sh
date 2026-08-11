#!/bin/bash
# Archive immutability gate (Phase 3): once a sub-requirement is frozen into
# archive/<ISO-ts>/, any later byte change must be detected by
# validate-artifact-layout.py --verify-archive (exit 1).
set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
ARCHIVE="$ROOT/scripts/archive-subrequirement.py"
VALIDATE="$ROOT/scripts/validate-artifact-layout.py"

fail() {
  echo "[archive-immutability.test] $1" >&2
  exit 1
}

[[ -f "$ARCHIVE" ]] || fail "Missing archive script: $ARCHIVE"
[[ -f "$VALIDATE" ]] || fail "Missing layout validator: $VALIDATE"

# Isolated requirement root in a temp dir; removed on exit.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

SUB="$TMP/sub-requirements/SR-001"
mkdir -p "$SUB/spec"

printf '# spec\nfrozen content\n' > "$SUB/spec/spec.md"
printf '# plan\n' > "$SUB/spec/plan.md"
printf '# tasks\n' > "$SUB/spec/tasks.md"
printf '# design\n' > "$SUB/design.md"
printf '# verification\n\n## 评审轮次记录\n\n- Round 1: approved.\n\n## 验证命令与结果\n\n- echo ok -> ok\n\n## 签署\n\n- reviewer: signed\n' > "$SUB/verification.md"

cat > "$TMP/status.json" <<'JSON'
{
  "requirement_id": "archive-immutability",
  "updated_at": "2026-07-10T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "merged",
      "ui_bearing": false,
      "design_approved": true
    }
  }
}
JSON

TS="2026-07-10T000000Z"

# 1) Freeze the merged sub-req into the immutable archive.
python3 "$ARCHIVE" --req-root "$TMP" --subreq SR-001 --now "$TS" \
  || fail "archive-subrequirement.py failed to freeze SR-001"

# 2) A fresh, untampered snapshot must validate cleanly (exit 0).
python3 "$VALIDATE" --verify-archive "$TMP" >/dev/null 2>&1 \
  || fail "fresh archive should validate clean (--verify-archive must exit 0)"

# 3) Tamper one byte in the archived snapshot.
TAMPER="$SUB/archive/$TS/spec/spec.md"
[[ -f "$TAMPER" ]] || fail "archived snapshot missing: $TAMPER"
printf '# spec\nTAMPERED content\n' > "$TAMPER"

# 4) Re-verify: the hash mismatch must be detected (exit 1).
if python3 "$VALIDATE" --verify-archive "$TMP" >/dev/null 2>&1; then
  fail "tampered archive must be detected (--verify-archive should exit 1)"
fi

echo "PASS: archive snapshot is immutable under byte tamper."
