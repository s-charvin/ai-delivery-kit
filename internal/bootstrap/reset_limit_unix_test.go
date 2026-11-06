//go:build darwin || linux || freebsd || openbsd || netbsd || dragonfly

package bootstrap

import "syscall"

const backupFileLimitSupported = true

func limitBackupFileSize() error {
	return syscall.Setrlimit(syscall.RLIMIT_FSIZE, &syscall.Rlimit{Cur: 1048576, Max: 1048576})
}
