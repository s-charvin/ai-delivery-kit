package bootstrap

import (
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// 真实入口不能经普通 IDE 父链接写到项目外；备份源也不能从项目外读取。
func TestIDEEntrypointsRejectLinkedParents(t *testing.T) {
	for _, operation := range []string{"init", "restore-destination", "restore-source", "backup"} {
		t.Run(operation, func(t *testing.T) {
			root, outside := t.TempDir(), t.TempDir()
			stamp := "2026-11-05T00-00-00Z"
			original := `{"hooks":{},"foreign":true}`
			writeFixture(t, filepath.Join(outside, "hooks.json"), original)
			backup := filepath.Join(root, ideGateBackupRelRoot, stamp)
			var link string
			switch operation {
			case "init":
				link = filepath.Join(root, ".agents")
			case "restore-destination":
				link = filepath.Join(root, ".cursor")
			case "restore-source":
				link = filepath.Join(backup, ".cursor")
			case "backup":
				link = filepath.Join(root, ".ai-delivery", "backups")
			}
			if err := os.MkdirAll(filepath.Dir(link), 0700); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(outside, link); err != nil {
				t.Skipf("当前运行环境没有链接创建能力: %v", err)
			}
			var err error
			switch operation {
			case "init":
				err = (Engine{}).Run(Config{RepoRoot: root, ProjectID: "linked"})
			case "restore-destination":
				writeFixture(t, filepath.Join(backup, ".cursor/hooks.json"), `{"hooks":{}}`)
				_, err = RestoreIDEGateBackup(root, stamp, nil)
			case "restore-source":
				_, err = RestoreIDEGateBackup(root, stamp, nil)
			case "backup":
				target := filepath.Join(root, "AGENTS.md")
				writeFixture(t, target, original)
				err = newAmendSession(root, nil, nil).writeAmendableAgentsMD("AGENTS.md", target, []byte("当前受管规范"))
			}
			if err == nil {
				t.Fatal("链接边界被接受")
			}
			body, readErr := os.ReadFile(filepath.Join(outside, "hooks.json"))
			if readErr != nil || string(body) != original {
				t.Fatalf("外部原件被改变: %s %v", body, readErr)
			}
		})
	}
}

func TestBootstrapRejectsNestedManagedParentLink(t *testing.T) {
	root, outside := t.TempDir(), t.TempDir()
	if err := (Engine{}).Run(Config{RepoRoot: root, ProjectID: "linked"}); err != nil {
		t.Fatal(err)
	}
	parent := filepath.Join(root, ".agents/skills/ai-delivery-orchestrator")
	if err := os.RemoveAll(filepath.Join(parent, "templates")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(parent, "templates")); err != nil {
		t.Skipf("当前运行环境没有链接创建能力: %v", err)
	}
	err := (Engine{}).Run(Config{RepoRoot: root, ProjectID: "linked", AllowManagedUpdate: true})
	if err == nil {
		t.Fatal("升级穿过受管目录内的父链接")
	}
	entries, err := os.ReadDir(outside)
	if err != nil || len(entries) != 0 {
		t.Fatalf("升级写出项目: %v %v", entries, err)
	}
}

func TestResetKeepsTheProjectRootLockIdentity(t *testing.T) {
	root, _ := resetFixture(t)
	unlock, err := projectfs.ProjectLock(root)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, ".ai-delivery.lock")
	before, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	unlock()
	report := ResetReport{}
	if err := (Engine{}).Run(Config{RepoRoot: root, AllowManagedUpdate: true, ResetData: ".ai-delivery", ResetReport: &report}); err != nil {
		t.Fatal(err)
	}
	after, err := os.Stat(path)
	if err != nil || !os.SameFile(before, after) {
		t.Fatal("重建移动/替换了稳定项目锁", err)
	}
	if _, err := os.Stat(filepath.Join(report.OriginalDir, ".ai-delivery.lock")); !os.IsNotExist(err) {
		t.Fatal("项目锁进入被隔离数据根")
	}
}

func TestIDEBackupSameSecondDoesNotOverwriteRecoveryPoint(t *testing.T) {
	root := t.TempDir()
	p := filepath.Join(root, "AGENTS.md")
	writeFixture(t, p, `{"hooks":{},"value":"first"}`)
	now := func() time.Time { return time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC) }
	first := AmendReport{}
	if err := newAmendSession(root, now, &first).writeAmendableAgentsMD("AGENTS.md", p, []byte("当前受管规范")); err != nil {
		t.Fatal(err)
	}
	writeFixture(t, p, `{"hooks":{},"value":"second"}`)
	second := AmendReport{}
	if err := newAmendSession(root, now, &second).writeAmendableAgentsMD("AGENTS.md", p, []byte("当前受管规范")); err != nil {
		t.Fatal(err)
	}
	if first.BackupDir == second.BackupDir {
		t.Fatal("同秒备份覆盖恢复点")
	}
	body, _ := os.ReadFile(filepath.Join(first.BackupDir, "AGENTS.md"))
	if !strings.Contains(string(body), "first") {
		t.Fatal("初始恢复点丢失")
	}
}
func TestIDERestoreAbsentSensitiveFilePreservesBackupMode(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix mode 断言")
	}
	root := t.TempDir()
	stamp := "2026-11-05T00-00-00Z"
	p := filepath.Join(root, ideGateBackupRelRoot, stamp, ".codex/config.toml")
	writeFixture(t, p, "secret = true\n")
	if _, err := RestoreIDEGateBackup(root, stamp, nil); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(filepath.Join(root, ".codex/config.toml"))
	if err != nil || info.Mode().Perm() != 0600 {
		t.Fatal("恢复扩大敏感配置权限", info, err)
	}
}

func TestIDEAmendRejectsConcurrentUserEditBeforePublication(t *testing.T) {
	root := t.TempDir()
	p := filepath.Join(root, "AGENTS.md")
	writeFixture(t, p, `{"hooks":{},"value":"first"}`)
	user := `{"hooks":{},"value":"concurrent user edit"}`
	now := func() time.Time { writeFixture(t, p, user); return time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC) }
	err := newAmendSession(root, now, nil).writeAmendableAgentsMD("AGENTS.md", p, []byte("当前受管规范"))
	if err == nil {
		t.Fatal("并发用户编辑被旧合并覆盖")
	}
	body, _ := os.ReadFile(p)
	if string(body) != user {
		t.Fatal("用户编辑丢失")
	}
}

func TestIDERestoreDoesNotPruneItsSourceMidRestore(t *testing.T) {
	root := t.TempDir()
	stamp := "2026-01-01T00-00-00Z"
	for _, rel := range []string{".cursor/hooks.json", ".claude/settings.json"} {
		writeFixture(t, filepath.Join(root, rel), `{"current":true}`)
		writeFixture(t, filepath.Join(root, ideGateBackupRelRoot, stamp, rel), `{"original":true}`)
	}
	for _, other := range []string{"2026-02-01T00-00-00Z", "2026-03-01T00-00-00Z", "2026-04-01T00-00-00Z"} {
		os.MkdirAll(filepath.Join(root, ideGateBackupRelRoot, other), 0700)
	}
	if _, err := RestoreIDEGateBackup(root, stamp, func() time.Time { return time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC) }); err != nil {
		t.Fatal("恢复期间删除源备份", err)
	}
	for _, kept := range []string{stamp, "2026-02-01T00-00-00Z", "2026-03-01T00-00-00Z", "2026-04-01T00-00-00Z"} {
		if _, err := os.Stat(filepath.Join(root, ideGateBackupRelRoot, kept)); err != nil {
			t.Fatal("恢复清理了既有恢复点", kept, err)
		}
	}
	for _, rel := range []string{".cursor/hooks.json", ".claude/settings.json"} {
		body, _ := os.ReadFile(filepath.Join(root, rel))
		if string(body) != `{"original":true}` {
			t.Fatal(rel, string(body))
		}
	}
}

func TestIDERestoreRejectsConcurrentByteChanges(t *testing.T) {
	for _, change := range []string{"source", "destination"} {
		t.Run(change, func(t *testing.T) {
			root := t.TempDir()
			stamp := "2026-01-01T00-00-00Z"
			src := filepath.Join(root, ideGateBackupRelRoot, stamp, ".codex/hooks.json")
			dst := filepath.Join(root, ".codex/hooks.json")
			original := `{ "number":9007199254740993, "version":"current" }`
			backup := `{ "number":9007199254740995, "version":"backup" }`
			changed := `{ "number":9007199254740997, "version":"concurrent" }`
			writeFixture(t, src, backup)
			writeFixture(t, dst, original)
			now := func() time.Time {
				target := src
				if change == "destination" {
					target = dst
				}
				writeFixture(t, target, changed)
				return time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC)
			}
			if _, err := RestoreIDEGateBackup(root, stamp, now); err == nil {
				t.Fatal("恢复未拒绝写前字节漂移")
			}
			want := original
			if change == "destination" {
				want = changed
			}
			got, err := os.ReadFile(dst)
			if err != nil || string(got) != want {
				t.Fatalf("恢复覆盖当前用户字节: %q %v", got, err)
			}
		})
	}
}
