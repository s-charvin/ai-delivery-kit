#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
REQ_ROOT="$ROOT/.ai-delivery/requirements/example-requirement"
SUBREQ_ROOT="$REQ_ROOT/sub-requirements/SR-001"
SPEC_ROOT="$ROOT/.specify/fixtures/example-sr-001"

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
require_file "$SUBREQ_ROOT/README.md"
require_file "$SUBREQ_ROOT/requirement-slice.md"
require_file "$SUBREQ_ROOT/dependency.json"
require_file "$SUBREQ_ROOT/status.json"
require_file "$SUBREQ_ROOT/traceability.json"
require_file "$SUBREQ_ROOT/decisions.md"
require_file "$SUBREQ_ROOT/api-contract-mapping.md"
require_file "$SUBREQ_ROOT/figma-mapping.md"
require_file "$SUBREQ_ROOT/interaction-design.md"
require_file "$SPEC_ROOT/spec.md"
require_file "$SPEC_ROOT/plan.md"
require_file "$SPEC_ROOT/tasks.md"

require_markdown_meta "$REQ_ROOT/requirement.md"
require_markdown_meta "$REQ_ROOT/breakdown-summary.md"
require_markdown_meta "$REQ_ROOT/global-rules.md"
require_markdown_meta "$SUBREQ_ROOT/README.md"
require_markdown_meta "$SUBREQ_ROOT/requirement-slice.md"
require_markdown_meta "$SUBREQ_ROOT/decisions.md"
require_markdown_meta "$SUBREQ_ROOT/api-contract-mapping.md"
require_markdown_meta "$SUBREQ_ROOT/figma-mapping.md"
require_markdown_meta "$SUBREQ_ROOT/interaction-design.md"
require_markdown_meta "$SPEC_ROOT/spec.md"
require_markdown_meta "$SPEC_ROOT/plan.md"
require_markdown_meta "$SPEC_ROOT/tasks.md"

require_json_version "$REQ_ROOT/dependency-graph.json"
require_json_version "$SUBREQ_ROOT/dependency.json"
require_json_version "$SUBREQ_ROOT/status.json"
require_json_version "$SUBREQ_ROOT/traceability.json"

require_contains "$SUBREQ_ROOT/status.json" '"blocked_from_status"'
require_contains "$SUBREQ_ROOT/status.json" '"resume_target_status"'
require_contains "$SUBREQ_ROOT/traceability.json" '"spec_kit_refs"'
require_contains "$SUBREQ_ROOT/traceability.json" '"api_contract_mapping"'
require_contains "$SUBREQ_ROOT/traceability.json" '"status": "mapped"'
require_contains "$SUBREQ_ROOT/traceability.json" '".specify/fixtures/example-sr-001/spec.md"'
require_contains "$SUBREQ_ROOT/traceability.json" '".specify/fixtures/example-sr-001/plan.md"'
require_contains "$SUBREQ_ROOT/traceability.json" '".specify/fixtures/example-sr-001/tasks.md"'

print -- "PASS: zero-based full-chain fixture is present and bridgeable."
