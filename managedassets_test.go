package kitassets

import (
	"io/fs"
	"testing"
)

func TestEmbeddedAssetsContainGovernedSources(t *testing.T) {
	required := []string{
		".agents/skills/ai-delivery/requirement-breakdown/SKILL.md",
		".agents/skills/ai-delivery/requirement-breakdown/references/dual-truth-rules.md",
		".agents/skills/ai-delivery/api-contract-mapping/templates/api-contract-mapping-template.md",
		".agents/skills/ai-delivery/ui-requirement-mapping/templates/figma-mapping-template.md",
		".agents/skills/ai-delivery/ui-acceptance-contract/templates/ui-acceptance-contract-template.yaml",
		".agents/skills/ai-delivery/ui-interaction-design/templates/interaction-design-template.md",
		".agents/skills/ai-delivery/ai-delivery-orchestrator/references/reconcile-rules.md",
		"scripts/validate-project-ai-delivery-skills.sh",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}

	for _, path := range required {
		if _, err := Embedded.ReadFile(path); err != nil {
			t.Fatalf("expected embedded asset %s: %v", path, err)
		}
	}
}

func TestManagedSourcePathsAreEmbeddable(t *testing.T) {
	for _, path := range ManagedSourcePaths() {
		info, err := fs.Stat(Embedded, path)
		if err != nil {
			t.Fatalf("expected managed source path %s in embedded assets: %v", path, err)
		}
		if !info.IsDir() && info.Size() == 0 {
			t.Fatalf("expected non-empty managed file for %s", path)
		}
	}
}
