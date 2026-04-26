package repo

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
)

type Info struct {
	Root             string
	HasSpecify       bool
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
		Root:       root,
		HasSpecify: pathExists(filepath.Join(root, ".specify")),
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
		if pathExists(gitPath) {
			return current, nil
		}

		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("target is not inside a git repository: %s", start)
		}
		current = parent
	}
}

func pathExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
