package workspace

import (
	"context"
	"encoding/json"
	"fmt"
	"path"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

// ContextFacts 是 reader 观察的选择事实；fact://context 不代表磁盘文件。
type ContextFacts struct {
	Artifacts            map[string]string `json:"artifacts"`
	DeclaredPaths        []string          `json:"declared_paths"`
	ObservedChangedPaths []string          `json:"observed_changed_paths"`
	Directories          []string          `json:"directories"`
	AgentPaths           []string          `json:"agent_paths"`
	GitChangesKnown      bool              `json:"git_changes_known"`
	GuidanceURI          string            `json:"guidance_uri"`
	ProjectRootResolved  string            `json:"project_root_resolved"`
	ScopePaths           []ScopePathFact   `json:"scope_paths"`
	RunOutputPaths       []string          `json:"run_output_paths,omitempty"`
	ArchiveOutputPaths   []string          `json:"archive_output_paths,omitempty"`
	ArchiveDate          string            `json:"archive_date,omitempty"`
	Historical           bool              `json:"historical,omitempty"`
}

// ScopePathFact 只冻结选择所需的存在性、类型和解析终点，不消费业务正文。
type ScopePathFact struct {
	Path         string `json:"path"`
	ResolvedPath string `json:"resolved_path"`
	Kind         string `json:"kind"`
}

func Facts(s model.Snapshot) (ContextFacts, error) {
	var f ContextFacts
	b, ok := s.Document(ContextFact)
	if !ok {
		return f, fmt.Errorf("缺少上下文选择事实")
	}
	err := json.Unmarshal(b, &f)
	return f, err
}
func (r Reader) Load(ctx context.Context, w model.Workspace, scope model.Scope, req model.ReadRequest) (model.Snapshot, error) {
	return r.load(ctx, w, scope, req, nil, false)
}

// LoadRun 让显式执行输入参与规范选择，只排除本切片 verification 与运行器输出。
func (r Reader) LoadRun(ctx context.Context, w model.Workspace, scope model.Scope, paths []string) (model.Snapshot, error) {
	return r.load(ctx, w, scope, model.ReadRequest{Action: &model.Action{Intent: "verify"}}, paths, true)
}

func (r Reader) load(ctx context.Context, w model.Workspace, scope model.Scope, req model.ReadRequest, declared []string, run bool) (model.Snapshot, error) {
	if err := req.Validate(); err != nil {
		return nil, err
	}
	if err := ValidateScope(scope); err != nil {
		return nil, err
	}
	if !filepath.IsAbs(w.ProjectRoot) || !inside(w.ProjectRoot, w.DeliveryRoot) {
		return nil, fmt.Errorf("无效工作区边界")
	}
	c := newConsumption(w.ProjectRoot)
	diags := []model.Diagnostic{}
	add := func(p, code string, err error) {
		diags = append(diags, inputDiagnostic(p, code, scope.SubrequirementID, err))
	}
	finish := func() (model.Snapshot, error) {
		s, err := NewSnapshot(w, scope, req, c.documents, c.identities(), diags)
		if err != nil {
			return nil, err
		}
		if err := r.Verify(ctx, s); err != nil {
			return nil, err
		}
		return s, nil
	}
	readAlias := func(name, relative string) ([]byte, bool, error) {
		body, ok, err := c.read(ctx, relative)
		if err == nil && ok {
			c.documents[FactPrefix+name] = append([]byte(nil), body...)
		}
		return body, ok, err
	}
	metadata := func(name, file string) (map[string]any, error) {
		rel, _ := filepath.Rel(w.ProjectRoot, filepath.Join(w.DeliveryRoot, "meta", file))
		p := filepath.ToSlash(rel)
		body, ok, err := readAlias(name, p)
		if err != nil {
			return nil, err
		}
		if !ok {
			return nil, fmt.Errorf("缺少 %s", p)
		}
		v, err := protocol.Object(body)
		if err != nil {
			return nil, &protocol.FormatError{Path: p, Cause: err}
		}
		if err := protocol.ValidateMetadata(name, v); err != nil {
			return nil, &protocol.FormatError{Path: p, Cause: err}
		}
		return v, nil
	}
	// 资源一旦安装，验证读取与完整动作身份共用消费集合；绝不调用项目旧核心。
	deliveryRel, _ := filepath.Rel(w.ProjectRoot, w.DeliveryRoot)
	manifestPath := filepath.ToSlash(filepath.Join(deliveryRel, assets.ManifestName))
	_, installed, manifestErr := c.read(ctx, manifestPath)
	if manifestErr != nil {
		return nil, &assets.Error{Path: manifestPath, Message: manifestErr.Error()}
	} else if installed || r.requireInstalledResources {
		if err := assets.Verify(filepath.ToSlash(deliveryRel), func(p string) ([]byte, bool, error) { return c.read(ctx, p) }); err != nil {
			return nil, err
		}
	}
	binding, err := metadata("binding", "project-binding.json")
	if err != nil {
		add("binding", "invalid_binding", err)
		return finish()
	}
	if err := validateBinding(binding, w.ProjectRoot, w.DeliveryRoot); err != nil {
		add("binding", "invalid_binding", err)
		return finish()
	}
	artifacts, err := ArtifactPaths(w, scope, binding)
	if err != nil {
		add("binding", "invalid_layout", err)
		return finish()
	}
	if _, err := metadata("policy", "workflow-policy.json"); err != nil {
		add("policy", "invalid_policy", err)
	}
	for _, name := range []string{"status", "requirement", "global_rules", "requirement_slice", "solution_design", "decisions"} {
		relative := artifacts[name]
		if err := governedPath(ctx, c, w, relative); err != nil {
			add(relative, "unsafe_path", err)
			continue
		}
		if _, _, err := readAlias(name, relative); err != nil {
			add(relative, "unreadable_source", err)
		}
	}
	if body, ok := c.documents[FactPrefix+"status"]; ok {
		status, err := protocol.Object(body)
		if err != nil {
			add(artifacts["status"], "invalid_status", &protocol.FormatError{Path: artifacts["status"], Cause: err})
		} else if err := protocol.RequireVersion(status, "_schema", "status"); err != nil {
			add(artifacts["status"], "invalid_status", &protocol.FormatError{Path: artifacts["status"], Cause: err})
		} else {
			entries, err := protocol.RequireObjectField(status, "sub_requirements", artifacts["status"])
			if err != nil {
				add(artifacts["status"], "invalid_status", err)
			} else if entry, ok := entries[scope.SubrequirementID].(map[string]any); !ok {
				add(artifacts["status"], "unknown_slice", fmt.Errorf("未知切片或切片不是对象: %s", scope.SubrequirementID))
			} else {
				current, ok := entry["status"].(string)
				if !ok || !knownStatus(current) {
					add(artifacts["status"], "invalid_status", fmt.Errorf("未知当前切片 status: %v", entry["status"]))
				}
				if err := protocol.RejectRemovedFields(entry); err != nil {
					add(artifacts["status"], "invalid_status", &protocol.FormatError{Path: artifacts["status"], Cause: err})
				}
			}
		}
	} else {
		add(artifacts["status"], "missing_status", fmt.Errorf("缺少 status 正文"))
	}
	facts := ContextFacts{Artifacts: artifacts, DeclaredPaths: []string{}, ObservedChangedPaths: []string{}, Directories: []string{}, AgentPaths: []string{}, GitChangesKnown: true, ProjectRootResolved: c.root}
	if req.Action != nil {
		if raw, ok := c.documents[FactPrefix+"status"]; ok {
			if status, err := protocol.Object(raw); err == nil {
				entries, _ := status["sub_requirements"].(map[string]any)
				entry, _ := entries[scope.SubrequirementID].(map[string]any)
				facts.Historical = entry["status"] == "archived"
			}
		}
	}
	if req.Action != nil && req.Action.Intent == "archive" {
		facts.ArchiveOutputPaths = []string{artifacts["delivery_report"], artifacts["retrospective_index"]}
		if !facts.Historical {
			facts.ArchiveDate = time.Now().UTC().Format("2006-01-02")
		}
	}
	if run {
		facts.RunOutputPaths = RunOutputPaths(w, artifacts)
	}
	if req.Context != nil {
		uri, err := GuidanceURI(req.Context.Role)
		if err != nil {
			return nil, err
		}
		facts.GuidanceURI = uri
		body, err := Resource(uri)
		if err != nil {
			return nil, err
		}
		c.documents[uri] = body
		if req.Context.BudgetChars < 0 {
			return nil, fmt.Errorf("budget_chars 不得为负数")
		}
		declared = req.Context.DeclaredPaths
	}
	for _, value := range declared {
		rel, err := NormalizePath(value)
		if err != nil {
			add(value, "unsafe_scope", err)
			continue
		}
		if strings.HasSuffix(value, "/") {
			rel += "/"
		}
		facts.DeclaredPaths = append(facts.DeclaredPaths, rel)
	}
	observed, known := []string{}, true
	if !facts.Historical {
		observed, known, err = ObservedChanges(ctx, w.ProjectRoot)
	}
	facts.GitChangesKnown = known
	if err != nil {
		add(".git", "git_changes_unknown", err)
	} else {
		facts.ObservedChangedPaths = FilterExactOutputs(FilterRunOutputs(observed, facts.RunOutputPaths), facts.ArchiveOutputPaths)
	}
	agents := map[string]bool{"AGENTS.md": true}
	for _, output := range facts.ArchiveOutputPaths {
		for parent := path.Dir(output); ; parent = path.Dir(parent) {
			agents[path.Join(parent, "AGENTS.md")] = true
			if parent == "." {
				break
			}
		}
	}
	dirs := map[string]bool{}
	scopeSeen := map[string]bool{}
	for _, value := range append(append([]string{}, facts.DeclaredPaths...), facts.ObservedChangedPaths...) {
		rel, err := NormalizePath(value)
		if err != nil {
			add(value, "unsafe_scope", err)
			continue
		}
		observation, err := c.observeScope(ctx, rel)
		if err != nil {
			add(value, "unsafe_scope", err)
			continue
		}
		if !scopeSeen[rel] {
			facts.ScopePaths = append(facts.ScopePaths, observation)
			scopeSeen[rel] = true
		}
		isDir := strings.HasSuffix(value, "/") || observation.Kind == "directory"
		parent := path.Dir(rel)
		if isDir {
			parent = rel
			dirs[rel] = true
		}
		for {
			agents[path.Join(parent, "AGENTS.md")] = true
			if parent == "." {
				break
			}
			parent = path.Dir(parent)
		}
	}
	for p := range dirs {
		facts.Directories = append(facts.Directories, p)
	}
	sort.Strings(facts.Directories)
	for p := range agents {
		facts.AgentPaths = append(facts.AgentPaths, p)
	}
	sort.Strings(facts.AgentPaths)
	for _, p := range facts.AgentPaths {
		if _, _, err := c.read(ctx, p); err != nil {
			add(p, "unreadable_agents", err)
		}
	}
	for _, p := range []string{".trellis/spec/index.md", "docs/knowledge/index.md", "docs/harness/index.md"} {
		if len(FilterExactOutputs([]string{p}, facts.ArchiveOutputPaths)) == 0 {
			continue
		}
		if _, _, err := c.read(ctx, p); err != nil {
			add(p, "unreadable_index", err)
		}
	}
	body, err := json.Marshal(facts)
	if err != nil {
		return nil, err
	}
	c.documents[ContextFact] = body
	return finish()
}
func knownStatus(status string) bool {
	for _, v := range protocol.Defaults("policy")["status_sequence"].([]any) {
		if v == status {
			return true
		}
	}
	switch status {
	case "blocked_missing_requirement", "blocked_requirement_conflict", "blocked_dependency",
		"blocked_missing_design", "blocked_requirement_figma_conflict", "blocked_figma_conflict",
		"blocked_missing_state_code", "blocked_missing_visual_truth", "blocked_verification_failure",
		"blocked_design_mismatch", "blocked_dependency_slice", "blocked_merge_conflict":
		return true
	}
	return false
}
func governedPath(ctx context.Context, c *consumption, w model.Workspace, relative string) error {
	resolved, _, err := c.resolve(ctx, filepath.Join(c.root, relative), 0, map[string]bool{})
	if err != nil {
		return err
	}
	governed, err := filepath.EvalSymlinks(w.DeliveryRoot)
	if err != nil {
		return err
	}
	actualRoot, err := filepath.EvalSymlinks(w.ProjectRoot)
	if err != nil {
		return err
	}
	if !inside(governed, filepath.Join(actualRoot, resolved)) {
		return fmt.Errorf("治理产物实际目标超出治理根: %s", relative)
	}
	return nil
}
