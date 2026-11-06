package projectfs

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// NoLinkedParents 保留系统路径别名，但拒绝项目根自身及项目内的链接写入边界。
func NoLinkedParents(root, path string) error {
	rel, err := filepath.Rel(root, path)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return fmt.Errorf("路径超出项目: %s", path)
	}
	current := root
	parts := append([]string{"."}, strings.Split(rel, string(filepath.Separator))...)
	for _, part := range parts {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("不支持符号链接写入路径: %s", current)
		}
	}
	return nil
}
