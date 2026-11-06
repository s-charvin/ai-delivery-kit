package bootstrap

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func resetFixture(t *testing.T) (string, string) {
	t.Helper()
	root := t.TempDir()
	old := filepath.Join(root, ".ai-delivery")
	writeFixture(t, filepath.Join(old, "meta/workflow-policy.json"), "{broken old policy")
	writeFixture(t, filepath.Join(old, "requirements/R/原始需求.md"), "用户原件\x00\xff")
	writeFixture(t, filepath.Join(root, ".agents/skills/ai-delivery-orchestrator/local.txt"), "old managed skill")
	writeFixture(t, filepath.Join(root, ".agents/skills/other/SKILL.md"), "third party")
	writeFixture(t, filepath.Join(root, "product/main.go"), "product bytes")
	writeFixture(t, filepath.Join(root, "AGENTS.md"), "用户自己的规范\n")
	return root, old
}

func TestResetDataBacksUpRawBytesAndBuildsCurrentWorkspace(t *testing.T) {
	root, old := resetFixture(t)
	links := []string{}
	for rel, target := range map[string]string{"requirements/R/link": "原始需求.md", "external-link": filepath.Join(t.TempDir(), "not-followed")} {
		if err := os.Symlink(target, filepath.Join(old, rel)); err != nil {
			if runtime.GOOS != "windows" {
				t.Fatal(err)
			}
			t.Logf("链接子场景未执行（Windows 当前账户能力）: %v", err)
		} else {
			links = append(links, rel)
		}
	}
	report := ResetReport{}
	err := (Engine{}).Run(Config{RepoRoot: root, ProjectID: "demo", AllowManagedUpdate: true, ResetData: ".ai-delivery", ResetReport: &report})
	if err != nil {
		t.Fatal(err)
	}
	if report.BackupDir == "" || report.OriginalDir == "" {
		t.Fatal("missing recovery locations")
	}
	for rel, want := range map[string]string{
		".ai-delivery/meta/workflow-policy.json":            "{broken old policy",
		".ai-delivery/requirements/R/原始需求.md":               "用户原件\x00\xff",
		".agents/skills/ai-delivery-orchestrator/local.txt": "old managed skill",
		"AGENTS.md": "用户自己的规范\n",
	} {
		body, err := os.ReadFile(filepath.Join(report.BackupDir, "files", rel))
		if err != nil || string(body) != want {
			t.Fatalf("backup lost %s: %v", rel, err)
		}
		info, _ := os.Stat(filepath.Join(report.BackupDir, "files", rel))
		if runtime.GOOS != "windows" && info.Mode().Perm() != 0600 {
			t.Fatalf("permissions grew: %o", info.Mode().Perm())
		}
	}
	for _, rel := range links {
		got, err := os.Readlink(filepath.Join(report.BackupDir, "files/.ai-delivery", rel))
		if err != nil || got == "" {
			t.Fatalf("lost link %s", rel)
		}
	}
	if _, err := os.Stat(filepath.Join(report.OriginalDir, "requirements/R/原始需求.md")); err != nil {
		t.Fatal("original tree unavailable", err)
	}
	policy, err := os.ReadFile(filepath.Join(root, ".ai-delivery/meta/workflow-policy.json"))
	if err != nil {
		t.Fatal(err)
	}
	var data map[string]any
	if err = json.Unmarshal(policy, &data); err != nil || data["version"] != float64(4) {
		t.Fatalf("not current: %s", policy)
	}
	if _, err = os.Stat(filepath.Join(root, ".ai-delivery/requirements/R")); !os.IsNotExist(err) {
		t.Fatal("old tasks inherited")
	}
	if _, err = os.Stat(filepath.Join(root, ".agents/skills/ai-delivery-orchestrator/local.txt")); !os.IsNotExist(err) {
		t.Fatal("obsolete kit helper inherited")
	}
	for rel, want := range map[string]string{".agents/skills/other/SKILL.md": "third party", "product/main.go": "product bytes"} {
		body, _ := os.ReadFile(filepath.Join(root, rel))
		if string(body) != want {
			t.Fatalf("changed unrelated %s", rel)
		}
	}
	manifest, err := os.ReadFile(filepath.Join(report.BackupDir, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(manifest), `"type": "absent"`) {
		t.Fatal("missing absence restoration record")
	}
	info, _ := os.Stat(report.BackupDir)
	if runtime.GOOS != "windows" && info.Mode().Perm() != 0700 {
		t.Fatalf("backup not private: %o", info.Mode().Perm())
	}
}

func TestResetDataRejectsUnsafePathsAndPreservesOriginals(t *testing.T) {
	for _, source := range []string{".", "..", ".git", ".agents", ".codex", ".ai-delivery-backups", "product", "/tmp/external"} {
		t.Run(source, func(t *testing.T) {
			root, old := resetFixture(t)
			err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: source})
			if err == nil {
				t.Fatalf("unsafe source accepted: %s", source)
			}
			body, _ := os.ReadFile(filepath.Join(old, "meta/workflow-policy.json"))
			if string(body) != "{broken old policy" {
				t.Fatal("source changed")
			}
		})
	}
	for _, rel := range []string{".ai-delivery", ".ai-delivery-backups", ".agents/skills/ai-delivery-orchestrator", ".agents"} {
		t.Run("symlink_"+rel, func(t *testing.T) {
			root, old := resetFixture(t)
			external := t.TempDir()
			writeFixture(t, filepath.Join(external, "sentinel"), "external")
			if err := os.RemoveAll(filepath.Join(root, rel)); err != nil {
				t.Fatal(err)
			}
			if err := os.MkdirAll(filepath.Dir(filepath.Join(root, rel)), 0755); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(external, filepath.Join(root, rel)); err != nil {
				if runtime.GOOS == "windows" {
					t.Skipf("当前账户不能创建链接: %v", err)
				}
				t.Fatal(err)
			}
			if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery"}); err == nil {
				t.Fatal("linked write target accepted")
			}
			body, _ := os.ReadFile(filepath.Join(external, "sentinel"))
			if string(body) != "external" {
				t.Fatal("external changed")
			}
			_ = old
		})
	}
}

func TestResetCustomRootAndUniqueBackups(t *testing.T) {
	root, old := resetFixture(t)
	custom := filepath.Join(root, "tooling/delivery")
	if err := os.MkdirAll(filepath.Dir(custom), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(old, custom); err != nil {
		t.Fatal(err)
	}
	e := Engine{Now: func() time.Time { return time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC) }}
	first := ResetReport{}
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: "tooling/delivery", ResetReport: &first}); err != nil {
		t.Fatal(err)
	}
	if first.SourceRoot != custom {
		t.Fatal("source not reported")
	}
	second := ResetReport{}
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery", ResetReport: &second}); err != nil {
		t.Fatal(err)
	}
	if first.BackupDir == second.BackupDir {
		t.Fatal("backup overwritten")
	}
	if _, err := os.Stat(filepath.Join(first.BackupDir, "manifest.json")); err != nil {
		t.Fatal("first backup lost")
	}
	if err := e.Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: "tooling/delivery"}); err == nil {
		t.Fatal("missing old root not reported")
	}
}

func TestResetFailureAfterBackupKeepsRecovery(t *testing.T) {
	root, old := resetFixture(t)
	// 真正受管发布目标为目录，备份可完成，但初始化不能把目录当文件写入。
	if err := os.Remove(filepath.Join(root, "AGENTS.md")); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(root, "AGENTS.md"), 0700); err != nil {
		t.Fatal(err)
	}
	writeFixture(t, filepath.Join(root, "AGENTS.md", "original.txt"), "受管目标下原件")
	report := ResetReport{}
	err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery", ResetReport: &report})
	if err == nil {
		t.Fatal("initialization unexpectedly succeeded")
	}
	if !strings.Contains(err.Error(), report.BackupDir) || report.BackupDir == "" {
		t.Fatal("missing recovery diagnostic", err)
	}
	body, readErr := os.ReadFile(filepath.Join(report.BackupDir, "files/.ai-delivery/meta/workflow-policy.json"))
	if readErr != nil || string(body) != "{broken old policy" {
		t.Fatal("backup unavailable")
	}
	if _, err = os.Stat(filepath.Join(report.OriginalDir, "meta/workflow-policy.json")); err != nil {
		t.Fatal("original unavailable")
	}
	owned, readErr := os.ReadFile(filepath.Join(report.BackupDir, "files/AGENTS.md/original.txt"))
	if readErr != nil || string(owned) != "受管目标下原件" {
		t.Fatalf("失败发布前的受管目标原件未完整保全: %q %v", owned, readErr)
	}
	_ = old
}

func TestResetShortWriteDoesNotChangeOriginal(t *testing.T) {
	if root := os.Getenv("AI_DELIVERY_RESET_SHORT_WRITE_ROOT"); root != "" {
		if err := limitBackupFileSize(); err != nil {
			t.Fatal(err)
		}
		if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery"}); err == nil {
			t.Fatal("short write succeeded")
		}
		return
	}
	if !backupFileLimitSupported {
		t.Skip("当前平台无此 Unix 文件大小限制故障注入；通用 reset 行为仍执行")
	}
	root, old := resetFixture(t)
	large := strings.Repeat("x", 2100000)
	writeFixture(t, filepath.Join(old, "large"), large)
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(executable, "-test.run=^TestResetShortWriteDoesNotChangeOriginal$")
	cmd.Env = append(os.Environ(), "AI_DELIVERY_RESET_SHORT_WRITE_ROOT="+root)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("helper: %s %v", out, err)
	}
	body, _ := os.ReadFile(filepath.Join(old, "large"))
	if string(body) != large {
		t.Fatal("failed backup changed source")
	}
	entries, _ := os.ReadDir(filepath.Join(root, ".ai-delivery-backups"))
	if len(entries) != 0 {
		t.Fatal("partial backup published")
	}
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery"}); err != nil {
		t.Fatal("retry failed", err)
	}
}

func TestResetNeverFollowsFixedTemporarySymlink(t *testing.T) {
	root, _ := resetFixture(t)
	outside := filepath.Join(t.TempDir(), "important")
	writeFixture(t, outside, "external original")
	if err := os.Symlink(outside, filepath.Join(root, "AGENTS.md.tmp")); err != nil {
		if runtime.GOOS == "windows" {
			t.Skipf("当前账户不能创建链接: %v", err)
		}
		t.Fatal(err)
	}
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery"}); err != nil {
		t.Fatal(err)
	}
	body, _ := os.ReadFile(outside)
	if string(body) != "external original" {
		t.Fatal("fixed temporary symlink overwrote external original")
	}
	info, err := os.Lstat(filepath.Join(root, "AGENTS.md"))
	if err != nil || !info.Mode().IsRegular() {
		t.Fatal("new config is not a regular file")
	}
}

func TestResetPreservesSensitiveConfigurationModes(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix mode 位断言不适用于 Windows ACL；Windows 备份/重建由通用行为用例运行")
	}
	root, _ := resetFixture(t)
	path := filepath.Join(root, ".codex/config.toml")
	writeFixture(t, path, "secret_key = \"protected\"\n")
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery"}); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil || info.Mode().Perm() != 0600 {
		t.Fatalf("active permissions grew: %v %v", info, err)
	}
	if err = filepath.WalkDir(filepath.Join(root, ".ai-delivery/backups"), func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.Name() == "config.toml" {
			info, err := d.Info()
			if err != nil {
				return err
			}
			if info.Mode().Perm() != 0600 {
				t.Errorf("IDE backup permissions grew: %o", info.Mode().Perm())
			}
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
}
