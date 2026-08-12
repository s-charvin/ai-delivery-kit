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
		"scripts/validate-artifact-layout.py",
		"scripts/archive-subrequirement.py",
		"scripts/archive-subrequirement.py",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
		"tests/ai-delivery-skills/ui-contract-validator.test.sh",
		"tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh",
		"tests/ai-delivery-skills/fixtures/ui-contract-good.html",
		"tests/ai-delivery-skills/fixtures/ui-contract-bad.html",
	}
}
