package cli

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
	"io"
	"os"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

type diagnosticJSON struct {
	Code       string   `json:"code"`
	Path       string   `json:"path"`
	Category   string   `json:"category"`
	Scope      string   `json:"scope"`
	Message    string   `json:"message"`
	Recovery   string   `json:"recovery"`
	SourceRefs []string `json:"source_refs"`
}
type contextSourceJSON struct {
	Path     string  `json:"path"`
	SHA256   *string `json:"sha256"`
	Kind     string  `json:"kind"`
	Required bool    `json:"required"`
	Delivery string  `json:"delivery"`
	Reason   string  `json:"reason"`
	Body     *string `json:"body,omitempty"`
}
type workspaceJSON struct {
	ProjectRoot    string `json:"project_root"`
	DeliveryRoot   string `json:"delivery_root"`
	ProgramPath    string `json:"program_path"`
	ProgramID      string `json:"program_id"`
	ProtocolDigest string `json:"protocol_digest"`
	ResourceDigest string `json:"resource_digest"`
}

func workspaceDTO(w model.Workspace) workspaceJSON {
	return workspaceJSON{w.ProjectRoot, w.DeliveryRoot, w.ProgramPath, w.ProgramID, w.ProtocolDigest, w.ResourceDigest}
}
func diagnosticsDTO(ds []model.Diagnostic) []diagnosticJSON {
	out := make([]diagnosticJSON, 0, len(ds))
	for _, d := range ds {
		refs := append([]string{}, d.SourceRefs...)
		out = append(out, diagnosticJSON{d.Code, d.Path, d.Category, d.Scope, d.Message, d.Recovery, refs})
	}
	return out
}
func (a *App) deliveryJSON(value any, code int) int {
	encoder := json.NewEncoder(a.stdout)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		fmt.Fprintln(a.stderr, err)
		return 3
	}
	return code
}
func errorDiagnostic(err error, code int) (model.Diagnostic, int) {
	d := model.Diagnostic{Code: "invalid_input", Category: "input", Scope: "request", Message: err.Error(), Recovery: "修复命令参数或项目输入后重新执行；未初始化项目先运行 ai-delivery init"}
	if errors.Is(err, model.ErrUnknownIntent) {
		d.Recovery = "从诊断列出的合法意图中选择；运行 ai-delivery check --help 查看参数；analysis 是 context 角色，workflow finish 的 CLI 检查意图是 merge"
	}
	var resource *assets.Error
	var format *protocol.FormatError
	if errors.As(err, &resource) {
		exe, _ := os.Executable()
		d.Message += "；当前程序：" + exe + "，发行：" + version.String()
		d.Code = "resource_mismatch"
		d.Path = resource.Path
		d.Category = "capability"
		d.Recovery = "核对 info 的程序绝对路径/发行版本后，显式 ai-delivery init --upgrade <项目路径> 刷新资源；当前业务数据不重置"
		code = 3
	}
	if errors.As(err, &format) {
		d.Code = "invalid_format"
		d.Path = format.Path
		d.Recovery = protocol.FormatRecovery(format.Path)
	}
	return d, code
}
func (a *App) deliveryError(err error, code int) int {
	d, code := errorDiagnostic(err, code)
	return a.deliveryJSON(struct {
		ContextComplete bool             `json:"context_complete"`
		Diagnostics     []diagnosticJSON `json:"diagnostics"`
	}{false, diagnosticsDTO([]model.Diagnostic{d})}, code)
}

type pathsFlag []string

func (p *pathsFlag) String() string         { return fmt.Sprint([]string(*p)) }
func (p *pathsFlag) Set(value string) error { *p = append(*p, value); return nil }
func (a *App) runContext(args []string) int {
	flags := flag.NewFlagSet("context", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	subreq := flags.String("subreq", "", "切片 ID")
	role := flags.String("role", "", "必填上下文角色；分析角色用 analysis，check 动作意图用 analyze")
	budget := flags.Int("budget-chars", 64000, "正文字符预算")
	format := flags.String("format", "json", "输出格式")
	var paths pathsFlag
	flags.Var(&paths, "path", "声明阅读范围（可重复）")
	flags.Var(&paths, "declared-path", "声明阅读范围（可重复）")
	flags.Var(&paths, "changed-path", "声明阅读范围（可重复）")
	if err := flags.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return a.commandHelp(flags, "ai-delivery context --req <req-id> --subreq <subreq-id> --role <role> [--path <path>]", []string{"只接受 json 格式；budget-chars 必须非负。", "context_complete 只描述所选材料完整性，不是动作授权。"}, nil)
		}
		return a.deliveryError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" || *req == "" || *subreq == "" || *budget < 0 {
		return a.deliveryError(fmt.Errorf("context 要求 --req、--subreq、--role、非负预算和 json 格式，且不接受位置参数"), 2)
	}
	if _, err := workspace.GuidanceURI(*role); err != nil {
		return a.deliveryError(err, 2)
	}
	reader := workspace.NewInstalledReader()
	w, err := reader.Resolve(context.Background(), *project, *delivery)
	if err != nil {
		return a.deliveryError(err, 2)
	}
	report, err := (service.Service{Reader: reader}).PrepareContext(context.Background(), w, model.Scope{RequirementID: *req, SubrequirementID: *subreq}, model.ContextRequest{Role: *role, DeclaredPaths: paths, BudgetChars: *budget})
	if err != nil {
		return a.deliveryError(err, 2)
	}
	sources := make([]contextSourceJSON, 0, len(report.View.Sources))
	for _, s := range report.View.Sources {
		sources = append(sources, contextSourceJSON{s.Path, s.SHA256, s.Kind, s.Required, s.Delivery, s.Reason, s.Body})
	}
	facts, _ := workspace.Facts(report.Snapshot)
	declared := map[string]bool{}
	for _, p := range facts.DeclaredPaths {
		declared[p] = true
	}
	unassigned := []string{}
	for _, p := range facts.ObservedChangedPaths {
		if !declared[p] {
			unassigned = append(unassigned, p)
		}
	}
	result := struct {
		SnapshotID           string              `json:"snapshot_id"`
		Workspace            workspaceJSON       `json:"workspace"`
		RequirementID        string              `json:"requirement_id"`
		SubrequirementID     string              `json:"subrequirement_id"`
		Role                 string              `json:"role"`
		ContextComplete      bool                `json:"context_complete"`
		Sources              []contextSourceJSON `json:"sources"`
		Diagnostics          []diagnosticJSON    `json:"diagnostics"`
		DeclaredPaths        []string            `json:"declared_paths"`
		ObservedChangedPaths []string            `json:"observed_changed_paths"`
		UnassignedPaths      []string            `json:"unassigned_paths"`
		GitChangesKnown      bool                `json:"git_changes_known"`
	}{report.Snapshot.ID(), workspaceDTO(w), *req, *subreq, *role, report.View.ContextComplete, sources, diagnosticsDTO(report.View.Diagnostics), facts.DeclaredPaths, facts.ObservedChangedPaths, unassigned, facts.GitChangesKnown}
	code := 0
	if !report.View.ContextComplete {
		code = 2
	}
	return a.deliveryJSON(result, code)
}
func (a *App) runInfo(args []string) int {
	flags := flag.NewFlagSet("info", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	resource := flags.String("resource", "", "内嵌资源 URI")
	format := flags.String("format", "json", "输出格式")
	if err := flags.Parse(args); err != nil {
		return a.deliveryError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" {
		return a.deliveryError(fmt.Errorf("info 只接受 json 格式和命名参数"), 2)
	}
	if *resource != "" {
		body, err := workspace.Resource(*resource)
		if err != nil {
			return a.deliveryError(err, 2)
		}
		digest, err := workspace.ResourceDigest()
		if err != nil {
			return a.deliveryError(err, 3)
		}
		return a.deliveryJSON(struct {
			Path           string `json:"path"`
			SHA256         string `json:"sha256"`
			ResourceDigest string `json:"resource_digest"`
			Body           string `json:"body"`
		}{*resource, fmt.Sprintf("%x", sha256.Sum256(body)), digest, string(body)}, 0)
	}
	reader := workspace.NewInstalledReader()
	w, err := reader.Resolve(context.Background(), *project, *delivery)
	if err != nil {
		return a.deliveryError(err, 2)
	}
	return a.deliveryJSON(struct {
		Workspace    workspaceJSON `json:"workspace"`
		Capabilities []string      `json:"capabilities"`
		Release      string        `json:"release"`
		Revision     string        `json:"revision"`
	}{workspaceDTO(w), []string{"context", "info", "check", "run", "evidence", "advance", "archive", "validate", "hook"}, version.Version, version.Commit}, 0)
}
