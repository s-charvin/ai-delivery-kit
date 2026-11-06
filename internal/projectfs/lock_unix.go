//go:build darwin || linux || freebsd || openbsd || netbsd || dragonfly

package projectfs

import (
	"os"
	"syscall"
)

func openLock(path string) (*os.File, error) {
	return os.OpenFile(path, os.O_CREATE|os.O_RDWR|syscall.O_NOFOLLOW, 0600)
}
func acquireLock(file *os.File) error {
	return syscall.Flock(int(file.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
}
func releaseLock(file *os.File) error { return syscall.Flock(int(file.Fd()), syscall.LOCK_UN) }
