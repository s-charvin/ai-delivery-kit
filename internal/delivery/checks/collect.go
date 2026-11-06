package checks

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/contextview"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

type Reader struct{ Reader workspace.Reader }

var _ model.ContractReader = Reader{}

func diagnostic(s model.Snapshot, id, p, message string) model.Diagnostic {
	return diagnosticCause(s, id, p, errors.New(message))
}
func diagnosticCause(s model.Snapshot, id, p string, cause error) model.Diagnostic {
	d := model.Diagnostic{Code: "invalid_" + id, Path: p, Category: "contract", Scope: s.Scope().SubrequirementID, Message: cause.Error(), Recovery: "修复该作用域的合同或补齐当前证据后重新检查"}
	var format *protocol.FormatError
	if errors.As(cause, &format) {
		if format.Path != "" {
			d.Path = format.Path
		}
		d.Recovery = protocol.FormatRecovery(d.Path)
	}
	var missing *missingContractError
	if errors.As(cause, &missing) {
		d.Code = "missing_" + id
		d.Path = missing.path
	}
	return d
}
func role(a model.Action) string {
	switch a.Intent {
	case "analyze":
		return "analysis"
	case "design":
		return "design"
	case "ui":
		return "ui"
	case "verify", "merge":
		return "review"
	case "archive":
		return "finish"
	}
	return "implement"
}

// Collect 只通过 workspace.Reader 扩展事实；不执行测试、不写状态、也不生成批准。
func (r Reader) Collect(ctx context.Context, s model.Snapshot, checks []model.CheckSpec) (model.ObservationSet, error) {
	facts, err := workspace.Facts(s)
	if err != nil {
		return model.ObservationSet{Snapshot: s, Observations: invalidAll(s, checks, err)}, nil
	}
	a := s.Request().Action
	if a == nil {
		return model.ObservationSet{}, fmt.Errorf("合同采集需要动作快照")
	}
	problems := map[string][]model.Diagnostic{}
	add := func(id, p, msg string) { problems[id] = append(problems[id], diagnostic(s, id, p, msg)) }
	addCause := func(id, p string, cause error) { problems[id] = append(problems[id], diagnosticCause(s, id, p, cause)) }
	// 实际变更正文也属于动作身份；仅冻结路径类型无法发现同一文件继续编辑。
	paths := append([]string{}, facts.ObservedChangedPaths...)
	if len(facts.RunOutputPaths) != 0 {
		paths, err = workspace.KnownRunInputPaths(s, nil, facts.Artifacts["solution_design"])
		if err != nil {
			return model.ObservationSet{}, err
		}
	}
	historical := selectedEntry(s)["status"] == "archived"
	if historical {
		paths = nil
	}
	for _, c := range checks {
		paths = append(paths, c.InputPaths...)
	}
	sources, ds := contextview.Plan(s, model.ContextRequest{Role: role(*a)})
	if historical {
		sources = nil
		ds = nil
	}
	problems["inputs"] = append(problems["inputs"], ds...)
	for _, source := range sources {
		if strings.HasPrefix(source.Path, "kit://") {
			continue
		}
		if a.Intent == "design" && a.TargetStatus == "" && source.Path == facts.Artifacts["solution_design"] {
			continue
		}
		paths = append(paths, source.Path)
	}
	// 闭包遍历登记唯一请求路径；深度和数量超限明确阻塞，不截断后通过。
	type queued struct {
		path  string
		depth int
		owner string
	}
	queue := []queued{}
	for _, p := range paths {
		queue = append(queue, queued{p, 0, "inputs"})
	}
	seen := map[string]bool{}
	parsedUI := map[string]bool{}
	parsedReceipt := map[string]bool{}
	receiptDocuments := map[string]bool{}
	uiDocuments := map[string]bool{
		facts.Artifacts["ui_truth_index"]:    true,
		facts.Artifacts["visual_acceptance"]: true,
	}
	fixedHistorical := map[string]bool{}
	_, entries, _ := statusData(s)
	for id, raw := range entries {
		e, _ := raw.(map[string]any)
		if e["status"] != "archived" {
			continue
		}
		all, err := dependencyPaths(s, []string{id})
		if err != nil {
			return model.ObservationSet{}, err
		}
		for _, name := range archiveContractNames {
			fixedHistorical[all[id][name]] = true
		}
	}
	consume := func() error {
		for len(queue) > 0 {
			q := queue[0]
			queue = queue[1:]
			normalized, err := workspace.NormalizePath(q.path)
			if err != nil {
				add(q.owner, q.path, err.Error())
				continue
			}
			q.path = normalized
			// 同一文件可先作为普通证据读取，后才由依赖图识别为 UI 合同。
			if seen[q.path] && (!uiDocuments[q.path] || parsedUI[q.path]) && (!receiptDocuments[q.path] || parsedReceipt[q.path]) {
				continue
			}
			seen[q.path] = true
			if uiDocuments[q.path] {
				parsedUI[q.path] = true
			}
			if receiptDocuments[q.path] {
				parsedReceipt[q.path] = true
			}
			if q.depth > 64 || len(seen) > 10000 {
				add(q.owner, q.path, "治理引用深度超过 64 或文件数超过 10000")
				continue
			}
			next, err := r.Reader.Extend(ctx, s, []string{q.path})
			if err != nil {
				if ctx.Err() != nil {
					return ctx.Err()
				}
				var pe *os.PathError
				if errors.As(err, &pe) {
					return err
				}
				add(q.owner, q.path, err.Error())
				continue
			}
			s = next
			body, ok := s.Document(q.path)
			if !ok {
				continue
			}
			if fixedHistorical[q.path] {
				continue
			}
			if data, err := protocol.Object(body); err == nil {
				// UI 合同及其所有文件引用进入同一消费闭包。
				if uiDocuments[q.path] {
					for _, p := range UIReferences(data) {
						queue = append(queue, queued{p, q.depth + 1, "ui_index"})
					}
				}
				if receiptDocuments[q.path] {
					refs, e := ReceiptReferences(data)
					if e != nil {
						add("verification", q.path, e.Error())
					} else {
						for _, p := range refs {
							queue = append(queue, queued{p, q.depth + 1, "verification"})
						}
					}
				}
			}
			if outsideMarker(string(body), VerificationStart) {
				data, err := ParseBlock(body, VerificationStart, VerificationEnd)
				if err != nil {
					add("verification", q.path, err.Error())
					continue
				}
				if declared, ok := data["checks"].([]any); ok {
					for _, raw := range declared {
						c, _ := raw.(map[string]any)
						if p, ok := c["receipt_path"].(string); ok {
							if normalized, err := workspace.NormalizePath(p); err == nil {
								receiptDocuments[normalized] = true
							}
						}
					}
				}
				refs, err := VerificationReferences(data)
				if err != nil {
					add("verification", q.path, err.Error())
					continue
				}
				for _, p := range refs {
					queue = append(queue, queued{p, q.depth + 1, "verification"})
				}
			}
		}
		return nil
	}
	if err := consume(); err != nil {
		return model.ObservationSet{}, err
	}
	parents, dependencyErrors := dependencies(s, facts.Artifacts["dependency_graph"])
	if historical {
		parents = nil
		dependencyErrors = nil
	}
	if a.Intent == "archive" && !historical {
		for id, raw := range entries {
			e, _ := raw.(map[string]any)
			if id != s.Scope().SubrequirementID && (e["status"] == "merged" || e["status"] == "archived") && !contains(parents, id) {
				parents = append(parents, id)
			}
		}
		sort.Strings(parents)
	}
	parentPaths, err := dependencyPaths(s, parents)
	if err != nil {
		dependencyErrors = append(dependencyErrors, err.Error())
	}
	for _, id := range parents {
		p := parentPaths[id]
		for _, name := range []string{"solution_design", "verification", "ui_truth_index", "visual_acceptance"} {
			if p[name] != "" {
				if name == "ui_truth_index" || name == "visual_acceptance" {
					uiDocuments[p[name]] = true
				}
				queue = append(queue, queued{p[name], 0, "dependencies"})
			}
		}
	}
	if err := consume(); err != nil {
		return model.ObservationSet{}, err
	}
	for _, message := range dependencyErrors {
		add("dependencies", facts.Artifacts["dependency_graph"], message)
	}
	for _, id := range parents {
		e, _ := entries[id].(map[string]any)
		p := parentPaths[id]
		problems["dependencies"] = append(problems["dependencies"], validateSliceStatus(s, model.Scope{RequirementID: s.Scope().RequirementID, SubrequirementID: id}, p)...)
		if e["status"] == "archived" {
			for _, message := range ValidateArchiveEvidence(s, p, e) {
				add("dependencies", p["solution_design"], id+": "+message)
			}
			continue
		}
		if e["ui_truth_mode"] == "figma" || e["ui_truth_mode"] == "runtime-baseline" {
			for _, message := range ValidateDesignScenarios(s, p["solution_design"], p["ui_truth_index"]) {
				add("dependencies", p["solution_design"], id+": "+message)
			}
			for _, cause := range validateUIIndex(s, p["ui_truth_index"], uiString(e["ui_truth_mode"])) {
				addCause("dependencies", p["ui_truth_index"], fmt.Errorf("%s: %w", id, cause))
			}
			for _, cause := range validateUIAcceptance(s, p["ui_truth_index"], p["visual_acceptance"]) {
				addCause("dependencies", p["visual_acceptance"], fmt.Errorf("%s: %w", id, cause))
			}
		}
		raw, _ := s.Document(p["solution_design"])
		for _, cause := range validateDesign(raw, e) {
			addCause("dependencies", p["solution_design"], fmt.Errorf("%s: %w", id, cause))
		}
		raw, _ = s.Document(p["verification"])
		data, err := ParseBlock(raw, VerificationStart, VerificationEnd)
		if err != nil {
			add("dependencies", p["verification"], id+": "+err.Error())
			continue
		}
		design, _ := s.Document(p["solution_design"])
		acs, _ := AcceptanceIDs(design)
		// 仅替换被校验的切片身份；读取集合与动作身份仍由同一不可变快照保存。
		parent := scopedSnapshot{Snapshot: s, scope: model.Scope{RequirementID: s.Scope().RequirementID, SubrequirementID: id}}
		for _, message := range ValidateVerification(data, parent, p["solution_design"], acs) {
			add("dependencies", p["verification"], id+": "+message)
		}
	}
	observations := []model.CheckObservation{}
	for _, c := range checks {
		switch c.ID {
		case "inputs":
			for _, name := range []string{"requirement", "requirement_slice"} {
				p := facts.Artifacts[name]
				b, ok := s.Document(p)
				if !contextview.SourceBodyHealthy(b, ok) {
					add(c.ID, p, "缺少或无效的当前 "+name+" 正文")
				}
			}
			for _, source := range sources {
				if strings.HasPrefix(source.Path, "kit://") || a.Intent == "design" && a.TargetStatus == "" && source.Path == facts.Artifacts["solution_design"] {
					continue
				}
				b, ok := s.Document(source.Path)
				if source.Required && !contextview.SourceBodyHealthy(b, ok) {
					add(c.ID, source.Path, "必读来源缺失、为空或不是有效 UTF-8 正文")
				}
			}
		case "status":
			problems[c.ID] = append(problems[c.ID], validateStatus(s, facts.Artifacts)...)
		case "dependencies":
		case "archive_history":
			for _, message := range ValidateArchiveEvidence(s, facts.Artifacts, selectedEntry(s)) {
				add(c.ID, facts.Artifacts["status"], message)
			}
		case "archive_ready":
			if raw, ok := s.Document(facts.Artifacts["retrospective"]); !ok || !utf8.Valid(raw) {
				add(c.ID, facts.Artifacts["retrospective"], "归档需要有效复盘台账")
			} else {
				date, err := time.Parse("2006-01-02", facts.ArchiveDate)
				if err != nil {
					add(c.ID, facts.Artifacts["retrospective"], "缺少 reader 冻结的归档日期")
				} else if _, err := RetrospectiveEntries(raw, date); err != nil {
					addCause(c.ID, facts.Artifacts["retrospective"], err)
				}
			}
		case "ui_index":
			for _, cause := range validateUIIndex(s, facts.Artifacts["ui_truth_index"], uiString(selectedEntry(s)["ui_truth_mode"])) {
				addCause(c.ID, facts.Artifacts["ui_truth_index"], cause)
			}
		case "ui_acceptance":
			for _, cause := range validateUIAcceptance(s, facts.Artifacts["ui_truth_index"], facts.Artifacts["visual_acceptance"]) {
				addCause(c.ID, facts.Artifacts["visual_acceptance"], cause)
			}
		case "design":
			entry := selectedEntry(s)
			if entry["ui_truth_mode"] == "figma" || entry["ui_truth_mode"] == "runtime-baseline" {
				for _, message := range ValidateDesignScenarios(s, facts.Artifacts["solution_design"], facts.Artifacts["ui_truth_index"]) {
					add(c.ID, facts.Artifacts["solution_design"], message)
				}
			}
			raw, _ := s.Document(facts.Artifacts["solution_design"])
			for _, cause := range validateDesign(raw, selectedEntry(s)) {
				addCause(c.ID, facts.Artifacts["solution_design"], cause)
			}
		case "verification":
			p := facts.Artifacts["verification"]
			raw, _ := s.Document(p)
			data, err := ParseBlock(raw, VerificationStart, VerificationEnd)
			if err != nil {
				add(c.ID, p, err.Error())
				break
			}
			for _, marker := range []string{"ai-delivery-verification:review-rounds", "ai-delivery-verification:commands-results", "ai-delivery-verification:sign-off"} {
				if !strings.Contains(string(raw), marker) {
					add(c.ID, p, "缺少验证机器标记: "+marker)
				}
			}
			design, _ := s.Document(facts.Artifacts["solution_design"])
			acs, err := AcceptanceIDs(design)
			if err != nil {
				add(c.ID, facts.Artifacts["solution_design"], err.Error())
			}
			for _, message := range ValidateVerification(data, s, facts.Artifacts["solution_design"], acs) {
				add(c.ID, p, message)
			}
		default:
			add(c.ID, "", "未知核心检查")
		}
		result := "passed"
		if len(problems[c.ID]) > 0 {
			result = "invalid"
		}
		details, _ := json.Marshal(struct {
			Diagnostics []model.Diagnostic `json:"diagnostics"`
		}{problems[c.ID]})
		observations = append(observations, model.CheckObservation{CheckID: c.ID, Result: result, Provenance: "declaration", Evidence: s.Files(), Details: details})
	}
	// 非计划类别的引用错误也不能消失（例如依赖中的 verification 块）。
	known := map[string]bool{}
	for _, c := range checks {
		known[c.ID] = true
	}
	extras := []model.Diagnostic{}
	keys := []string{}
	for id := range problems {
		keys = append(keys, id)
	}
	sort.Strings(keys)
	for _, id := range keys {
		if !known[id] {
			extras = append(extras, problems[id]...)
		}
	}
	if len(extras) > 0 && len(observations) > 0 {
		observations[0].Result = "invalid"
		all := append(problems[observations[0].CheckID], extras...)
		observations[0].Details, _ = json.Marshal(struct {
			Diagnostics []model.Diagnostic `json:"diagnostics"`
		}{all})
	}
	return model.ObservationSet{Snapshot: s, Observations: observations}, nil
}

type scopedSnapshot struct {
	model.Snapshot
	scope model.Scope
}

func (s scopedSnapshot) Scope() model.Scope { return s.scope }
func invalidAll(s model.Snapshot, checks []model.CheckSpec, err error) []model.CheckObservation {
	out := []model.CheckObservation{}
	for _, c := range checks {
		b, _ := json.Marshal(struct {
			Diagnostics []model.Diagnostic `json:"diagnostics"`
		}{[]model.Diagnostic{diagnostic(s, c.ID, "", err.Error())}})
		out = append(out, model.CheckObservation{CheckID: c.ID, Result: "invalid", Provenance: "declaration", Details: b})
	}
	return out
}
