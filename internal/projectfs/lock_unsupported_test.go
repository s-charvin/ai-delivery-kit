//go:build !darwin && !linux && !freebsd && !openbsd && !netbsd && !dragonfly && !windows

package projectfs

import (
	"os"
	"path/filepath"
	"testing"
)

func TestUnsupportedPlatformRefusesAllLockWrites(t *testing.T) {
	root := t.TempDir()
	if unlock, err := ProjectLock(root); err == nil {
		unlock()
		t.Fatal("不支持的平台返回空锁")
	}
	if _, err := os.Lstat(filepath.Join(root, ".ai-delivery.lock")); !os.IsNotExist(err) {
		t.Fatal("不支持的平台产生了锁文件", err)
	}
}
