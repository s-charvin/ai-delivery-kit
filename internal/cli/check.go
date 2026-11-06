package cli

import (
	"context"
	"flag"
	"fmt"
	"io"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

type checkSpecJSON struct {
	ID            string   `json:"id"`
	Applicability string   `json:"applicability"`
	AcceptanceIDs []string `json:"acceptance_ids"`
	SourceRefs    []string `json:"source_refs"`
	InputPaths    []string `json:"input_paths"`
}

func (a *App) checkError(err error, code int) int {
	d, code := errorDiagnostic(err, code)
	return a.deliveryJSON(struct {
		Allowed     bool             `json:"allowed"`
		Diagnostics []diagnosticJSON `json:"diagnostics"`
	}{false, diagnosticsDTO([]model.Diagnostic{d})}, code)
}
func (a *App) runCheck(args []string) int {
	flags := flag.NewFlagSet("check", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	subreq := flags.String("subreq", "", "切片 ID")
	intent := flags.String("intent", "", "必填动作意图；分析用 analyze，完成检查用 merge")
	target := flags.String("to", "", "目标状态；仅检查当前动作时可省略")
	format := flags.String("format", "json", "输出格式，仅 json")
	if err := flags.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return a.commandHelp(flags, "ai-delivery check --req <req-id> --subreq <subreq-id> --intent <intent> [--to <target-status>]", []string{"合法意图不表示当前动作已获许可；由当前合同和唯一核心判断。", "advance 使用本次同切片、同目标 check 返回的 snapshot_id。"}, map[string][]string{"intent": model.IntentChoices()})
		}
		return a.checkError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" || *req == "" || *subreq == "" {
		return a.checkError(fmt.Errorf("check 需要 req/subreq/intent，只接受命名参数与 json 格式"), 2)
	}
	parsed, err := model.ParseIntent(*intent)
	if err != nil {
		return a.checkError(err, 2)
	}
	if err := workspace.ValidateScope(model.Scope{RequirementID: *req, SubrequirementID: *subreq}); err != nil {
		return a.checkError(err, 2)
	}
	r := workspace.NewInstalledReader()
	w, err := r.Resolve(context.Background(), *project, *delivery)
	if err != nil {
		return a.checkError(err, 2)
	}
	action := model.Action{Intent: parsed, TargetStatus: *target}
	report, err := (service.Service{Reader: r}).CheckAction(context.Background(), w, model.Scope{RequirementID: *req, SubrequirementID: *subreq}, action)
	if err != nil {
		return a.checkError(err, 3)
	}
	specs := []checkSpecJSON{}
	for _, c := range report.Decision.Checks {
		specs = append(specs, checkSpecJSON{c.ID, c.Applicability, append([]string{}, c.AcceptanceIDs...), append([]string{}, c.SourceRefs...), append([]string{}, c.InputPaths...)})
	}
	result := struct {
		SnapshotID       string           `json:"snapshot_id"`
		Workspace        workspaceJSON    `json:"workspace"`
		RequirementID    string           `json:"requirement_id"`
		SubrequirementID string           `json:"subrequirement_id"`
		Intent           model.Intent     `json:"intent"`
		TargetStatus     string           `json:"target_status"`
		Allowed          bool             `json:"allowed"`
		Checks           []checkSpecJSON  `json:"checks"`
		Diagnostics      []diagnosticJSON `json:"diagnostics"`
	}{report.Snapshot.ID(), workspaceDTO(w), *req, *subreq, action.Intent, action.TargetStatus, report.Decision.Allowed, specs, diagnosticsDTO(report.Decision.Diagnostics)}
	code := 0
	if !report.Decision.Allowed {
		code = 2
		for _, diagnostic := range report.Decision.Diagnostics {
			if diagnostic.Code == "capability_unavailable" {
				code = 3
				break
			}
		}
	}
	return a.deliveryJSON(result, code)
}
