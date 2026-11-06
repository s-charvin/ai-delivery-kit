//go:build !darwin && !linux && !freebsd && !openbsd && !netbsd && !dragonfly

package bootstrap

import "fmt"

const backupFileLimitSupported = false

func limitBackupFileSize() error { return fmt.Errorf("此平台没有 Unix RLIMIT_FSIZE 故障注入") }
