package kitassets

import (
	"io/fs"
	"testing"
)

func TestEmbeddedAssetsContainGovernedSources(t *testing.T) {
	required := []string{
		".agents/skills/ai-delivery-orchestrator/SKILL.md",
		".agents/skills/ai-delivery-orchestrator/templates/status-template.json",
		".agents/skills/requirement-breakdown/SKILL.md",
		".agents/skills/requirement-breakdown/templates/requirement-slice-template.md",
		".agents/skills/ui-truth-mapping/SKILL.md",
		".agents/skills/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml",
		".agents/skills/ui-truth-mapping/templates/section-map-template.json",
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
