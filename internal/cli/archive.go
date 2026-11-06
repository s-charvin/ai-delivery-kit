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

func (a *App) runArchive(args []string) int {
	flags := flag.NewFlagSet("archive", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	sr := flags.String("subreq", "", "切片 ID")
	expected := flags.String("expected-snapshot", "", "archive 意图 check 身份")
	confirm := flags.Bool("confirm-archive", false, "调用方声明已取得此次用户 CP-ARCHIVE 确认；程序不验证对话身份")
	report := flags.String("delivery-report-template", "", "本地化交付报告模板")
	index := flags.String("retrospective-index-template", "", "本地化复盘索引模板")
	format := flags.String("format", "json", "输出格式")
	if err := flags.Parse(args); err != nil {
		return a.checkError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" || *expected == "" || !*confirm {
		return a.checkError(fmt.Errorf("archive 需要 expected-snapshot 和明确 --confirm-archive；check 就绪不代表用户批准"), 2)
	}
	scope := model.Scope{RequirementID: *req, SubrequirementID: *sr}
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
	result, err := (service.Service{Reader: reader}).Archive(ctx, w, scope, model.ArchiveRequest{ExpectedSnapshot: *expected, Confirmed: *confirm, DeliveryReportTemplate: *report, RetrospectiveIndexTemplate: *index})
	code := 0
	if err != nil {
		code = 2
		var pe *os.PathError
		if errors.As(err, &pe) || errors.Is(err, mutation.ErrCapability) {
			code = 3
		}
		result.Decision.Allowed = false
		d, classified := errorDiagnostic(err, code)
		code = classified
		d.Scope = *sr
		result.Decision.Diagnostics = append(result.Decision.Diagnostics, d)
	} else if !result.Decision.Allowed {
		code = 2
	}
	return a.deliveryJSON(struct {
		Allowed     bool             `json:"allowed"`
		Before      string           `json:"before_snapshot_id"`
		After       *string          `json:"after_snapshot_id"`
		Written     []string         `json:"written_paths"`
		Diagnostics []diagnosticJSON `json:"diagnostics"`
	}{result.Decision.Allowed, result.BeforeSnapshotID, result.AfterSnapshotID, result.WrittenPaths, diagnosticsDTO(result.Decision.Diagnostics)}, code)
}
