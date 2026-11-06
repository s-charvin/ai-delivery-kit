package service

import (
	"context"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/contextview"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

// Service 组合同一 reader 与纯选择器；其他动作由后续竖切实现。
type Service struct{ Reader workspace.Reader }

func (s Service) PrepareContext(ctx context.Context, w model.Workspace, scope model.Scope, req model.ContextRequest) (model.ContextReport, error) {
	snapshot, err := s.Reader.Load(ctx, w, scope, model.ReadRequest{Context: &req})
	if err != nil {
		return model.ContextReport{}, err
	}
	plan, _ := contextview.Plan(snapshot, req)
	for _, source := range plan {
		if strings.HasPrefix(source.Path, "kit://") {
			continue
		}
		next, err := s.Reader.Extend(ctx, snapshot, []string{source.Path})
		if err != nil {
			snapshot, err = workspace.Diagnose(snapshot, model.Diagnostic{Code: "source_read_failed", Path: source.Path, Category: "context_input", Scope: scope.SubrequirementID, Message: err.Error(), Recovery: "修复来源路径或输入漂移后重新读取"})
			if err != nil {
				return model.ContextReport{}, err
			}
			continue
		}
		snapshot = next
	}
	if err := s.Reader.Verify(ctx, snapshot); err != nil {
		return model.ContextReport{}, err
	}
	return model.ContextReport{Snapshot: snapshot, View: (contextview.Selector{}).Select(snapshot, req)}, nil
}
