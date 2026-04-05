#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

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
  - copies the helper scripts and onboarding guide into the target repository
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

TARGET_REPO=$(abs_dir "$TARGET_REPO")

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=$(slugify "${TARGET_REPO:t}")
fi

TIMESTAMP=$(/bin/date -u +"%Y-%m-%dT%H:%M:%SZ")
UPDATED_BY="bootstrap-ai-delivery-project"

MANAGED_PATHS=(
  "$TARGET_REPO/.codex/skills/ai-delivery"
  "$TARGET_REPO/.codex/skills/README.md"
  "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh"
  "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh"
  "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh"
  "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh"
  "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh"
  "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh"
  "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md"
)

if [[ "$MODE" == "bootstrap" ]]; then
  for path in "${MANAGED_PATHS[@]}"; do
    if [[ -e "$path" ]]; then
      fail "Managed asset already exists: $path. Use --mode sync to refresh an existing repository."
    fi
  done
fi

/bin/mkdir -p -- \
  "$TARGET_REPO/.codex/skills" \
  "$TARGET_REPO/scripts" \
  "$TARGET_REPO/tests/ai-delivery-skills" \
  "$TARGET_REPO/docs/guides" \
  "$TARGET_REPO/.ai-delivery/requirements" \
  "$TARGET_REPO/.ai-delivery/figma-cache" \
  "$TARGET_REPO/.ai-delivery/logs/sessions" \
  "$TARGET_REPO/.ai-delivery/logs/subagents" \
  "$TARGET_REPO/.ai-delivery/meta" \
  "$TARGET_REPO/.ai-delivery/runtime"

copy_managed_tree "$ROOT/.codex/skills/ai-delivery" "$TARGET_REPO/.codex/skills/ai-delivery"
copy_managed_file "$ROOT/.codex/skills/README.md" "$TARGET_REPO/.codex/skills/README.md"
copy_managed_file "$ROOT/scripts/bootstrap-ai-delivery-project.sh" "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh"
copy_managed_file "$ROOT/scripts/sync-ai-delivery-project-assets.sh" "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh"
copy_managed_file "$ROOT/scripts/install-project-ai-delivery-skills.sh" "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh"
copy_managed_file "$ROOT/scripts/validate-project-ai-delivery-skills.sh" "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh"
copy_managed_file "$ROOT/tests/ai-delivery-skills/validate-sources.test.sh" "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh"
copy_managed_file "$ROOT/tests/ai-delivery-skills/bootstrap-project.test.sh" "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh"
copy_managed_file "$ROOT/docs/guides/ai-delivery-any-repo-onboarding.md" "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md"

/bin/chmod +x \
  "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh" \
  "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh" \
  "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh" \
  "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh" \
  "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh" \
  "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh"

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
print -- "  3. zsh scripts/install-project-ai-delivery-skills.sh"
print -- "  4. zsh scripts/validate-project-ai-delivery-skills.sh"
