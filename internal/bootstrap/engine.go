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
		switch asset.Kind {
		case "dir":
			if err := copyEmbeddedDir(asset.Source, target); err != nil {
				return err
			}
		case "hook_wrapper":
			if err := writeHookWrapper(target); err != nil {
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

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/project-binding.json"), map[string]any{
		"version":          1,
		"project_id":       cfg.ProjectID,
		"project_root":     cfg.RepoRoot,
		"ai_delivery_path": ".ai-delivery",
		"layout": map[string]any{
			"requirement_root": "requirements/{req_id}",
			"sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
			"requirement_artifacts": map[string]any{
				"status":             "requirements/{req_id}/status.json",
				"requirement":        "requirements/{req_id}/requirement.md",
				"breakdown_summary":  "requirements/{req_id}/breakdown-summary.md",
				"global_rules":       "requirements/{req_id}/global-rules.md",
				"dependency_graph":    "requirements/{req_id}/dependency-graph.json",
				"progress":           "requirements/{req_id}/progress.md",
				"todo":               "requirements/{req_id}/todo.md",
				"delivery_report":    "requirements/{req_id}/delivery-report.md",
			},
			"sub_requirement_artifacts": map[string]any{
				"requirement_slice":  "requirements/{req_id}/sub-requirements/{sr_id}/requirement-slice.md",
				"decisions":          "requirements/{req_id}/sub-requirements/{sr_id}/decisions.md",
				"readme":             "requirements/{req_id}/sub-requirements/{sr_id}/README.md",
				"traceability":       "requirements/{req_id}/sub-requirements/{sr_id}/traceability.json",
				"design":             "requirements/{req_id}/sub-requirements/{sr_id}/design.md",
				"verification":       "requirements/{req_id}/sub-requirements/{sr_id}/verification.md",
				"spec":               "requirements/{req_id}/sub-requirements/{sr_id}/spec/spec.md",
				"plan":               "requirements/{req_id}/sub-requirements/{sr_id}/spec/plan.md",
				"tasks":              "requirements/{req_id}/sub-requirements/{sr_id}/spec/tasks.md",
				"ui_contract_index":  "requirements/{req_id}/sub-requirements/{sr_id}/contracts/ui-contract-index.json",
				"manifest":           "requirements/{req_id}/sub-requirements/{sr_id}/archive/{ts}/MANIFEST.json",
			},
		},
		"coordination": map[string]any{
			"mcp_url":     "",
			"pipeline_id": "",
			"party_id":    "",
		},
		"updated_at": timestamp,
		"updated_by": updatedBy,
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
			"spec_pipeline",
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
			"archived",
		},
		"source_index_policy": map[string]any{
			"required_traceability_keys": []string{
				"requirement",
				"figma",
				"api",
				"spec",
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
		"review_loop": map[string]any{
			"max_rounds": 3,
		},
		"spec_persistence": map[string]any{
			"_doc":     "spec-kit 持久化约定：活跃期 living（spec.md 唯一事实源，plan/tasks 原地再生），完结后 flow_forward（archive/ 冻结不可变，变更开新需求目录）",
			"active":   "living",
			"complete": "flow_forward",
			"living": map[string]any{
				"source_of_truth":   "spec/spec.md",
				"derived":           []string{"spec/plan.md", "spec/tasks.md"},
				"on_drift":          "downgrade_to_spec_ready",
				"before_regenerate": "旧关键决策先落 decisions.md",
			},
			"flow_forward": map[string]any{
				"immutable_root":  "archive",
				"change_requires": "new_requirement_dir",
			},
		},
		"verification_policy": map[string]any{
			"_doc":               "superpowers 验证纪律：merged/archived 必须有 verification.md 硬证据；验证器只查存在性与必备小节标题，不做语义判断",
			"required_at":        []string{"merged", "archived"},
			"artifact":           "verification.md",
			"required_sections":  []string{"评审轮次记录", "验证命令与结果", "签署"},
		},
		"archive": map[string]any{
			"_doc":                "flow-forward 冻结：merged -> archived 经 CP-ARCHIVE 确认，archive/ 区不可变（MANIFEST.json sha256 校验）",
			"require_checkpoint":  "CP-ARCHIVE",
			"immutable":           true,
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

	return nil
}

func managedDirectories() []string {
	return []string{
		".agents/skills",
		".ai-delivery/requirements",
		".ai-delivery/scripts",
		".ai-delivery/tests/ai-delivery-skills",
		".ai-delivery/meta",
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

// uiContractHookWrapper is the 2-line IDE adapter that points at the
// canonical gate under .ai-delivery/scripts/hooks/.
const uiContractHookWrapper = "#!/usr/bin/env bash\nexec bash \"$(git rev-parse --show-toplevel)/.ai-delivery/scripts/hooks/validate-ui-contract.sh\" \"$@\"\n"

func writeHookWrapper(target string) error {
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return fmt.Errorf("create parent for %s: %w", target, err)
	}
	if err := os.WriteFile(target, []byte(uiContractHookWrapper), 0o755); err != nil {
		return fmt.Errorf("write hook wrapper %s: %w", target, err)
	}
	return nil
}
