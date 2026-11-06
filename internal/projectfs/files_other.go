//go:build !windows

package projectfs

import "os"

// CreateExclusiveFile 创建新证据文件，并保留句柄供后续文件身份复核。
func CreateExclusiveFile(path string) (*os.File, error) {
	return os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_RDWR, 0600)
}

func createTemporaryFile(dir string) (*os.File, error) {
	return os.CreateTemp(dir, ".ai-delivery-write-*")
}
