#!/bin/zsh
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
SOURCE_ROOT="$ROOT/.codex/skills/ai-delivery"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
TARGET_ROOT="$CODEX_HOME_DIR/skills"

[[ -d "$SOURCE_ROOT" ]] || {
  print -u2 -- "Missing project-local ai-delivery skills at $SOURCE_ROOT"
  exit 1
}

mkdir -p "$TARGET_ROOT"

for skill_name in requirement-breakdown ui-requirement-mapping ui-interaction-design; do
  source_dir="$SOURCE_ROOT/$skill_name"
  target_dir="$TARGET_ROOT/$skill_name"

  [[ -d "$source_dir" ]] || {
    print -u2 -- "Missing source skill directory: $source_dir"
    exit 1
  }

  rm -rf "$target_dir"
  ln -s "$source_dir" "$target_dir"
done

print -- "Synced project-local ai-delivery skills into $TARGET_ROOT"
