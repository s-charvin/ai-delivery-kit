package workspace

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

// ObservedChanges 只返回项目内变化，转换 Git 顶层坐标后扩大阅读范围；不授予写入权。
// 项目外变化不属于该工作区，known=false 表示已有 Git 无法读取。
func ObservedChanges(ctx context.Context, root string) (paths []string, known bool, err error) {
	marked := os.Getenv("GIT_DIR") != ""
	for p := root; ; p = filepath.Dir(p) {
		if _, err := os.Lstat(filepath.Join(p, ".git")); err == nil {
			marked = true
		}
		if filepath.Dir(p) == p {
			break
		}
	}
	if !marked {
		return []string{}, true, nil
	}
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	run := func(args ...string) ([]byte, error) {
		cmd := exec.CommandContext(ctx, "git", append([]string{"-C", root}, args...)...)
		cmd.Env = append(os.Environ(), "LC_ALL=C")
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		out, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("无法读取真实 Git 变更: %v %s", err, strings.TrimSpace(stderr.String()))
		}
		return out, nil
	}
	prefixBytes, err := run("rev-parse", "--show-prefix")
	if err != nil {
		return nil, false, err
	}
	prefix := string(bytes.TrimSuffix(prefixBytes, []byte{'\n'}))
	if prefix != "" {
		normalized, err := NormalizePath(prefix)
		if err != nil {
			return nil, false, err
		}
		prefix = normalized + "/"
	}
	out, err := run("status", "--porcelain=v1", "-z", "--untracked-files=all")
	if err != nil {
		return nil, false, err
	}
	if len(out) == 0 {
		return []string{}, true, nil
	}
	records := bytes.Split(out, []byte{0})
	if len(records[len(records)-1]) != 0 {
		return nil, false, fmt.Errorf("Git porcelain 缺少记录终止符")
	}
	seen := map[string]bool{}
	add := func(b []byte) error {
		if !utf8.Valid(b) {
			return fmt.Errorf("Git 路径不是 UTF-8")
		}
		p := string(b)
		p, err = NormalizePath(p)
		if err != nil {
			return err
		}
		if !strings.HasPrefix(p, prefix) {
			return nil
		}
		p = strings.TrimPrefix(p, prefix)
		if p != ".ai-delivery.lock" && p != ".ai-delivery-backups" && !strings.HasPrefix(p, ".ai-delivery-backups/") {
			seen[p] = true
		}
		return nil
	}
	for i := 0; i < len(records)-1; i++ {
		row := records[i]
		if len(row) < 4 || row[2] != ' ' {
			return nil, false, fmt.Errorf("Git porcelain 路径格式错误")
		}
		if err := add(row[3:]); err != nil {
			return nil, false, err
		}
		if bytes.ContainsAny(row[:2], "RC") {
			i++
			if i >= len(records)-1 || len(records[i]) == 0 {
				return nil, false, fmt.Errorf("Git 重命名缺少原路径")
			}
			if err := add(records[i]); err != nil {
				return nil, false, err
			}
		}
	}
	paths = make([]string, 0, len(seen))
	for p := range seen {
		paths = append(paths, p)
	}
	sort.Strings(paths)
	return paths, true, nil
}
