#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
SKILL_ROOT="$ROOT/.codex/skills/ai-delivery"
COMMON_ROOT="$SKILL_ROOT/common"

fail() {
  print -u2 -- "[validate-project-ai-delivery-skills] $1"
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Missing file: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "Missing directory: $1"
}

require_contains() {
  local file=$1
  local needle=$2
  grep -Fq -- "$needle" "$file" || fail "Expected '$needle' in $file"
}

require_not_contains() {
  local file=$1
  local needle=$2
  if grep -Fq -- "$needle" "$file"; then
    fail "Unexpected '$needle' in $file"
  fi
}

require_frontmatter_skill() {
  local file=$1
  local expected_name=$2

  require_contains "$file" '---'
  [[ "$(head -n 1 "$file")" == '---' ]] || fail "Expected YAML frontmatter at top of $file"
  require_contains "$file" "name: $expected_name"
  require_contains "$file" 'description: Use when'
}

validate_openai_yaml() {
  local skill_name=$1
  local yaml_file="$SKILL_ROOT/$skill_name/agents/openai.yaml"
  local short_description

  require_file "$yaml_file"
  require_contains "$yaml_file" 'interface:'
  require_contains "$yaml_file" 'display_name:'
  require_contains "$yaml_file" 'short_description:'
  require_contains "$yaml_file" 'default_prompt:'
  require_contains "$yaml_file" "\$$skill_name"

  short_description=$(sed -n 's/^  short_description: "\(.*\)"$/\1/p' "$yaml_file")
  [[ -n "$short_description" ]] || fail "Missing parsed short_description in $yaml_file"
  local length=${#short_description}
  (( length >= 25 && length <= 64 )) || fail "short_description length must be 25-64 in $yaml_file (got $length)"
}

validate_markdown_links() {
  local file=$1
  local links
  links=$(perl -ne 'while (/\[[^\]]*\]\(([^)]+)\)/g) { print "$1\n" }' "$file")

  if [[ -z "$links" ]]; then
    return
  fi

  while IFS= read -r link; do
    [[ -z "$link" ]] && continue
    [[ "$link" == http* ]] && continue
    [[ "$link" == mailto:* ]] && continue
    [[ "$link" == '#'* ]] && continue

    if [[ "$link" == /* ]]; then
      [[ -e "$link" ]] || fail "Broken absolute link '$link' in $file"
    else
      (cd "$(dirname "$file")" && [[ -e "$link" ]]) || fail "Broken relative link '$link' in $file"
    fi
  done <<< "$links"
}

validate_common_contract() {
  require_dir "$SKILL_ROOT/requirement-breakdown"
  require_dir "$SKILL_ROOT/ui-requirement-mapping"
  require_dir "$SKILL_ROOT/ui-interaction-design"

  require_file "$COMMON_ROOT/README.md"
  require_file "$COMMON_ROOT/references/dual-truth-rules.md"
  require_file "$COMMON_ROOT/references/blocker-catalog.md"
  require_file "$COMMON_ROOT/references/logging-checklist.md"
  require_file "$COMMON_ROOT/templates/requirement-slice-template.md"
  require_file "$COMMON_ROOT/templates/figma-mapping-template.md"
  require_file "$COMMON_ROOT/templates/interaction-design-template.md"

  require_contains "$COMMON_ROOT/README.md" 'business-project assets'
  require_contains "$COMMON_ROOT/README.md" '.ai-delivery'
  require_contains "$COMMON_ROOT/README.md" 'not owned by `ai-delivery-admin`'
  require_contains "$COMMON_ROOT/README.md" 'admin support surfaces'
}

validate_generic_skill() {
  local skill_name=$1
  local skill_file="$SKILL_ROOT/$skill_name/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    return 0
  fi

  require_frontmatter_skill "$skill_file" "$skill_name"
  validate_openai_yaml "$skill_name"
  validate_markdown_links "$skill_file"
  require_contains "$skill_file" '.ai-delivery'
  require_contains "$skill_file" 'admin support'
  require_contains "$skill_file" 'governed'
  require_not_contains "$skill_file" 'owned by ai-delivery-admin'
  require_not_contains "$skill_file" 'move workflow truth into ai-delivery-admin'
}

validate_requirement_breakdown_skill() {
  local skill_file="$SKILL_ROOT/requirement-breakdown/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    return 0
  fi

  require_contains "$skill_file" 'top-level requirement material'
  require_contains "$skill_file" 'breakdown-summary.md'
  require_contains "$skill_file" 'global-rules.md'
  require_contains "$skill_file" 'dependency-graph.json'
  require_contains "$skill_file" 'requirement-slice.md'
  require_contains "$skill_file" 'split_ready'
  require_contains "$skill_file" 'blocked_requirement_conflict'
  require_contains "$skill_file" 'blocked_missing_requirement'
  require_contains "$skill_file" 'Do not invent product truth'
}

validate_ui_requirement_mapping_skill() {
  local skill_file="$SKILL_ROOT/ui-requirement-mapping/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    return 0
  fi

  require_contains "$skill_file" 'requirement-slice.md'
  require_contains "$skill_file" 'Figma retrieval order'
  require_contains "$skill_file" 'structured node'
  require_contains "$skill_file" 'figma-mapping.md'
  require_contains "$skill_file" 'traceability.json'
  require_contains "$skill_file" 'figma-cache/'
  require_contains "$skill_file" 'split_ready'
  require_contains "$skill_file" 'blocked_from_status'
  require_contains "$skill_file" 'resume_target_status'
  require_contains "$skill_file" 'spec_kit_refs'
  require_contains "$skill_file" 'blocked_missing_design'
  require_contains "$skill_file" 'blocked_requirement_figma_conflict'
  require_contains "$skill_file" 'companion UI'
  require_contains "$skill_file" 'shared nodes'
}

validate_ui_interaction_design_skill() {
  local skill_file="$SKILL_ROOT/ui-interaction-design/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    return 0
  fi

  require_contains "$skill_file" 'requirement-slice.md'
  require_contains "$skill_file" 'figma-mapping.md'
  require_contains "$skill_file" 'interaction-design.md'
  require_contains "$skill_file" 'traceability.json'
  require_contains "$skill_file" 'figma_mapped'
  require_contains "$skill_file" 'interaction_ready'
  require_contains "$skill_file" 'blocked_from_status'
  require_contains "$skill_file" 'resume_target_status'
  require_contains "$skill_file" 'Source: Requirement'
  require_contains "$skill_file" 'assumed_micro_interaction'
  require_contains "$skill_file" 'blocked_missing_design'
  require_contains "$skill_file" 'blocked_requirement_figma_conflict'
  require_contains "$skill_file" 'blocked_missing_requirement'
  require_contains "$skill_file" 'Do not invent business flow or page structure'
}

validate_common_contract
validate_generic_skill requirement-breakdown
validate_generic_skill ui-requirement-mapping
validate_generic_skill ui-interaction-design
validate_requirement_breakdown_skill
validate_ui_requirement_mapping_skill
validate_ui_interaction_design_skill

print -- 'PASS: project-local ai-delivery skill sources are structurally valid.'
