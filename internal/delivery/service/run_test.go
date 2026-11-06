package service_test

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunNativeHelper(t *testing.T) {
	if len(os.Args) > 1 && os.Args[len(os.Args)-1] == "native-child" {
		fmt.Println("真实宿主成功🙂")
	}
}
func runProject(t *testing.T, status string) (string, model.RunRequest) {
	t.Helper()
	root := actionProject(t, status)
	write(t, root, "src/owner.txt", "当前生产逻辑")
	exe, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	argv := []string{exe, "-test.run=^TestRunNativeHelper$", "--", "native-child"}
	method := map[string]any{"version": 1, "checks": []any{map[string]any{"id": "native-owner", "argv": argv, "cwd": ".", "parser_id": "exit-code", "acceptance_ids": []string{"AC-001"}, "input_paths": []string{"src/owner.txt"}, "report_paths": []string{}, "source_refs": []string{"src/owner.txt"}}}}
	b, _ := json.Marshal(method)
	block := checks.NativeMethodsStart + "\n```json\n" + string(b) + "\n```\n" + checks.NativeMethodsEnd + "\n"
	design := strings.Replace(validDesign, "<!-- ai-delivery:behavior-contract:traceability -->", block+"<!-- ai-delivery:behavior-contract:traceability -->", 1)
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", design)
	setStatus(t, root, status, func(d map[string]any) {
		entry := d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
		entry["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(design)))
		if status == "blocked_verification_failure" {
			entry["blocked_from_status"] = "in_dev"
			entry["resume_target_status"] = "in_dev"
			entry["blocker_scope"] = "slice_local"
		}
	})
	return root, model.RunRequest{CheckID: "native-owner", Argv: argv, Cwd: ".", TimeoutSeconds: 20}
}
func runNative(t *testing.T, root string, req model.RunRequest) (model.RunReceipt, error) {
	t.Helper()
	reader := workspace.Reader{}
	w, e := reader.Resolve(context.Background(), root, "")
	if e != nil {
		t.Fatal(e)
	}
	return (service.Service{Reader: reader}).RunCheck(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, req)
}
func TestRunServiceWithoutVerificationAndWithBlocker(t *testing.T) {
	for _, status := range []string{"in_dev", "blocked_verification_failure"} {
		t.Run(status, func(t *testing.T) {
			root, req := runProject(t, status)
			statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			before, _ := os.ReadFile(statusPath)
			r, e := runNative(t, root, req)
			if e != nil || r.Observation.Result != "passed" {
				t.Fatal(e, string(r.Observation.Details))
			}
			after, _ := os.ReadFile(statusPath)
			if string(before) != string(after) {
				t.Fatal("运行改写状态/批准")
			}
			if _, e = os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")); !os.IsNotExist(e) {
				t.Fatal("运行伪造verification或review")
			}
			var d struct {
				Inputs []struct {
					Path string `json:"path"`
				} `json:"inputs_before"`
			}
			json.Unmarshal(r.Observation.Details, &d)
			found := map[string]bool{}
			for _, f := range d.Inputs {
				found[f.Path] = true
			}
			for _, p := range []string{"src/owner.txt", "src/AGENTS.md", "AGENTS.md", "rules/api.md", ".ai-delivery/meta/project-binding.json", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md"} {
				if !found[p] {
					t.Error("缺少运行必需输入", p)
				}
			}
			checkJSON, e := checks.ReceiptToCheck(r)
			if e != nil {
				t.Fatal(e)
			}
			if strings.Contains(string(checkJSON), "reviews") {
				t.Fatal("结果映射制造评审")
			}
		})
	}
}
func TestRunServiceRejectsStaleAuthorityWrongMethodAndMissingSources(t *testing.T) {
	for _, kind := range []string{"review", "source", "argv", "cwd", "reserved", "extra-output", "dependency"} {
		t.Run(kind, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			switch kind {
			case "review":
				p := filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md")
				f, _ := os.OpenFile(p, os.O_APPEND|os.O_WRONLY, 0644)
				f.WriteString("修改设计\n")
				f.Close()
			case "source":
				os.Remove(filepath.Join(root, "rules/api.md"))
			case "argv":
				req.Argv = []string{req.Argv[0], "-test.run=none"}
			case "cwd":
				req.Cwd = "src"
			case "reserved":
				req.CheckID = "inputs"
			case "extra-output":
				req.InputPaths = []string{".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"}
			case "dependency":
				write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":["missing"]}}}`)
			}
			if r, e := runNative(t, root, req); e == nil {
				t.Fatal("非法运行前置被接受", kind, string(r.Observation.Details))
			}
		})
	}
}
func TestRunServiceGitOutputExcludedButKnownProductionIncluded(t *testing.T) {
	root, req := runProject(t, "in_dev")
	cmd := exec.Command("git", "init", root)
	if out, e := cmd.CombinedOutput(); e != nil {
		t.Fatal(string(out), e)
	}
	write(t, root, "new-production.txt", "实际新增生产输入")
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md", "旧验证结果，不用于本轮输入")
	r, e := runNative(t, root, req)
	if e != nil || r.Observation.Result != "passed" {
		t.Fatal(e, string(r.Observation.Details))
	}
	var d struct {
		Inputs []struct {
			Path string `json:"path"`
		} `json:"inputs_before"`
	}
	json.Unmarshal(r.Observation.Details, &d)
	found := false
	for _, f := range d.Inputs {
		if f.Path == "new-production.txt" {
			found = true
		}
		if strings.HasSuffix(f.Path, "verification.md") || strings.Contains(f.Path, "/runs/") {
			t.Fatal("输出进入自身输入", f)
		}
	}
	if !found {
		t.Fatal("已知实际生产变更遗漏")
	}
	again, e := runNative(t, root, req)
	if e != nil || again.Observation.Result != "passed" {
		t.Fatal("连续运行被自身历史输出阻塞", e, string(again.Observation.Details))
	}
}

func TestRunMappingFitsV2ButNeverSuppliesFreshReview(t *testing.T) {
	root, req := runProject(t, "in_dev")
	r, e := runNative(t, root, req)
	if e != nil {
		t.Fatal(e)
	}
	checkBytes, e := checks.ReceiptToCheck(r)
	if e != nil {
		t.Fatal(e)
	}
	c, e := protocol.Object(checkBytes)
	if e != nil {
		t.Fatal(e)
	}
	receipt, e := protocol.Object(r.Observation.Details)
	if e != nil {
		t.Fatal(e)
	}
	inputs := []any{}
	for _, v := range receipt["inputs_before"].([]any) {
		f := v.(map[string]any)
		if f["kind"] == "file" {
			inputs = append(inputs, map[string]any{"path": f["path"], "sha256": f["sha256"]})
		}
		if f["kind"] == "absent" {
			inputs = append(inputs, map[string]any{"path": f["path"], "sha256": nil, "state": "absent"})
		}
	}
	data := map[string]any{"version": 2, "subreq_id": "SR-001", "inputs": inputs, "checks": []any{c}}
	b, _ := json.Marshal(data)
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md", "<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->\n"+checks.VerificationStart+"\n```json\n"+string(b)+"\n```\n"+checks.VerificationEnd+"\n")
	if check(t, root, "merge", "merged").Decision.Allowed {
		t.Fatal("运行收据代替了fresh review")
	}
	// 测试夹具显式模拟后续独立评审；生产映射不产生该记录。
	persistVerification(t, root, data)
	if d := check(t, root, "merge", "merged"); !d.Decision.Allowed {
		t.Fatal("当前v2不能消费执行收据", d.Decision.Diagnostics)
	}
	write(t, root, "src/owner.txt", "评审后变更")
	if check(t, root, "merge", "merged").Decision.Allowed {
		t.Fatal("运行输入漂移后仍接受旧收据")
	}
}

func TestReviewedMalformedNativeMethodStillInvalidatesDesign(t *testing.T) {
	root, _ := runProject(t, "in_dev")
	p := filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md")
	b, e := os.ReadFile(p)
	if e != nil {
		t.Fatal(e)
	}
	bad := strings.Replace(string(b), `"parser_id":"exit-code"`, `"parser_id":"unknown"`, 1)
	os.WriteFile(p, []byte(bad), 0644)
	setStatus(t, root, "in_dev", func(d map[string]any) {
		d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(bad)))
	})
	if check(t, root, "implement", "in_dev").Decision.Allowed {
		t.Fatal("设计评审不能授权未知解析器")
	}
}

func TestPriorRunEvidenceAsRequiredReferenceIsNotOwnFutureOutput(t *testing.T) {
	root, req := runProject(t, "in_dev")
	first, e := runNative(t, root, req)
	if e != nil {
		t.Fatal(e)
	}
	b, e := os.ReadFile(filepath.Join(root, first.Path))
	if e != nil {
		t.Fatal(e)
	}
	ref, _ := json.Marshal(map[string]any{"version": 2, "inputs": []any{map[string]any{"path": first.Path, "sha256": fmt.Sprintf("%x", sha256.Sum256(b))}}, "checks": []any{}})
	write(t, root, ".ai-delivery/requirements/R/requirement.md", "原始需求的必要上游运行来源\n"+checks.VerificationStart+"\n```json\n"+string(ref)+"\n```\n"+checks.VerificationEnd+"\n")
	second, e := runNative(t, root, req)
	if e != nil || second.Observation.Result != "passed" {
		t.Fatal(e, string(second.Observation.Details))
	}
	var d struct {
		Inputs []struct {
			Path string `json:"path"`
		} `json:"inputs_before"`
	}
	json.Unmarshal(second.Observation.Details, &d)
	found := false
	for _, f := range d.Inputs {
		found = found || f.Path == first.Path
	}
	if !found {
		t.Fatal("丢弃必要历史输入")
	}
}
