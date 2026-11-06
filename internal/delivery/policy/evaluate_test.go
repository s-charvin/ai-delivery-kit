package policy_test

import (
	"encoding/json"
	"go/ast"
	"go/parser"
	"go/token"
	"reflect"
	"strconv"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/policy"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func snapshot(t *testing.T, a model.Action, status, mode string) model.Snapshot {
	t.Helper()
	b, _ := json.Marshal(map[string]any{"sub_requirements": map[string]any{"SR-001": map[string]any{"status": status, "ui_truth_mode": mode}}})
	s, e := workspace.NewSnapshot(model.Workspace{}, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &a}, map[string][]byte{workspace.FactPrefix + "status": b}, nil, nil)
	if e != nil {
		t.Fatal(e)
	}
	return s
}
func passing(plan []model.CheckSpec) []model.CheckObservation {
	out := []model.CheckObservation{}
	for _, c := range plan {
		out = append(out, model.CheckObservation{CheckID: c.ID, Result: "passed", Provenance: "declaration"})
	}
	return out
}
func TestPolicyCannotUseOmittedChecksOrAnotherAction(t *testing.T) {
	p := policy.Policy{}
	a := model.Action{Intent: "implement", TargetStatus: "in_dev"}
	s := snapshot(t, a, "design_ready", "none")
	plan := p.PlanChecks(s, a)
	if d := p.Evaluate(s, a, plan, passing(plan)); !d.Allowed {
		t.Fatal(d)
	}
	for _, cs := range [][]model.CheckSpec{nil, plan[:len(plan)-1]} {
		if p.Evaluate(s, a, cs, passing(cs)).Allowed {
			t.Fatal("删除必需检查不能授权")
		}
	}
	other := a
	other.TargetStatus = "merged"
	if p.Evaluate(s, other, plan, passing(plan)).Allowed {
		t.Fatal("另一target快照不能授权")
	}
	req := model.ContextRequest{Role: "implement"}
	c, _ := workspace.NewSnapshot(model.Workspace{}, s.Scope(), model.ReadRequest{Context: &req}, nil, nil, nil)
	if p.Evaluate(c, a, plan, passing(plan)).Allowed {
		t.Fatal("context域不能授权")
	}
	base := p.Evaluate(s, a, plan, passing(plan))
	for i := 0; i < 50; i++ {
		if !reflect.DeepEqual(base, p.Evaluate(s, a, plan, passing(plan))) {
			t.Fatal("判断不确定")
		}
	}
	plan[0].ID = "changed"
	if reflect.DeepEqual(base.Checks, plan) {
		t.Fatal("返回plan共享可变内存")
	}
}
func TestPolicyRoutesAndCapabilities(t *testing.T) {
	cases := []struct {
		status, mode, intent, to string
		want                     bool
	}{
		{"draft", "none", "analyze", "split_ready", true},
		{"split_ready", "none", "design", "design_ready", true},
		{"in_dev", "none", "design", "", true},
		{"in_dev", "none", "verify", "", true},
		{"in_dev", "none", "merge", "merged", true},
		{"split_ready", "none", "implement", "in_dev", false},
		{"design_ready", "none", "merge", "merged", false},
		{"in_dev", "none", "verify", "visual_acceptance_passed", false},
		{"split_ready", "figma", "ui", "acceptance_frozen", true},
		{"design_ready", "runtime-baseline", "implement", "in_dev", true},
		{"merged", "none", "archive", "archived", true},
		{"archived", "none", "design", "", false},
	}
	for _, tc := range cases {
		t.Run(strings.Join([]string{tc.status, tc.mode, tc.intent, tc.to}, "/"), func(t *testing.T) {
			p := policy.Policy{}
			a := model.Action{Intent: model.Intent(tc.intent), TargetStatus: tc.to}
			s := snapshot(t, a, tc.status, tc.mode)
			plan := p.PlanChecks(s, a)
			d := p.Evaluate(s, a, plan, passing(plan))
			if d.Allowed != tc.want {
				t.Fatal(d)
			}
		})
	}
}
func TestPolicyPackageHasNoIOImports(t *testing.T) {
	fs := token.NewFileSet()
	pkgs, e := parser.ParseDir(fs, ".", nil, parser.ImportsOnly)
	if e != nil {
		t.Fatal(e)
	}
	for _, p := range pkgs {
		for name, f := range p.Files {
			if strings.HasSuffix(name, "_test.go") {
				continue
			}
			ast.Inspect(f, func(n ast.Node) bool {
				im, ok := n.(*ast.ImportSpec)
				if !ok {
					return true
				}
				v, _ := strconv.Unquote(im.Path.Value)
				switch v {
				case "encoding/json", "fmt", "reflect", "sort", "strings", "github.com/s-charvin/ai-delivery-kit/internal/delivery/model":
				default:
					t.Errorf("policy引入非纯边界 %s", v)
				}
				return true
			})
		}
	}
}

func TestUIFourModesStageObligations(t *testing.T) {
	p := policy.Policy{}
	for _, mode := range []string{"none", "existing", "runtime-baseline", "figma"} {
		truth := mode == "runtime-baseline" || mode == "figma"
		for _, tc := range []struct {
			status, intent, to         string
			index, acceptance, allowed bool
		}{
			{"draft", "analyze", "split_ready", false, false, true},
			{"split_ready", "ui", "", false, false, truth},
			{"split_ready", "ui", "acceptance_frozen", truth, false, truth},
			{"split_ready", "design", "design_ready", false, false, !truth},
			{"acceptance_frozen", "design", "design_ready", truth, false, truth},
			{"design_ready", "implement", "in_dev", truth, false, true},
			{"in_dev", "verify", "", truth, truth, true},
			{"in_dev", "verify", "visual_acceptance_passed", truth, truth, truth},
			{"in_dev", "merge", "merged", truth, truth, !truth},
			{"visual_acceptance_passed", "merge", "merged", truth, truth, truth},
		} {
			t.Run(mode+"/"+tc.status+"/"+tc.intent+"/"+tc.to, func(t *testing.T) {
				a := model.Action{Intent: model.Intent(tc.intent), TargetStatus: tc.to}
				s := snapshot(t, a, tc.status, mode)
				plan := p.PlanChecks(s, a)
				has := map[string]bool{}
				for _, c := range plan {
					has[c.ID] = true
				}
				if has["ui_index"] != tc.index || has["ui_acceptance"] != tc.acceptance {
					t.Fatalf("错误 UI 义务: %+v", plan)
				}
				d := p.Evaluate(s, a, plan, passing(plan))
				if d.Allowed != tc.allowed {
					t.Fatalf("allowed=%v want=%v: %+v", d.Allowed, tc.allowed, d)
				}
				if truth && tc.index {
					obs := passing(plan)
					for i := range obs {
						if obs[i].CheckID == "ui_index" {
							obs[i].Result = "invalid"
						}
					}
					if p.Evaluate(s, a, plan, obs).Allowed {
						t.Fatal("invalid UI 被推进")
					}
				}
			})
		}
	}

}
