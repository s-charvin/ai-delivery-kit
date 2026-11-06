//go:build !darwin && !linux && !freebsd && !openbsd && !netbsd && !dragonfly && !windows

package projectfs

import (
	"fmt"
	"os"
)

func openLock(path string) (*os.File, error) {
	return nil, fmt.Errorf("当前平台不支持项目合作锁，拒绝写动作: %s", path)
}
func acquireLock(file *os.File) error { return fmt.Errorf("当前平台不支持项目合作锁") }
func releaseLock(file *os.File) error { return fmt.Errorf("当前平台不支持项目合作锁") }
