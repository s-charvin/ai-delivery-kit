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
	// Report, when non-nil, receives IDE gate amendment and backup results from this run.
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
		"version":          2,
		"project_id":       cfg.ProjectID,
		"project_root":     cfg.RepoRoot,
		"ai_delivery_path": ".ai-delivery",
		"layout": map[string]any{
			"requirement_root":    "requirements/{req_id}",
			"sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
			"requirement_artifacts": map[string]any{
				"status":            "requirements/{req_id}/status.json",
				"requirement":       "requirements/{req_id}/requirement.md",
				"breakdown_summary": "requirements/{req_id}/breakdown-summary.md",
				"global_rules":      "requirements/{req_id}/global-rules.md",
				"dependency_graph":  "requirements/{req_id}/dependency-graph.json",
				"progress":          "requirements/{req_id}/progress.md",
				"todo":              "requirements/{req_id}/todo.md",
				"delivery_report":   "requirements/{req_id}/delivery-report.md",
			},
			"sub_requirement_artifacts": map[string]any{
				"requirement_slice": "requirements/{req_id}/sub-requirements/{sr_id}/requirement-slice.md",
				"decisions":         "requirements/{req_id}/sub-requirements/{sr_id}/decisions.md",
				"readme":            "requirements/{req_id}/sub-requirements/{sr_id}/README.md",
				"traceability":      "requirements/{req_id}/sub-requirements/{sr_id}/traceability.json",
				"solution_design":   "requirements/{req_id}/sub-requirements/{sr_id}/design.md",
				"verification":      "requirements/{req_id}/sub-requirements/{sr_id}/verification.md",
				"visual_acceptance": "requirements/{req_id}/sub-requirements/{sr_id}/visual-acceptance.json",
				"spec":              "requirements/{req_id}/sub-requirements/{sr_id}/spec/spec.md",
				"plan":              "requirements/{req_id}/sub-requirements/{sr_id}/spec/plan.md",
				"tasks":             "requirements/{req_id}/sub-requirements/{sr_id}/spec/tasks.md",
				"ui_truth_index":    "requirements/{req_id}/sub-requirements/{sr_id}/contracts/ui-truth-index.json",
				"manifest":          "requirements/{req_id}/sub-requirements/{sr_id}/archive/{ts}/MANIFEST.json",
			},
		},
		"updated_at": timestamp,
		"updated_by": updatedBy,
	}); err != nil {
		return err
	}

	if err := writeJSONIfMissing(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/workflow-policy.json"), map[string]any{
		"version": 2,
		"truth_policy": map[string]any{
			"functional_source": "Requirement",
			"visual_source":     "Figma",
			"visual_sources_by_mode": map[string]any{
				"none":             []string{},
				"existing":         []string{},
				"runtime-baseline": []string{"requirement", "project", "user-decision"},
				"figma":            []string{"figma", "requirement", "project", "user-decision"},
			},
			"conflict_behavior": "block",
		},
		"workflow_gates": []string{
			"requirement_breakdown",
			"spec_pipeline",
			"implementation",
		},
		"capabilities": map[string]any{
			"ui_truth": map[string]any{
				"modes": map[string]any{
					"none": map[string]any{
						"enabled":          false,
						"stage2":           false,
						"requires_index":   false,
						"requires_preview": false,
						"final_acceptance": "ordinary_behavior_and_semantic_tests",
					},
					"existing": map[string]any{
						"enabled":          false,
						"stage2":           false,
						"requires_index":   false,
						"requires_preview": false,
						"final_acceptance": "ordinary_behavior_and_semantic_tests",
					},
					"runtime-baseline": map[string]any{
						"enabled":          true,
						"stage2":           true,
						"requires_index":   true,
						"requires_preview": true,
						"final_acceptance": "visual_acceptance",
					},
					"figma": map[string]any{
						"enabled":          true,
						"stage2":           true,
						"requires_index":   true,
						"requires_preview": true,
						"final_acceptance": "visual_acceptance",
					},
				},
				"checkpoint": "CP-UI",
				"index":      "contracts/ui-truth-index.json",
				"preview":    "official_host_stack_preview",
			},
		},
		"solution_design": map[string]any{
			"modes":           []string{"none", "light", "full"},
			"full_checkpoint": "CP-DESIGN",
			"artifact_key":    "solution_design",
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
			"solution_design_full":     []string{"CP-DESIGN"},
			"development_confirmation": []string{"CP-001"},
			"archive_confirmation":     []string{"CP-ARCHIVE"},
		},
		"worktree_policy": map[string]any{
			"require_isolated_worktree":           true,
			"allow_precreate_before_dependencies": false,
			"ui_stage2_reuses_worktree":           true,
		},
		"review_loop": map[string]any{
			"max_rounds": 3,
		},
		"spec_persistence": map[string]any{
			"_doc":     "Spec-kit persistence: active work uses living mode with spec.md as the sole source of truth and in-place plan/tasks regeneration; completed work uses flow_forward with an immutable archive and a new requirement directory for changes",
			"active":   "living",
			"complete": "flow_forward",
			"living": map[string]any{
				"source_of_truth":   "spec/spec.md",
				"derived":           []string{"spec/plan.md", "spec/tasks.md"},
				"on_drift":          "downgrade_to_spec_ready",
				"before_regenerate": "Record prior key decisions in decisions.md before regeneration",
			},
			"flow_forward": map[string]any{
				"immutable_root":  "archive",
				"change_requires": "new_requirement_dir",
			},
		},
		"verification_policy": map[string]any{
			"_doc":        "Verification discipline: merged/archived requires verification.md evidence; language-neutral markers keep human-readable headings localizable",
			"required_at": []string{"merged", "archived"},
			"artifact":    "verification.md",
			"required_markers": []string{
				"ai-delivery-verification:review-rounds",
				"ai-delivery-verification:commands-results",
				"ai-delivery-verification:sign-off",
			},
		},
		"archive": map[string]any{
			"_doc":               "Flow-forward freeze: merged -> archived requires CP-ARCHIVE confirmation; archive/ is immutable and verified by MANIFEST.json SHA-256",
			"require_checkpoint": "CP-ARCHIVE",
			"immutable":          true,
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
