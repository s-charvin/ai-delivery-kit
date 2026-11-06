package service

import (
	"context"
	"fmt"
	"reflect"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/policy"
)

// CheckAction 在消费闭包固定后才公布动作身份；check 不执行原生命令。
func (s Service) CheckAction(ctx context.Context, w model.Workspace, scope model.Scope, a model.Action) (model.CheckReport, error) {
	snapshot, err := s.Reader.Load(ctx, w, scope, model.ReadRequest{Action: &a})
	if err != nil {
		return model.CheckReport{}, err
	}
	p := policy.Policy{}
	reader := checks.Reader{Reader: s.Reader}
	for round := 0; round < 66; round++ {
		plan := p.PlanChecks(snapshot, a)
		set, err := reader.Collect(ctx, snapshot, plan)
		if err != nil {
			return model.CheckReport{}, err
		}
		nextPlan := p.PlanChecks(set.Snapshot, a)
		if snapshot.ID() == set.Snapshot.ID() && reflect.DeepEqual(plan, nextPlan) {
			if err := s.Reader.Verify(ctx, set.Snapshot); err != nil {
				return model.CheckReport{}, err
			}
			return model.CheckReport{Snapshot: set.Snapshot, Decision: p.Evaluate(set.Snapshot, a, nextPlan, set.Observations)}, nil
		}
		snapshot = set.Snapshot
	}
	return model.CheckReport{}, fmt.Errorf("合同引用闭包无法在 66 轮内稳定，动作被阻塞")
}
