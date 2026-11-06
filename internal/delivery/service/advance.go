package service

import (
	"context"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/mutation"
)

func (s Service) Advance(ctx context.Context, w model.Workspace, scope model.Scope, target, expectedSnapshot string) (model.MutationResult, error) {
	return mutation.Advance(ctx, w, scope, target, expectedSnapshot, s.CheckAction)
}
