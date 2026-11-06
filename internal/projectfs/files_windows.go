package projectfs

import (
	"fmt"
	"os"
	"syscall"
)

// CreateExclusiveFile 创建新证据文件，并保留句柄供后续文件身份复核。
func CreateExclusiveFile(path string) (*os.File, error) {
	return openSharedFile(path, syscall.CREATE_NEW)
}

func openSharedFile(path string, disposition uint32) (*os.File, error) {
	name, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return nil, &os.PathError{Op: "open", Path: path, Err: err}
	}
	// 允许路径删除或改名；实际归属仍由原始句柄身份与内容复核决定。
	handle, err := syscall.CreateFile(name, syscall.GENERIC_READ|syscall.GENERIC_WRITE,
		syscall.FILE_SHARE_READ|syscall.FILE_SHARE_WRITE|syscall.FILE_SHARE_DELETE,
		nil, disposition, syscall.FILE_ATTRIBUTE_NORMAL, 0)
	if err != nil {
		return nil, &os.PathError{Op: "open", Path: path, Err: err}
	}
	return os.NewFile(uintptr(handle), path), nil
}

func createTemporaryFile(dir string) (*os.File, error) {
	original, err := os.CreateTemp(dir, ".ai-delivery-write-*")
	if err != nil {
		return nil, err
	}
	path := original.Name()
	defer original.Close()
	// 原始句柄在重开期间继续禁止路径替换，随后交由共享删除句柄保留身份。
	shared, err := openSharedFile(path, syscall.OPEN_EXISTING)
	if err == nil {
		var before, after os.FileInfo
		before, err = original.Stat()
		if err == nil {
			after, err = shared.Stat()
		}
		if err == nil && !os.SameFile(before, after) {
			err = fmt.Errorf("暂存文件身份改变: %s", path)
		}
		if err == nil {
			return shared, nil
		}
		shared.Close()
	}
	original.Close()
	os.Remove(path)
	return nil, err
}
