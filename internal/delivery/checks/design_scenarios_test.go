package checks

import (
	"context"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDesignRequiresExactIndexedScenarioReference(t *testing.T) {
	for _, tc := range []struct {
		name, replacement string
		want              string
	}{{"exact", "default-phone", "passed"}, {"missing", "not-mentioned", "invalid"}, {"substring", "default-phone-extra", "invalid"}, {"prefix", "extra-default-phone", "invalid"}, {"complete-two", "default-phone default-tablet", "passed"}, {"missing-one", "default-phone", "invalid"}} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			copyUIFixture(t, root, "component-only")
			if tc.name == "complete-two" || tc.name == "missing-one" {
				index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
				unit := uiUnit(index)
				scenario := map[string]any{}
				for k, v := range uiScenario(index) {
					scenario[k] = v
				}
				scenario["scenario_id"] = "default-tablet"
				unit["scenarios"] = append(uiList(unit["scenarios"]), scenario)
				uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
			}
			p := uiSlice + "design.md"
			raw, err := os.ReadFile(filepath.Join(root, p))
			if err != nil {
				t.Fatal(err)
			}
			text := strings.ReplaceAll(string(raw), "default-phone", tc.replacement)
			if err = os.WriteFile(filepath.Join(root, p), []byte(text), 0644); err != nil {
				t.Fatal(err)
			}
			sp := ".ai-delivery/requirements/REQ-UI/status.json"
			status := uiReadJSON(t, root, sp)
			entry := status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
			entry["design_review"] = reviewedEntry(text)["design_review"]
			uiWriteJSON(t, root, sp, status)
			s, err := (workspace.Reader{}).Load(context.Background(), model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}, model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "design"}})
			if err != nil {
				t.Fatal(err)
			}
			got, err := (Reader{}).Collect(context.Background(), s, []model.CheckSpec{{ID: "design", InputPaths: []string{p, uiSlice + "contracts/ui-truth-index.json"}}})
			if err != nil {
				t.Fatal(err)
			}
			if len(got.Observations) != 1 || got.Observations[0].Result != tc.want {
				t.Fatalf("当前合法hash设计的场景引用结果错误: %+v", got.Observations)
			}
			if tc.want == "invalid" && !strings.Contains(string(got.Observations[0].Details), "scenario_id") {
				t.Fatal(string(got.Observations[0].Details))
			}
		})
	}
}

// 这是冻结历史身份的协议夹具；不得据此构造实际用户批准。
func TestDesignScenarioQueryDoesNotReopenArchivedRuntimeEvidence(t *testing.T) {
	root := t.TempDir()
	copyUIFixture(t, root, "component-only")
	sp := ".ai-delivery/requirements/REQ-UI/status.json"
	status := uiReadJSON(t, root, sp)
	entry := status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
	entry["status"] = "archived"
	uiWriteJSON(t, root, sp, status)
	r := workspace.Reader{}
	w := model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}
	scope := model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}
	req := model.ReadRequest{Action: &model.Action{Intent: "archive"}}
	s, err := r.Load(context.Background(), w, scope, req)
	if err != nil {
		t.Fatal(err)
	}
	facts, err := workspace.Facts(s)
	if err != nil {
		t.Fatal(err)
	}
	canonical := []string{}
	for _, name := range archiveContractNames {
		canonical = append(canonical, facts.Artifacts[name])
	}
	s, err = r.Extend(context.Background(), s, canonical)
	if err != nil {
		t.Fatal(err)
	}
	evidence, err := ArchiveEvidence(s, facts.Artifacts, entry)
	if err != nil {
		t.Fatal(err)
	}
	entry["archive_evidence"] = evidence
	uiWriteJSON(t, root, sp, status)
	for _, p := range []string{"native.log", "test/goldens/profile-card-default.png", "test/motion/profile-card-default.gif"} {
		if err = os.Remove(filepath.Join(root, p)); err != nil {
			t.Fatal(err)
		}
	}
	s, err = r.Load(context.Background(), w, scope, req)
	if err != nil {
		t.Fatal(err)
	}
	got, err := (Reader{}).Collect(context.Background(), s, []model.CheckSpec{{ID: "archive_history", InputPaths: canonical}})
	if err != nil {
		t.Fatal(err)
	}
	if got.Observations[0].Result != "passed" {
		t.Fatalf("历史被重新验收: %s", got.Observations[0].Details)
	}
	for _, p := range got.Snapshot.Files() {
		if strings.HasSuffix(p.Path, ".png") || strings.HasSuffix(p.Path, ".gif") || p.Path == "native.log" {
			t.Fatal("展开历史运行证据", p.Path)
		}
	}
}
