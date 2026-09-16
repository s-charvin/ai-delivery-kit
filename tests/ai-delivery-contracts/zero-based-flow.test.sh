#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
FIXTURE_ROOT="$ROOT/tests/ai-delivery-contracts/fixtures/example-requirement"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/zero-based-flow.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/.ai-delivery/requirements"
cp -R "$FIXTURE_ROOT" "$WORK/.ai-delivery/requirements/example-requirement"

REQ_ROOT="$WORK/.ai-delivery/requirements/example-requirement"
SUBREQ_ROOT="$REQ_ROOT/sub-requirements/SR-001"

fail() {
  print -u2 -- "[zero-based-flow] $1"
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_markdown_meta() {
  grep -Eq '^<!-- ai-delivery-meta:\s*\{.*"version"' "$1" || fail "Missing markdown version metadata: $1"
}

require_json_version() {
  grep -Fq '"version"' "$1" || fail "Missing JSON version metadata: $1"
}

require_contains() {
  local file=$1
  local needle=$2
  grep -Fq -- "$needle" "$file" || fail "Expected '$needle' in $file"
}

require_file "$REQ_ROOT/requirement.md"
require_file "$REQ_ROOT/breakdown-summary.md"
require_file "$REQ_ROOT/global-rules.md"
require_file "$REQ_ROOT/dependency-graph.json"
require_file "$REQ_ROOT/status.json"
require_file "$SUBREQ_ROOT/README.md"
require_file "$SUBREQ_ROOT/requirement-slice.md"
require_file "$SUBREQ_ROOT/dependency.json"
require_file "$SUBREQ_ROOT/traceability.json"
require_file "$SUBREQ_ROOT/decisions.md"
require_file "$SUBREQ_ROOT/api-contract-mapping.md"
require_file "$SUBREQ_ROOT/figma-mapping.md"
require_file "$SUBREQ_ROOT/interaction-design.md"
[[ ! -e "$SUBREQ_ROOT/spec.md" ]] || fail "schema 2.0 must not precreate spec.md"
[[ ! -e "$SUBREQ_ROOT/plan.md" ]] || fail "schema 2.0 must not precreate plan.md"
[[ ! -e "$SUBREQ_ROOT/tasks.md" ]] || fail "schema 2.0 must not precreate tasks.md"

require_markdown_meta "$REQ_ROOT/requirement.md"
require_markdown_meta "$REQ_ROOT/breakdown-summary.md"
require_markdown_meta "$REQ_ROOT/global-rules.md"
require_markdown_meta "$SUBREQ_ROOT/README.md"
require_markdown_meta "$SUBREQ_ROOT/requirement-slice.md"
require_markdown_meta "$SUBREQ_ROOT/decisions.md"
require_markdown_meta "$SUBREQ_ROOT/api-contract-mapping.md"
require_markdown_meta "$SUBREQ_ROOT/figma-mapping.md"
require_markdown_meta "$SUBREQ_ROOT/interaction-design.md"

require_json_version "$REQ_ROOT/dependency-graph.json"
require_json_version "$SUBREQ_ROOT/dependency.json"
require_contains "$REQ_ROOT/status.json" '"_schema": "2.0"'
require_json_version "$SUBREQ_ROOT/traceability.json"

require_contains "$REQ_ROOT/status.json" '"blocked_from_status"'
require_contains "$REQ_ROOT/status.json" '"resume_target_status"'
require_contains "$REQ_ROOT/status.json" '"ui_truth_mode"'
require_contains "$REQ_ROOT/status.json" '"state_flow_required"'
require_contains "$REQ_ROOT/status.json" '"user_decision_required"'
require_contains "$REQ_ROOT/status.json" '"design_review"'
require_contains "$SUBREQ_ROOT/traceability.json" '"api_contract_mapping"'
require_contains "$SUBREQ_ROOT/traceability.json" '"source_index"'
require_contains "$SUBREQ_ROOT/traceability.json" '"design": []'
if grep -Eq '"spec_refs"|"design_mode"|"design_approved"' "$REQ_ROOT/status.json" "$SUBREQ_ROOT/traceability.json"; then
  fail "removed schema fields leaked into the Stage 1 fixture"
fi

node - "$SUBREQ_ROOT/traceability.json" <<'NODE'
const fs = require('node:fs')
const filePath = process.argv[2]
const data = JSON.parse(fs.readFileSync(filePath, 'utf8'))
const status = data.api_contract_mapping?.status
const allowed = new Set(['missing_nonblocking', 'pending', 'mapped', 'needs_revalidation'])

if (!allowed.has(status)) {
  throw new Error(`Unexpected api_contract_mapping.status in ${filePath}: ${status}`)
}
NODE

print -- "PASS: zero-based schema 2.0 Stage 1 fixture is present and bridgeable."
