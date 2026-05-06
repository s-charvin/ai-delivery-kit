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
    if [[ -d "$candidate/.agents/skills/requirement-breakdown" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  done

  if candidate=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
    if [[ -d "$candidate/.agents/skills/requirement-breakdown" ]]; then
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
  require_contains "$file" 'description: '
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
  local readme_file=""
  local validate_script
  local validate_test
  local bootstrap_script=""
  local ci_workflow=""
  local release_workflow=""

  validate_script=$(resolve_managed_asset_path "scripts/validate-project-ai-delivery-skills.sh")
  validate_test=$(resolve_managed_asset_path "tests/ai-delivery-skills/validate-sources.test.sh")

  require_file "$validate_script"
  require_file "$validate_test"

  if [[ "$SKILL_LAYOUT" == "source" ]]; then
    readme_file="$ROOT/README.md"
    bootstrap_script="$ROOT/scripts/bootstrap-ai-delivery-project.sh"
    ci_workflow="$ROOT/.github/workflows/ci.yml"
    release_workflow="$ROOT/.github/workflows/release.yml"
    require_file "$readme_file"
    require_file "$bootstrap_script"
    require_file "$ci_workflow"
    require_file "$release_workflow"
    require_file "$ROOT/tests/ai-delivery-skills/bootstrap-project.test.sh"
    require_contains "$bootstrap_script" 'go run ./cmd/ai-delivery init'
    require_contains "$bootstrap_script" '/path/to/repo'
    require_not_contains "$bootstrap_script" '--target-repo'
    require_not_contains "$bootstrap_script" 'install-project-ai-delivery-skills'
    require_not_contains "$bootstrap_script" 'sync-ai-delivery-project-assets'

    require_contains "$readme_file" 'ai-delivery init /path/to/repo'
    require_contains "$readme_file" 'scripts/install-ai-delivery.sh'
    require_contains "$readme_file" 'scripts/bootstrap-ai-delivery.sh'
    require_contains "$readme_file" 'ai-delivery-orchestrator'
    require_contains "$readme_file" 'continue an existing requirement or create a new one'
    require_contains "$readme_file" 'runs `specify init` only when `specify-cli` is already available or was installed during onboarding'
    require_contains "$readme_file" 'main'
    require_contains "$readme_file" 'tag push'
    require_not_contains "$readme_file" '--project-id'
    require_not_contains "$readme_file" '--main-branch'
    require_contains "$ci_workflow" 'uses: actions/checkout@v5'
    require_contains "$ci_workflow" 'uses: actions/setup-go@v6'
    require_contains "$ci_workflow" 'uses: goreleaser/goreleaser-action@v7'
    require_contains "$ci_workflow" 'cache: false'
    require_contains "$ci_workflow" "version: '~> v2'"
    require_contains "$release_workflow" 'uses: actions/checkout@v5'
    require_contains "$release_workflow" 'uses: actions/setup-go@v6'
    require_contains "$release_workflow" 'uses: goreleaser/goreleaser-action@v7'
    require_contains "$release_workflow" 'uses: softprops/action-gh-release@v3'
    require_contains "$release_workflow" 'cache: false'
    require_contains "$release_workflow" "version: '~> v2'"
  fi
}

validate_generic_skill() {
  local skill_name=$1
  local skill_file="$SKILL_ROOT/$skill_name/SKILL.md"

  require_frontmatter_skill "$skill_file" "$skill_name"
  validate_openai_yaml "$skill_name"
  validate_markdown_links "$skill_file"
  require_not_contains "$skill_file" '../common/'
}

validate_requirement_breakdown_skill() {
  local skill_file="$SKILL_ROOT/requirement-breakdown/SKILL.md"

  validate_skill_local_assets \
    requirement-breakdown \
    templates/requirement-slice-template.md

  require_contains "$skill_file" 'requirement document'
  require_contains "$skill_file" 'requirement-slice'
  require_contains "$skill_file" 'source_ref'
  require_contains "$skill_file" 'open questions'
  require_contains "$skill_file" 'Do NOT copy the original text verbatim'
}

validate_ui_truth_mapping_skill() {
  local skill_file="$SKILL_ROOT/ui-truth-mapping/SKILL.md"

  validate_skill_local_assets \
    ui-truth-mapping \
    templates/ui-acceptance-contract-template.yaml \
    templates/section-map-template.json

  require_contains "$skill_file" 'requirement-slice'
  require_contains "$skill_file" 'Figma'
  require_contains "$skill_file" 'ui-acceptance-contract.yaml'
  require_contains "$skill_file" 'section-map'
  require_contains "$skill_file" 'Do not invent visual truth'
  require_contains "$skill_file" 'screen state'
}

validate_orchestrator_skill() {
  local skill_file="$SKILL_ROOT/ai-delivery-orchestrator/SKILL.md"

  validate_skill_local_assets \
    ai-delivery-orchestrator \
    templates/status-template.json

  require_contains "$skill_file" 'Runtime Modes'
  require_contains "$skill_file" 'tasks_ready_user_confirmation'
  require_contains "$skill_file" 'visual_acceptance_passed'
  require_contains "$skill_file" 'create req-'
  require_contains "$skill_file" 'human confirmation'
  require_contains "$skill_file" 'blocker_scope'
  require_contains "$skill_file" 'runnable queue'
}

ROOT=$(resolve_repo_root)

if [[ -f "$ROOT/managedassets.go" ]]; then
  SKILL_LAYOUT="source"
  SKILL_ROOT="$ROOT/.agents/skills"
elif [[ -d "$ROOT/.agents/skills/requirement-breakdown" ]]; then
  SKILL_LAYOUT="bootstrapped"
  SKILL_ROOT="$ROOT/.agents/skills"
else
  fail "Unable to detect project-local skill layout under $ROOT"
fi

validate_managed_contract
validate_generic_skill requirement-breakdown
validate_generic_skill ui-truth-mapping
validate_generic_skill ai-delivery-orchestrator
validate_requirement_breakdown_skill
validate_ui_truth_mapping_skill
validate_orchestrator_skill

print -- 'PASS: project-local ai-delivery skill sources are structurally valid.'
