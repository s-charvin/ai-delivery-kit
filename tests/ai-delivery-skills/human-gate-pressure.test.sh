#!/usr/bin/env bash
set -euo pipefail

# Pressure scenarios: an agent under delivery pressure must not shortcut the
# human-review gates (CP-DESIGN / CP-001 / visual acceptance) by forging or
# leaving stale state in status.json. Each shortcut attempt is encoded as a
# mechanical rejection by reconcile-delivery.py / validate-delivery-status.py,
# not as agent behavior replay.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

RECONCILE="$ROOT/.agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py"
if [[ -f "$ROOT/managedassets.go" ]]; then
  STATUS_VALIDATOR="$ROOT/scripts/validate-delivery-status.py"
else
  STATUS_VALIDATOR="$ROOT/.ai-delivery/scripts/validate-delivery-status.py"
fi

fail() {
  echo "[human-gate-pressure] $1" >&2
  exit 1
}

[[ -f "$RECONCILE" ]] || fail "Missing reconcile script: $RECONCILE"
[[ -f "$STATUS_VALIDATOR" ]] || fail "Missing status validator: $STATUS_VALIDATOR"

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/human-gate-pressure.XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

new_scenario() {
  local name=$1
  local dir="$TMP_DIR/$name"
  mkdir -p "$dir"
  echo "$dir"
}

reconcile_output() {
  local dir=$1
  python3 - "$dir" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
status_path = root / "status.json"
data = json.loads(status_path.read_text(encoding="utf-8"))
data["_schema"] = "1.1"
for subreq_id, entry in data.get("sub_requirements", {}).items():
    entry.setdefault("state_flow_required", False)
    if entry.get("design_approved") is True:
        design = root / "sub-requirements" / subreq_id / "design.md"
        if design.is_file():
            entry["design_review"] = {
                "review_mode": "human" if entry.get("design_mode") == "full" else "self",
                "reviewed_design_sha256": hashlib.sha256(design.read_bytes()).hexdigest(),
                "reviewed_at": "2026-09-09T00:00:00Z",
                "reviewed_by": "fixture-user",
            }
    else:
        entry["design_review"] = {
            "review_mode": "none",
            "reviewed_design_sha256": None,
            "reviewed_at": None,
            "reviewed_by": None,
        }
status_path.write_text(json.dumps(data), encoding="utf-8")
PY
  python3 "$RECONCILE" "$dir/status.json" --req-root "$dir" 2>/dev/null || true
}

require_line() {
  local scenario=$1
  local output=$2
  local expected=$3
  echo "$output" | grep -Fq "$expected" \
    || fail "$scenario: expected line '$expected' in output:\n$output"
}

refute_line() {
  local scenario=$1
  local output=$2
  local forbidden=$3
  if echo "$output" | grep -Fq "$forbidden"; then
    fail "$scenario: forbidden line '$forbidden' present in output:\n$output"
  fi
}

# Scenario 1: stale CP-001 credential left behind after a regression must not
# authorize implement. SR-001 regressed to spec_ready, SR-002 still tasks_ready.
S1=$(new_scenario "stale-cp001")
mkdir -p "$S1/sub-requirements/SR-001" "$S1/sub-requirements/SR-002"
printf '# Solution Design\n' > "$S1/sub-requirements/SR-001/design.md"
printf '# Solution Design\n' > "$S1/sub-requirements/SR-002/design.md"
cat > "$S1/status.json" <<'EOF'
{
  "requirement_id": "stale-cp001",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": "CP-001",
  "runtime_mode": "confirm_to_dev",
  "sub_requirements": {
    "SR-001": {
      "status": "spec_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": "regressed after contract change"
    },
    "SR-002": {
      "status": "tasks_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    }
  }
}
EOF
OUT1=$(reconcile_output "$S1")
refute_line "stale-cp001" "$OUT1" "RUNTIME_MODE=confirm_to_dev"
refute_line "stale-cp001" "$OUT1" "NEXT_ACTION=implement"
refute_line "stale-cp001" "$OUT1" "CHECKPOINT=CP-001"

# Scenario 2: partial tasks_ready must not raise the CP-001 gate at all.
S2=$(new_scenario "partial-tasks-ready")
mkdir -p "$S2/sub-requirements/SR-001" "$S2/sub-requirements/SR-002"
printf '# Solution Design\n' > "$S2/sub-requirements/SR-001/design.md"
printf '# Solution Design\n' > "$S2/sub-requirements/SR-002/design.md"
cat > "$S2/status.json" <<'EOF'
{
  "requirement_id": "partial-tasks-ready",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "tasks_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    },
    "SR-002": {
      "status": "spec_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    }
  }
}
EOF
OUT2=$(reconcile_output "$S2")
refute_line "partial-tasks-ready" "$OUT2" "CHECKPOINT=CP-001"
refute_line "partial-tasks-ready" "$OUT2" "RUNTIME_MODE=confirm_to_dev"
refute_line "partial-tasks-ready" "$OUT2" "NEXT_ACTION=implement"

# Scenario 3: forged spec_ready without design approval must fall back to design.
S3=$(new_scenario "forged-spec-ready")
cat > "$S3/status.json" <<'EOF'
{
  "requirement_id": "forged-spec-ready",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "spec_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": false,
      "notes": null
    }
  }
}
EOF
OUT3=$(reconcile_output "$S3")
require_line "forged-spec-ready" "$OUT3" "NEXT_ACTION=solution-design"
refute_line "forged-spec-ready" "$OUT3" "NEXT_ACTION=spec"

# Scenario 4: a pending design approval must not block unrelated runnable work;
# CP-DESIGN stays visible as a reminder.
S4=$(new_scenario "design-pending-plus-runnable")
mkdir -p "$S4/sub-requirements/SR-002"
cat > "$S4/sub-requirements/SR-002/design.md" <<'EOF'
# Solution Design

Approved design for the runnable slice.
EOF
cat > "$S4/status.json" <<'EOF'
{
  "requirement_id": "design-pending-plus-runnable",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": false,
      "notes": "light audit passed"
    },
    "SR-002": {
      "status": "spec_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    }
  }
}
EOF
OUT4=$(reconcile_output "$S4")
require_line "design-pending-plus-runnable" "$OUT4" "RUNTIME_MODE=resume"
require_line "design-pending-plus-runnable" "$OUT4" "CHECKPOINT=CP-DESIGN"
require_line "design-pending-plus-runnable" "$OUT4" "NEXT_ACTION=plan"
require_line "design-pending-plus-runnable" "$OUT4" "NEXT_SUBREQ=SR-002"

# Scenario 5: design pending with nothing else runnable pauses at CP-DESIGN.
S5=$(new_scenario "design-pending-only")
cat > "$S5/status.json" <<'EOF'
{
  "requirement_id": "design-pending-only",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": false,
      "notes": "light audit passed"
    }
  }
}
EOF
OUT5=$(reconcile_output "$S5")
require_line "design-pending-only" "$OUT5" "RUNTIME_MODE=confirm_solution_design"
require_line "design-pending-only" "$OUT5" "CHECKPOINT=CP-DESIGN"
require_line "design-pending-only" "$OUT5" "NEXT_ACTION=solution-design"

# Scenario 6: a slice-local blocker must not stop unrelated runnable work.
S6=$(new_scenario "blocked-plus-runnable")
mkdir -p "$S6/sub-requirements/SR-001" "$S6/sub-requirements/SR-002"
printf '# Solution Design\n' > "$S6/sub-requirements/SR-001/design.md"
printf '# Solution Design\n' > "$S6/sub-requirements/SR-002/design.md"
cat > "$S6/status.json" <<'EOF'
{
  "requirement_id": "blocked-plus-runnable",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "blocked_verification_failure",
      "blocker_scope": "slice_local",
      "resume_target_status": "in_dev",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    },
    "SR-002": {
      "status": "spec_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    }
  }
}
EOF
OUT6=$(reconcile_output "$S6")
require_line "blocked-plus-runnable" "$OUT6" "RUNTIME_MODE=resume"
require_line "blocked-plus-runnable" "$OUT6" "RUNNABLE=SR-002:spec_ready->plan"
require_line "blocked-plus-runnable" "$OUT6" "BLOCKER_SCOPES=SR-001:slice_local"
require_line "blocked-plus-runnable" "$OUT6" "NEXT_ACTION=plan"

# Scenario 7: forging visual_acceptance_passed without evidence files must be
# rejected by the status validator gate.
S7=$(new_scenario "forged-visual-acceptance")
cat > "$S7/status.json" <<'EOF'
{
  "requirement_id": "forged-visual-acceptance",
  "updated_at": "2026-08-06T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "visual_acceptance_passed",
      "ui_bearing": true,
      "ui_truth_mode": "figma",
      "design_mode": "full",
      "design_approved": true,
      "notes": null
    }
  }
}
EOF
if VALIDATOR_OUT=$(python3 "$STATUS_VALIDATOR" "$S7/status.json" --req-root "$S7" 2>&1); then
  fail "forged-visual-acceptance: validator accepted a forged visual_acceptance_passed:\n$VALIDATOR_OUT"
fi
echo "$VALIDATOR_OUT" | grep -Fq "visual-acceptance" \
  || fail "forged-visual-acceptance: expected visual-acceptance evidence gate, got:\n$VALIDATOR_OUT"

# Scenario 8: split_ready UI work is production code and must pause for CP-UI
# before ui-truth-mapping can be dispatched.
S8=$(new_scenario "ui-implementation-without-approval")
cat > "$S8/status.json" <<'EOF'
{
  "requirement_id": "ui-implementation-without-approval",
  "updated_at": "2026-08-25T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": true,
      "ui_truth_mode": "figma",
      "design_mode": "full",
      "design_approved": false,
      "notes": "light audit passed"
    }
  }
}
EOF
OUT8=$(reconcile_output "$S8")
require_line "ui-implementation-without-approval" "$OUT8" "RUNTIME_MODE=confirm_ui"
require_line "ui-implementation-without-approval" "$OUT8" "CHECKPOINT=CP-UI"
require_line "ui-implementation-without-approval" "$OUT8" "NEXT_ACTION=none"
refute_line "ui-implementation-without-approval" "$OUT8" "NEXT_ACTION=ui-truth-mapping"

# Scenario 9: an existing frozen surface is UI-bearing but does not need the
# UI truth capability gate. It proceeds to solution design directly.
S9=$(new_scenario "existing-ui-no-cpui")
cat > "$S9/status.json" <<'EOF'
{
  "requirement_id": "existing-ui-no-cpui",
  "updated_at": "2026-08-26T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": true,
      "ui_truth_mode": "existing",
      "design_mode": "light",
      "design_approved": false,
      "notes": "behavior-only change on a frozen component"
    }
  }
}
EOF
OUT9=$(reconcile_output "$S9")
require_line "existing-ui-no-cpui" "$OUT9" "NEXT_ACTION=solution-design"
refute_line "existing-ui-no-cpui" "$OUT9" "CHECKPOINT=CP-UI"

# Scenario 10: design_mode=none is a deliberate no-design path, not a hidden
# no_design_client profile. It proceeds to spec without a design gate.
S10=$(new_scenario "design-mode-none")
cat > "$S10/status.json" <<'EOF'
{
  "requirement_id": "design-mode-none",
  "updated_at": "2026-08-26T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "none",
      "design_approved": false,
      "notes": "small server-only fix"
    }
  }
}
EOF
OUT10=$(reconcile_output "$S10")
require_line "design-mode-none" "$OUT10" "NEXT_ACTION=spec"
refute_line "design-mode-none" "$OUT10" "NEXT_ACTION=solution-design"

# Scenario 11: old bypass fields are rejected rather than selecting a hidden
# compatibility branch.
S11=$(new_scenario "legacy-bypass-fields")
cat > "$S11/status.json" <<'EOF'
{
  "requirement_id": "legacy-bypass-fields",
  "updated_at": "2026-08-26T00:00:00Z",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "split_ready",
      "ui_bearing": true,
      "ui_truth_mode": "existing",
      "design_mode": "light",
      "design_approved": true,
      "ui_contract_exempt": true,
      "notes": "deprecated bypass must fail"
    }
  }
}
EOF
OUT11=$(reconcile_output "$S11")
echo "$OUT11" | grep -Eq "ui_contract_exempt|legacy|unsupported" \
  || fail "legacy bypass was not rejected: $OUT11"

# Scenario 12: a late full-design regression cannot fall through to implement,
# finish, or archive merely because the slice already advanced its status.
S12=$(new_scenario "late-design-regression")
cat > "$S12/status.json" <<'EOF'
{
  "requirement_id": "late-design-regression",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "in_dev",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "full",
      "design_approved": false,
      "notes": "approval was removed after a scope change"
    }
  }
}
EOF
OUT12=$(reconcile_output "$S12")
require_line "late-design-regression" "$OUT12" "RUNTIME_MODE=confirm_solution_design"
require_line "late-design-regression" "$OUT12" "CHECKPOINT=CP-DESIGN"
require_line "late-design-regression" "$OUT12" "NEXT_ACTION=solution-design"
refute_line "late-design-regression" "$OUT12" "NEXT_ACTION=implement"

# Scenario 13: light solution design is an executable prerequisite even when
# the slice is already tasks_ready; CP-001 must not hide that action.
S13=$(new_scenario "light-design-before-dev")
cat > "$S13/status.json" <<'EOF'
{
  "requirement_id": "light-design-before-dev",
  "current_checkpoint": null,
  "runtime_mode": "resume",
  "sub_requirements": {
    "SR-001": {
      "status": "tasks_ready",
      "ui_bearing": false,
      "ui_truth_mode": "none",
      "design_mode": "light",
      "design_approved": false,
      "notes": "short design record has not been generated"
    }
  }
}
EOF
OUT13=$(reconcile_output "$S13")
require_line "light-design-before-dev" "$OUT13" "RUNTIME_MODE=resume"
require_line "light-design-before-dev" "$OUT13" "NEXT_ACTION=solution-design"
refute_line "light-design-before-dev" "$OUT13" "CHECKPOINT=CP-001"

echo 'PASS: human-review gate pressure scenarios rejected as expected.'
