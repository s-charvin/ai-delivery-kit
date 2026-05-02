#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

if [[ -d "$ROOT/.agents/skills/ai-delivery" ]]; then
  SKILL_ROOT="$ROOT/.agents/skills/ai-delivery"
  VALIDATE_SCRIPT="$ROOT/scripts/validate-project-ai-delivery-skills.sh"
else
  SKILL_ROOT="$ROOT/.agents/skills"
  VALIDATE_SCRIPT="$ROOT/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
fi

fail() {
  print -u2 -- "[ui-composition-guardrails-test] $1"
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_contains() {
  local file=$1
  local needle=$2

  if ! grep -Fq -- "$needle" "$file"; then
    fail "Expected '$needle' in $file"
  fi
}

REQ_SKILL="$SKILL_ROOT/requirement-breakdown/SKILL.md"
REQ_TEMPLATE="$SKILL_ROOT/requirement-breakdown/templates/requirement-slice-template.md"
MAP_SKILL="$SKILL_ROOT/ui-requirement-mapping/SKILL.md"
MAP_TEMPLATE="$SKILL_ROOT/ui-requirement-mapping/templates/figma-mapping-template.md"
ACCEPT_SKILL="$SKILL_ROOT/ui-acceptance-contract/SKILL.md"
ACCEPT_TEMPLATE="$SKILL_ROOT/ui-acceptance-contract/templates/ui-acceptance-contract-template.yaml"

require_file "$REQ_SKILL"
require_file "$REQ_TEMPLATE"
require_file "$MAP_SKILL"
require_file "$MAP_TEMPLATE"
require_file "$ACCEPT_SKILL"
require_file "$ACCEPT_TEMPLATE"
require_file "$VALIDATE_SCRIPT"

# Scenario 1: route-level SECTION plus owned child carrier must preserve shell composition truth.
require_contains "$REQ_SKILL" 'owns_route_shell'
require_contains "$REQ_SKILL" 'parent_shell_subreq_id'
require_contains "$REQ_SKILL" 'composes_with_subreq_ids'
require_contains "$REQ_SKILL" 'mount_region_desc'
require_contains "$REQ_SKILL" 'full_page_context_required'
require_contains "$REQ_TEMPLATE" 'owns_route_shell'
require_contains "$REQ_TEMPLATE" 'parent_shell_subreq_id'
require_contains "$REQ_TEMPLATE" 'composes_with_subreq_ids'
require_contains "$REQ_TEMPLATE" 'mount_region_desc'
require_contains "$REQ_TEMPLATE" 'full_page_context_required'

require_contains "$MAP_SKILL" 'raw_payload_summary is supplemental only'
require_contains "$MAP_SKILL" 'route-level carrier'
require_contains "$MAP_SKILL" 'owned sub-carrier composition'
require_contains "$MAP_SKILL" 'parent shell artifact refs and composition context are required'
require_contains "$MAP_TEMPLATE" 'composition_context'
require_contains "$MAP_TEMPLATE" 'route_shell_subreq_id'
require_contains "$MAP_TEMPLATE" 'route_shell_contract_ref'
require_contains "$MAP_TEMPLATE" 'mount_node_id'
require_contains "$MAP_TEMPLATE" 'owned_subtree_root_node_id'
require_contains "$MAP_TEMPLATE" 'inherited_regions'

require_contains "$ACCEPT_SKILL" 'parent_shell_contract_ref'
require_contains "$ACCEPT_SKILL" 'mount_path'
require_contains "$ACCEPT_SKILL" 'composed_screen_context'
require_contains "$ACCEPT_SKILL" 'governed by SR-xxx'
require_contains "$ACCEPT_TEMPLATE" 'parent_shell_contract_ref'
require_contains "$ACCEPT_TEMPLATE" 'mount_path'
require_contains "$ACCEPT_TEMPLATE" 'composed_screen_context'

# Scenario 2: carrier with multiple visible blocks must produce a non-empty component tree.
require_contains "$ACCEPT_SKILL" 'children: [] is forbidden'
require_contains "$ACCEPT_SKILL" '2+ visible blocks/lanes/clusters/rows'
require_contains "$ACCEPT_SKILL" 'If visible text exists, typography cannot be empty'
require_contains "$ACCEPT_SKILL" 'If visible icon/image exists, icon/image cannot be empty'
require_contains "$VALIDATE_SCRIPT" 'raw_payload_summary'
require_contains "$VALIDATE_SCRIPT" 'children: []'
require_contains "$VALIDATE_SCRIPT" 'parent_shell_contract_ref'
require_contains "$VALIDATE_SCRIPT" 'typography: {}'
require_contains "$VALIDATE_SCRIPT" 'icon: {}'

print -- "PASS: composition guardrails are documented and validated across breakdown, mapping, and acceptance."
