#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=""

TARGET_REPO=""
PROJECT_ID=""
MAIN_BRANCH="main-dev"
MODE="bootstrap"

usage() {
  /bin/cat <<'EOF'
Usage:
  zsh scripts/bootstrap-ai-delivery-project.sh --target-repo /path/to/repo [--project-id my-project] [--main-branch main-dev]
  zsh scripts/bootstrap-ai-delivery-project.sh --mode sync --target-repo /path/to/repo

What it does:
  - copies the project-local ai-delivery skills into the target repository
  - copies the helper scripts, verification tests, and onboarding guide under .ai-delivery/
  - seeds the minimal .ai-delivery/ directory contract if files are missing

Modes:
  bootstrap  first-time setup, fails if managed assets already exist
  sync       refresh managed assets in an existing repository while preserving existing workflow data
EOF
}

fail() {
  print -u2 -- "[bootstrap-ai-delivery-project] $1"
  exit 1
}

resolve_repo_root() {
  local candidate

  for candidate in "$SCRIPT_DIR/.." "$SCRIPT_DIR/../.."; do
    candidate=$(cd -- "$candidate" 2>/dev/null && pwd -P) || continue
    if [[ -d "$candidate/.codex/skills/ai-delivery" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  done

  if candidate=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
    if [[ -d "$candidate/.codex/skills/ai-delivery" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  fi

  fail "Unable to resolve repository root from $SCRIPT_DIR"
}

abs_dir() {
  local target=$1
  [[ -d "$target" ]] || fail "Directory does not exist: $target"
  (cd -- "$target" && pwd -P)
}

slugify() {
  local value=$1
  local slug

  slug=$(print -r -- "$value" | /usr/bin/tr '[:upper:]' '[:lower:]' | /usr/bin/sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')
  [[ -n "$slug" ]] || slug="project"
  print -r -- "$slug"
}

copy_managed_tree() {
  local source_dir=$1
  local target_dir=$2

  /bin/rm -rf "$target_dir"
  /bin/mkdir -p -- "${target_dir:h}"
  /bin/cp -R "$source_dir" "$target_dir"
}

copy_managed_file() {
  local source_file=$1
  local target_file=$2

  /bin/mkdir -p -- "${target_file:h}"
  /bin/cp "$source_file" "$target_file"
}

seed_file_if_missing() {
  local target_file=$1

  if [[ -e "$target_file" ]]; then
    return 0
  fi

  /bin/mkdir -p -- "${target_file:h}"
  : > "$target_file"
}

remove_managed_file_if_exists() {
  local target_file=$1
  local current_dir

  [[ -e "$target_file" ]] || return 0

  /bin/rm -f -- "$target_file"

  current_dir=${target_file:h}
  while [[ "$current_dir" != "$TARGET_REPO" ]]; do
    /bin/rmdir -- "$current_dir" 2>/dev/null || break
    current_dir=${current_dir:h}
  done
}

resolve_source_managed_asset_path() {
  local root_relative=$1
  local ai_delivery_relative=$2
  local candidate

  for candidate in "$ROOT/$root_relative" "$ROOT/.ai-delivery/$ai_delivery_relative"; do
    if [[ -e "$candidate" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  done

  fail "Missing source managed asset: $root_relative"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-repo)
      [[ $# -ge 2 ]] || fail "Missing value for --target-repo"
      TARGET_REPO=$2
      shift 2
      ;;
    --project-id)
      [[ $# -ge 2 ]] || fail "Missing value for --project-id"
      PROJECT_ID=$2
      shift 2
      ;;
    --main-branch)
      [[ $# -ge 2 ]] || fail "Missing value for --main-branch"
      MAIN_BRANCH=$2
      shift 2
      ;;
    --mode)
      [[ $# -ge 2 ]] || fail "Missing value for --mode"
      MODE=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[[ -n "$TARGET_REPO" ]] || fail "You must provide --target-repo"
[[ "$MODE" == "bootstrap" || "$MODE" == "sync" ]] || fail "Unsupported mode: $MODE"

ROOT=$(resolve_repo_root)
TARGET_REPO=$(abs_dir "$TARGET_REPO")
TARGET_AI_DELIVERY_ROOT="$TARGET_REPO/.ai-delivery"
TARGET_MANAGED_SCRIPT_ROOT="$TARGET_AI_DELIVERY_ROOT/scripts"
TARGET_MANAGED_TEST_ROOT="$TARGET_AI_DELIVERY_ROOT/tests/ai-delivery-skills"
TARGET_MANAGED_DOC_ROOT="$TARGET_AI_DELIVERY_ROOT/docs/guides"
SOURCE_BOOTSTRAP_SCRIPT=$(resolve_source_managed_asset_path "scripts/bootstrap-ai-delivery-project.sh" "scripts/bootstrap-ai-delivery-project.sh")
SOURCE_SYNC_SCRIPT=$(resolve_source_managed_asset_path "scripts/sync-ai-delivery-project-assets.sh" "scripts/sync-ai-delivery-project-assets.sh")
SOURCE_INSTALL_SCRIPT=$(resolve_source_managed_asset_path "scripts/install-project-ai-delivery-skills.sh" "scripts/install-project-ai-delivery-skills.sh")
SOURCE_VALIDATE_SCRIPT=$(resolve_source_managed_asset_path "scripts/validate-project-ai-delivery-skills.sh" "scripts/validate-project-ai-delivery-skills.sh")
SOURCE_VALIDATE_TEST=$(resolve_source_managed_asset_path "tests/ai-delivery-skills/validate-sources.test.sh" "tests/ai-delivery-skills/validate-sources.test.sh")
SOURCE_BOOTSTRAP_TEST=$(resolve_source_managed_asset_path "tests/ai-delivery-skills/bootstrap-project.test.sh" "tests/ai-delivery-skills/bootstrap-project.test.sh")
SOURCE_ONBOARDING_GUIDE=$(resolve_source_managed_asset_path "docs/guides/ai-delivery-any-repo-onboarding.md" "docs/guides/ai-delivery-any-repo-onboarding.md")

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=$(slugify "${TARGET_REPO:t}")
fi

TIMESTAMP=$(/bin/date -u +"%Y-%m-%dT%H:%M:%SZ")
UPDATED_BY="bootstrap-ai-delivery-project"

MANAGED_PATHS=(
  "$TARGET_REPO/.codex/skills/ai-delivery"
  "$TARGET_REPO/.codex/skills/README.md"
  "$TARGET_MANAGED_SCRIPT_ROOT/bootstrap-ai-delivery-project.sh"
  "$TARGET_MANAGED_SCRIPT_ROOT/sync-ai-delivery-project-assets.sh"
  "$TARGET_MANAGED_SCRIPT_ROOT/install-project-ai-delivery-skills.sh"
  "$TARGET_MANAGED_SCRIPT_ROOT/validate-project-ai-delivery-skills.sh"
  "$TARGET_MANAGED_TEST_ROOT/validate-sources.test.sh"
  "$TARGET_MANAGED_TEST_ROOT/bootstrap-project.test.sh"
  "$TARGET_MANAGED_DOC_ROOT/ai-delivery-any-repo-onboarding.md"
)

LEGACY_MANAGED_PATHS=(
  "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh"
  "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh"
  "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh"
  "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh"
  "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh"
  "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh"
  "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md"
)

if [[ "$MODE" == "bootstrap" ]]; then
  for path in "${MANAGED_PATHS[@]}" "${LEGACY_MANAGED_PATHS[@]}"; do
    if [[ -e "$path" ]]; then
      fail "Managed asset already exists: $path. Use --mode sync to refresh an existing repository."
    fi
  done
fi

/bin/mkdir -p -- \
  "$TARGET_REPO/.codex/skills" \
  "$TARGET_REPO/.ai-delivery/requirements" \
  "$TARGET_REPO/.ai-delivery/figma-cache" \
  "$TARGET_MANAGED_SCRIPT_ROOT" \
  "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills" \
  "$TARGET_MANAGED_DOC_ROOT" \
  "$TARGET_REPO/.ai-delivery/logs/sessions" \
  "$TARGET_REPO/.ai-delivery/logs/subagents" \
  "$TARGET_REPO/.ai-delivery/meta" \
  "$TARGET_REPO/.ai-delivery/runtime"

copy_managed_tree "$ROOT/.codex/skills/ai-delivery" "$TARGET_REPO/.codex/skills/ai-delivery"
copy_managed_file "$ROOT/.codex/skills/README.md" "$TARGET_REPO/.codex/skills/README.md"
copy_managed_file "$SOURCE_BOOTSTRAP_SCRIPT" "$TARGET_MANAGED_SCRIPT_ROOT/bootstrap-ai-delivery-project.sh"
copy_managed_file "$SOURCE_SYNC_SCRIPT" "$TARGET_MANAGED_SCRIPT_ROOT/sync-ai-delivery-project-assets.sh"
copy_managed_file "$SOURCE_INSTALL_SCRIPT" "$TARGET_MANAGED_SCRIPT_ROOT/install-project-ai-delivery-skills.sh"
copy_managed_file "$SOURCE_VALIDATE_SCRIPT" "$TARGET_MANAGED_SCRIPT_ROOT/validate-project-ai-delivery-skills.sh"
copy_managed_file "$SOURCE_VALIDATE_TEST" "$TARGET_MANAGED_TEST_ROOT/validate-sources.test.sh"
copy_managed_file "$SOURCE_BOOTSTRAP_TEST" "$TARGET_MANAGED_TEST_ROOT/bootstrap-project.test.sh"
copy_managed_file "$SOURCE_ONBOARDING_GUIDE" "$TARGET_MANAGED_DOC_ROOT/ai-delivery-any-repo-onboarding.md"

for legacy_path in "${LEGACY_MANAGED_PATHS[@]}"; do
  remove_managed_file_if_exists "$legacy_path"
done

/bin/chmod +x \
  "$TARGET_MANAGED_SCRIPT_ROOT/bootstrap-ai-delivery-project.sh" \
  "$TARGET_MANAGED_SCRIPT_ROOT/sync-ai-delivery-project-assets.sh" \
  "$TARGET_MANAGED_SCRIPT_ROOT/install-project-ai-delivery-skills.sh" \
  "$TARGET_MANAGED_SCRIPT_ROOT/validate-project-ai-delivery-skills.sh" \
  "$TARGET_MANAGED_TEST_ROOT/validate-sources.test.sh" \
  "$TARGET_MANAGED_TEST_ROOT/bootstrap-project.test.sh"

seed_file_if_missing "$TARGET_REPO/.ai-delivery/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/requirements/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/figma-cache/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/logs/sessions/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/logs/subagents/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/meta/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/runtime/.gitkeep"
seed_file_if_missing "$TARGET_REPO/.ai-delivery/logs/events.ndjson"

if [[ ! -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/meta/project-binding.json" <<EOF
{
  "version": 1,
  "project_id": "$PROJECT_ID",
  "project_root": "$TARGET_REPO",
  "specify_path": ".specify",
  "ai_delivery_path": ".ai-delivery",
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json" <<EOF
{
  "version": 1,
  "truth_policy": {
    "functional_source": "Requirement",
    "visual_source": "Figma",
    "conflict_behavior": "block"
  },
  "worktree_policy": {
    "require_isolated_worktree": true,
    "allow_precreate_before_dependencies": false
  },
  "logging_policy": {
    "require_logs_for_main_session": true,
    "require_logs_for_subagent": true,
    "require_logs_for_state_change": true
  },
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/meta/naming-rules.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/meta/naming-rules.json" <<EOF
{
  "version": 1,
  "sub_requirement_id_pattern": "SR-%03d",
  "commit_prefix_template": "[{{subreq_id}}] ",
  "require_commit_prefix": true,
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/main-branch.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/main-branch.json" <<EOF
{
  "version": 1,
  "branch_name": "$MAIN_BRANCH",
  "status": "configured",
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/worktrees.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/worktrees.json" <<EOF
{
  "version": 1,
  "items": [],
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/merge-queue.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/merge-queue.json" <<EOF
{
  "version": 1,
  "items": [],
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/dependency-graph.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/dependency-graph.json" <<EOF
{
  "version": 1,
  "requirements": [],
  "edges": [],
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/blockers.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/blockers.json" <<EOF
{
  "version": 1,
  "items": [],
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

if [[ ! -f "$TARGET_REPO/.ai-delivery/runtime/task-board.json" ]]; then
  /bin/cat > "$TARGET_REPO/.ai-delivery/runtime/task-board.json" <<EOF
{
  "version": 1,
  "items": [],
  "updated_at": "$TIMESTAMP",
  "updated_by": "$UPDATED_BY"
}
EOF
fi

print -- "Managed AI Delivery assets copied into $TARGET_REPO"
print -- "Next steps:"
print -- "  1. cd $TARGET_REPO"
print -- "  2. specify init --here --ai codex --ai-skills --script sh"
print -- "  3. zsh .ai-delivery/scripts/install-project-ai-delivery-skills.sh"
print -- "  4. zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
