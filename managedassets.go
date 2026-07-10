package kitassets

import "embed"

// Embedded must live at the module root because go:embed cannot traverse .. to reach sibling directories.
//
//go:embed .agents/skills/ai-delivery-orchestrator .agents/skills/requirement-breakdown .agents/skills/ui-truth-mapping scripts/validate-project-ai-delivery-skills.sh scripts/validate-ui-contract.py scripts/validate-delivery-status.py scripts/hooks/validate-ui-contract.sh scripts/hooks/extract-hook-path.py tests/ai-delivery-skills/api-nonblocking-policy.test.sh tests/ai-delivery-skills/validate-sources.test.sh tests/ai-delivery-skills/ui-contract-validator.test.sh tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh .cursor/hooks.json .cursor/hooks/validate-ui-contract.sh .cursor/rules/ui-contract-gate.mdc .claude/settings.json .claude/hooks/validate-ui-contract.sh .claude/rules/ui-contract-gate.md .codex/hooks.json .codex/hooks/validate-ui-contract.sh .codex/config.toml AGENTS.md
var Embedded embed.FS
