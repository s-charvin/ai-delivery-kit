package bootstrap

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeFixture(t *testing.T, path, body string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0600); err != nil {
		t.Fatal(err)
	}
}

func TestUpgradeRejectsUnsupportedMetadataBeforeWriting(t *testing.T) {
	for _, tc := range []struct{ name, file, body string }{
		{"old policy", "workflow-policy.json", `{"version":3}`},
		{"null context", "workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":null}`},
		{"bad sources", "workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":{}}}`},
		{"null layout", "project-binding.json", `{"version":3,"layout":null}`},
		{"bad layout scalar", "project-binding.json", `{"version":3,"layout":{"requirement_root":123}}`},
		{"bad layout template", "project-binding.json", `{"version":3,"layout":{"requirement_artifacts":{"status":"../escape"}}}`},
		{"null layout group", "project-binding.json", `{"version":3,"layout":{"requirement_artifacts":null}}`},

		{"future policy", "workflow-policy.json", `{"version":5}`},
		{"missing contract", "workflow-policy.json", `{"version":4}`},
		{"old contract", "workflow-policy.json", `{"version":4,"verification_contract_version":1}`},
		{"historical exemption", "workflow-policy.json", `{"version":4,"verification_contract_version":2,"legacy_terminal_slices":{}}`},
		{"migration digest", "workflow-policy.json", `{"version":4,"verification_contract_version":2,"migration_source_sha256":"x"}`},
		{"binding removed flag", "project-binding.json", `{"version":3,"ui_contract_exempt":true}`},
		{"removed participation", "project-binding.json", `{"version":3,"coordination":{"participation":"no_design_client"}}`},
		{"nested removed flag", "workflow-policy.json", `{"version":4,"verification_contract_version":2,"local":{"design_mode":"full"}}`},
		{"old binding", "project-binding.json", `{"version":2}`},
		{"future binding", "project-binding.json", `{"version":4}`},
		{"broken policy", "workflow-policy.json", `{broken`},
		{"duplicate version", "workflow-policy.json", `{"version":3,"version":4,"verification_contract_version":2}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			e := Engine{}
			if err := e.Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
				t.Fatal(err)
			}
			path := filepath.Join(root, ".ai-delivery/meta", tc.file)
			writeFixture(t, path, tc.body)
			asset := filepath.Join(root, ".agents/skills/ai-delivery-orchestrator/SKILL.md")
			writeFixture(t, asset, "local asset before upgrade")
			err := e.Run(Config{RepoRoot: root, ProjectID: "test", AllowManagedUpdate: true})
			if err == nil {
				t.Fatal("unsupported metadata accepted")
			}
			for _, want := range []string{path, "--reset-data", "AI"} {
				if !strings.Contains(err.Error(), want) {
					t.Fatalf("missing actionable diagnostic %q: %v", want, err)
				}
			}
			for path, want := range map[string]string{path: tc.body, asset: "local asset before upgrade"} {
				body, _ := os.ReadFile(path)
				if string(body) != want {
					t.Fatalf("preflight changed %s", path)
				}
			}
		})
	}
}

func TestUpgradeMissingMetadataDoesNotInventDefaults(t *testing.T) {
	for _, file := range []string{"workflow-policy.json", "project-binding.json"} {
		root := t.TempDir()
		e := Engine{}
		if err := e.Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
			t.Fatal(err)
		}
		path := filepath.Join(root, ".ai-delivery/meta", file)
		if err := os.Remove(path); err != nil {
			t.Fatal(err)
		}
		if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err == nil {
			t.Fatal("missing metadata recreated")
		}
		if _, err := os.Lstat(path); !os.IsNotExist(err) {
			t.Fatal("missing metadata was written")
		}
	}
}

func TestUpgradeCurrentMetadataPreservesBytesAndIgnoresBackupAndOldStatus(t *testing.T) {
	root := t.TempDir()
	e := Engine{}
	if err := e.Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, ".ai-delivery/meta/workflow-policy.json")
	original := `{"version":4,"verification_contract_version":2,"context":{"sources":[]},"local":{"large":9007199254740993}}`
	writeFixture(t, path, original)
	writeFixture(t, path+".pre-v4", "broken old backup")
	writeFixture(t, filepath.Join(root, ".ai-delivery/requirements/old/status.json"), `{"_schema":"1.0"}`)
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err != nil {
		t.Fatal(err)
	}
	body, _ := os.ReadFile(path)
	if string(body) != original {
		t.Fatal("upgrade rewrote policy")
	}
}

func TestUpgradeMissingWholeDataRootDoesNotInventInstallation(t *testing.T) {
	root := t.TempDir()
	if err := (Engine{}).Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
		t.Fatal(err)
	}
	if err := os.RemoveAll(filepath.Join(root, ".ai-delivery")); err != nil {
		t.Fatal(err)
	}
	asset := filepath.Join(root, ".agents/skills/ai-delivery-orchestrator/SKILL.md")
	writeFixture(t, asset, "old installed skill")
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err == nil {
		t.Fatal("missing installed data root was silently reseeded")
	}
	body, _ := os.ReadFile(asset)
	if string(body) != "old installed skill" {
		t.Fatal("incompatible upgrade overwrote asset")
	}
}

func TestUpgradeUsesCurrentCustomRootWithoutCreatingShadow(t *testing.T) {
	root := t.TempDir()
	e := Engine{}
	if err := e.Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
		t.Fatal(err)
	}
	custom := filepath.Join(root, "governed")
	if err := os.Rename(filepath.Join(root, ".ai-delivery"), custom); err != nil {
		t.Fatal(err)
	}
	binding := filepath.Join(custom, "meta/project-binding.json")
	writeFixture(t, binding, `{"version":3,"ai_delivery_path":"governed","layout":{}}`)
	writeFixture(t, filepath.Join(custom, "requirements/R/status.json"), `{"_schema":"2.0"}`)
	writeFixture(t, filepath.Join(root, ".agents/skills/requirement-breakdown/SKILL.md"), "stale current resource")
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Lstat(filepath.Join(root, ".ai-delivery")); !os.IsNotExist(err) {
		t.Fatal("created standard shadow root")
	}
	body, _ := os.ReadFile(filepath.Join(root, ".agents/skills/requirement-breakdown/SKILL.md"))
	if string(body) == "stale current resource" {
		t.Fatal("custom asset not refreshed")
	}
	body, _ = os.ReadFile(filepath.Join(custom, "requirements/R/status.json"))
	if string(body) != `{"_schema":"2.0"}` {
		t.Fatal("custom requirement changed")
	}
	writeFixture(t, binding, `{"version":2,"ai_delivery_path":"governed"}`)
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err == nil || !strings.Contains(err.Error(), binding) {
		t.Fatal("custom old metadata bypassed preflight", err)
	}
}

func TestUpgradeHiddenCurrentRootAndRestorableBackups(t *testing.T) {
	root := t.TempDir()
	e := Engine{}
	if err := e.Run(Config{RepoRoot: root, ProjectID: "test"}); err != nil {
		t.Fatal(err)
	}
	custom := filepath.Join(root, ".governed")
	if err := os.Rename(filepath.Join(root, ".ai-delivery"), custom); err != nil {
		t.Fatal(err)
	}
	writeFixture(t, filepath.Join(custom, "meta/project-binding.json"), `{"version":3,"ai_delivery_path":".governed","layout":{}}`)
	writeFixture(t, filepath.Join(root, "AGENTS.md"), agentsGateStart+"\n旧受管规范\n"+agentsGateEnd+"\n")
	report := AmendReport{}
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true, Report: &report}); err != nil {
		t.Fatal(err)
	}
	stamps, err := ListIDEGateBackups(root)
	if err != nil || len(stamps) != 1 {
		t.Fatalf("custom backup not discoverable: %v %v", stamps, err)
	}
	if _, err = RestoreIDEGateBackup(root, stamps[0], nil); err != nil {
		t.Fatal("printed restore entry does not work", err)
	}
	if _, err = os.Lstat(filepath.Join(root, ".ai-delivery")); !os.IsNotExist(err) {
		t.Fatal("restore created shadow root")
	}
}
