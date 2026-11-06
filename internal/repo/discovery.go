package repo

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

type Info struct {
	Root             string
	ManagedConflicts []string
}

func Discover(start string) (Info, error) {
	abs, err := filepath.Abs(start)
	if err != nil {
		return Info{}, fmt.Errorf("resolve target path: %w", err)
	}

	stat, err := os.Stat(abs)
	if err != nil {
		return Info{}, fmt.Errorf("stat target path: %w", err)
	}
	if !stat.IsDir() {
		return Info{}, fmt.Errorf("target path must be a directory: %s", abs)
	}

	root, err := findGitRoot(abs)
	if err != nil {
		return Info{}, err
	}

	info := Info{
		Root: root,
	}

	for _, relPath := range bootstrap.ManagedConflictPaths() {
		target := filepath.Join(root, filepath.FromSlash(relPath))
		if pathExists(target) {
			info.ManagedConflicts = append(info.ManagedConflicts, target)
		}
	}

	return info, nil
}

func findGitRoot(start string) (string, error) {
	current := filepath.Clean(start)
	for {
		gitPath := filepath.Join(current, ".git")
		if info, err := os.Lstat(gitPath); err == nil {
			if info.IsDir() {
				return current, nil
			}
			body, err := os.ReadFile(gitPath)
			if err != nil {
				return "", fmt.Errorf("读取 Git 标记 %s: %w", gitPath, err)
			}
			text := strings.TrimSpace(string(body))
			if !strings.HasPrefix(text, "gitdir: ") {
				return "", fmt.Errorf("无效 Git 标记: %s", gitPath)
			}
			target := strings.TrimSpace(strings.TrimPrefix(text, "gitdir: "))
			if !filepath.IsAbs(target) {
				target = filepath.Join(current, target)
			}
			if st, err := os.Stat(target); err != nil || !st.IsDir() {
				return "", fmt.Errorf("无法读取 Git 目录: %s", target)
			}
			return current, nil
		} else if !os.IsNotExist(err) {
			return "", fmt.Errorf("读取 Git 标记 %s: %w", gitPath, err)
		}

		parent := filepath.Dir(current)
		if parent == current {
			return nonGitProjectRoot(start)
		}
		current = parent
	}
}

func pathExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// 没有 Git 时只根据显式目标本身的当前 binding 定位治理根，不扫描其他项目。
func nonGitProjectRoot(start string) (string, error) {
	p := filepath.Join(start, "meta/project-binding.json")
	b, err := os.ReadFile(p)
	if os.IsNotExist(err) {
		return start, nil
	}
	if err != nil {
		return "", err
	}
	obj, err := protocol.Object(b)
	if err == nil {
		err = protocol.ValidateMetadata("binding", obj)
	}
	if err != nil {
		return "", &protocol.FormatError{Path: p, Cause: err}
	}
	declared := ".ai-delivery"
	if v, ok := obj["ai_delivery_path"].(string); ok {
		declared = v
	}
	root := start
	for range strings.Split(filepath.ToSlash(filepath.Clean(declared)), "/") {
		root = filepath.Dir(root)
	}
	if filepath.Clean(filepath.Join(root, declared)) != filepath.Clean(start) {
		return "", fmt.Errorf("%s: binding 实际位置与 ai_delivery_path 不一致", p)
	}
	return root, nil
}
