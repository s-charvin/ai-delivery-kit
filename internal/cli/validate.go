package cli

import (
	"context"
	"flag"
	"fmt"
	"io"
	"path/filepath"

	"github.com/s-charvin/ai-delivery-kit/internal/assets"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func (a *App) runValidate(args []string) int {
	flags := flag.NewFlagSet("validate", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	kind := flags.String("kind", "", "status|layout|skills|sources|api-policy")
	req := flags.String("req", "", "需求 ID")
	sr := flags.String("subreq", "", "切片 ID")
	format := flags.String("format", "json", "格式")
	intent := flags.String("intent", "", "可选动作意图；直接复用 check")
	target := flags.String("to", "", "可选目标状态")
	if err := flags.Parse(args); err != nil {
		return a.checkError(err, 2)
	}
	if flags.NArg() != 0 || *format != "json" {
		return a.checkError(fmt.Errorf("validate 仅接受命名参数与 JSON"), 2)
	}
	if *kind != "status" && *kind != "layout" && *kind != "skills" && *kind != "sources" && *kind != "api-policy" {
		return a.checkError(fmt.Errorf("未知 validate kind: %s", *kind), 2)
	}
	if *target != "" && *intent == "" {
		return a.checkError(fmt.Errorf("--to 需要 --intent"), 2)
	}
	if *kind != "status" && *kind != "layout" && (*req != "" || *sr != "" || *intent != "" || *target != "") {
		return a.checkError(fmt.Errorf("资源静态查询不接受动作或切片参数"), 2)
	}
	if *intent != "" {
		return a.runCheck([]string{"--project", *project, "--delivery-root", *delivery, "--req", *req, "--subreq", *sr, "--intent", *intent, "--to", *target, "--format", *format})
	}
	if *kind == "layout" && (*req != "" || *sr != "") {
		return a.checkError(fmt.Errorf("带切片的 layout 验收需要 --intent；阶段合同由同一 check 服务判定"), 2)
	}
	ctx := context.Background()
	r := workspace.NewInstalledReader()
	w, err := r.Resolve(ctx, *project, *delivery)
	if err != nil {
		return a.checkError(err, 2)
	}
	if *kind == "status" {
		scope := model.Scope{RequirementID: *req, SubrequirementID: *sr}
		if err := workspace.ValidateScope(scope); err != nil {
			return a.checkError(err, 2)
		}
		snapshot, ds, err := (service.Service{Reader: r}).ValidateStatus(ctx, w, scope)
		if err != nil {
			return a.checkError(err, 2)
		}
		code := 0
		if len(ds) > 0 {
			code = 2
		}
		return a.deliveryJSON(map[string]any{"valid": len(ds) == 0, "kind": *kind, "scope": "slice-status-fields", "meaning": "仅当前字段、mode与禁止产物；不证明阶段或交付就绪", "snapshot_id": snapshot.ID(), "diagnostics": diagnosticsDTO(ds)}, code)
	}
	snapshot, err := workspace.NewSnapshot(w, model.Scope{}, model.ReadRequest{Action: &model.Action{Intent: "analyze"}}, nil, nil, nil)
	if err != nil {
		return a.checkError(err, 3)
	}
	read := func(p string) ([]byte, bool, error) {
		var err error
		snapshot, err = r.Extend(ctx, snapshot, []string{p})
		if err != nil {
			return nil, false, err
		}
		b, ok := snapshot.Document(p)
		return b, ok, nil
	}
	rel, _ := filepath.Rel(w.ProjectRoot, w.DeliveryRoot)
	if err = assets.Verify(filepath.ToSlash(rel), read); err != nil {
		return a.checkError(err, 3)
	}
	if *kind == "layout" {
		for _, spec := range []struct{ file, kind string }{{"project-binding.json", "binding"}, {"workflow-policy.json", "policy"}} {
			p := filepath.ToSlash(filepath.Join(rel, "meta", spec.file))
			b, _, e := read(p)
			if e != nil {
				return a.checkError(e, 2)
			}
			obj, e := protocol.Object(b)
			if e == nil {
				e = protocol.ValidateMetadata(spec.kind, obj)
			}
			if e == nil && spec.kind == "binding" {
				_, e = workspace.Layout(obj)
			}
			if e != nil {
				return a.checkError(&protocol.FormatError{Path: p, Cause: e}, 2)
			}
		}
	} else if err = assets.ValidateSources(*kind, read); err != nil {
		return a.checkError(err, 2)
	}
	if err = r.Verify(ctx, snapshot); err != nil {
		return a.checkError(err, 2)
	}
	scope := "managed-resources"
	if *kind == "layout" {
		scope = "project-layout-configuration"
	}
	return a.deliveryJSON(map[string]any{"valid": true, "kind": *kind, "scope": scope, "snapshot_id": snapshot.ID()}, 0)
}
