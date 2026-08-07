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
git -C "$TARGET_REPO" checkout -q -b main-dev
mkdir -p "$TARGET_REPO/docs/guides"
cat > "$TARGET_REPO/docs/guides/ai-delivery-any-repo-onboarding.md" <<'EOF'
# stale root onboarding guide

This file intentionally does not describe the bootstrapped flattened skill layout.
EOF

zsh "$SOURCE_BOOTSTRAP_SCRIPT" "$TARGET_REPO"

[[ -d "$TARGET_REPO/.agents/skills/requirement-breakdown" ]]
[[ -d "$TARGET_REPO/.agents/skills/ui-truth-mapping" ]]
[[ -d "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator" ]]
[[ -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/logs" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/runtime" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/requirement-breakdown/SKILL.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/requirement-breakdown/templates/requirement-slice-template.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-truth-mapping/SKILL.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-truth-mapping/templates/ui-contract-template.html" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/SKILL.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/templates/status-template.json" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md" ]]
for guide in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
  [[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/references/frameworks/$guide" ]]
done
[[ -f "$TARGET_REPO/.ai-delivery/scripts/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.ai-delivery/scripts/hooks/extract-hook-path.py" ]]
[[ -f "$TARGET_REPO/.cursor/hooks.json" ]]
[[ -f "$TARGET_REPO/.cursor/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.cursor/rules/ui-contract-gate.mdc" ]]
[[ -f "$TARGET_REPO/.claude/settings.json" ]]
[[ -f "$TARGET_REPO/.claude/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.claude/rules/ui-contract-gate.md" ]]
[[ -f "$TARGET_REPO/.codex/hooks.json" ]]
[[ -f "$TARGET_REPO/.codex/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.codex/config.toml" ]]
grep -Fq 'hooks = true' "$TARGET_REPO/.codex/config.toml"
[[ -f "$TARGET_REPO/AGENTS.md" ]]
grep -Fq 'ai-delivery:ui-contract-gate:start' "$TARGET_REPO/AGENTS.md"
[[ ! -e "$TARGET_REPO/.codex/rules/ui-contract-gate.md" ]]
grep -Fq 'Write|TabWrite' "$TARGET_REPO/.cursor/hooks.json"
grep -Fq 'CLAUDE_PROJECT_DIR' "$TARGET_REPO/.claude/settings.json"

[[ ! -e "$TARGET_REPO/.codex/skills/ai-delivery" ]]
[[ ! -e "$TARGET_REPO/.codex/skills/README.md" ]]
[[ ! -e "$TARGET_REPO/.agents/skills/common" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/install-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/bootstrap-ai-delivery-project.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/sync-ai-delivery-project-assets.sh" ]]
[[ ! -e "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/bootstrap-project.test.sh" ]]
[[ ! -e "$TARGET_REPO/scripts/validate-project-ai-delivery-skills.sh" ]]
[[ ! -e "$TARGET_REPO/tests/ai-delivery-skills/validate-sources.test.sh" ]]
[[ ! -e "$TARGET_REPO/.agents/AGENTS.md" ]]
[[ ! -e "$TARGET_REPO/.specify" ]]
grep -Fq '"project_id": "target-repo"' "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
grep -Fq '"status_sequence"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"acceptance_frozen"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"review_loop"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"max_rounds"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"

zsh "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
zsh "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh"
