package service_test

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func writeVerification(t *testing.T, root string, extra []any) map[string]any {
	t.Helper()
	p := ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md"
	write(t, root, "result.log", "真正宿主报告")
	fingerprint := func(p string) map[string]any {
		b, e := os.ReadFile(filepath.Join(root, p))
		if e != nil {
			t.Fatal(e)
		}
		return map[string]any{"path": p, "sha256": fmt.Sprintf("%x", sha256.Sum256(b))}
	}
	d := map[string]any{"version": 2, "subreq_id": "SR-001", "inputs": append([]any{fingerprint(p)}, extra...), "checks": []any{map[string]any{"id": "save", "required": true, "result": "passed", "mode": "executed", "command": "native save test", "exit_code": 0, "acceptance_ids": []any{"AC-001"}, "evidence": []any{fingerprint("result.log")}}}}
	persistVerification(t, root, d)
	return d
}
func persistVerification(t *testing.T, root string, d map[string]any) {
	t.Helper()
	inputHash, e := protocol.CanonicalSHA256(d["inputs"])
	if e != nil {
		t.Fatal(e)
	}
	reviewHash, e := protocol.ReviewDigest(d)
	if e != nil {
		t.Fatal(e)
	}
	d["reviews"] = []any{map[string]any{"reviewer": "独立评审", "context": "fresh", "result": "clean", "input_sha256": inputHash, "verification_sha256": reviewHash, "findings": []any{}}}
	b, _ := json.Marshal(d)
	body := "<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->\n<!-- ai-delivery-verification:contract:v2 -->\n```json\n" + string(b) + "\n```\n<!-- /ai-delivery-verification:contract:v2 -->\n"
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md", body)
}
func TestMergeBindsFullEvidenceAndAbsenceClosure(t *testing.T) {
	root := actionProject(t, "in_dev")
	writeVerification(t, root, []any{map[string]any{"path": "deleted.go", "state": "absent", "sha256": nil}})
	first := check(t, root, "merge", "merged")
	if !first.Decision.Allowed {
		t.Fatal(first.Decision.Diagnostics)
	}
	found := false
	for _, f := range first.Snapshot.Files() {
		found = found || f.Path == "result.log"
	}
	if !found {
		t.Fatal("证据未进入动作身份")
	}
	if d := check(t, root, "merge", "merged"); d.Snapshot.ID() != first.Snapshot.ID() {
		t.Fatal("稳定输入摘要不稳定")
	}
	write(t, root, "result.log", "发生漂移")
	if (workspace.Reader{}).Verify(context.Background(), first.Snapshot) == nil {
		t.Fatal("旧动作未发现传递证据漂移")
	}
	d := check(t, root, "merge", "merged")
	if d.Decision.Allowed || d.Snapshot.ID() == first.Snapshot.ID() {
		t.Fatal("陈旧证据被接受")
	}
	writeVerification(t, root, []any{map[string]any{"path": "deleted.go", "state": "absent", "sha256": nil}})
	write(t, root, "deleted.go", "reappeared")
	if check(t, root, "merge", "merged").Decision.Allowed {
		t.Fatal("absence重新出现被接受")
	}
}
func TestSafeLinkedEvidenceAndAbsentTarget(t *testing.T) {
	root := actionProject(t, "in_dev")
	d := writeVerification(t, root, nil)
	if err := os.Symlink("result.log", filepath.Join(root, "result-link.log")); err != nil {
		t.Fatal(err)
	}
	d["checks"].([]any)[0].(map[string]any)["evidence"].([]any)[0].(map[string]any)["path"] = "result-link.log"
	persistVerification(t, root, d)
	if report := check(t, root, "merge", "merged"); !report.Decision.Allowed {
		t.Fatal(report.Decision.Diagnostics)
	}
	if err := os.Symlink("missing.go", filepath.Join(root, "deleted-link.go")); err != nil {
		t.Fatal(err)
	}
	d["inputs"] = append(d["inputs"].([]any), map[string]any{"path": "deleted-link.go", "state": "absent", "sha256": nil})
	persistVerification(t, root, d)
	if report := check(t, root, "merge", "merged"); !report.Decision.Allowed {
		t.Fatal(report.Decision.Diagnostics)
	}
}
func TestBlockerRecoveryStillRequiresReview(t *testing.T) {
	root := actionProject(t, "blocked_verification_failure")
	setStatus(t, root, "blocked_verification_failure", func(d map[string]any) {
		e := d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
		e["blocked_from_status"] = "in_dev"
		e["resume_target_status"] = "in_dev"
		e["blocker_scope"] = "slice_local"
	})
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("恢复验证失败不能跳过验证review")
	}
	writeVerification(t, root, nil)
	if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
}
func TestQuotedContractExampleInRequirementDoesNotCreateReferences(t *testing.T) {
	root := actionProject(t, "design_ready")
	write(t, root, ".ai-delivery/requirements/R/requirement.md", "原始需求\n````markdown\n<!-- ai-delivery-verification:contract:v2 -->\n```json\n{}\n```\n<!-- /ai-delivery-verification:contract:v2 -->\n````\n")
	if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
}

func TestTransitiveReferencesDepthAndDuplicateDeduplication(t *testing.T) {
	for _, depth := range []int{3, 65} {
		t.Run(fmt.Sprint(depth), func(t *testing.T) {
			root := actionProject(t, "in_dev")
			next := ""
			nextHash := ""
			for i := depth; i >= 0; i-- {
				inputs := []any{}
				if next != "" {
					inputs = append(inputs, map[string]any{"path": next, "sha256": nextHash})
				}
				b, _ := json.Marshal(map[string]any{"version": 2, "inputs": inputs, "checks": []any{}})
				raw := "<!-- ai-delivery-verification:contract:v2 -->\n```json\n" + string(b) + "\n```\n<!-- /ai-delivery-verification:contract:v2 -->\n"
				next = fmt.Sprintf("refs/%d.md", i)
				nextHash = fmt.Sprintf("%x", sha256.Sum256([]byte(raw)))
				write(t, root, next, raw)
			}
			writeVerification(t, root, []any{map[string]any{"path": next, "sha256": nextHash}})
			d := check(t, root, "merge", "merged")
			if (depth == 3) != d.Decision.Allowed {
				t.Fatal(d.Decision.Diagnostics)
			}
			if depth == 3 {
				count := 0
				for _, f := range d.Snapshot.Files() {
					if f.Path == "refs/3.md" {
						count++
					}
				}
				if count != 1 {
					t.Fatal("闭包未消费传递终点或重复", count)
				}
			}
		})
	}
}

func TestDependencyGraphCurrentShapesAndNoLegacyFallback(t *testing.T) {
	root := actionProject(t, "design_ready")
	setStatus(t, root, "design_ready", func(d map[string]any) {
		d["sub_requirements"].(map[string]any)["SR-002"] = map[string]any{"status": 17}
	})
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/dependency.json", `{"depends_on":[]}`)
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("旧dependency.json不能替代canonical总图")
	}
	for _, raw := range []string{`{"nodes":{"SR-001":{"depends_on":[]}}}`, `{"sub_requirements":{"SR-001":{"depends_on":[]}}}`, `{"edges":[{"id":"SR-001","depends_on":[]}]}`, `{"SR-001":{"depends_on":[]}}`} {
		write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", raw)
		if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
			t.Fatal(raw, d.Decision.Diagnostics)
		}
	}
}

func TestDraftAnalysisDoesNotRequireUncreatedDependencyGraph(t *testing.T) {
	root := actionProject(t, "draft")
	setStatus(t, root, "draft", func(d map[string]any) {
		entry := d["sub_requirements"].(map[string]any)["SR-001"]
		d["sub_requirements"].(map[string]any)["SR-002"] = entry
	})
	if d := check(t, root, "analyze", ""); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
	if check(t, root, "analyze", "split_ready").Decision.Allowed {
		t.Fatal("推进活跃多切片前必须有当前拓扑")
	}
}

func TestHumanReviewRemainsRequiredAfterApprovalAndCheckIsConcurrent(t *testing.T) {
	root := actionProject(t, "design_ready")
	text := validDesign + "D-001 用户决定保留数据\n"
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", text)
	setStatus(t, root, "design_ready", func(d map[string]any) {
		d["current_checkpoint"] = "CP-DESIGN"
		e := d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
		e["user_decision_required"] = true
		e["design_review"].(map[string]any)["review_mode"] = "human"
		e["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(text)))
	})
	first := check(t, root, "implement", "in_dev")
	if !first.Decision.Allowed {
		t.Fatal(first.Decision.Diagnostics)
	}
	r := workspace.Reader{}
	w, e := r.Resolve(context.Background(), root, "")
	if e != nil {
		t.Fatal(e)
	}
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			d, e := (service.Service{Reader: r}).CheckAction(context.Background(), w, first.Snapshot.Scope(), *first.Snapshot.Request().Action)
			if e != nil || !d.Decision.Allowed || d.Snapshot.ID() != first.Snapshot.ID() {
				t.Errorf("并发判断不一致: %v %+v", e, d.Decision)
			}
		}()
	}
	wg.Wait()
	b, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/status.json"))
	if !strings.Contains(string(b), `"user_decision_required":true`) {
		t.Fatal("check改写了人工决定义务")
	}
}

const validDesign = `# 当前设计
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
保存
<!-- ai-delivery:behavior-contract:behavior -->
B-001 保存
<!-- ai-delivery:behavior-contract:acceptance -->
AC-001 数据保存成功
<!-- ai-delivery:behavior-contract:traceability -->
B-001 AC-001
<!-- ai-delivery:behavior-contract:end -->
<!-- ai-delivery:user-decisions -->
无需人工决定
`

func actionProject(t *testing.T, status string) string {
	root := project(t)
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", validDesign)
	setStatus(t, root, status, nil)
	return root
}
func setStatus(t *testing.T, root, status string, change func(map[string]any)) {
	e := map[string]any{"status": status, "ui_bearing": false, "ui_truth_mode": "none", "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(validDesign))), "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_by": "当前AI"}}
	data := map[string]any{"_schema": "2.0", "sub_requirements": map[string]any{"SR-001": e}}
	if change != nil {
		change(data)
	}
	b, _ := json.Marshal(data)
	write(t, root, ".ai-delivery/requirements/R/status.json", string(b))
}
func check(t *testing.T, root, intent, to string) model.CheckReport {
	t.Helper()
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	report, err := (service.Service{Reader: r}).CheckAction(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.Action{Intent: model.Intent(intent), TargetStatus: to})
	if err != nil {
		t.Fatal(err)
	}
	return report
}
func TestCheckSelfReviewNoNewCheckpointAndOriginalRequirementRequired(t *testing.T) {
	root := actionProject(t, "split_ready")
	d := check(t, root, "design", "design_ready")
	if !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
	setStatus(t, root, "design_ready", func(d map[string]any) { d["current_checkpoint"] = "CP-DESIGN" })
	if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
	os.Remove(filepath.Join(root, ".ai-delivery/requirements/R/requirement.md"))
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("缺少原始需求不可授权")
	}
}
func TestCompleteContextStillRejectsMergeAndDoesNotWrite(t *testing.T) {
	root := actionProject(t, "in_dev")
	if !prepare(t, root, request()).View.ContextComplete {
		t.Fatal("材料应齐全")
	}
	p := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	before, _ := os.ReadFile(p)
	report := check(t, root, "merge", "merged")
	if report.Decision.Allowed {
		t.Fatal("缺失verification不能merge")
	}
	after, _ := os.ReadFile(p)
	if string(before) != string(after) {
		t.Fatal("check写了状态")
	}
}
func TestStaleDesignReopensDesignButCannotImplement(t *testing.T) {
	root := actionProject(t, "in_dev")
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", validDesign+"change\n")
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("陈旧review不可实现")
	}
	if d := check(t, root, "design", ""); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
}
func TestDependenciesUnknownVersusProvenIndependent(t *testing.T) {
	root := actionProject(t, "design_ready")
	setStatus(t, root, "design_ready", func(d map[string]any) {
		d["sub_requirements"].(map[string]any)["SR-002"] = map[string]any{"status": 17}
	})
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("无拓扑不能猜独立")
	}
	graph := ".ai-delivery/requirements/R/dependency-graph.json"
	write(t, root, graph, `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":[]}}}`)
	if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
	for _, body := range []string{`{broken`, `{"nodes":{"SR-001":{"depends_on":["missing"]}}}`, `{"nodes":{"SR-001":{"depends_on":["SR-002"]},"SR-002":{"depends_on":["SR-001"]}}}`, `{"nodes":{"SR-001":{"depends_on":false}}}`, `{"nodes":{"unknown":{"depends_on":[]}}}`} {
		write(t, root, graph, body)
		if check(t, root, "implement", "in_dev").Decision.Allowed {
			t.Fatalf("坏拓扑授权: %s", body)
		}
	}
}
func TestForbiddenUIArtifactsAndBadTypes(t *testing.T) {
	root := actionProject(t, "design_ready")
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/contracts/ui-truth-index.json", `{}`)
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("none不允许truth index")
	}
	os.Remove(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/contracts/ui-truth-index.json"))
	for _, field := range []string{"ui_bearing", "state_flow_required", "user_decision_required"} {
		setStatus(t, root, "design_ready", func(d map[string]any) {
			d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)[field] = "false"
		})
		if check(t, root, "implement", "in_dev").Decision.Allowed {
			t.Fatal("错误类型", field)
		}
	}
	setStatus(t, root, "visual_acceptance_passed", nil)
	if check(t, root, "design", "").Decision.Allowed {
		t.Fatal("none不能占据visual_acceptance_passed")
	}
}

func TestForbiddenTruthArtifactViaAncestorLink(t *testing.T) {
	root := actionProject(t, "design_ready")
	write(t, root, ".ai-delivery/shared-contracts/ui-truth-index.json", `{}`)
	if err := os.Symlink("../../../../shared-contracts", filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/contracts")); err != nil {
		t.Fatal(err)
	}
	if _, err := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/contracts/ui-truth-index.json")); err != nil {
		t.Fatal(err)
	}
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("祖先链接不能隐藏不适用的truth产物")
	}
}
func TestCheckRejectsUnsafeEvidenceWithoutLosingRequired(t *testing.T) {
	root := actionProject(t, "in_dev")
	body := "<!-- ai-delivery-verification:contract:v2 -->\n```json\n{\"version\":2,\"subreq_id\":\"SR-001\",\"inputs\":[{\"path\":\"../outside\",\"sha256\":null}],\"checks\":[]}\n```\n<!-- /ai-delivery-verification:contract:v2 -->\n"
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md", body)
	d := check(t, root, "merge", "merged")
	if d.Decision.Allowed {
		t.Fatal("越界证据被接受")
	}
	b, _ := json.Marshal(d.Decision.Diagnostics)
	if !strings.Contains(string(b), "verification") {
		t.Fatal(string(b))
	}
}
