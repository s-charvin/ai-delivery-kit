package kitassets

func ManagedSourcePaths() []string {
	return []string{
		".agents/skills/ai-delivery/requirement-breakdown",
		".agents/skills/ai-delivery/api-contract-mapping",
		".agents/skills/ai-delivery/ui-requirement-mapping",
		".agents/skills/ai-delivery/ui-acceptance-contract",
		".agents/skills/ai-delivery/ui-interaction-design",
		".agents/skills/ai-delivery/ai-delivery-orchestrator",
		"scripts/validate-project-ai-delivery-skills.sh",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}
}
