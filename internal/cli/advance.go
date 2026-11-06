package cli

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"syscall"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/mutation"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func (a *App) runAdvance(args []string) int {
	flags := flag.NewFlagSet("advance", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	subreq := flags.String("subreq", "", "切片 ID")
	target := flags.String("to", "", "目标状态")
	expected := flags.String("expected-snapshot", "", "同动作 check 身份")
	format := flags.String("format", "json", "输出格式")
	if err := flags.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return a.commandHelp(flags, "ai-delivery advance --req <req-id> --subreq <subreq-id> --to <target-status> --expected-snapshot <snapshot_id>", []string{"先对同一切片和目标运行 check，使用其当前 snapshot_id；advance 按目标推导意图，不接受 --intent。", "只接受 json 格式；归档使用专门的 archive 命令。"}, nil)
		}
		return a.checkError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" || *target == "" || *expected == "" {
		return a.checkError(fmt.Errorf("advance 需要 to/expected-snapshot，只接受命名参数和 json"), 2)
	}
	scope := model.Scope{RequirementID: *req, SubrequirementID: *subreq}
	if err := workspace.ValidateScope(scope); err != nil {
		return a.checkError(err, 2)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	reader := workspace.NewInstalledReader()
	w, err := reader.Resolve(ctx, *project, *delivery)
	if err != nil {
		return a.checkError(err, 2)
	}
	result, err := (service.Service{Reader: reader}).Advance(ctx, w, scope, *target, *expected)
	if err != nil {
		code := 2
		var pe *os.PathError
		if errors.As(err, &pe) || errors.Is(err, mutation.ErrCapability) {
			code = 3
		}
		return a.checkError(err, code)
	}
	code := 0
	if !result.Decision.Allowed {
		code = 2
		for _, d := range result.Decision.Diagnostics {
			if d.Code == "capability_unavailable" {
				code = 3
			}
		}
	}
	return a.deliveryJSON(struct {
		Allowed          bool             `json:"allowed"`
		BeforeSnapshotID string           `json:"before_snapshot_id"`
		AfterSnapshotID  *string          `json:"after_snapshot_id"`
		WrittenPaths     []string         `json:"written_paths"`
		Diagnostics      []diagnosticJSON `json:"diagnostics"`
	}{result.Decision.Allowed, result.BeforeSnapshotID, result.AfterSnapshotID, result.WrittenPaths, diagnosticsDTO(result.Decision.Diagnostics)}, code)
}
