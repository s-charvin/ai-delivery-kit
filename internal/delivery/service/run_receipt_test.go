package service_test

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func verificationFromRun(t *testing.T, root string, r model.RunReceipt, current bool) map[string]any {
	t.Helper()
	b, e := checks.ReceiptToCheck(r)
	if e != nil {
		t.Fatalf("%v\nreceipt=%s", e, r.Observation.Details)
	}
	c, e := protocol.Object(b)
	if e != nil {
		t.Fatal(e)
	}
	d, e := protocol.Object(r.Observation.Details)
	if e != nil {
		t.Fatal(e)
	}
	inputs := []any{}
	roles, _ := d["input_roles"].(map[string]any)
	for _, value := range d["inputs_before"].([]any) {
		f := value.(map[string]any)
		p := f["path"].(string)
		if roles[p] == "prerequisite" {
			continue
		}
		if f["kind"] == "file" {
			hash := f["sha256"]
			if current {
				b, e := os.ReadFile(filepath.Join(root, p))
				if e != nil {
					t.Fatal(e)
				}
				hash = fmt.Sprintf("%x", sha256.Sum256(b))
			}
			inputs = append(inputs, map[string]any{"path": p, "sha256": hash})
		}
		if f["kind"] == "absent" {
			inputs = append(inputs, map[string]any{"path": p, "sha256": nil, "state": "absent"})
		}
	}
	return map[string]any{"version": 2, "subreq_id": "SR-001", "inputs": inputs, "checks": []any{c}}
}
func updateRunStatus(t *testing.T, root, state string) {
	t.Helper()
	p := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	raw, e := os.ReadFile(p)
	if e != nil {
		t.Fatal(e)
	}
	d, e := protocol.Object(raw)
	if e != nil {
		t.Fatal(e)
	}
	d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["status"] = state
	b, _ := json.Marshal(d)
	if e = os.WriteFile(p, b, 0644); e != nil {
		t.Fatal(e)
	}
}
func TestReceiptConsumerRejectsStaleExecutionWithRefreshedV2Inputs(t *testing.T) {
	for _, kind := range []string{"production", "design-method", "extra-input", "removed-receipt-path"} {
		t.Run(kind, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			if kind == "extra-input" {
				write(t, root, "extra.cfg", "before")
				req.InputPaths = []string{"extra.cfg"}
			}
			r, e := runNative(t, root, req)
			if e != nil {
				t.Fatal(e)
			}
			switch kind {
			case "production", "removed-receipt-path":
				write(t, root, "src/owner.txt", "未重新执行的新逻辑")
			case "extra-input":
				write(t, root, "extra.cfg", "after")
			case "design-method":
				p := filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md")
				b, _ := os.ReadFile(p)
				design := strings.Replace(string(b), `"native-owner"`, `"native-new"`, 1)
				os.WriteFile(p, []byte(design), 0644)
				setStatus(t, root, "in_dev", func(d map[string]any) {
					d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(design)))
				})
			}
			data := verificationFromRun(t, root, r, true)
			if kind == "removed-receipt-path" {
				delete(data["checks"].([]any)[0].(map[string]any), "receipt_path")
			}
			persistVerification(t, root, data)
			if result := check(t, root, "merge", "merged"); result.Decision.Allowed {
				t.Fatal("旧收据拼接当前inputs通过merge", kind)
			}
		})
	}
}
func TestReceiptStatusRoleAllowsLegalAdvanceButExplicitStatusRemainsInput(t *testing.T) {
	for _, explicit := range []string{"none", "extra", "source", "method", "alias-extra"} {
		t.Run(explicit, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			statusPath := ".ai-delivery/requirements/R/status.json"
			if explicit == "extra" {
				req.InputPaths = []string{statusPath}
			}
			if explicit == "alias-extra" {
				if e := os.Symlink(statusPath, filepath.Join(root, "state-alias.json")); e != nil {
					t.Fatal(e)
				}
				req.InputPaths = []string{"state-alias.json"}
			}
			if explicit == "source" || explicit == "method" {
				p := filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md")
				b, _ := os.ReadFile(p)
				key := "source_refs"
				if explicit == "method" {
					key = "input_paths"
				}
				design := strings.Replace(string(b), `"`+key+`":["src/owner.txt"]`, `"`+key+`":["src/owner.txt","`+statusPath+`"]`, 1)
				os.WriteFile(p, []byte(design), 0644)
				setStatus(t, root, "in_dev", func(d map[string]any) {
					d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(design)))
				})
			}
			r, e := runNative(t, root, req)
			if e != nil {
				t.Fatal(e)
			}
			data := verificationFromRun(t, root, r, false)
			persistVerification(t, root, data)
			if d := check(t, root, "merge", "merged"); !d.Decision.Allowed {
				t.Fatal("控制组运行证据无效", d.Decision.Diagnostics)
			}
			updateRunStatus(t, root, "merged")
			if explicit != "none" {
				data = verificationFromRun(t, root, r, true)
				persistVerification(t, root, data)
			}
			reader := workspace.Reader{}
			w, e := reader.Resolve(context.Background(), root, "")
			if e != nil {
				t.Fatal(e)
			}
			report, e := (service.Service{Reader: reader}).CheckAction(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.Action{Intent: "archive", TargetStatus: "archived"})
			if e != nil {
				t.Fatal(e)
			}
			raw, _ := report.Snapshot.Document(".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")
			parsed, parseErr := checks.ParseBlock(raw, checks.VerificationStart, checks.VerificationEnd)
			if parseErr != nil {
				t.Fatal(parseErr)
			}
			problems := checks.ValidateVerification(parsed, report.Snapshot, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", []string{"AC-001"})
			if (len(problems) == 0) != (explicit == "none") {
				t.Fatal("状态输入角色错误", explicit, problems)
			}
		})
	}
}

func TestReceiptConsumerRecomputesRolesAndRejectsMissingCurrentFields(t *testing.T) {
	for _, kind := range []string{"production-prerequisite", "explicit-status-prerequisite", "missing-roles", "missing-extra", "missing-capture", "forced-record", "actual-command-mismatch"} {
		t.Run(kind, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			statusPath := ".ai-delivery/requirements/R/status.json"
			if kind == "explicit-status-prerequisite" {
				req.InputPaths = []string{statusPath}
			}
			r, e := runNative(t, root, req)
			if e != nil {
				t.Fatal(e)
			}
			v := verificationFromRun(t, root, r, false)
			d, e := protocol.Object(r.Observation.Details)
			if e != nil {
				t.Fatal(e)
			}
			switch kind {
			case "production-prerequisite":
				d["input_roles"].(map[string]any)["src/owner.txt"] = "prerequisite"
			case "explicit-status-prerequisite":
				d["input_roles"].(map[string]any)[statusPath] = "prerequisite"
			case "missing-roles":
				delete(d, "input_roles")
			case "missing-extra":
				delete(d, "extra_input_paths")
			case "missing-capture":
				delete(d, "stdout_capture")
			case "forced-record":
				d["forced_termination"] = true
			case "actual-command-mismatch":
				d["argv"] = []any{"wrong-native-command"}
				command, _ := json.Marshal(d["argv"])
				v["checks"].([]any)[0].(map[string]any)["command"] = string(command)
			}
			b, _ := json.MarshalIndent(d, "", "  ")
			b = append(b, '\n')
			os.WriteFile(filepath.Join(root, r.Path), b, 0600)
			c := v["checks"].([]any)[0].(map[string]any)
			for _, value := range c["evidence"].([]any) {
				f := value.(map[string]any)
				if f["path"] == r.Path {
					f["sha256"] = fmt.Sprintf("%x", sha256.Sum256(b))
				}
			}
			persistVerification(t, root, v)
			if d := check(t, root, "merge", "merged"); d.Decision.Allowed {
				t.Fatal("收据自行角色声明或旧缺字段被接受", kind)
			}
		})
	}
}
func TestReceiptClosureReadsExecutionInputsAbsentFromV2List(t *testing.T) {
	root, req := runProject(t, "in_dev")
	r, e := runNative(t, root, req)
	if e != nil {
		t.Fatal(e)
	}
	v := verificationFromRun(t, root, r, false)
	design := ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md"
	for _, value := range v["inputs"].([]any) {
		if value.(map[string]any)["path"] == design {
			v["inputs"] = []any{value}
			break
		}
	}
	persistVerification(t, root, v)
	result := check(t, root, "merge", "merged")
	if !result.Decision.Allowed {
		t.Fatal("合法收据控制组未通过", result.Decision.Diagnostics)
	}
	found := false
	for _, f := range result.Snapshot.Files() {
		found = found || f.Path == "src/owner.txt"
	}
	if !found {
		t.Fatal("真实输入未进入最终闭包")
	}
	write(t, root, "src/owner.txt", "执行后变化")
	persistVerification(t, root, v)
	if check(t, root, "merge", "merged").Decision.Allowed {
		t.Fatal("遗漏v2普通输入列表就绕过了receipt输入")
	}
}
func TestReceiptExecutionInputProjectionExcludesOnlyDefaultStatus(t *testing.T) {
	root, req := runProject(t, "in_dev")
	r, e := runNative(t, root, req)
	if e != nil {
		t.Fatal(e)
	}
	b, e := checks.ReceiptExecutionInputs(r)
	if e != nil {
		t.Fatal(e)
	}
	var inputs []map[string]any
	if e = json.Unmarshal(b, &inputs); e != nil {
		t.Fatal(e)
	}
	found := false
	for _, f := range inputs {
		if f["path"] == ".ai-delivery/requirements/R/status.json" {
			t.Fatal("默认前置造成v2自循环")
		}
		found = found || f["path"] == "src/owner.txt"
	}
	if !found {
		t.Fatal("执行输入被丢弃")
	}
}

func TestNativeExecutedCannotDowngradeToOpaqueLogs(t *testing.T) {
	for _, mode := range []string{"executed", "renamed-executed", "reused", "manual", "waived"} {
		t.Run(mode, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			r, e := runNative(t, root, req)
			if e != nil {
				t.Fatal(e)
			}
			v := verificationFromRun(t, root, r, false)
			c := v["checks"].([]any)[0].(map[string]any)
			delete(c, "receipt_path")
			evidence := []any{}
			for _, entry := range c["evidence"].([]any) {
				if entry.(map[string]any)["path"] != r.Path {
					evidence = append(evidence, entry)
				}
			}
			c["evidence"] = evidence
			authority := map[string]any{"by": "显式协议测试确认者", "at": "2026-11-05T12:00:00+08:00", "reason": "明确授权手工验证/豁免的测试夹具", "source_ref": ".ai-delivery/requirements/R/requirement.md"}
			switch mode {
			case "renamed-executed":
				c["id"] = "other-external"
			case "reused":
				c["mode"] = "reused"
				c["reuse_reason"] = "旧日志"
			case "manual":
				c["mode"] = "manual"
				c["command"] = "依据来源执行明确手工验证步骤"
				c["confirmation"] = authority
			case "waived":
				c["result"] = "waived"
				c["waiver"] = authority
			}
			persistVerification(t, root, v)
			result := check(t, root, "merge", "merged")
			want := mode == "manual" || mode == "waived"
			if result.Decision.Allowed != want {
				t.Fatal("native方法不能静默降级，明确手工/豁免沿既有规则", mode, result.Decision.Diagnostics)
			}
		})
	}
}

func TestNativeReceiptConnectionCannotBeInferredFromOpaqueEvidence(t *testing.T) {
	root, req := runProject(t, "in_dev")
	receipt, err := runNative(t, root, req)
	if err != nil {
		t.Fatal(err)
	}
	v := verificationFromRun(t, root, receipt, false)
	delete(v["checks"].([]any)[0].(map[string]any), "receipt_path")
	persistVerification(t, root, v)
	if checked := check(t, root, "merge", "merged"); checked.Decision.Allowed {
		t.Fatal("删除 receipt_path 后由普通 evidence 猜测收据身份")
	}
	// 显式连接恢复后，收据即使先作为普通输入读取也必须展开全部输入/输出。
	c := v["checks"].([]any)[0].(map[string]any)
	c["receipt_path"] = receipt.Path
	body, err := os.ReadFile(filepath.Join(root, receipt.Path))
	if err != nil {
		t.Fatal(err)
	}
	v["inputs"] = append(v["inputs"].([]any), map[string]any{"path": receipt.Path, "sha256": fmt.Sprintf("%x", sha256.Sum256(body))})
	persistVerification(t, root, v)
	checked := check(t, root, "merge", "merged")
	if !checked.Decision.Allowed {
		t.Fatal(checked.Decision.Diagnostics)
	}
	found := false
	for _, id := range checked.Snapshot.Files() {
		found = found || strings.HasSuffix(id.Path, "stdout.log")
	}
	if !found {
		t.Fatal("先普通读取后登记的收据未展开原始流")
	}
	c["receipt_path"] = "result.log"
	write(t, root, "result.log", `{"receipt_version":"host-vendor-v7"}`)
	persistVerification(t, root, v)
	if check(t, root, "merge", "merged").Decision.Allowed {
		t.Fatal("显式非法 receipt_path 回退为 opaque")
	}
}
