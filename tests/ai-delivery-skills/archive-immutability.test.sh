#!/bin/bash
# Archive behavior gate: archiving updates status in place and never creates a
# second copy of canonical requirement artifacts.
set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
ARCHIVE="$ROOT/scripts/archive-subrequirement.py"

fail() {
  echo "[archive-immutability.test] $1" >&2
  exit 1
}

[[ -f "$ARCHIVE" ]] || fail "Missing archive script: $ARCHIVE"

# Isolated requirement root in a temp dir; removed on exit.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

REQ="$TMP/.ai-delivery/requirements/archive-immutability"
SUB="$REQ/sub-requirements/SR-001"
mkdir -p "$SUB/spec"

printf '# spec\nfrozen content\n' > "$SUB/spec/spec.md"
printf '# plan\n' > "$SUB/spec/plan.md"
printf '# tasks\n' > "$SUB/spec/tasks.md"
printf '# design\n' > "$SUB/design.md"
printf '# verification\n\n<!-- ai-delivery-verification:review-rounds -->\n## Review Rounds\n\n- Round 1: approved.\n\n<!-- ai-delivery-verification:commands-results -->\n## Verification Commands and Results\n\n- echo ok -> ok\n\n<!-- ai-delivery-verification:sign-off -->\n## Sign-off\n\n- reviewer: signed\n' > "$SUB/verification.md"

mkdir -p "$TMP/.ai-delivery/meta"
printf '{"layout": {}}\n' > "$TMP/.ai-delivery/meta/project-binding.json"
cat > "$REQ/retrospective.md" <<'EOF'
<!-- ai-delivery-retrospective:reviewed-at:2026-07-10 -->
EOF

cat > "$REQ/status.json" <<'JSON'
{
  "requirement_id": "archive-immutability",
  "updated_at": "2026-07-10T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "merged",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "light",
      "design_approved": true
    }
  }
}
JSON

NOW="2026-07-10T00:00:00+00:00"
TS="2026-07-10T000000Z"

# 1) Archive the merged sub-req in place.
python3 "$ARCHIVE" --req-root "$REQ" --subreq SR-001 --now "$NOW" --no-delivery-report \
  || fail "archive-subrequirement.py failed to archive SR-001"

grep -Fq '"status": "archived"' "$REQ/status.json" \
  || fail "archive did not update status in place"
[[ ! -d "$SUB/archive" ]] || fail "archive created a duplicate artifact directory"
[[ -f "$SUB/spec/spec.md" ]] || fail "canonical spec was moved or removed"
[[ -f "$SUB/spec/plan.md" ]] || fail "canonical plan was moved or removed"
[[ -f "$SUB/spec/tasks.md" ]] || fail "canonical tasks were moved or removed"
[[ -f "$SUB/design.md" ]] || fail "canonical design was moved or removed"
[[ -f "$SUB/verification.md" ]] || fail "canonical verification was moved or removed"

echo "PASS: archive updates status in place without duplicate artifacts."
