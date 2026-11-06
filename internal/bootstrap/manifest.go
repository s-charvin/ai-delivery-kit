package bootstrap

type ManagedAsset struct {
	Source string
	Target string
	Kind   string
}

func Manifest() []ManagedAsset {
	return []ManagedAsset{
		{Source: ".agents/skills/ai-delivery-orchestrator", Target: ".agents/skills/ai-delivery-orchestrator", Kind: "dir"},
		{Source: ".agents-zh/skills", Target: ".agents-zh/skills", Kind: "dir"},
		{Source: ".agents/skills/requirement-breakdown", Target: ".agents/skills/requirement-breakdown", Kind: "dir"},
		{Source: ".agents/skills/ui-truth-mapping", Target: ".agents/skills/ui-truth-mapping", Kind: "dir"},
		{Source: "AGENTS.md", Target: "AGENTS.md", Kind: "file"},
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
