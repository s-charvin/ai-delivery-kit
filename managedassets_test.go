package kitassets

import (
	"io/fs"
	"strings"
	"testing"
)

func TestEmbeddedAssetsContainGovernedSources(t *testing.T) {
	required := []string{
		".agents/skills/ai-delivery-orchestrator/SKILL.md",
		".agents/skills/ai-delivery-orchestrator/templates/status-template.json",
		".agents/skills/requirement-breakdown/SKILL.md",
		".agents/skills/requirement-breakdown/templates/requirement-slice-template.md",
		".agents/skills/ui-truth-mapping/SKILL.md",
		".agents/skills/ui-truth-mapping/templates/ui-contract-template.html",
		"scripts/validate-project-ai-delivery-skills.sh",
		"scripts/validate-ui-contract-html.py",
		"scripts/validate-delivery-status.py",
		"scripts/validate-artifact-layout.py",
		"scripts/archive-subrequirement.py",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
		"tests/ai-delivery-skills/ui-contract-validator.test.sh",
		"tests/ai-delivery-skills/ui-contract-gate-pressure.test.sh",
		"tests/ai-delivery-skills/fixtures/ui-contract-good.html",
		"tests/ai-delivery-skills/fixtures/ui-contract-bad.html",
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

func TestRestoredGateContentReferencesHTMLContract(t *testing.T) {
	gateFiles := []string{
		"AGENTS.md",
		".cursor/rules/ui-contract-gate.mdc",
		".claude/rules/ui-contract-gate.md",
		"scripts/hooks/validate-ui-contract.sh",
	}

	for _, path := range gateFiles {
		body, err := Embedded.ReadFile(path)
		if err != nil {
			t.Fatalf("expected embedded gate asset %s: %v", path, err)
		}
		if !strings.Contains(string(body), "ui-contract.html") {
			t.Fatalf("expected %s to reference ui-contract.html, got:\n%s", path, string(body))
		}
	}
}
