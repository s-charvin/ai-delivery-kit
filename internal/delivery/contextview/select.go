package contextview

import (
	"crypto/sha256"
	"fmt"
	"path"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

type SourceSpec struct {
	Path, Kind, Reason string
	Required           bool
}
type Selector struct{}

var _ model.ContextSelector = Selector{}

func diagnostic(s model.Snapshot, p, code string, err error) model.Diagnostic {
	return model.Diagnostic{Code: code, Path: p, Category: "context_input", Scope: s.Scope().SubrequirementID, Message: err.Error(), Recovery: "修复来源或补读完整正文后重新生成上下文"}
}
func stringsField(m map[string]any, key string) ([]string, error) {
	v, exists := m[key]
	if !exists {
		return nil, nil
	}
	items, ok := v.([]any)
	if !ok {
		return nil, fmt.Errorf("%s 必须为字符串数组", key)
	}
	out := make([]string, 0, len(items))
	for _, v := range items {
		s, ok := v.(string)
		if !ok || s == "" {
			return nil, fmt.Errorf("%s 必须为非空字符串数组", key)
		}
		out = append(out, s)
	}
	return out, nil
}
func has(items []string, value string) bool {
	for _, v := range items {
		if v == value {
			return true
		}
	}
	return false
}

// Plan 只按已冻结的角色、范围和原文声明选择材料，不判断推进权限。
func Plan(s model.Snapshot, req model.ContextRequest) ([]SourceSpec, []model.Diagnostic) {
	specs := []SourceSpec{}
	diags := []model.Diagnostic{}
	addError := func(p, code string, err error) { diags = append(diags, diagnostic(s, p, code, err)) }
	facts, err := workspace.Facts(s)
	if err != nil {
		addError(workspace.ContextFact, "missing_context_facts", err)
		return specs, diags
	}
	positions := map[string]int{}
	add := func(p, kind string, required bool, reason string) {
		if i, ok := positions[p]; ok {
			previous := &specs[i]
			if previous.Kind != kind {
				addError(p, "source_kind_conflict", fmt.Errorf("同一来源性质冲突: %s / %s", previous.Kind, kind))
			}
			previous.Required = previous.Required || required
			previous.Reason += "; " + reason
			return
		}
		positions[p] = len(specs)
		specs = append(specs, SourceSpec{p, kind, reason, required})
	}
	present := map[string]bool{}
	for _, identity := range s.Files() {
		if identity.Kind != "absent" {
			present[identity.Path] = true
		}
	}
	for _, p := range facts.AgentPaths {
		_, ok := s.Document(p)
		required := ok || present[p]
		if required || p == "AGENTS.md" {
			add(p, "standard", required, "项目及范围规范")
		}
	}
	statusBody, ok := workspace.Fact(s, "status")
	if !ok {
		addError("status", "missing_status", fmt.Errorf("缺少 status"))
		return specs, diags
	}
	status, err := protocol.Object(statusBody)
	if err != nil {
		addError("status", "invalid_status", err)
		return specs, diags
	}
	entries, _ := status["sub_requirements"].(map[string]any)
	entry, _ := entries[s.Scope().SubrequirementID].(map[string]any)
	current, _ := entry["status"].(string)
	active := has([]string{"design_ready", "in_dev", "visual_acceptance_passed", "merged"}, current)
	design, _ := workspace.Fact(s, "solution_design")
	referenced := func(p string) bool {
		expression := `(^|[^\pL\pN_.-])` + regexp.QuoteMeta(path.Base(p)) + `([^\pL\pN_.-]|$)`
		return regexp.MustCompile(expression).Match(design)
	}
	for _, name := range []string{"requirement", "global_rules", "requirement_slice", "solution_design", "decisions"} {
		p := facts.Artifacts[name]
		_, exists := s.Document(p)
		required := name == "requirement" || name == "solution_design" && active || name == "requirement_slice" && referenced(p)
		if required || exists {
			add(p, "task", true, "当前需求与切片合同正文")
		}
	}
	if facts.GuidanceURI != "" {
		add(facts.GuidanceURI, "guidance", true, req.Role+" 阶段规则；补读命令: ai-delivery info --resource "+facts.GuidanceURI)
	}
	body, ok := workspace.Fact(s, "policy")
	if !ok {
		addError("policy", "missing_policy", fmt.Errorf("缺少 policy"))
		return specs, diags
	}
	policy, err := protocol.Object(body)
	if err != nil {
		addError("policy", "invalid_policy", err)
		return specs, diags
	}
	contextConfig, exists := policy["context"]
	var sources []any
	if exists {
		m, ok := contextConfig.(map[string]any)
		if !ok {
			addError("policy", "invalid_sources", fmt.Errorf("context 必须为对象"))
			return specs, diags
		}
		if v, exists := m["sources"]; exists {
			var ok bool
			sources, ok = v.([]any)
			if !ok {
				addError("policy", "invalid_sources", fmt.Errorf("context.sources 必须为数组"))
				return specs, diags
			}
		}
	}
	selection := append(append([]string{}, facts.DeclaredPaths...), facts.ObservedChangedPaths...)
	for _, dir := range facts.Directories {
		selection = append(selection, strings.TrimRight(dir, "/")+"/")
	}
	registered := map[string]bool{}
	for _, v := range sources {
		source, ok := v.(map[string]any)
		if !ok {
			addError("policy", "invalid_source", fmt.Errorf("来源必须是对象"))
			continue
		}
		p, ok := source["path"].(string)
		if !ok || p == "" {
			addError("policy", "invalid_source", fmt.Errorf("来源必须包含 path"))
			continue
		}
		p, err = workspace.NormalizePath(p)
		if err != nil {
			addError("policy", "invalid_source", err)
			continue
		}
		registered[p] = true
		roles, err := stringsField(source, "roles")
		if err != nil {
			addError(p, "invalid_source", err)
			continue
		}
		valid := true
		for _, role := range roles {
			if _, err := workspace.GuidanceURI(role); err != nil {
				addError(p, "invalid_source", err)
				valid = false
			}
		}
		patterns, err := stringsField(source, "paths")
		if err != nil {
			addError(p, "invalid_source", err)
			continue
		}
		kind := "standard"
		if value, exists := source["kind"]; exists {
			kind, ok = value.(string)
			if !ok || !has([]string{"knowledge", "standard", "advice"}, kind) {
				addError(p, "invalid_source", fmt.Errorf("未知来源性质"))
				valid = false
			}
		}
		required := true
		for _, field := range []string{"required", "writable"} {
			if value, exists := source[field]; exists {
				b, ok := value.(bool)
				if !ok {
					addError(p, "invalid_source", fmt.Errorf("%s 必须为布尔值", field))
					valid = false
				} else if field == "required" {
					required = b
				}
			}
		}
		if !valid {
			continue
		}
		if len(roles) > 0 && !has(roles, req.Role) {
			continue
		}
		if len(patterns) > 0 && len(selection) > 0 {
			matched := false
			for _, p := range selection {
				for _, pat := range patterns {
					matched = matched || Match(pat, p)
				}
			}
			if !matched {
				continue
			}
		}
		add(p, kind, required, "登记来源与角色/范围匹配；不授予写入权")
	}
	for _, p := range []string{".trellis/spec/index.md", "docs/knowledge/index.md", "docs/harness/index.md"} {
		if _, ok := s.Document(p); ok && !registered[p] {
			add(p, "knowledge", false, "已有框架索引；不能代替叶子来源正文")
		}
	}
	return specs, diags
}

// SourceBodyHealthy 是正文健康事实，不包含来源适用性、预算或动作授权。
func SourceBodyHealthy(body []byte, present bool) bool {
	return present && utf8.Valid(body) && strings.TrimSpace(string(body)) != ""
}

func (Selector) Select(s model.Snapshot, req model.ContextRequest) model.ContextView {
	view := model.ContextView{ContextComplete: true, Sources: []model.ContextSource{}, Diagnostics: s.Diagnostics()}
	specs, diags := Plan(s, req)
	view.Diagnostics = append(view.Diagnostics, diags...)
	budget := req.BudgetChars
	for _, spec := range specs {
		source := model.ContextSource{Path: spec.Path, Kind: spec.Kind, Required: spec.Required, Delivery: "missing", Reason: spec.Reason}
		body, ok := s.Document(spec.Path)
		if SourceBodyHealthy(body, ok) {
			digest := fmt.Sprintf("%x", sha256.Sum256(body))
			source.SHA256 = &digest
			source.Delivery = "needs_read"
			count := utf8.RuneCount(body)
			if count <= budget {
				value := string(body)
				source.Body = &value
				source.Delivery = "provided"
				budget -= count
			}
		} else if spec.Required {
			view.Diagnostics = append(view.Diagnostics, diagnostic(s, spec.Path, "missing_source", fmt.Errorf("必需来源缺失、为空或不是 UTF-8 正文")))
		}
		if spec.Required && source.Delivery != "provided" {
			view.ContextComplete = false
		}
		view.Sources = append(view.Sources, source)
	}
	if len(view.Diagnostics) > 0 {
		view.ContextComplete = false
	}
	return view
}
