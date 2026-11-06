package kitassets

import "embed"

// 只内嵌当前人读资源；开发期 migration-oracle 从不进入发行程序。
//go:embed .agents/skills/ai-delivery-orchestrator/SKILL.md .agents/skills/ai-delivery-orchestrator/agents .agents/skills/ai-delivery-orchestrator/references .agents/skills/ai-delivery-orchestrator/templates .agents/skills/requirement-breakdown .agents/skills/ui-truth-mapping .agents-zh/skills AGENTS.md
var Embedded embed.FS
