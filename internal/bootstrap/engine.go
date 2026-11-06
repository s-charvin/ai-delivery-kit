package bootstrap

import (
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	kitassets "github.com/s-charvin/ai-delivery-kit"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

const updatedBy = "bootstrap-ai-delivery-project"

type Config struct {
	RepoRoot           string
	ProjectID          string
	AllowManagedUpdate bool
	ResetData          string
	ResetReport        *ResetReport
	Progress           io.Writer
	DeliveryPath       string
	// Report, when non-nil, receives IDE gate amendment and backup results from this run.
	Report *AmendReport
}

type Engine struct {
	Now func() time.Time
}

func (e Engine) Run(cfg Config) error {
	if cfg.ResetData != "" && !cfg.AllowManagedUpdate {
		return fmt.Errorf("--reset-data requires --upgrade")
	}
	unlock, err := projectLock(cfg.RepoRoot, cfg.ResetData != "")
	if err != nil {
		return err
	}
	defer unlock()
	if cfg.ResetData != "" {
		return e.resetAndRun(cfg)
	}
	if cfg.AllowManagedUpdate {
		var err error
		cfg.DeliveryPath, err = currentDeliveryPath(cfg.RepoRoot, cfg.DeliveryPath)
		if err != nil {
			return err
		}
		if err := checkCurrentMetadata(cfg.RepoRoot, cfg.DeliveryPath); err != nil {
			return err
		}
	}
	return e.run(cfg)
}

func (e Engine) run(cfg Config) error {
	if cfg.DeliveryPath == "" {
		cfg.DeliveryPath = ".ai-delivery"
	}
	if !cfg.AllowManagedUpdate {
		for _, relPath := range ManagedConflictPaths() {
			target := filepath.Join(cfg.RepoRoot, filepath.FromSlash(relPath))
			if _, err := os.Stat(target); err == nil {
				return fmt.Errorf("managed asset already exists: %s", target)
			}
		}
	}

	legacy, err := legacyResources(cfg)
	if err != nil {
		return err
	}

	for _, rel := range managedDirectories() {
		if err := projectfs.NoLinkedParents(cfg.RepoRoot, managedTarget(cfg, rel)); err != nil {
			return err
		}
		if err := os.MkdirAll(managedTarget(cfg, rel), 0o755); err != nil {
			return fmt.Errorf("create directory %s: %w", rel, err)
		}
	}

	report := cfg.Report
	if report == nil {
		report = &AmendReport{}
	}
	session := newAmendSession(cfg.RepoRoot, e.Now, report)
	session.backupRelRoot = filepath.Join(cfg.DeliveryPath, "backups/ide-gates")

	for _, asset := range Manifest() {
		target := managedTarget(cfg, asset.Target)
		switch asset.Kind {
		case "dir":
			if err := copyEmbeddedDir(asset.Source, target, cfg.RepoRoot); err != nil {
				return err
			}
		default:
			if err := copyEmbeddedFile(asset.Source, target, session); err != nil {
				return err
			}
		}
	}

	now := time.Now().UTC()
	if e.Now != nil {
		now = e.Now().UTC()
	}
	timestamp := now.Format(time.RFC3339)

	for _, item := range []struct{ kind, name string }{
		{"binding", "project-binding.json"}, {"policy", "workflow-policy.json"}, {"naming", "naming-rules.json"},
	} {
		data := protocol.Defaults(item.kind)
		data["updated_at"] = timestamp
		data["updated_by"] = updatedBy
		if item.kind == "binding" {
			data["project_id"] = cfg.ProjectID
			data["project_root"] = cfg.RepoRoot
			data["ai_delivery_path"] = cfg.DeliveryPath
		}
		if err := writeJSONIfMissing(managedTarget(cfg, ".ai-delivery/meta/"+item.name), data, cfg.RepoRoot); err != nil {
			return err
		}
	}

	if err := seedFileIfMissing(managedTarget(cfg, ".ai-delivery/.gitignore"), []byte(".runtime/\n"), 0o644, cfg.RepoRoot); err != nil {
		return err
	}
	if err := removeLegacyResources(legacy); err != nil {
		return err
	}
	return writeResourceManifest(cfg)
}

func managedDirectories() []string {
	return []string{
		".agents/skills",
		".ai-delivery/requirements",
		".ai-delivery/meta",
	}
}

func copyEmbeddedDir(source, target string, roots ...string) error {
	root := target
	if len(roots) > 0 {
		root = roots[0]
	}
	return fs.WalkDir(kitassets.Embedded, source, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.Name() == ".DS_Store" {
			return nil
		}

		relative := strings.TrimPrefix(path, source)
		relative = strings.TrimPrefix(relative, "/")
		destination := filepath.Join(target, filepath.FromSlash(relative))
		if err := projectfs.NoLinkedParents(root, destination); err != nil {
			return err
		}

		if d.IsDir() {
			return os.MkdirAll(destination, 0o755)
		}

		return copyEmbeddedFile(path, destination, newAmendSession(root, nil, nil))
	})
}

func copyEmbeddedFile(source, target string, session *amendSession) error {
	if session != nil {
		if err := projectfs.NoLinkedParents(session.repoRoot, target); err != nil {
			return err
		}
	}
	body, err := kitassets.Embedded.ReadFile(source)
	if err != nil {
		return fmt.Errorf("read embedded asset %s: %w", source, err)
	}
	rel := filepath.ToSlash(source)
	switch {
	case isAmendableAgentsMDTarget(rel):
		if session == nil {
			return fmt.Errorf("amendable AGENTS.md requires session: %s", source)
		}
		return session.writeAmendableAgentsMD(rel, target, body)
	}

	mode := fileModeForTarget(target)
	if session != nil {
		return session.write(target, body, mode)
	}
	return atomicWriteFile(target, body, mode)
}

func seedFileIfMissing(target string, body []byte, mode os.FileMode, roots ...string) error {
	root := filepath.Dir(target)
	if len(roots) > 0 {
		root = roots[0]
	}
	if err := projectfs.NoLinkedParents(root, target); err != nil {
		return err
	}
	if _, err := os.Stat(target); err == nil {
		return nil
	}
	return newAmendSession(root, nil, nil).write(target, body, mode)
}

func writeJSONIfMissing(target string, body map[string]any, roots ...string) error {
	content, err := json.MarshalIndent(body, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal %s: %w", target, err)
	}
	content = append(content, '\n')
	return seedFileIfMissing(target, content, 0o644, roots...)
}

func fileModeForTarget(target string) os.FileMode {
	if strings.HasSuffix(target, ".sh") {
		return 0o755
	}
	return 0o644
}

func managedTarget(cfg Config, relative string) string {
	if strings.HasPrefix(relative, ".ai-delivery/") {
		relative = filepath.Join(cfg.DeliveryPath, strings.TrimPrefix(relative, ".ai-delivery/"))
	}
	return filepath.Join(cfg.RepoRoot, filepath.FromSlash(relative))
}
