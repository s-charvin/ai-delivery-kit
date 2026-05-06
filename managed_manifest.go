package kitassets

func ManagedSourcePaths() []string {
	return []string{
		".agents/skills/ai-delivery-orchestrator",
		".agents/skills/requirement-breakdown",
		".agents/skills/ui-truth-mapping",
		"scripts/validate-project-ai-delivery-skills.sh",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}
}
