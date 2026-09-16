#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
VALIDATOR="$ROOT/scripts/validate-delivery-status.py"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

fail() { echo "[verification-gate.test] $*" >&2; exit 1; }
run_validator() { python3 "$VALIDATOR" "$1/status.json" --req-root "$1" 2>&1; }

REQ="$WORK/current"
SUB="$REQ/sub-requirements/SR-001"
mkdir -p "$SUB"
cat >"$SUB/design.md" <<'EOF'
# Design Contract
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## Scope
One server behavior.
<!-- ai-delivery:behavior-contract:behavior -->
## Behavior
| ID | Given | When | Then |
|---|---|---|---|
| B-001 | request | handled | response |
<!-- ai-delivery:behavior-contract:acceptance -->
## Acceptance
| ID | Outcome | Evidence |
|---|---|---|
| AC-001 | B-001 is observable | focused test |
<!-- ai-delivery:behavior-contract:traceability -->
## Traceability
| Behavior | Requirement | UI | Acceptance |
|---|---|---|---|
| B-001 | REQ-VERIFY | not_applicable | AC-001 |
<!-- ai-delivery:behavior-contract:end -->
<!-- ai-delivery:user-decisions -->
## User decisions
not_applicable
EOF

python3 - "$REQ" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
design = root / "sub-requirements/SR-001/design.md"
status = {
    "_schema": "2.0",
    "requirement_id": "REQ-VERIFY",
    "sub_requirements": {
        "SR-001": {
            "status": "merged",
            "ui_bearing": False,
            "ui_truth_mode": "none",
            "state_flow_required": False,
            "user_decision_required": False,
            "design_review": {
                "review_mode": "self",
                "reviewed_design_sha256": hashlib.sha256(design.read_bytes()).hexdigest(),
                "reviewed_at": "2026-09-16T00:00:00Z",
                "reviewed_by": "fixture-agent",
            },
        }
    },
}
(root / "status.json").write_text(json.dumps(status), encoding="utf-8")
PY

if output=$(run_validator "$REQ"); then
  fail "schema 2.0 merged without verification.md passed: $output"
fi
grep -q 'requires verification.md' <<<"$output" || fail "missing verification gate: $output"

cat >"$SUB/verification.md" <<'EOF'
# Evidencia de verificacion
<!-- ai-delivery-verification:review-rounds -->
- Ronda 1: clean
<!-- ai-delivery-verification:commands-results -->
- `make test` -> correcto
EOF
if output=$(run_validator "$REQ"); then
  fail "verification missing sign-off marker passed: $output"
fi
grep -q 'missing required marker' <<<"$output" || fail "missing marker error: $output"

cat >>"$SUB/verification.md" <<'EOF'
<!-- ai-delivery-verification:sign-off -->
- Revisor: orchestrator
EOF
output=$(run_validator "$REQ") || fail "complete verification failed: $output"

# Historical terminal schema remains read-only compatible without invented evidence.
LEGACY="$WORK/legacy"
mkdir -p "$LEGACY/sub-requirements/SR-001"
cat >"$LEGACY/status.json" <<'EOF'
{
  "_schema": "1.1",
  "sub_requirements": {
    "SR-001": {
      "status": "merged",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "none",
      "design_approved": false
    }
  }
}
EOF
output=$(run_validator "$LEGACY") || fail "legacy terminal record should remain readable: $output"

echo 'PASS: verification gate applies to schema 2.0 and preserves terminal legacy compatibility.'
