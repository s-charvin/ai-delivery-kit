package policy_test

import (
	"encoding/json"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/policy"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"testing"
)

func TestRunPreflightRetainsPrerequisitesWithoutSuccessDeadlock(t *testing.T) {
	p := policy.Policy{}
	a := model.Action{Intent: "verify"}
	for _, status := range []string{"in_dev", "design_ready", "blocked_verification_failure", "blocked_missing_design", "draft"} {
		b, _ := json.Marshal(map[string]any{"sub_requirements": map[string]any{"SR-001": map[string]any{"status": status, "ui_truth_mode": "none", "blocked_from_status": "in_dev", "resume_target_status": "in_dev"}}})
		s, e := workspace.NewSnapshot(model.Workspace{}, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &a}, map[string][]byte{model.FactPrefix + "status": b}, nil, nil)
		if e != nil {
			t.Fatal(e)
		}
		plan := p.PlanRun(s)
		for _, c := range plan {
			if c.ID == "verification" {
				t.Fatal("运行必须先成功的死锁")
			}
		}
		want := status == "in_dev" || status == "design_ready" || status == "blocked_verification_failure"
		if got := p.EvaluateRun(s, plan, passing(plan)); got.Allowed != want {
			t.Fatal(status, got)
		}
		obs := passing(plan)
		for i := range obs {
			if obs[i].CheckID == "design" || obs[i].CheckID == "dependencies" {
				obs[i].Result = "invalid"
			}
		}
		if p.EvaluateRun(s, plan, obs).Allowed {
			t.Fatal("重测绕过设计/依赖前置")
		}
		if p.EvaluateRun(s, plan[:len(plan)-1], passing(plan)).Allowed {
			t.Fatal("调用者删除前置项")
		}
	}
}
