package projectfs

import (
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// AtomicWriteFile 在同目录独占暂存、完整写入并同步后发布；保留已有文件权限。
// 调用方先用 NoLinkedParents 核对项目边界，并持有合作锁与业务漂移前置条件。
func AtomicWriteFile(target string, body []byte, mode os.FileMode) error {
	return AtomicWriteFileChecked(target, body, mode, nil)
}

// AtomicWriteFileChecked 在暂存完成后、发布前复核业务输入；失败不改原件。
func AtomicWriteFileChecked(target string, body []byte, mode os.FileMode, beforePublish func(string) error) error {
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	if info, err := os.Lstat(target); err == nil {
		if !info.Mode().IsRegular() {
			return fmt.Errorf("写入目标必须是普通文件: %s", target)
		}
		mode = info.Mode().Perm()
	} else if !os.IsNotExist(err) {
		return err
	}
	file, err := createTemporaryFile(filepath.Dir(target))
	if err != nil {
		return err
	}
	tmp := file.Name()
	defer func() {
		file.Close()
		os.Remove(tmp)
	}()
	staged, err := file.Stat()
	if err != nil {
		return err
	}
	if err = file.Chmod(mode); err == nil {
		var n int
		n, err = file.Write(body)
		if err == nil && n != len(body) {
			err = io.ErrShortWrite
		}
	}
	if err == nil {
		err = file.Sync()
	}
	if err != nil {
		return err
	}
	if beforePublish != nil {
		if err := beforePublish(tmp); err != nil {
			return err
		}
	}
	current, err := os.Lstat(tmp)
	if err != nil {
		return err
	}
	if !current.Mode().IsRegular() || !os.SameFile(staged, current) {
		return fmt.Errorf("暂存文件身份改变: %s", tmp)
	}
	stored, err := os.ReadFile(tmp)
	if err != nil {
		return err
	}
	if !bytes.Equal(stored, body) {
		return fmt.Errorf("暂存文件内容改变: %s", tmp)
	}
	if err := file.Close(); err != nil {
		return err
	}
	return os.Rename(tmp, target)
}
