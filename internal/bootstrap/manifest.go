package bootstrap

import "strings"

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
		{Source: "scripts/validate-ui-contract.py", Target: ".ai-delivery/scripts/validate-ui-contract.py", Kind: "file"},
		{Source: "scripts/validate-delivery-status.py", Target: ".ai-delivery/scripts/validate-delivery-status.py", Kind: "file"},
		{Source: "scripts/hooks/validate-ui-contract.sh", Target: ".ai-delivery/scripts/hooks/validate-ui-contract.sh", Kind: "file"},
		{Source: "scripts/hooks/extract-hook-path.py", Target: ".ai-delivery/scripts/hooks/extract-hook-path.py", Kind: "file"},
		{Source: ".cursor/hooks.json", Target: ".cursor/hooks.json", Kind: "file"},
		{Source: ".cursor/hooks/validate-ui-contract.sh", Target: ".cursor/hooks/validate-ui-contract.sh", Kind: "file"},
		{Source: ".cursor/rules/ui-contract-gate.mdc", Target: ".cursor/rules/ui-contract-gate.mdc", Kind: "file"},
		{Source: ".claude/settings.json", Target: ".claude/settings.json", Kind: "file"},
		{Source: ".claude/hooks/validate-ui-contract.sh", Target: ".claude/hooks/validate-ui-contract.sh", Kind: "file"},
		{Source: ".claude/rules/ui-contract-gate.md", Target: ".claude/rules/ui-contract-gate.md", Kind: "file"},
		{Source: ".codex/hooks.json", Target: ".codex/hooks.json", Kind: "file"},
		{Source: ".codex/hooks/validate-ui-contract.sh", Target: ".codex/hooks/validate-ui-contract.sh", Kind: "file"},
		{Source: ".codex/rules/ui-contract-gate.md", Target: ".codex/rules/ui-contract-gate.md", Kind: "file"},
		{Source: "tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/validate-sources.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/ui-contract-validator.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/ui-contract-validator.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh", Kind: "file"},
	}
}

// IDEGateAssets are project-local Cursor/Claude/Codex gate files that may be
// overwritten by specify init and must be re-applied afterward.
func IDEGateAssets() []ManagedAsset {
	assets := make([]ManagedAsset, 0, 12)
	for _, asset := range Manifest() {
		switch {
		case strings.HasPrefix(asset.Target, ".cursor/"),
			strings.HasPrefix(asset.Target, ".claude/"),
			strings.HasPrefix(asset.Target, ".codex/"),
			strings.HasPrefix(asset.Target, ".ai-delivery/scripts/hooks/"):
			assets = append(assets, asset)
		}
	}
	return assets
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
		if isAmendableJSONTarget(asset.Target) {
			// Existing IDE hook/settings JSON is amended in place, not a hard conflict.
			continue
		}
		paths = append(paths, asset.Target)
	}
	paths = append(paths, SeededManagedFiles()...)
	return paths
}
