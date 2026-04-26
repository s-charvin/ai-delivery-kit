package bootstrap

type ManagedAsset struct {
	Source string
	Target string
	Kind   string
}

func Manifest() []ManagedAsset {
	return []ManagedAsset{
		{Source: ".agents/skills/ai-delivery/requirement-breakdown", Target: ".agents/skills/requirement-breakdown", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/api-contract-mapping", Target: ".agents/skills/api-contract-mapping", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-requirement-mapping", Target: ".agents/skills/ui-requirement-mapping", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-acceptance-contract", Target: ".agents/skills/ui-acceptance-contract", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-interaction-design", Target: ".agents/skills/ui-interaction-design", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ai-delivery-orchestrator", Target: ".agents/skills/ai-delivery-orchestrator", Kind: "dir"},
		{Source: "scripts/validate-project-ai-delivery-skills.sh", Target: ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/validate-sources.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh", Kind: "file"},
	}
}

func SeededManagedFiles() []string {
	paths := append([]string{}, SeededPlaceholderFiles()...)
	paths = append(paths, SeededJSONFiles()...)
	return paths
}

func SeededPlaceholderFiles() []string {
	return []string{
		".ai-delivery/.gitkeep",
		".ai-delivery/requirements/.gitkeep",
		".ai-delivery/figma-cache/.gitkeep",
		".ai-delivery/logs/sessions/.gitkeep",
		".ai-delivery/logs/subagents/.gitkeep",
		".ai-delivery/meta/.gitkeep",
		".ai-delivery/runtime/.gitkeep",
		".ai-delivery/logs/events.ndjson",
	}
}

func SeededJSONFiles() []string {
	return []string{
		".ai-delivery/meta/project-binding.json",
		".ai-delivery/meta/workflow-policy.json",
		".ai-delivery/meta/naming-rules.json",
		".ai-delivery/runtime/main-branch.json",
		".ai-delivery/runtime/worktrees.json",
		".ai-delivery/runtime/merge-queue.json",
		".ai-delivery/runtime/dependency-graph.json",
		".ai-delivery/runtime/blockers.json",
		".ai-delivery/runtime/task-board.json",
		".ai-delivery/runtime/slice-closures.json",
		".ai-delivery/runtime/agent-sessions.json",
	}
}

func ManagedConflictPaths() []string {
	paths := make([]string, 0, len(Manifest())+len(SeededManagedFiles()))
	for _, asset := range Manifest() {
		paths = append(paths, asset.Target)
	}
	paths = append(paths, SeededManagedFiles()...)
	return paths
}
