package service

import (
	"context"
	"fmt"
	"reflect"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/policy"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

// RunCheck 选择已审阅设计中的方法；前置不要求该轮已有成功结果，也不推进状态。
func (s Service) RunCheck(ctx context.Context, w model.Workspace, scope model.Scope, req model.RunRequest) (model.RunReceipt, error) {
	snapshot, err := s.Reader.LoadRun(ctx, w, scope, nil)
	if err != nil {
		return model.RunReceipt{}, err
	}
	design, _ := model.Fact(snapshot, "solution_design")
	methods, err := checks.NativeMethods(design)
	if err != nil {
		return model.RunReceipt{}, err
	}
	var selected *model.CheckSpec
	for _, spec := range methods {
		if spec.ID == req.CheckID {
			copy := spec
			selected = &copy
		}
	}
	if selected == nil {
		return model.RunReceipt{}, fmt.Errorf("当前设计没有明确 native-method: %s", req.CheckID)
	}
	if req.Cwd != selected.Method.Cwd || !reflect.DeepEqual(req.Argv, selected.Method.Argv) {
		return model.RunReceipt{}, fmt.Errorf("argv/cwd 与当前已绑定方法不一致")
	}
	facts, err := workspace.Facts(snapshot)
	if err != nil {
		return model.RunReceipt{}, err
	}
	explicit := append(append(append([]string{}, selected.InputPaths...), selected.SourceRefs...), req.InputPaths...)
	paths, err := workspace.KnownRunInputPaths(snapshot, explicit, facts.Artifacts["solution_design"])
	if err != nil {
		return model.RunReceipt{}, err
	}
	snapshot, err = s.Reader.LoadRun(ctx, w, scope, paths)
	if err != nil {
		return model.RunReceipt{}, err
	}
	currentDesign, _ := model.Fact(snapshot, "solution_design")
	if string(currentDesign) != string(design) {
		return model.RunReceipt{}, fmt.Errorf("选择方法时设计已漂移")
	}
	snapshot, err = s.Reader.Extend(ctx, snapshot, paths)
	if err != nil {
		return model.RunReceipt{}, err
	}
	p := policy.Policy{}
	reader := checks.Reader{Reader: s.Reader}
	for round := 0; round < 66; round++ {
		plan := p.PlanRun(snapshot)
		set, e := reader.Collect(ctx, snapshot, plan)
		if e != nil {
			return model.RunReceipt{}, e
		}
		nextPlan := p.PlanRun(set.Snapshot)
		if snapshot.ID() == set.Snapshot.ID() && reflect.DeepEqual(plan, nextPlan) {
			decision := p.EvaluateRun(set.Snapshot, nextPlan, set.Observations)
			if !decision.Allowed {
				return model.RunReceipt{}, fmt.Errorf("运行前置未满足: %+v", decision.Diagnostics)
			}
			if _, err := workspace.KnownRunInputPaths(set.Snapshot, explicit, facts.Artifacts["solution_design"]); err != nil {
				return model.RunReceipt{}, err
			}
			for _, f := range set.Snapshot.Files() {
				if f.Path == facts.Artifacts["verification"] || f.ResolvedPath == facts.Artifacts["verification"] || f.Path == ".ai-delivery.lock" || f.ResolvedPath == ".ai-delivery.lock" {
					return model.RunReceipt{}, fmt.Errorf("运行输入闭包引用自身输出: %s", f.Path)
				}
			}
			return (runner.Runner{Reader: s.Reader}).Run(ctx, set.Snapshot, *selected, req)
		}
		snapshot = set.Snapshot
	}
	return model.RunReceipt{}, fmt.Errorf("运行前置消费闭包未在 66 轮内稳定")
}
