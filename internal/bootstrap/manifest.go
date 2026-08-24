package bootstrap

type ManagedAsset struct {
	Source string
	Target string
	Kind   string
}

func Manifest() []ManagedAsset {
	return []ManagedAsset{
		{Source: ".agents/skills/ai-delivery-orchestrator", Target: ".agents/skills/ai-delivery-orchestrator", Kind: "dir"},
		{Source: ".agents/skills/requirement-breakdown", Target: ".agents/skills/requirement-breakdown", Kind: "dir"},
		{Source: ".agents/skills/ui-truth-mapping", Target: ".agents/skills/ui-truth-mapping", Kind: "dir"},
		{Source: "scripts/validate-project-ai-delivery-skills.sh", Target: ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh", Kind: "file"},
		{Source: "scripts/validate-delivery-status.py", Target: ".ai-delivery/scripts/validate-delivery-status.py", Kind: "file"},
		{Source: "scripts/validate-artifact-layout.py", Target: ".ai-delivery/scripts/validate-artifact-layout.py", Kind: "file"},
		{Source: "scripts/archive-subrequirement.py", Target: ".ai-delivery/scripts/archive-subrequirement.py", Kind: "file"},
		{Source: ".cursor/hooks.json", Target: ".cursor/hooks.json", Kind: "file"},
		{Source: ".claude/settings.json", Target: ".claude/settings.json", Kind: "file"},
		{Source: ".codex/hooks.json", Target: ".codex/hooks.json", Kind: "file"},
		{Source: ".codex/config.toml", Target: ".codex/config.toml", Kind: "file"},
		{Source: "AGENTS.md", Target: "AGENTS.md", Kind: "file"},
		{Source: "tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/validate-sources.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh", Kind: "file"},
	}
}

func SeededManagedFiles() []string {
	return SeededJSONFiles()
}

func SeededJSONFiles() []string {
	return []string{
		".ai-delivery/meta/project-binding.json",
		".ai-delivery/meta/workflow-policy.json",
		".ai-delivery/meta/naming-rules.json",
	}
}

func ManagedConflictPaths() []string {
	paths := make([]string, 0, len(Manifest())+len(SeededManagedFiles()))
	for _, asset := range Manifest() {
		if isAmendableManagedTarget(asset.Target) {
			continue
		}
		paths = append(paths, asset.Target)
	}
	paths = append(paths, SeededManagedFiles()...)
	return paths
}
