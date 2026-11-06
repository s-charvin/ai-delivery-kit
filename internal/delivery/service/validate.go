package service

import (
	"context"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

// ValidateStatus 是只读合同查询，不把格式通过解释成动作授权。
func (s Service) ValidateStatus(ctx context.Context, w model.Workspace, scope model.Scope) (model.Snapshot, []model.Diagnostic, error) {
	snapshot, err := s.Reader.Load(ctx, w, scope, model.ReadRequest{Action: &model.Action{Intent: "analyze"}})
	if err != nil {
		return nil, nil, err
	}
	facts, err := workspace.Facts(snapshot)
	if err != nil {
		return snapshot, snapshot.Diagnostics(), err
	}
	snapshot, err = s.Reader.Extend(ctx, snapshot, []string{facts.Artifacts["ui_truth_index"], facts.Artifacts["visual_acceptance"]})
	if err != nil {
		return nil, nil, err
	}
	ds := append(snapshot.Diagnostics(), checks.ValidateStatus(snapshot)...)
	if err = s.Reader.Verify(ctx, snapshot); err != nil {
		return nil, nil, err
	}
	return snapshot, ds, nil
}
