package projectfs

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// ProjectLock 与归档基线共用固定项目根锁；不随交付数据根的重建或移动变化。
func ProjectLock(root string) (func(), error) {
	path := filepath.Join(root, ".ai-delivery.lock")
	if err := NoLinkedParents(root, path); err != nil {
		return nil, err
	}
	file, err := openLock(path)
	if err != nil {
		return nil, err
	}
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		file.Close()
		return nil, fmt.Errorf("项目锁必须是普通文件: %s", path)
	}
	if err = acquireLock(file); err != nil {
		file.Close()
		return nil, fmt.Errorf("无法获得项目合作锁 %s；请等待其他归档/升级/重建完成: %w", path, err)
	}
	current, err := os.Lstat(path)
	if err != nil || !os.SameFile(info, current) || !current.Mode().IsRegular() {
		releaseLock(file)
		file.Close()
		return nil, fmt.Errorf("项目锁路径在获取时发生变化: %s", path)
	}
	var once sync.Once
	return func() { once.Do(func() { releaseLock(file); file.Close() }) }, nil
}
