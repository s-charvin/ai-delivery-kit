package projectfs

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestAtomicWritePreservesOriginalModeAndPublishesCompleteBytes(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "nested", "data.json")
	if err := AtomicWriteFile(target, []byte("first"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := AtomicWriteFile(target, []byte("complete second body"), 0644); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(target)
	if err != nil || string(body) != "complete second body" {
		t.Fatal(string(body), err)
	}
	info, err := os.Stat(target)
	if err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS != "windows" && info.Mode().Perm() != 0600 {
		t.Fatal(info.Mode())
	}
	entries, err := os.ReadDir(filepath.Dir(target))
	if err != nil || len(entries) != 1 {
		t.Fatal("残留暂存文件", entries, err)
	}
}

func TestWritesRejectLinksAndNonRegularTargets(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "outside")
	if err := os.WriteFile(outside, []byte("unchanged"), 0600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "link")
	if err := os.Symlink(outside, link); err != nil {
		t.Skip(err)
	}
	if err := AtomicWriteFile(link, []byte("changed"), 0644); err == nil {
		t.Fatal("接受链接写入")
	}
	if err := AtomicWriteFile(root, []byte("changed"), 0644); err == nil {
		t.Fatal("接受目录写入")
	}
	body, _ := os.ReadFile(outside)
	if string(body) != "unchanged" {
		t.Fatal("修改链接目标")
	}
}

func TestNoLinkedParentsChecksContainmentAndRoot(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	if err := NoLinkedParents(root, filepath.Join(outside, "new")); err == nil {
		t.Fatal("接受越界路径")
	}
	link := filepath.Join(root, "link")
	if err := os.Symlink(outside, link); err != nil {
		t.Skip(err)
	}
	for _, pair := range [][2]string{{root, filepath.Join(link, "new")}, {link, filepath.Join(link, "new")}} {
		if err := NoLinkedParents(pair[0], pair[1]); err == nil {
			t.Fatal("接受链接父目录")
		}
	}
	if err := NoLinkedParents(root, filepath.Join(root, "missing", "new")); err != nil {
		t.Fatal(err)
	}
}
