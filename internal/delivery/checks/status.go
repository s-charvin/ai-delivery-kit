package checks

import (
	"fmt"
	"sort"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func statusData(s model.Snapshot) (map[string]any, map[string]any, error) {
	b, ok := model.Fact(s, "status")
	if !ok {
		return nil, nil, fmt.Errorf("缺少 status")
	}
	p := "status"
	if facts, e := workspace.Facts(s); e == nil {
		p = facts.Artifacts["status"]
	}
	d, err := protocol.Object(b)
	if err != nil {
		return nil, nil, &protocol.FormatError{Path: p, Cause: err}
	}
	if err = protocol.RequireVersion(d, "_schema", "status"); err != nil {
		return nil, nil, &protocol.FormatError{Path: p + "#/_schema", Cause: err}
	}
	entries, err := protocol.RequireObjectField(d, "sub_requirements", p)
	return d, entries, err
}
func selectedEntry(s model.Snapshot) map[string]any {
	_, entries, _ := statusData(s)
	e, _ := entries[s.Scope().SubrequirementID].(map[string]any)
	return e
}
func knownStatus(v any) bool {
	str, ok := v.(string)
	if !ok {
		return false
	}
	for _, x := range protocol.Defaults("policy")["status_sequence"].([]any) {
		if str == x {
			return true
		}
	}
	return contains([]string{"blocked_missing_requirement", "blocked_requirement_conflict", "blocked_dependency", "blocked_missing_design", "blocked_requirement_figma_conflict", "blocked_figma_conflict", "blocked_missing_state_code", "blocked_missing_visual_truth", "blocked_verification_failure", "blocked_design_mismatch", "blocked_dependency_slice", "blocked_merge_conflict"}, str)
}
func entryErrors(e map[string]any) []error {
	if e == nil {
		return []error{fmt.Errorf("切片必须为对象")}
	}
	out := []error{}
	if err := protocol.RejectRemovedFields(e); err != nil {
		out = append(out, &protocol.FormatError{Cause: err})
	}
	if !knownStatus(e["status"]) {
		out = append(out, &protocol.FormatError{Cause: fmt.Errorf("status 实际类型=%T，实际值=%v；当前要求合法状态", e["status"], e["status"])})
	}
	mode, _ := e["ui_truth_mode"].(string)
	if !contains([]string{"none", "existing", "runtime-baseline", "figma"}, mode) {
		out = append(out, &protocol.FormatError{Cause: fmt.Errorf("ui_truth_mode 实际类型=%T，实际值=%v；当前要求 none/existing/runtime-baseline/figma", e["ui_truth_mode"], e["ui_truth_mode"])})
	}
	for _, key := range []string{"ui_bearing", "state_flow_required", "user_decision_required"} {
		if _, ok := e[key].(bool); !ok {
			out = append(out, &protocol.FormatError{Cause: fmt.Errorf("%s 实际类型=%T，实际值=%v；当前要求布尔值", key, e[key], e[key])})
		}
	}
	if b, ok := e["ui_bearing"].(bool); ok && b != (mode != "none") {
		out = append(out, fmt.Errorf("%s", "ui_bearing 与 ui_truth_mode 不一致"))
	}
	if (mode == "none" || mode == "existing") && (e["status"] == "acceptance_frozen" || e["status"] == "visual_acceptance_passed") {
		out = append(out, fmt.Errorf("%s", "当前 mode 不适用 UI truth 阶段状态"))
	}
	if _, ok := e["design_review"].(map[string]any); !ok {
		out = append(out, &protocol.FormatError{Cause: fmt.Errorf("design_review 实际类型=%T，实际值=%v；当前要求对象", e["design_review"], e["design_review"])})
	}
	for _, key := range []string{"blocked_from_status", "resume_target_status"} {
		if v, exists := e[key]; exists && v != nil {
			str, ok := v.(string)
			if !ok || !knownStatus(str) || strings.HasPrefix(str, "blocked_") {
				out = append(out, fmt.Errorf("%s", key+" 必须为正常状态"))
			}
		}
	}
	if v, exists := e["blocker_scope"]; exists && v != nil {
		str, ok := v.(string)
		if !ok || !contains([]string{"slice_local", "requirement_global", "action_level_integration"}, str) {
			out = append(out, fmt.Errorf("%s", "未知 blocker_scope"))
		}
	}
	if str, _ := e["status"].(string); strings.HasPrefix(str, "blocked_") {
		if e["blocked_from_status"] == "merged" || e["blocked_from_status"] == "archived" {
			out = append(out, fmt.Errorf("%s", "终态不能作为阻塞恢复来源"))
		}
	}
	return out
}

func validateStatus(s model.Snapshot, paths map[string]string) []model.Diagnostic {
	rootDiagnostic := func(message string) model.Diagnostic {
		d := diagnostic(s, "status", paths["status"], message)
		d.Scope = s.Scope().RequirementID
		return d
	}
	data, _, err := statusData(s)
	if err != nil {
		d := diagnosticCause(s, "status", paths["status"], err)
		d.Scope = s.Scope().RequirementID
		return []model.Diagnostic{d}
	}
	out := validateSliceStatus(s, s.Scope(), paths)
	rootFields := map[string]any{}
	for key, value := range data {
		if key != "sub_requirements" {
			rootFields[key] = value
		}
	}
	if err := protocol.RejectRemovedFields(rootFields); err != nil {
		d := diagnosticCause(s, "status", paths["status"], &protocol.FormatError{Path: paths["status"], Cause: err})
		d.Scope = s.Scope().RequirementID
		out = append(out, d)
	}
	if cp := data["current_checkpoint"]; cp != nil {
		str, ok := cp.(string)
		if !ok || !contains([]string{"CP-UI", "CP-DESIGN", "CP-002", "CP-ARCHIVE"}, str) {
			out = append(out, rootDiagnostic("未知 current_checkpoint"))
		}
	}
	return out
}

// 当前切片与可达上游共用字段、mode 和产物身份规则；只消费既有冻结事实。
func validateSliceStatus(s model.Snapshot, scope model.Scope, paths map[string]string) []model.Diagnostic {
	_, entries, err := statusData(s)
	if err != nil {
		return nil
	}
	entry, _ := entries[scope.SubrequirementID].(map[string]any)
	out := []model.Diagnostic{}
	add := func(p, message string) {
		d := diagnostic(s, "status", p, message)
		d.Scope = scope.SubrequirementID
		out = append(out, d)
	}
	for _, cause := range entryErrors(entry) {
		d := diagnosticCause(s, "status", paths["status"]+"#/sub_requirements/"+scope.SubrequirementID, cause)
		d.Scope = scope.SubrequirementID
		out = append(out, d)
	}
	mode := entry["ui_truth_mode"]
	if mode == "none" || mode == "existing" {
		for _, key := range []string{"ui_truth_index", "visual_acceptance"} {
			if identity, ok, err := workspace.Identity(s, paths[key]); err != nil {
				add(paths[key], err.Error())
			} else if ok && identity.Kind != "absent" {
				add(paths[key], "当前 mode 禁止 "+key)
				continue
			}
			for _, f := range s.Files() {
				if f.Path == paths[key] && f.Kind != "absent" {
					add(paths[key], "当前 mode 禁止 "+key)
					break
				}
			}
		}
	}
	return out
}

// dependencies 返回当前切片可达上游；只把有已知依赖路径的局部错误传递到当前切片。
func dependencies(s model.Snapshot, graph string) ([]string, []string) {
	_, entries, err := statusData(s)
	if err != nil {
		return nil, []string{err.Error()}
	}
	body, exists := s.Document(graph)
	if !exists {
		active := false
		if a := s.Request().Action; a != nil && a.TargetStatus != "" && a.TargetStatus != "draft" && a.TargetStatus != "merged" && a.TargetStatus != "archived" {
			active = true
		}
		for _, value := range entries {
			e, ok := value.(map[string]any)
			if !ok || (e["status"] != "draft" && e["status"] != "merged" && e["status"] != "archived") {
				active = true
			}
		}
		if len(entries) > 1 && active {
			return nil, []string{"多切片缺少依赖图，无法证明独立性"}
		}
		return nil, nil
	}
	data, err := protocol.Object(body)
	if err != nil {
		return nil, []string{err.Error()}
	}
	nodes := data
	if raw, ok := data["nodes"]; ok {
		nodes, ok = raw.(map[string]any)
		if !ok {
			return nil, []string{"nodes 必须为对象"}
		}
	} else if raw, ok := data["sub_requirements"]; ok {
		nodes, ok = raw.(map[string]any)
		if !ok {
			return nil, []string{"sub_requirements 必须为对象"}
		}
	} else if raw, ok := data["edges"]; ok {
		edges, ok := raw.([]any)
		if !ok {
			return nil, []string{"edges 必须为对象列表"}
		}
		nodes = map[string]any{}
		for _, v := range edges {
			node, ok := v.(map[string]any)
			if !ok {
				return nil, []string{"edges 必须为对象列表"}
			}
			id, ok := node["id"].(string)
			if !ok {
				id, ok = node["subreq_id"].(string)
			}
			if !ok || id == "" || nodes[id] != nil {
				return nil, []string{"edges 节点 ID 缺失或重复"}
			}
			nodes[id] = node
		}
	}
	keys := []string{}
	for id := range nodes {
		keys = append(keys, id)
	}
	sort.Strings(keys)
	for _, id := range keys {
		if _, ok := entries[id]; !ok {
			return nil, []string{"未知依赖节点: " + id}
		}
	}
	visiting, seen := map[string]bool{}, map[string]bool{}
	parents := []string{}
	out := []string{}
	var visit func(string, int)
	visit = func(id string, depth int) {
		if depth > 64 {
			out = append(out, "依赖深度超过 64")
			return
		}
		if visiting[id] {
			out = append(out, "依赖图包含环: "+id)
			return
		}
		if seen[id] {
			return
		}
		seen[id] = true
		visiting[id] = true
		defer delete(visiting, id)
		if id != s.Scope().SubrequirementID {
			parents = append(parents, id)
		}
		raw, exists := nodes[id]
		if !exists {
			return
		}
		node, ok := raw.(map[string]any)
		if !ok {
			out = append(out, "依赖节点必须为对象: "+id)
			return
		}
		raw, exists = node["depends_on"]
		if !exists {
			return
		}
		list, ok := raw.([]any)
		if !ok {
			out = append(out, "depends_on 必须为字符串列表: "+id)
			return
		}
		duplicate := map[string]bool{}
		for _, v := range list {
			parent, ok := v.(string)
			if !ok || parent == "" {
				out = append(out, "depends_on 必须为字符串列表: "+id)
				continue
			}
			if duplicate[parent] {
				out = append(out, "依赖重复: "+parent)
			}
			duplicate[parent] = true
			if _, ok := entries[parent]; !ok {
				out = append(out, "未知上游: "+parent)
				continue
			}
			visit(parent, depth+1)
		}
	}
	visit(s.Scope().SubrequirementID, 0)
	for _, id := range parents {
		e, _ := entries[id].(map[string]any)
		if e["status"] != "merged" && e["status"] != "archived" {
			out = append(out, "上游尚未合并: "+id)
		}
	}
	sort.Strings(parents)
	return parents, out
}

func dependencyPaths(s model.Snapshot, ids []string) (map[string]map[string]string, error) {
	b, _ := model.Fact(s, "binding")
	binding, err := protocol.Object(b)
	if err != nil {
		return nil, err
	}
	out := map[string]map[string]string{}
	for _, id := range ids {
		paths, err := workspace.ArtifactPaths(s.Workspace(), model.Scope{RequirementID: s.Scope().RequirementID, SubrequirementID: id}, binding)
		if err != nil {
			return nil, err
		}
		out[id] = paths
	}
	return out, nil
}

// ValidateStatus 复用当前字段与 mode 规则，只返回格式诊断，不授予动作权限。
func ValidateStatus(s model.Snapshot) []model.Diagnostic {
	facts, err := workspace.Facts(s)
	if err != nil {
		return []model.Diagnostic{diagnostic(s, "status", "", err.Error())}
	}
	return validateStatus(s, facts.Artifacts)
}
