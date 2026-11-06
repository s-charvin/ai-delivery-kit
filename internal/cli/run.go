package cli

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"syscall"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func (a *App) runNative(args []string) int {
	flags := flag.NewFlagSet("run", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	subreq := flags.String("subreq", "", "切片 ID")
	check := flags.String("check", "", "绑定的检查 ID")
	cwd := flags.String("cwd", ".", "绑定的项目相对工作目录")
	timeout := flags.Int("timeout", 120, "超时秒数，范围 1–86400")
	format := flags.String("format", "json", "输出格式")
	var inputs pathsFlag
	flags.Var(&inputs, "input", "额外执行输入，可重复")
	if e := flags.Parse(args); e != nil {
		if e == flag.ErrHelp {
			return a.commandHelp(flags, "ai-delivery run --req <req-id> --subreq <subreq-id> --check <check-id> [--cwd .] -- <native argv...>", []string{"-- 后是原生命令 argv；argv/cwd 必须精确匹配当前已审阅设计中的 native-methods。", "可选注册格式与 run 返回 check/inputs 的用法见 references/delivery-quality-loop.md 的可选原生执行采集节。", "只接受 json 格式；run 记录执行事实，不推进状态、不生成独立评审。"}, nil)
		}
		return a.checkError(e, 2)
	}
	if *req == "" || *subreq == "" || *check == "" || flags.NArg() == 0 || *timeout <= 0 || *timeout > 86400 || *format != "json" {
		return a.checkError(fmt.Errorf("run 需要 req/subreq/check、有效 timeout 与 -- 后的原生 argv"), 2)
	}
	scope := model.Scope{RequirementID: *req, SubrequirementID: *subreq}
	if e := workspace.ValidateScope(scope); e != nil {
		return a.checkError(e, 2)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	reader := workspace.NewInstalledReader()
	w, e := reader.Resolve(ctx, *project, *delivery)
	if e != nil {
		return a.checkError(e, 2)
	}
	r, e := (service.Service{Reader: reader}).RunCheck(ctx, w, scope, model.RunRequest{CheckID: *check, Argv: flags.Args(), Cwd: *cwd, TimeoutSeconds: *timeout, InputPaths: inputs})
	if e != nil {
		code := 2
		var pe *os.PathError
		if errors.As(e, &pe) || errors.Is(e, runner.ErrCapability) {
			code = 3
		}
		return a.checkError(e, code)
	}
	mapped, e := checks.ReceiptToCheck(r)
	var executionInputs []byte
	if e == nil {
		executionInputs, e = checks.ReceiptExecutionInputs(r)
	}
	code := 0
	if r.Observation.Result != "passed" {
		code = 2
	}
	if r.Observation.Result == "not_run" {
		code = 3
	}
	diagnostics := []diagnosticJSON{}
	if e != nil {
		code = 2
		diagnostics = diagnosticsDTO([]model.Diagnostic{{Code: "receipt_mapping_failed", Category: "evidence", Message: e.Error(), Recovery: "查看原始收据中的失败事实并重新执行"}})
	}
	return a.deliveryJSON(struct {
		Path        string           `json:"receipt_path"`
		Result      string           `json:"result"`
		Receipt     json.RawMessage  `json:"receipt"`
		Check       json.RawMessage  `json:"check,omitempty"`
		Inputs      json.RawMessage  `json:"inputs,omitempty"`
		Diagnostics []diagnosticJSON `json:"diagnostics"`
	}{r.Path, r.Observation.Result, r.Observation.Details, mapped, executionInputs, diagnostics}, code)
}
