package bootstrap

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunWritesGovernedAssetsAndSeedFiles(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	if err := engine.Run(Config{
		RepoRoot:   target,
		ProjectID:  "demo-project",
		MainBranch: "main",
	}); err != nil {
		t.Fatalf("run failed: %v", err)
	}

	required := []string{
		filepath.Join(target, ".agents/skills/requirement-breakdown/SKILL.md"),
		filepath.Join(target, ".agents/skills/api-contract-mapping/references/dual-truth-rules.md"),
		filepath.Join(target, ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh"),
		filepath.Join(target, ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh"),
		filepath.Join(target, ".ai-delivery/meta/project-binding.json"),
		filepath.Join(target, ".ai-delivery/meta/workflow-policy.json"),
		filepath.Join(target, ".ai-delivery/runtime/main-branch.json"),
		filepath.Join(target, ".ai-delivery/runtime/slice-closures.json"),
		filepath.Join(target, ".ai-delivery/logs/events.ndjson"),
	}

	for _, path := range required {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("expected %s: %v", path, err)
		}
	}

	if _, err := os.Stat(filepath.Join(target, ".ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md")); !os.IsNotExist(err) {
		t.Fatalf("expected onboarding guide to be absent, got %v", err)
	}

	binding, err := os.ReadFile(filepath.Join(target, ".ai-delivery/meta/project-binding.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(binding), `"project_id": "demo-project"`) {
		t.Fatalf("expected project id in binding json, got %s", string(binding))
	}

	branch, err := os.ReadFile(filepath.Join(target, ".ai-delivery/runtime/main-branch.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(branch), `"branch_name": "main"`) {
		t.Fatalf("expected main branch in runtime json, got %s", string(branch))
	}
}

func TestRunFailsOnManagedConflictWithoutMutatingRepo(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(target, ".agents/skills/requirement-breakdown"), 0o755); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	err := engine.Run(Config{
		RepoRoot:   target,
		ProjectID:  "demo-project",
		MainBranch: "main",
	})
	if err == nil {
		t.Fatal("expected conflict error, got nil")
	}

	if _, statErr := os.Stat(filepath.Join(target, ".ai-delivery")); !os.IsNotExist(statErr) {
		t.Fatalf("expected no bootstrap mutation on preflight failure, got stat err %v", statErr)
	}
}

func TestRunFailsOnSeededManagedFileConflictWithoutMutatingRepo(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	conflict := filepath.Join(target, ".ai-delivery", "meta", "project-binding.json")
	if err := os.MkdirAll(filepath.Dir(conflict), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(conflict, []byte("{}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	err := engine.Run(Config{
		RepoRoot:   target,
		ProjectID:  "demo-project",
		MainBranch: "main",
	})
	if err == nil {
		t.Fatal("expected conflict error, got nil")
	}

	if _, statErr := os.Stat(filepath.Join(target, ".agents")); !os.IsNotExist(statErr) {
		t.Fatalf("expected no bootstrap mutation on seeded file preflight failure, got stat err %v", statErr)
	}
}
