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
		RepoRoot:  target,
		ProjectID: "demo-project",
	}); err != nil {
		t.Fatalf("run failed: %v", err)
	}

	required := []string{
		filepath.Join(target, ".agents/skills/requirement-breakdown/SKILL.md"),
		filepath.Join(target, ".agents/skills/ui-truth-mapping/SKILL.md"),
		filepath.Join(target, ".agents/skills/ui-truth-mapping/templates/ui-contract-template.html"),
		filepath.Join(target, ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh"),
		filepath.Join(target, ".ai-delivery/scripts/validate-ui-contract-html.py"),
		filepath.Join(target, ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh"),
		filepath.Join(target, ".ai-delivery/tests/ai-delivery-skills/fixtures/ui-contract-good.html"),
		filepath.Join(target, ".ai-delivery/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"),
		filepath.Join(target, ".ai-delivery/meta/project-binding.json"),
		filepath.Join(target, ".ai-delivery/meta/workflow-policy.json"),
	}

	for _, path := range required {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("expected %s: %v", path, err)
		}
	}

	// admin 后台弃用后，日志/运行时看板脚手架不再播种。
	for _, rel := range []string{".ai-delivery/logs", ".ai-delivery/runtime"} {
		if _, err := os.Stat(filepath.Join(target, rel)); !os.IsNotExist(err) {
			t.Fatalf("expected %s to be absent, got %v", rel, err)
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

	if _, err := os.Stat(filepath.Join(target, ".agents/AGENTS.md")); !os.IsNotExist(err) {
		t.Fatalf("expected bootstrap not to inject .agents/AGENTS.md, got %v", err)
	}

	for _, rel := range []string{
		".cursor/hooks/validate-ui-contract.sh",
		".claude/hooks/validate-ui-contract.sh",
		".codex/hooks/validate-ui-contract.sh",
	} {
		body, err := os.ReadFile(filepath.Join(target, rel))
		if err != nil {
			t.Fatalf("expected generated hook wrapper %s: %v", rel, err)
		}
		text := string(body)
		if !strings.Contains(text, ".ai-delivery/scripts/hooks/validate-ui-contract.sh") {
			t.Fatalf("expected %s to point at canonical hook, got:\n%s", rel, text)
		}
		if strings.Count(text, "\n") > 3 {
			t.Fatalf("expected short hook wrapper for %s, got %d lines", rel, strings.Count(text, "\n"))
		}
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
		RepoRoot:  target,
		ProjectID: "demo-project",
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
		RepoRoot:  target,
		ProjectID: "demo-project",
	})
	if err == nil {
		t.Fatal("expected conflict error, got nil")
	}

	if _, statErr := os.Stat(filepath.Join(target, ".agents")); !os.IsNotExist(statErr) {
		t.Fatalf("expected no bootstrap mutation on seeded file preflight failure, got stat err %v", statErr)
	}
}

func TestRunUpgradeModeRefreshesManagedAssetsWithoutResettingRequirementData(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}

	skillPath := filepath.Join(target, ".agents/skills/requirement-breakdown/SKILL.md")
	if err := os.MkdirAll(filepath.Dir(skillPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(skillPath, []byte("outdated-skill\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// 需求产物属于交付真值，升级绝不能覆盖。
	requirementPath := filepath.Join(target, ".ai-delivery/requirements/req-demo/status.json")
	if err := os.MkdirAll(filepath.Dir(requirementPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(requirementPath, []byte("{\"status\":\"in_dev\"}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	if err := engine.Run(Config{
		RepoRoot:           target,
		ProjectID:          "demo-project",
		AllowManagedUpdate: true,
	}); err != nil {
		t.Fatalf("upgrade run failed: %v", err)
	}

	skillBody, err := os.ReadFile(skillPath)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(skillBody), "outdated-skill") {
		t.Fatalf("expected upgrade mode to refresh managed skills, got %s", string(skillBody))
	}

	requirementBody, err := os.ReadFile(requirementPath)
	if err != nil {
		t.Fatal(err)
	}
	if strings.TrimSpace(string(requirementBody)) != "{\"status\":\"in_dev\"}" {
		t.Fatalf("expected requirement data to be preserved, got %s", string(requirementBody))
	}
}
