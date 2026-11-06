//go:build darwin || linux || freebsd || openbsd || netbsd || dragonfly || windows

package projectfs

import (
	"os"
	"path/filepath"
	"testing"
)

func TestProjectLockIsExclusiveAndReleased(t *testing.T) {
	root := t.TempDir()
	unlock, err := ProjectLock(root)
	if err != nil {
		t.Fatal(err)
	}
	if other, err := ProjectLock(root); err == nil {
		other()
		t.Fatal("重复合作锁获准")
	}
	unlock()
	unlock()
	next, err := ProjectLock(root)
	if err != nil {
		t.Fatal(err)
	}
	next()
	if info, err := os.Stat(filepath.Join(root, ".ai-delivery.lock")); err != nil || !info.Mode().IsRegular() {
		t.Fatal(info, err)
	}
}

func TestLockRejectsSymlinkWithoutTouchingTarget(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(t.TempDir(), "target")
	os.WriteFile(target, []byte("untouched"), 0600)
	if err := os.Symlink(target, filepath.Join(root, ".ai-delivery.lock")); err != nil {
		t.Skip(err)
	}
	if unlock, err := ProjectLock(root); err == nil {
		unlock()
		t.Fatal("链接锁被接受")
	}
	body, _ := os.ReadFile(target)
	if string(body) != "untouched" {
		t.Fatal("链接目标被改变")
	}
}
