package kitassets

import "embed"

// Embedded must live at the module root because go:embed cannot traverse .. to reach sibling directories.
//
//go:embed .agents/skills/ai-delivery-orchestrator .agents/skills/requirement-breakdown .agents/skills/ui-truth-mapping scripts/validate-project-ai-delivery-skills.sh scripts/validate-delivery-status.py scripts/validate-artifact-layout.py scripts/archive-subrequirement.py tests/ai-delivery-skills/api-nonblocking-policy.test.sh tests/ai-delivery-skills/validate-sources.test.sh .cursor/hooks.json .claude/settings.json .codex/hooks.json .codex/config.toml AGENTS.md
var Embedded embed.FS
