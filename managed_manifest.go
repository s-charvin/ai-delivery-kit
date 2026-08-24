package kitassets

func ManagedSourcePaths() []string {
	return []string{
		".agents/skills/ai-delivery-orchestrator",
		".agents/skills/requirement-breakdown",
		".agents/skills/ui-truth-mapping",
		"scripts/validate-project-ai-delivery-skills.sh",
		"scripts/validate-delivery-status.py",
		"scripts/validate-artifact-layout.py",
		"scripts/archive-subrequirement.py",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}
}
