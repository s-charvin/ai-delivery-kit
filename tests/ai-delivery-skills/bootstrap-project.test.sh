#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-bootstrap.XXXXXX")
TARGET_REPO="$TEMP_DIR/target-repo"
CODEX_HOME_DIR="$TEMP_DIR/.codex-home"

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

mkdir -p "$TARGET_REPO"
git -C "$TARGET_REPO" init -q

zsh "$ROOT/scripts/bootstrap-ai-delivery-project.sh" \
  --target-repo "$TARGET_REPO" \
  --project-id "demo-project" \
  --main-branch "main-dev"

[[ -d "$TARGET_REPO/.codex/skills/ai-delivery" ]]
[[ -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json" ]]
[[ -f "$TARGET_REPO/.ai-delivery/runtime/main-branch.json" ]]
[[ -f "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md" ]]

grep -Fq '"project_id": "demo-project"' "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
grep -Fq '"branch_name": "main-dev"' "$TARGET_REPO/.ai-delivery/runtime/main-branch.json"

CODEX_HOME="$CODEX_HOME_DIR" zsh "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh"
[[ -L "$CODEX_HOME_DIR/skills/requirement-breakdown" ]]
[[ -L "$CODEX_HOME_DIR/skills/ui-requirement-mapping" ]]
[[ -L "$CODEX_HOME_DIR/skills/ui-interaction-design" ]]

zsh "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh"
zsh "$ROOT/scripts/sync-ai-delivery-project-assets.sh" --target-repo "$TARGET_REPO"
