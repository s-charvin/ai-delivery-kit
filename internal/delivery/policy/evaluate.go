package policy

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
)

type Policy struct{}

var _ model.Policy = Policy{}

func entry(s model.Snapshot) map[string]any {
	b, _ := model.Fact(s, "status")
	var status struct {
		Entries map[string]map[string]any `json:"sub_requirements"`
	}
	if json.Unmarshal(b, &status) != nil {
		return nil
	}
	return status.Entries[s.Scope().SubrequirementID]
}
func artifacts(s model.Snapshot) map[string]string {
	b, _ := model.Fact(s, "context")
	var f struct {
		Artifacts map[string]string `json:"artifacts"`
	}
	_ = json.Unmarshal(b, &f)
	return f.Artifacts
}
func designNeeded(a model.Action) bool {
	return a.TargetStatus == "design_ready" || a.Intent == "implement" || a.Intent == "verify" || a.Intent == "merge" || a.Intent == "archive"
}

// PlanChecks 的核心义务只由动作和冻结事实推导；配置/verification 的 required=false 不能删项。
func (Policy) PlanChecks(s model.Snapshot, a model.Action) []model.CheckSpec {
	return planChecks(s, a, false)
}

// PlanRun 只选择尝试验证所需前置，成功验证与 fresh review 仍由推进动作要求。
func (Policy) PlanRun(s model.Snapshot) []model.CheckSpec {
	return planChecks(s, model.Action{Intent: "verify"}, true)
}

func planChecks(s model.Snapshot, a model.Action, run bool) []model.CheckSpec {
	paths := artifacts(s)
	out := []model.CheckSpec{}
	add := func(id string, names ...string) {
		c := model.CheckSpec{ID: id, Applicability: "required"}
		for _, name := range names {
			if p := paths[name]; p != "" {
				c.InputPaths = append(c.InputPaths, p)
				c.SourceRefs = append(c.SourceRefs, p)
			}
		}
		out = append(out, c)
	}
	if entry(s)["status"] == "archived" {
		add("status", "status", "ui_truth_index", "visual_acceptance")
		add("archive_history", "solution_design", "verification", "ui_truth_index", "visual_acceptance")
		return out
	}
	add("inputs", "requirement", "requirement_slice", "global_rules")
	add("status", "status", "ui_truth_index", "visual_acceptance")
	add("dependencies", "dependency_graph")
	e := entry(s)
	truth := e["ui_truth_mode"] == "figma" || e["ui_truth_mode"] == "runtime-baseline"
	status, _ := e["status"].(string)
	if strings.HasPrefix(status, "blocked_") {
		status, _ = e["blocked_from_status"].(string)
	}
	frozen := status != "draft" && status != "split_ready"
	if truth && (frozen || a.TargetStatus == "acceptance_frozen") {
		add("ui_index", "ui_truth_index")
	}
	if truth && !run && (a.Intent == "verify" || a.Intent == "merge" || a.Intent == "archive" || status == "visual_acceptance_passed" || status == "merged" || status == "archived") {
		add("ui_acceptance", "visual_acceptance", "ui_truth_index")
	}
	if designNeeded(a) {
		add("design", "solution_design")
	}
	if !run && (a.Intent == "verify" || a.Intent == "merge" || a.Intent == "archive" || entry(s)["status"] == "blocked_verification_failure" && a.TargetStatus != "") {
		add("verification", "verification", "solution_design")
	}
	if a.Intent == "archive" {
		add("archive_ready", "retrospective")
	}
	return out
}

func diag(s model.Snapshot, code, message, recovery string) model.Diagnostic {
	return model.Diagnostic{Code: code, Category: "policy", Scope: s.Scope().SubrequirementID, Message: message, Recovery: recovery}
}

func (p Policy) Evaluate(s model.Snapshot, a model.Action, checks []model.CheckSpec, obs []model.CheckObservation) model.Decision {
	return p.evaluate(s, a, checks, obs, false)
}

func (p Policy) EvaluateRun(s model.Snapshot, checks []model.CheckSpec, obs []model.CheckObservation) model.Decision {
	return p.evaluate(s, model.Action{Intent: "verify"}, checks, obs, true)
}

func (p Policy) evaluate(s model.Snapshot, a model.Action, checks []model.CheckSpec, obs []model.CheckObservation, run bool) model.Decision {
	required := planChecks(s, a, run)
	d := model.Decision{Action: a, Checks: model.CloneCheckSpecs(required), Diagnostics: s.Diagnostics()}
	reject := func(code, message, recovery string) {
		d.Diagnostics = append(d.Diagnostics, diag(s, code, message, recovery))
	}
	req := s.Request()
	if req.Action == nil || req.Context != nil || *req.Action != a {
		reject("action_identity_mismatch", "快照不是当前动作请求", "重新为相同 intent/target 读取动作快照")
	}
	if !reflect.DeepEqual(required, checks) {
		reject("check_plan_mismatch", "调用者检查集与核心必需集合不一致", "重新从当前快照生成检查计划")
	}
	e := entry(s)
	status, _ := e["status"].(string)
	mode, _ := e["ui_truth_mode"].(string)
	if mode != "none" && mode != "existing" && mode != "runtime-baseline" && mode != "figma" {
		reject("unknown_ui_mode", "未知 UI truth 适用性", "修复当前切片 ui_truth_mode")
	}

	source := status
	if strings.HasPrefix(status, "blocked_") {
		from, _ := e["blocked_from_status"].(string)
		resume, _ := e["resume_target_status"].(string)
		if from == "merged" || from == "archived" || from == "" || resume == "" {
			reject("invalid_recovery", "阻塞恢复来源/目标无效", "修复原始 blocker 元数据")
		}
		if !(run && status == "blocked_verification_failure") && (a.TargetStatus == "" || a.TargetStatus != resume) {
			reject("blocked_action", "阻塞切片只能按记录的恢复目标重新验收", "选择 resume_target_status 并重新检查所有目标合同")
		}
		source = from
	}
	legalAction := legal(source, mode, a)
	if run {
		legalAction = legalAction || legal(source, mode, model.Action{Intent: "implement"})
	}
	if !legalAction {
		reject("illegal_transition", fmt.Sprintf("不允许 %s 执行 %s → %s", status, a.Intent, a.TargetStatus), "恢复最窄动作；不得跳过状态边或设计评审")
	}
	seen := map[string]model.CheckObservation{}
	for _, o := range obs {
		if _, ok := seen[o.CheckID]; ok {
			reject("duplicate_observation", "重复检查结果: "+o.CheckID, "重新采集唯一结果")
		}
		seen[o.CheckID] = o
	}
	for _, c := range required {
		if c.Applicability == "unknown" {
			reject("unknown_applicability", "检查适用性未知: "+c.ID, "补全适用性来源")
			continue
		}
		if c.Applicability == "not_applicable" {
			continue
		}
		o, ok := seen[c.ID]
		if !ok || o.Result != "passed" {
			reject("check_not_satisfied", "必需检查未满足: "+c.ID+" ("+o.Result+")", "补齐当前证据并重新检查")
		}
		var details struct {
			Diagnostics []model.Diagnostic `json:"diagnostics"`
		}
		if len(o.Details) > 0 {
			if err := json.Unmarshal(o.Details, &details); err != nil {
				reject("invalid_observation", "观察结果 JSON 无效", "重新采集合同观察")
			} else {
				d.Diagnostics = append(d.Diagnostics, details.Diagnostics...)
			}
		}
	}
	d.Allowed = len(d.Diagnostics) == 0
	return d
}

func legal(current, mode string, a model.Action) bool {
	truth := mode == "figma" || mode == "runtime-baseline"
	switch a.Intent {
	case "analyze":
		return current == "draft" && (a.TargetStatus == "" || a.TargetStatus == "split_ready")
	case "design":
		if a.TargetStatus == "" {
			return current == "split_ready" && !truth || current == "acceptance_frozen" && truth || current == "design_ready" || current == "in_dev" || current == "visual_acceptance_passed" || current == "merged"
		}
		return a.TargetStatus == "design_ready" && (current == "split_ready" && !truth || current == "acceptance_frozen" && truth || current == "design_ready" || current == "in_dev" || current == "visual_acceptance_passed")
	case "implement":
		return (current == "design_ready" || current == "in_dev") && (a.TargetStatus == "" || a.TargetStatus == "in_dev")
	case "verify":
		return current == "merged" && a.TargetStatus == "" || (current == "in_dev" || current == "visual_acceptance_passed") && (a.TargetStatus == "" || truth && a.TargetStatus == "visual_acceptance_passed")
	case "merge":
		return (current == "in_dev" && !truth || current == "visual_acceptance_passed" && truth) && (a.TargetStatus == "" || a.TargetStatus == "merged")
	case "ui":
		return current == "split_ready" && truth && (a.TargetStatus == "" || a.TargetStatus == "acceptance_frozen")
	case "archive":
		return current == "merged" && (a.TargetStatus == "" || a.TargetStatus == "archived") || current == "archived" && a.TargetStatus == ""
	}
	return false
}
