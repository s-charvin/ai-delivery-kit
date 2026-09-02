#!/bin/bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
ARCHIVE="$ROOT/scripts/archive-subrequirement.py"
LAYOUT="$ROOT/.agents/skills/ai-delivery-orchestrator/scripts/layout.py"

fail() {
  echo "[retrospective-feature.test] $1" >&2
  exit 1
}

[[ -f "$ARCHIVE" ]] || fail "missing archive script"
[[ -f "$LAYOUT" ]] || fail "missing layout resolver"
for rel in \
  .agents/skills/ai-delivery-orchestrator/SKILL.md \
  .agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md \
  .agents/skills/ai-delivery-orchestrator/references/retrospective-guidance.md \
  .agents-zh/skills/ai-delivery-orchestrator/references/retrospective-guidance.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md \
  .agents-zh/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md
do
  [[ -f "$ROOT/$rel" ]] || fail "missing $rel"
done
grep -Fq 'only matching historical problem sections' "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md" \
  || fail "English skill is missing progressive loading rule"
if ! python3 - "$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md" <<'PY'
import pathlib
import sys

needle = "".join(chr(int(code, 16)) for code in "53ea 52a0 8f7d 5339 914d 7684 5386 53f2 95ee 9898 7ae0 8282".split())
if needle not in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"):
    raise SystemExit(1)
PY
then
  fail "Chinese skill is missing progressive loading rule"
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

REQ="$TMP/.ai-delivery/requirements/req-generic"
SUB="$REQ/sub-requirements/SR-001"
mkdir -p "$SUB/spec"

printf '# spec\n' > "$SUB/spec/spec.md"
printf '# plan\n' > "$SUB/spec/plan.md"
printf '# tasks\n' > "$SUB/spec/tasks.md"
printf '# verification\n' > "$SUB/verification.md"
cat > "$REQ/retrospective.md" <<'EOF'
# Retrospective

<!-- ai-delivery-retrospective:problem-index:v1 -->
| ID | Observable trigger | Applicable scenario | Shortest path | Status | Details |
| --- | --- | --- | --- | --- | --- |
| RET-001 | State resets after returning to the flow | Resumed state with asynchronous restoration | Reproduce with restoration delayed, then separate persisted and live state | resolved | [RET-001](#ret-001) |
<!-- /ai-delivery-retrospective:problem-index:v1 -->

## RET-001: State restoration overwrites live input

Details.
EOF
sed '/^<!-- ai-delivery-template-language$/,/^-->/d' \
  "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md" \
  > "$TMP/index-template.md"

# Invalid index-template input must fail before freezing or changing status.
PRE_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP" "$PRE_ROOT"' EXIT
PRE_REQ="$PRE_ROOT/.ai-delivery/requirements/req-preflight"
PRE_SUB="$PRE_REQ/sub-requirements/SR-001"
mkdir -p "$PRE_SUB/spec"
printf '# spec\n' > "$PRE_SUB/spec/spec.md"
printf '# plan\n' > "$PRE_SUB/spec/plan.md"
printf '# tasks\n' > "$PRE_SUB/spec/tasks.md"
printf '# verification\n' > "$PRE_SUB/verification.md"
cp "$REQ/retrospective.md" "$PRE_REQ/retrospective.md"
cat > "$PRE_REQ/status.json" <<'EOF'
{
  "requirement_id": "req-preflight",
  "sub_requirements": {"SR-001": {"status": "merged"}}
}
EOF
if python3 "$ARCHIVE" --req-root "$PRE_REQ" --subreq SR-001 \
  --now "2026-09-02T00:00:00+00:00" --no-delivery-report \
  --retrospective-index-template "$ROOT/.agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md" \
  >"$PRE_ROOT/out" 2>"$PRE_ROOT/err"; then
  fail "unlocalized index template must be rejected"
fi
grep -Fq 'still contains its language instruction' "$PRE_ROOT/err" \
  || fail "missing index-template language rejection"
grep -Fq '"status": "merged"' "$PRE_REQ/status.json" \
  || fail "index-template preflight changed status"
[[ ! -e "$PRE_SUB/archive" ]] || fail "index-template preflight created an archive"

cat > "$REQ/status.json" <<'EOF'
{
  "requirement_id": "req-generic",
  "sub_requirements": {
    "SR-001": {"status": "merged"}
  }
}
EOF

python3 "$ARCHIVE" --req-root "$REQ" --subreq SR-001 --now "2026-09-02T00:00:00+00:00" --no-delivery-report \
  --retrospective-index-template "$TMP/index-template.md" \
  || fail "archive command failed"

INDEX="$TMP/.ai-delivery/retrospectives/index.md"
[[ -f "$INDEX" ]] || fail "retrospective index was not created"
grep -Fq '| req-generic/RET-001 |' "$INDEX" || fail "problem entry missing from index"
grep -Fq 'State resets after returning to the flow' "$INDEX" || fail "trigger missing from index"
grep -Fq 'Reproduce with restoration delayed' "$INDEX" || fail "shortest path missing from index"
grep -Fq '../requirements/req-generic/retrospective.md#ret-001' "$INDEX" || fail "details link missing from index"

# Existing rows belonging to another archived requirement must survive an update.
python3 - "$INDEX" <<'PY'
import pathlib
import sys

index = pathlib.Path(sys.argv[1])
marker = "<!-- /ai-delivery-retrospective:index:v1 -->"
text = index.read_text(encoding="utf-8")
text = text.replace(
    marker,
    "| req-other/RET-009 | Other trigger | Other scenario | Other path | resolved | "
    "2026-08-01T00:00:00+00:00 | [req-other/RET-009](../requirements/req-other/retrospective.md#ret-009) |\n"
    + marker,
)
index.write_text(text, encoding="utf-8")
PY

# A second registration must replace the requirement's rows, not duplicate them.
python3 - "$ARCHIVE" "$REQ" <<'PY'
import importlib.util
import pathlib
import sys

archive_path = pathlib.Path(sys.argv[1])
req_root = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("archive_subrequirement", archive_path)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
archive.register_retrospective_index(
    req_root,
    "req-generic",
    archive.datetime.datetime.fromisoformat("2026-09-02T00:00:01+00:00"),
    None,
)
PY
[[ $(grep -c '^| req-generic/RET-001 |' "$INDEX") -eq 1 ]] \
  || fail "index registration is not idempotent"
[[ $(grep -c '^| req-other/RET-009 |' "$INDEX") -eq 1 ]] \
  || fail "index update removed another requirement's problem row"

# A multi-level custom ai_delivery_path must resolve project-level artifacts
# from the binding's repository root, not from a parent inferred by depth.
CUSTOM_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP" "$PRE_ROOT" "${NO_ROOT:-}" "$CUSTOM_ROOT"' EXIT
CUSTOM_AD="$CUSTOM_ROOT/config/governed"
CUSTOM_REQ="$CUSTOM_AD/requirements/req-custom"
CUSTOM_SUB="$CUSTOM_REQ/sub-requirements/SR-001"
mkdir -p "$CUSTOM_AD/meta" "$CUSTOM_SUB/spec" "$CUSTOM_REQ/knowledge"
cat > "$CUSTOM_AD/meta/project-binding.json" <<'EOF'
{
  "ai_delivery_path": "config/governed",
  "layout": {
    "project_artifacts": {"retrospective_index": "retrospectives/index.md"},
    "requirement_artifacts": {
      "retrospective": "requirements/{req_id}/knowledge/retrospective.md"
    }
  }
}
EOF
printf '# spec\n' > "$CUSTOM_SUB/spec/spec.md"
printf '# plan\n' > "$CUSTOM_SUB/spec/plan.md"
printf '# tasks\n' > "$CUSTOM_SUB/spec/tasks.md"
printf '# verification\n' > "$CUSTOM_SUB/verification.md"
sed 's/req-generic/req-custom/g' "$REQ/retrospective.md" > "$CUSTOM_REQ/knowledge/retrospective.md"
cat > "$CUSTOM_REQ/status.json" <<'EOF'
{
  "requirement_id": "req-custom",
  "sub_requirements": {"SR-001": {"status": "merged"}}
}
EOF
python3 "$ARCHIVE" --req-root "$CUSTOM_REQ" --subreq SR-001 --now "2026-09-02T00:00:00+00:00" --no-delivery-report \
  --retrospective-index-template "$TMP/index-template.md" \
  || fail "custom ai_delivery_path archive command failed"
[[ -f "$CUSTOM_AD/retrospectives/index.md" ]] || fail "custom project index was not created"
[[ ! -e "$CUSTOM_ROOT/config/retrospectives/index.md" ]] || fail "custom index used the wrong repository root"
grep -Fq '../requirements/req-custom/knowledge/retrospective.md#ret-001' \
  "$CUSTOM_AD/retrospectives/index.md" || fail "custom ledger link is incorrect"

# A requirement without a ledger keeps the optional feature absent.
NO_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP" "$PRE_ROOT" "$NO_ROOT"' EXIT
NO_RET="$NO_ROOT/.ai-delivery/requirements/req-without-retrospective"
NO_SUB="$NO_RET/sub-requirements/SR-001"
mkdir -p "$NO_SUB/spec"
printf '# spec\n' > "$NO_SUB/spec/spec.md"
printf '# plan\n' > "$NO_SUB/spec/plan.md"
printf '# tasks\n' > "$NO_SUB/spec/tasks.md"
printf '# verification\n' > "$NO_SUB/verification.md"
cat > "$NO_RET/status.json" <<'EOF'
{
  "requirement_id": "req-without-retrospective",
  "sub_requirements": {"SR-001": {"status": "merged"}}
}
EOF
python3 "$ARCHIVE" --req-root "$NO_RET" --subreq SR-001 --now "2026-09-02T00:00:00+00:00" --no-delivery-report \
  >/dev/null
[[ ! -e "$NO_ROOT/.ai-delivery/retrospectives/index.md" ]] || fail "optional ledger created an index"

python3 - "$LAYOUT" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("layout", sys.argv[1])
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
root = pathlib.Path("/tmp/retrospective-layout-test")
assert layout.artifact_path(root, "retrospective", "req-x").name == "retrospective.md"
assert layout.artifact_path(root, "retrospective_index").name == "index.md"
PY

echo "PASS: retrospective ledger and progressive index behavior"
