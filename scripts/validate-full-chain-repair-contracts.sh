#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
REQ_ROOT="$ROOT/.ai-delivery/requirements/example-requirement"
SUBREQ_ROOT="$REQ_ROOT/sub-requirements/SR-001"

fail() {
  print -u2 -- "[validate-full-chain-repair-contracts] $1"
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_markdown_meta() {
  grep -Eq '^<!-- ai-delivery-meta:\s*\{.*"version"' "$1" || fail "Missing markdown version metadata: $1"
}

validate_json_version() {
  node - "$1" <<'NODE'
const fs = require('node:fs')
const filePath = process.argv[2]
const data = JSON.parse(fs.readFileSync(filePath, 'utf8'))

if (typeof data.version !== 'number') {
  throw new Error(`Missing numeric version in ${filePath}`)
}
NODE
}

validate_status() {
  node - "$1" <<'NODE'
const fs = require('node:fs')
const filePath = process.argv[2]
const data = JSON.parse(fs.readFileSync(filePath, 'utf8'))

for (const key of ['blocked_from_status', 'resume_target_status']) {
  if (!(key in data)) {
    throw new Error(`Missing ${key} in ${filePath}`)
  }
}
NODE
}

validate_traceability() {
  node - "$1" <<'NODE'
const fs = require('node:fs')
const path = require('node:path')
const filePath = process.argv[2]
const data = JSON.parse(fs.readFileSync(filePath, 'utf8'))

if (!data.spec_kit_refs || typeof data.spec_kit_refs !== 'object') {
  throw new Error(`Missing spec_kit_refs in ${filePath}`)
}

for (const key of ['spec_path', 'plan_path', 'tasks_path']) {
  const value = data.spec_kit_refs[key]
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`Missing ${key} in ${filePath}`)
  }

  const normalized = path.posix.normalize(value)
  if (!normalized.startsWith('.specify/')) {
    throw new Error(`${key} escapes .specify/: ${value}`)
  }
}
NODE
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
require_file "$SUBREQ_ROOT/figma-mapping.md"
require_file "$SUBREQ_ROOT/interaction-design.md"

require_markdown_meta "$REQ_ROOT/requirement.md"
require_markdown_meta "$REQ_ROOT/breakdown-summary.md"
require_markdown_meta "$REQ_ROOT/global-rules.md"
require_markdown_meta "$SUBREQ_ROOT/README.md"
require_markdown_meta "$SUBREQ_ROOT/requirement-slice.md"
require_markdown_meta "$SUBREQ_ROOT/decisions.md"
require_markdown_meta "$SUBREQ_ROOT/figma-mapping.md"
require_markdown_meta "$SUBREQ_ROOT/interaction-design.md"

validate_json_version "$REQ_ROOT/dependency-graph.json"
validate_json_version "$SUBREQ_ROOT/dependency.json"
validate_json_version "$SUBREQ_ROOT/status.json"
validate_json_version "$SUBREQ_ROOT/traceability.json"
validate_status "$SUBREQ_ROOT/status.json"
validate_traceability "$SUBREQ_ROOT/traceability.json"

print -- "PASS: full-chain repair contracts are valid."
