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

  for candidate in "$ROOT/$relative_path"; do
    if [[ -f "$candidate" ]]; then
      print -- "$candidate"
      return 0
    fi
  done

  print -u2 -- "[bootstrap-project-test] Missing managed asset: $relative_path"
  exit 1
}

SOURCE_BOOTSTRAP_SCRIPT=$(resolve_project_asset_path "scripts/bootstrap-ai-delivery-project.sh")

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-bootstrap.XXXXXX")
TARGET_REPO="$TEMP_DIR/target-repo"

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

mkdir -p "$TARGET_REPO"
git -C "$TARGET_REPO" init -q
mkdir -p "$TARGET_REPO/docs/guides"
cat > "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md" <<'EOF'
# stale root onboarding guide

This file intentionally does not describe the bootstrapped flattened skill layout.
EOF

zsh "$SOURCE_BOOTSTRAP_SCRIPT" \
  --target-repo "$TARGET_REPO" \
  --project-id "demo-project" \
  --main-branch "main-dev"

[[ -d "$TARGET_REPO/.agents/skills/requirement-breakdown" ]]
[[ -d "$TARGET_REPO/.agents/skills/api-contract-mapping" ]]
[[ -d "$TARGET_REPO/.agents/skills/ui-requirement-mapping" ]]
[[ -d "$TARGET_REPO/.agents/skills/ui-interaction-design" ]]
[[ -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json" ]]
[[ -f "$TARGET_REPO/.ai-delivery/runtime/main-branch.json" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/requirement-breakdown/references/dual-truth-rules.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/requirement-breakdown/templates/requirement-slice-template.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/api-contract-mapping/references/dual-truth-rules.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/api-contract-mapping/templates/api-contract-mapping-template.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-requirement-mapping/references/dual-truth-rules.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-requirement-mapping/templates/figma-mapping-template.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-interaction-design/references/dual-truth-rules.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-interaction-design/templates/interaction-design-template.md" ]]

[[ ! -e "$TARGET_REPO/.codex/skills/ai-delivery" ]]
[[ ! -e "$TARGET_REPO/.codex/skills/README.md" ]]
[[ ! -e "$TARGET_REPO/.agents/skills/common" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/bootstrap-ai-delivery-project.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/sync-ai-delivery-project-assets.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ ! -e "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh" ]]
grep -Fq 'stale root onboarding guide' "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md"

grep -Fq '"project_id": "demo-project"' "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
grep -Fq '"branch_name": "main-dev"' "$TARGET_REPO/.ai-delivery/runtime/main-branch.json"

zsh "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
zsh "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh"
