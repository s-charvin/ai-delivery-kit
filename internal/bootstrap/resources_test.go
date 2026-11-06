package bootstrap

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestLegacyCleanupUsesFrozenIdentityAndPreservesUnownedFiles(t *testing.T) {
	_, src, _, _ := runtime.Caller(0)
	original, err := os.ReadFile(filepath.Join(filepath.Dir(src), "../../tests/migration-oracle/legacy/scripts/validate-delivery-status.py"))
	if err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	e := Engine{}
	if err = e.Run(Config{RepoRoot: root}); err != nil {
		t.Fatal(err)
	}
	old := filepath.Join(root, ".ai-delivery/scripts/validate-delivery-status.py")
	writeFixture(t, old, string(original))
	unrelated := filepath.Join(root, ".ai-delivery/scripts/user-owned.py")
	writeFixture(t, unrelated, "用户自己的 Python 业务工具")
	if err = e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(old); !os.IsNotExist(err) {
		t.Fatal("明确原版旧入口未移除", err)
	}
	if b, err := os.ReadFile(unrelated); err != nil || string(b) != "用户自己的 Python 业务工具" {
		t.Fatal("误清理用户脚本", err)
	}
	writeFixture(t, old, "用户改写过的旧脚本")
	asset := filepath.Join(root, ".agents/skills/requirement-breakdown/SKILL.md")
	writeFixture(t, asset, "必须保留到冲突解决")
	if err = e.Run(Config{RepoRoot: root, AllowManagedUpdate: true}); err == nil {
		t.Fatal("改写旧入口未阻止刷新")
	}
	if b, _ := os.ReadFile(asset); string(b) != "必须保留到冲突解决" {
		t.Fatal("冲突发生前已写入资源")
	}
	if b, _ := os.ReadFile(old); string(b) != "用户改写过的旧脚本" {
		t.Fatal("覆盖旧入口")
	}
}
