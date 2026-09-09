#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
ARCHIVE="$ROOT/scripts/archive-subrequirement.py"
DEFAULT_TEMPLATE="$ROOT/.agents/skills/ai-delivery-orchestrator/templates/delivery-report-template.md"

fail() {
  echo "[delivery-report-language.test] $1" >&2
  exit 1
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

REQ="$TMP/.ai-delivery/requirements/report-language"
SUB="$REQ/sub-requirements/SR-001"
mkdir -p "$SUB/spec"
printf '# spec\n' > "$SUB/spec/spec.md"
printf '# plan\n' > "$SUB/spec/plan.md"
printf '# tasks\n' > "$SUB/spec/tasks.md"
printf '# verification\n' > "$SUB/verification.md"
mkdir -p "$TMP/.ai-delivery/meta"
printf '{"layout": {}}\n' > "$TMP/.ai-delivery/meta/project-binding.json"
cat > "$REQ/retrospective.md" <<'EOF'
<!-- ai-delivery-retrospective:reviewed-at:2026-08-25 -->
EOF

cat > "$REQ/status.json" <<'JSON'
{
  "requirement_id": "report-language",
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
JSON

if python3 "$ARCHIVE" \
  --req-root "$REQ" \
  --subreq SR-001 \
  --now "2026-08-25T00:00:00+00:00" \
  --delivery-report-template "$DEFAULT_TEMPLATE" \
  >"$TMP/default.out" 2>"$TMP/default.err"; then
  fail "the unlocalized default template must be rejected"
fi
grep -Fq 'still contains its language instruction' "$TMP/default.err" \
  || fail "missing language-instruction rejection"
grep -Fq '"status": "merged"' "$REQ/status.json" \
  || fail "failed preflight must not advance status"
[[ ! -e "$SUB/archive" ]] || fail "failed preflight must not create an archive"

cat > "$TMP/report-template.md" <<'TEMPLATE'
# Informe de entrega - <req-id>

- Archivado: <archived_at>
- Cantidad: <subreq_count>

## Subrequisitos

| ID | Estado | Archivo | Verificacion |
|----|--------|---------|--------------|
<subreq_rows>
TEMPLATE

python3 "$ARCHIVE" \
  --req-root "$REQ" \
  --subreq SR-001 \
  --now "2026-08-25T00:00:00+00:00" \
  --delivery-report-template "$TMP/report-template.md" \
  >"$TMP/localized.out" 2>"$TMP/localized.err" \
  || fail "localized delivery report template should archive successfully"

REPORT="$REQ/delivery-report.md"
[[ -f "$REPORT" ]] || fail "localized delivery report was not generated"
grep -Fq '# Informe de entrega - report-language' "$REPORT" \
  || fail "localized report heading was not preserved"
grep -Fq 'sub-requirements/SR-001/verification.md' "$REPORT" \
  || fail "verification cell should use a language-neutral path"
grep -Fq 'sub-requirements/SR-001/' "$REPORT" \
  || fail "report should reference canonical artifacts in place"
[[ ! -e "$REQ/sub-requirements/SR-001/archive" ]] \
  || fail "delivery report generation must not create an archive copy"
if grep -Fq 'ai-delivery-template-language' "$REPORT"; then
  fail "finished report contains a template language instruction"
fi
if grep -Fq 'Delivery Report' "$REPORT"; then
  fail "finished report leaked English default prose"
fi

echo "PASS: final archive requires and preserves a pre-localized delivery report template."
