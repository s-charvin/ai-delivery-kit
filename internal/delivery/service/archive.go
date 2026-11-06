package service

import (
	"context"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/mutation"
)

func (s Service) Archive(ctx context.Context, w model.Workspace, scope model.Scope, req model.ArchiveRequest) (model.MutationResult, error) {
	return (mutation.Archiver{Check: s.CheckAction}).Archive(ctx, w, scope, req)
}
