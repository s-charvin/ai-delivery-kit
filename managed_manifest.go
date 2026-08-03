package kitassets

func ManagedSourcePaths() []string {
	return []string{
		".agents/skills/ai-delivery-orchestrator",
		".agents/skills/requirement-breakdown",
		".agents/skills/ui-truth-mapping",
		".agents/skills/ui-truth-mapping/templates/ui-contract-template.html",
		"scripts/validate-project-ai-delivery-skills.sh",
		"scripts/validate-ui-contract-html.py",
		"scripts/validate-delivery-status.py",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
		"tests/ai-delivery-skills/ui-contract-validator.test.sh",
		"tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh",
	}
}
