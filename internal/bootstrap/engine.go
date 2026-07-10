package bootstrap

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	kitassets "github.com/s-charvin/ai-delivery-kit"
)

const updatedBy = "bootstrap-ai-delivery-project"

type Config struct {
	RepoRoot           string
	ProjectID          string
	MainBranch         string
	AllowManagedUpdate bool
	// Report 若非 nil，Run 会填入本次 IDE gate amend/备份结果。
	Report *AmendReport
}

type Engine struct {
	Now func() time.Time
}

func (e Engine) Run(cfg Config) error {
	if !cfg.AllowManagedUpdate {
		for _, relPath := range ManagedConflictPaths() {
			target := filepath.Join(cfg.RepoRoot, filepath.FromSlash(relPath))
			if _, err := os.Stat(target); err == nil {
				return fmt.Errorf("managed asset already exists: %s", target)
			}
		}
	}

	for _, rel := range managedDirectories() {
		if err := os.MkdirAll(filepath.Join(cfg.RepoRoot, filepath.FromSlash(rel)), 0o755); err != nil {
			return fmt.Errorf("create directory %s: %w", rel, err)
		}
	}

	report := cfg.Report
	if report == nil {
		report = &AmendReport{}
	}
	session := newAmendSession(cfg.RepoRoot, e.Now, report)

	for _, asset := range Manifest() {
		target := filepath.Join(cfg.RepoRoot, filepath.FromSlash(asset.Target))
		if asset.Kind == "dir" {
			if err := copyEmbeddedDir(asset.Source, target); err != nil {
				return err
			}
			continue
		}
		if err := copyEmbeddedFile(asset.Source, target, session); err != nil {
			return err
		}
	}

	for _, rel := range SeededPlaceholderFiles() {
		if err := seedFileIfMissing(filepath.Join(cfg.RepoRoot, filepath.FromSlash(rel)), nil, 0o644); err != nil {
			return err
		}
	}

	now := time.Now().UTC()
	if e.Now != nil {
		now = e.Now().UTC()
	}
	timestamp := now.Format(time.RFC3339)

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/project-binding.json"), map[string]any{
		"version":          1,
		"project_id":       cfg.ProjectID,
		"project_root":     cfg.RepoRoot,
		"specify_path":     ".specify",
		"ai_delivery_path": ".ai-delivery",
		"updated_at":       timestamp,
		"updated_by":       updatedBy,
	}); err != nil {
		return err
	}

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/workflow-policy.json"), map[string]any{
		"version": 1,
		"truth_policy": map[string]any{
			"functional_source": "Requirement",
			"visual_source":     "Figma",
			"conflict_behavior": "block",
		},
		"workflow_gates": []string{
			"requirement_breakdown",
			"ui_truth_mapping",
			"spec_kit_pipeline",
			"implementation",
		},
		"status_sequence": []string{
			"draft",
			"split_ready",
			"acceptance_frozen",
			"spec_ready",
			"plan_ready",
			"tasks_ready",
			"in_dev",
			"visual_acceptance_passed",
			"merged",
		},
		"source_index_policy": map[string]any{
			"required_traceability_keys": []string{
				"requirement",
				"figma",
				"api",
				"spec_kit",
				"pr",
				"ci",
				"visual",
				"deploy",
				"monitoring",
			},
		},
		"gate_requirements": map[string]any{
			"ui_bearing_before_spec":  []string{"acceptance_frozen"},
			"ui_bearing_before_plan":  []string{"acceptance_frozen"},
			"ui_bearing_before_tasks": []string{"acceptance_frozen"},
			"ui_bearing_before_merge": []string{"visual_acceptance_passed"},
		},
		"worktree_policy": map[string]any{
			"require_isolated_worktree":           true,
			"allow_precreate_before_dependencies": false,
		},
		"logging_policy": map[string]any{
			"require_logs_for_main_session": true,
			"require_logs_for_subagent":     true,
			"require_logs_for_state_change": true,
		},
		"updated_at": timestamp,
		"updated_by": updatedBy,
	}); err != nil {
		return err
	}

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/naming-rules.json"), map[string]any{
		"version":                    1,
		"sub_requirement_id_pattern": "SR-%03d",
		"commit_prefix_template":     "[{{subreq_id}}] ",
		"require_commit_prefix":      true,
		"updated_at":                 timestamp,
		"updated_by":                 updatedBy,
	}); err != nil {
		return err
	}

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/runtime/main-branch.json"), map[string]any{
		"version":     1,
		"branch_name": cfg.MainBranch,
		"status":      "configured",
		"updated_at":  timestamp,
		"updated_by":  updatedBy,
	}); err != nil {
		return err
	}

	for _, runtimeFile := range []struct {
		path string
		body map[string]any
	}{
		{path: ".ai-delivery/runtime/worktrees.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/merge-queue.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/dependency-graph.json", body: map[string]any{"version": 1, "requirements": []any{}, "edges": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/blockers.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/task-board.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/slice-closures.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
		{path: ".ai-delivery/runtime/agent-sessions.json", body: map[string]any{"version": 1, "items": []any{}, "updated_at": timestamp, "updated_by": updatedBy}},
	} {
		if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, filepath.FromSlash(runtimeFile.path)), runtimeFile.body); err != nil {
			return err
		}
	}

	return nil
}

func managedDirectories() []string {
	return []string{
		".agents/skills",
		".ai-delivery/requirements",
		".ai-delivery/figma-cache",
		".ai-delivery/scripts",
		".ai-delivery/tests/ai-delivery-skills",
		".ai-delivery/logs/sessions",
		".ai-delivery/logs/subagents",
		".ai-delivery/meta",
		".ai-delivery/runtime",
	}
}

func copyEmbeddedDir(source, target string) error {
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

		if d.IsDir() {
			return os.MkdirAll(destination, 0o755)
		}

		return copyEmbeddedFile(path, destination, nil)
	})
}

func copyEmbeddedFile(source, target string, session *amendSession) error {
	body, err := kitassets.Embedded.ReadFile(source)
	if err != nil {
		return fmt.Errorf("read embedded asset %s: %w", source, err)
	}
	rel := filepath.ToSlash(source)
	switch {
	case isAmendableJSONTarget(rel):
		if session == nil {
			return fmt.Errorf("amendable JSON requires session: %s", source)
		}
		return session.writeAmendableJSON(rel, target, body)
	case isAmendableAgentsMDTarget(rel):
		if session == nil {
			return fmt.Errorf("amendable AGENTS.md requires session: %s", source)
		}
		return session.writeAmendableAgentsMD(rel, target, body)
	case isAmendableCodexConfigTarget(rel):
		if session == nil {
			return fmt.Errorf("amendable Codex config requires session: %s", source)
		}
		return session.writeAmendableCodexConfig(rel, target, body)
	}

	mode := fileModeForTarget(target)
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return fmt.Errorf("create parent for %s: %w", target, err)
	}
	if err := os.WriteFile(target, body, mode); err != nil {
		return fmt.Errorf("write %s: %w", target, err)
	}
	return nil
}

// ReapplyIDEGates 在 specify init 等可能覆盖 IDE 配置后，重新下发门禁资产。
// amendable JSON 走合并+备份；自有 scripts/rules 直接覆盖。
// repoRoot 不存在时 no-op，避免合成路径污染工作区。
func ReapplyIDEGates(repoRoot string, now func() time.Time) (AmendReport, error) {
	report := AmendReport{}
	if repoRoot == "" {
		return report, fmt.Errorf("reapply IDE gates requires a repo root")
	}
	root := filepath.Clean(repoRoot)
	if !filepath.IsAbs(root) {
		abs, err := filepath.Abs(root)
		if err != nil {
			return report, err
		}
		root = abs
	}
	st, err := os.Stat(root)
	if err != nil {
		if os.IsNotExist(err) {
			return report, nil
		}
		return report, fmt.Errorf("stat repo root %s: %w", root, err)
	}
	if !st.IsDir() {
		return report, fmt.Errorf("reapply IDE gates: %s is not a directory", root)
	}
	session := newAmendSession(root, now, &report)
	for _, asset := range IDEGateAssets() {
		target := filepath.Join(root, filepath.FromSlash(asset.Target))
		if asset.Kind == "dir" {
			if err := copyEmbeddedDir(asset.Source, target); err != nil {
				return report, err
			}
			continue
		}
		if err := copyEmbeddedFile(asset.Source, target, session); err != nil {
			return report, err
		}
	}
	return report, nil
}

func seedFileIfMissing(target string, body []byte, mode os.FileMode) error {
	if _, err := os.Stat(target); err == nil {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return fmt.Errorf("create parent for %s: %w", target, err)
	}
	if err := os.WriteFile(target, body, mode); err != nil {
		return fmt.Errorf("write %s: %w", target, err)
	}
	return nil
}

func writeJSONIfMissing(target string, body map[string]any) error {
	content, err := json.MarshalIndent(body, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal %s: %w", target, err)
	}
	content = append(content, '\n')
	return seedFileIfMissing(target, content, 0o644)
}

func fileModeForTarget(target string) os.FileMode {
	if strings.HasSuffix(target, ".sh") {
		return 0o755
	}
	return 0o644
}
