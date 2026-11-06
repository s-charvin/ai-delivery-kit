package bootstrap

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

func writeResourceManifest(cfg Config) error {
	m, err := assets.Expected()
	if err != nil {
		return err
	}
	b, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	p := managedTarget(cfg, ".ai-delivery/"+assets.ManifestName)
	if err = projectfs.NoLinkedParents(cfg.RepoRoot, p); err != nil {
		return err
	}
	return atomicWriteFile(p, append(b, '\n'), 0644)
}

// 只识别冻结清单中的旧入口；用户改写过的文件必须先保存/处理冲突。
func legacyResources(cfg Config) (map[string]string, error) {
	entries, err := assets.Legacy()
	if err != nil {
		return nil, err
	}
	found := map[string]string{}
	for _, entry := range entries {
		rel := entry.Source
		if strings.HasPrefix(rel, "scripts/") || strings.HasPrefix(rel, "tests/") {
			rel = ".ai-delivery/" + rel
		}
		p := managedTarget(cfg, rel)
		if err := projectfs.NoLinkedParents(cfg.RepoRoot, p); err != nil {
			return nil, err
		}
		b, err := os.ReadFile(p)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return nil, err
		}
		digest := fmt.Sprintf("%x", sha256.Sum256(b))
		if digest != entry.SHA256 {
			return nil, fmt.Errorf("旧受管入口已被改写，未覆盖或删除：%s；请先保存并处理冲突，再显式 init --upgrade", p)
		}
		found[p] = digest
	}
	return found, nil
}
func removeLegacyResources(files map[string]string) error {
	for p, want := range files {
		b, err := os.ReadFile(p)
		if err != nil {
			return err
		}
		if fmt.Sprintf("%x", sha256.Sum256(b)) != want {
			return fmt.Errorf("旧入口写前漂移: %s", p)
		}
		if err = os.Remove(p); err != nil {
			return err
		}
	}
	return nil
}
