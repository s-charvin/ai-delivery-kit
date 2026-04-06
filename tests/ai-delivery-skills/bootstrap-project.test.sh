#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

resolve_project_asset_path() {
  local relative_path=$1
  local candidate

  for candidate in "$ROOT/$relative_path" "$ROOT/.ai-delivery/$relative_path"; do
    if [[ -f "$candidate" ]]; then
      print -- "$candidate"
      return 0
    fi
  done

  print -u2 -- "[bootstrap-project-test] Missing managed asset: $relative_path"
  exit 1
}

SOURCE_BOOTSTRAP_SCRIPT=$(resolve_project_asset_path "scripts/bootstrap-ai-delivery-project.sh")
SOURCE_SYNC_SCRIPT=$(resolve_project_asset_path "scripts/sync-ai-delivery-project-assets.sh")

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-bootstrap.XXXXXX")
TARGET_REPO="$TEMP_DIR/target-repo"
NESTED_TARGET_REPO="$TEMP_DIR/nested-target-repo"
CODEX_HOME_DIR="$TEMP_DIR/.codex-home"

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

mkdir -p "$TARGET_REPO"
git -C "$TARGET_REPO" init -q
mkdir -p "$NESTED_TARGET_REPO"
git -C "$NESTED_TARGET_REPO" init -q

zsh "$SOURCE_BOOTSTRAP_SCRIPT" \
  --target-repo "$TARGET_REPO" \
  --project-id "demo-project" \
  --main-branch "main-dev"

[[ -d "$TARGET_REPO/.codex/skills/ai-delivery" ]]
[[ -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json" ]]
[[ -f "$TARGET_REPO/.ai-delivery/runtime/main-branch.json" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/bootstrap-ai-delivery-project.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/sync-ai-delivery-project-assets.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]

[[ ! -e "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh" ]]
[[ ! -e "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh" ]]
[[ ! -e "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh" ]]
[[ ! -e "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ ! -e "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md" ]]

grep -Fq '"project_id": "demo-project"' "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
grep -Fq '"branch_name": "main-dev"' "$TARGET_REPO/.ai-delivery/runtime/main-branch.json"

CODEX_HOME="$CODEX_HOME_DIR" zsh "$TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh"
[[ -L "$CODEX_HOME_DIR/skills/requirement-breakdown" ]]
[[ -L "$CODEX_HOME_DIR/skills/ui-requirement-mapping" ]]
[[ -L "$CODEX_HOME_DIR/skills/ui-interaction-design" ]]

zsh "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
zsh "$TARGET_REPO/.ai-delivery/scripts/bootstrap-ai-delivery-project.sh" \
  --target-repo "$NESTED_TARGET_REPO" \
  --project-id "nested-demo-project" \
  --main-branch "main-dev"
[[ -f "$NESTED_TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh" ]]
[[ -f "$NESTED_TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ -f "$NESTED_TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]

mkdir -p \
  "$TARGET_REPO/scripts" \
  "$TARGET_REPO/tests/ai-delivery-skills" \
  "$TARGET_REPO/docs/guides"

touch \
  "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh" \
  "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh" \
  "$TARGET_REPO/scripts/bootstrap-ai-delivery-project.sh" \
  "$TARGET_REPO/scripts/sync-ai-delivery-project-assets.sh" \
  "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh" \
  "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh" \
  "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md"

zsh "$SOURCE_SYNC_SCRIPT" --target-repo "$TARGET_REPO"

[[ -f "$TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
[[ ! -e "$TARGET_REPO/scripts/install-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ ! -e "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
