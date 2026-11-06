package policy_test

import (
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/policy"
)

func TestMergedVerificationOnlyAllowsUntargetedEvidenceRefresh(t *testing.T) {
	p := policy.Policy{}
	for _, mode := range []string{"none", "existing", "runtime-baseline", "figma"} {
		for _, status := range []string{"merged", "archived"} {
			for _, intent := range []model.Intent{"verify", "implement", "merge"} {
				for _, target := range []string{"", "in_dev", "design_ready", "visual_acceptance_passed", "merged", "archived"} {
					t.Run(mode+"/"+status+"/"+string(intent)+"/"+target, func(t *testing.T) {
						a := model.Action{Intent: intent, TargetStatus: target}
						s := snapshot(t, a, status, mode)
						plan := p.PlanChecks(s, a)
						want := status == "merged" && intent == "verify" && target == ""
						if d := p.Evaluate(s, a, plan, passing(plan)); d.Allowed != want {
							t.Fatalf("allowed=%v want=%v: %+v", d.Allowed, want, d.Diagnostics)
						}
					})
				}
			}
		}
	}
}

func TestMergedRunRetainsPrerequisitesAndReadOnlyVerificationRetainsAcceptance(t *testing.T) {
	p := policy.Policy{}
	a := model.Action{Intent: "verify"}
	for _, mode := range []string{"none", "existing", "runtime-baseline", "figma"} {
		t.Run(mode, func(t *testing.T) {
			s := snapshot(t, a, "merged", mode)
			runPlan := p.PlanRun(s)
			if d := p.EvaluateRun(s, runPlan, passing(runPlan)); !d.Allowed {
				t.Fatalf("merged 无法采集新证据: %+v", d.Diagnostics)
			}
			has := map[string]bool{}
			for i, c := range runPlan {
				has[c.ID] = true
				obs := passing(runPlan)
				obs[i].Result = "invalid"
				if p.EvaluateRun(s, runPlan, obs).Allowed {
					t.Fatalf("重采集绕过前置 %s", c.ID)
				}
			}
			for _, id := range []string{"inputs", "status", "dependencies", "design"} {
				if !has[id] {
					t.Errorf("缺少运行前置 %s", id)
				}
			}
			truth := mode == "runtime-baseline" || mode == "figma"
			if has["ui_index"] != truth || has["verification"] || has["ui_acceptance"] {
				t.Fatalf("运行前置错误: %+v", runPlan)
			}
			if p.EvaluateRun(s, runPlan[:len(runPlan)-1], passing(runPlan)).Allowed {
				t.Fatal("调用者删项后仍可运行")
			}
			plan := p.PlanChecks(s, a)
			foundVerification, foundAcceptance := false, false
			for i, c := range plan {
				if c.ID != "verification" && c.ID != "ui_acceptance" {
					continue
				}
				foundVerification = foundVerification || c.ID == "verification"
				foundAcceptance = foundAcceptance || c.ID == "ui_acceptance"
				obs := passing(plan)
				obs[i].Result = "invalid"
				if p.Evaluate(s, a, plan, obs).Allowed {
					t.Fatalf("只读验收绕过 %s", c.ID)
				}
			}
			if !foundVerification || foundAcceptance != truth {
				t.Fatalf("只读验收缺少适用门禁: %+v", plan)
			}
			archived := snapshot(t, a, "archived", mode)
			archivedPlan := p.PlanRun(archived)
			if p.EvaluateRun(archived, archivedPlan, passing(archivedPlan)).Allowed {
				t.Fatal("终态不应重新执行原生命令")
			}
		})
	}
}
