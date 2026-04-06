#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=""
SKILL_ROOT=""
SKILL_LAYOUT=""

fail() {
  print -u2 -- "[validate-project-ai-delivery-skills] $1"
  exit 1
}

resolve_repo_root() {
  local candidate

  for candidate in "$SCRIPT_DIR/.." "$SCRIPT_DIR/../.."; do
    candidate=$(cd -- "$candidate" 2>/dev/null && pwd -P) || continue
    if [[ -d "$candidate/.agents/skills/requirement-breakdown" || -d "$candidate/.agents/skills/ai-delivery/requirement-breakdown" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  done

  if candidate=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
    if [[ -d "$candidate/.agents/skills/requirement-breakdown" || -d "$candidate/.agents/skills/ai-delivery/requirement-breakdown" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  fi

  fail "Unable to resolve repository root from $SCRIPT_DIR"
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

resolve_managed_asset_path() {
  local relative_path=$1
  local candidate=""

  case "$SKILL_LAYOUT" in
    source)
      candidate="$ROOT/$relative_path"
      ;;
    bootstrapped)
      candidate="$ROOT/.ai-delivery/$relative_path"
      ;;
    *)
      fail "Unknown skill layout while resolving managed asset: $SKILL_LAYOUT"
      ;;
  esac

  if [[ -e "$candidate" ]]; then
    print -r -- "$candidate"
    return 0
  fi

  fail "Missing managed asset: $relative_path"
}

validate_skill_local_assets() {
  local skill_name=$1
  shift
  local skill_dir="$SKILL_ROOT/$skill_name"
  local local_path

  require_dir "$skill_dir"
  require_file "$skill_dir/SKILL.md"
  require_file "$skill_dir/agents/openai.yaml"

  for local_path in "$@"; do
    require_file "$skill_dir/$local_path"
  done
}

validate_managed_contract() {
  local validate_script
  local validate_test
  local onboarding_guide
  local bootstrap_script=""

  validate_script=$(resolve_managed_asset_path "scripts/validate-project-ai-delivery-skills.sh")
  validate_test=$(resolve_managed_asset_path "tests/ai-delivery-skills/validate-sources.test.sh")
  onboarding_guide=$(resolve_managed_asset_path "docs/guides/ai-delivery-any-repo-onboarding.md")

  require_file "$validate_script"
  require_file "$validate_test"
  require_file "$onboarding_guide"

  if [[ "$SKILL_LAYOUT" == "source" ]]; then
    bootstrap_script="$ROOT/scripts/bootstrap-ai-delivery-project.sh"
    require_file "$bootstrap_script"
    require_file "$ROOT/tests/ai-delivery-skills/bootstrap-project.test.sh"
    require_contains "$bootstrap_script" '.agents/skills'
    require_not_contains "$bootstrap_script" 'install-project-ai-delivery-skills'
    require_not_contains "$bootstrap_script" 'sync-ai-delivery-project-assets'
  fi

  require_contains "$onboarding_guide" '.agents/skills/requirement-breakdown'
  require_contains "$onboarding_guide" '.agents/skills/api-contract-mapping'
  require_contains "$onboarding_guide" '.agents/skills/ui-requirement-mapping'
  require_contains "$onboarding_guide" '.agents/skills/ui-interaction-design'
  require_contains "$onboarding_guide" '.ai-delivery/scripts/validate-project-ai-delivery-skills.sh'
  require_not_contains "$onboarding_guide" 'install-project-ai-delivery-skills'
  require_not_contains "$onboarding_guide" 'sync-ai-delivery-project-assets'
  require_not_contains "$onboarding_guide" '### Step 3: 在目标仓库里安装 project-local skills 到当前 Codex 环境'
}

validate_generic_skill() {
  local skill_name=$1
  local skill_file="$SKILL_ROOT/$skill_name/SKILL.md"

  require_frontmatter_skill "$skill_file" "$skill_name"
  validate_openai_yaml "$skill_name"
  validate_markdown_links "$skill_file"
  require_contains "$skill_file" '.ai-delivery'
  require_contains "$skill_file" 'admin support'
  require_contains "$skill_file" 'governed'
  require_not_contains "$skill_file" 'owned by ai-delivery-admin'
  require_not_contains "$skill_file" 'move workflow truth into ai-delivery-admin'
  require_not_contains "$skill_file" '../common/'
}

validate_requirement_breakdown_skill() {
  local skill_file="$SKILL_ROOT/requirement-breakdown/SKILL.md"

  validate_skill_local_assets \
    requirement-breakdown \
    references/dual-truth-rules.md \
    references/blocker-catalog.md \
    references/logging-checklist.md \
    references/checklist.md \
    references/subreq-readme-template.md \
    templates/requirement-slice-template.md

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

validate_api_contract_mapping_skill() {
  local skill_file="$SKILL_ROOT/api-contract-mapping/SKILL.md"

  validate_skill_local_assets \
    api-contract-mapping \
    references/dual-truth-rules.md \
    references/blocker-catalog.md \
    references/logging-checklist.md \
    references/checklist.md \
    templates/api-contract-mapping-template.md

  require_contains "$skill_file" 'requirement-slice.md'
  require_contains "$skill_file" 'api-contract-mapping.md'
  require_contains "$skill_file" 'traceability.json'
  require_contains "$skill_file" 'Swagger'
  require_contains "$skill_file" 'OpenAPI'
  require_contains "$skill_file" 'downstream_revalidation'
  require_contains "$skill_file" 'blocked_missing_api_contract'
  require_contains "$skill_file" 'blocked_api_contract_conflict'
  require_contains "$skill_file" 'blocked_requirement_api_conflict'
}

validate_ui_requirement_mapping_skill() {
  local skill_file="$SKILL_ROOT/ui-requirement-mapping/SKILL.md"

  validate_skill_local_assets \
    ui-requirement-mapping \
    references/dual-truth-rules.md \
    references/blocker-catalog.md \
    references/logging-checklist.md \
    references/figma-fetch-order.md \
    references/mapping-checklist.md \
    templates/figma-mapping-template.md

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

  validate_skill_local_assets \
    ui-interaction-design \
    references/dual-truth-rules.md \
    references/blocker-catalog.md \
    references/logging-checklist.md \
    references/allowed-assumptions.md \
    references/interaction-quality-guidelines.md \
    references/state-checklist.md \
    templates/interaction-design-template.md

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
  require_contains "$skill_file" 'micro-interaction'
  require_contains "$skill_file" 'loading'
  require_contains "$skill_file" 'feedback'
  require_contains "$skill_file" 'timing'
  require_contains "$skill_file" 'a11y'
  require_contains "$skill_file" 'external skill'
  require_contains "$skill_file" 'blocked_missing_design'
  require_contains "$skill_file" 'blocked_requirement_figma_conflict'
  require_contains "$skill_file" 'blocked_missing_requirement'
  require_contains "$skill_file" 'Do not invent business flow or page structure'
}

ROOT=$(resolve_repo_root)

if [[ -d "$ROOT/.agents/skills/requirement-breakdown" ]]; then
  SKILL_LAYOUT="bootstrapped"
  SKILL_ROOT="$ROOT/.agents/skills"
elif [[ -d "$ROOT/.agents/skills/ai-delivery/requirement-breakdown" ]]; then
  SKILL_LAYOUT="source"
  SKILL_ROOT="$ROOT/.agents/skills/ai-delivery"
else
  fail "Unable to detect project-local skill layout under $ROOT"
fi

validate_managed_contract
validate_generic_skill requirement-breakdown
validate_generic_skill api-contract-mapping
validate_generic_skill ui-requirement-mapping
validate_generic_skill ui-interaction-design
validate_requirement_breakdown_skill
validate_api_contract_mapping_skill
validate_ui_requirement_mapping_skill
validate_ui_interaction_design_skill

print -- 'PASS: project-local ai-delivery skill sources are structurally valid.'
