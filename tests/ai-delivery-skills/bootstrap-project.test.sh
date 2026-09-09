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
[[ -f "$TARGET_REPO/.agents/skills/ui-truth-mapping/references/framework-adapters/flutter/golden-preview-test.dart.example" ]]
[[ -f "$TARGET_REPO/.agents/skills/ui-truth-mapping/templates/ui-truth-index-template.json" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/SKILL.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/templates/status-template.json" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/templates/visual-acceptance-template.json" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md" ]]
[[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/references/workspace-policy.md" ]]
for guide in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
  [[ -f "$TARGET_REPO/.agents/skills/ai-delivery-orchestrator/references/frameworks/$guide" ]]
done
[[ ! -e "$TARGET_REPO/.ai-delivery/scripts/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.cursor/hooks.json" ]]
[[ ! -e "$TARGET_REPO/.cursor/hooks/validate-ui-contract.sh" ]]
[[ ! -e "$TARGET_REPO/.cursor/rules/ui-contract-gate.mdc" ]]
[[ -f "$TARGET_REPO/.claude/settings.json" ]]
[[ ! -e "$TARGET_REPO/.claude/hooks/validate-ui-contract.sh" ]]
[[ ! -e "$TARGET_REPO/.claude/rules/ui-contract-gate.md" ]]
[[ -f "$TARGET_REPO/.codex/hooks.json" ]]
[[ ! -e "$TARGET_REPO/.codex/hooks/validate-ui-contract.sh" ]]
[[ -f "$TARGET_REPO/.codex/config.toml" ]]
grep -Fq 'hooks = true' "$TARGET_REPO/.codex/config.toml"
[[ -f "$TARGET_REPO/AGENTS.md" ]]
grep -Fq 'ai-delivery:ui-contract-gate:start' "$TARGET_REPO/AGENTS.md"
grep -Fq 'CP-UI' "$TARGET_REPO/AGENTS.md"
grep -Fq 'v2 profiles' "$TARGET_REPO/AGENTS.md"
grep -Fq 'runtime coverage' "$TARGET_REPO/AGENTS.md"
grep -Fq 'visual-acceptance.json' "$TARGET_REPO/AGENTS.md"
grep -Fq 'ui_truth_mode' "$TARGET_REPO/AGENTS.md"
grep -Fq 'design_mode' "$TARGET_REPO/AGENTS.md"
grep -Fq 'solution-design' "$TARGET_REPO/AGENTS.md"
grep -Fq 'capability' "$TARGET_REPO/AGENTS.md"
grep -Fq 'confirm_solution_design' "$TARGET_REPO/AGENTS.md"
grep -Fq 'Worktrees are optional' "$TARGET_REPO/AGENTS.md"
grep -Fq '<project-root>/.worktrees/<req-id>-<sr-id>' "$TARGET_REPO/AGENTS.md"
grep -Fq '/private/tmp' "$TARGET_REPO/AGENTS.md"
if grep -R -Fq 'ui_contract_exempt' "$TARGET_REPO/.agents/skills" "$TARGET_REPO/.ai-delivery/meta" \
  --exclude='reconcile-delivery.py'; then
  echo "legacy ui_contract_exempt bypass leaked into bootstrap output" >&2
  exit 1
fi
if grep -R -Fq 'no_design_client' "$TARGET_REPO/.agents/skills" "$TARGET_REPO/.ai-delivery/meta" \
  --exclude='reconcile-delivery.py'; then
  echo "legacy no_design_client profile leaked into bootstrap output" >&2
  exit 1
fi
[[ ! -e "$TARGET_REPO/.codex/rules/ui-contract-gate.md" ]]

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
grep -Fq '"capabilities"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"ui_truth"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
if grep -Fq '"ui_truth_mapping"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"; then
  echo "ui truth must be capability-gated, not a fixed workflow gate" >&2
  exit 1
fi
grep -Fq '"mode": "current_checkout_unless_user_confirmed"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"require_explicit_user_confirmation": true' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"project_local_root": ".worktrees"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"path_template": ".worktrees/{req_id}-{sr_id}"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"external_worktree_behavior": "stop_and_ask"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"native_tool_requires_exact_path": true' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"ui_stages_reuse_approved_workspace": true' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
if grep -Fq '"require_isolated_worktree"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"; then
  echo "legacy mandatory worktree policy leaked into bootstrap output" >&2
  exit 1
fi
grep -Fq '"acceptance_frozen"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"visual_acceptance": "requirements/{req_id}/sub-requirements/{sr_id}/visual-acceptance.json"' "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
grep -Fq '"review_loop"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"
grep -Fq '"max_rounds"' "$TARGET_REPO/.ai-delivery/meta/workflow-policy.json"

zsh "$TARGET_REPO/.ai-delivery/scripts/validate-project-ai-delivery-skills.sh"
zsh "$TARGET_REPO/.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh"
