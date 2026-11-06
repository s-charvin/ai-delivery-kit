package service_test

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestMergedNativeRunRefreshesGovernanceInputsWithoutAdvancing(t *testing.T) {
	root, argv, _ := successfulGoReceipt(t)
	const statusPath = ".ai-delivery/requirements/R/status.json"
	const verificationPath = ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"
	const retrospectivePath = ".ai-delivery/requirements/R/retrospective.md"
	const decisionsPath = ".ai-delivery/requirements/R/sub-requirements/SR-001/decisions.md"
	ledger := strings.ReplaceAll(archiveLedger, "2026-11-05", time.Now().UTC().Format("2006-01-02"))
	write(t, root, retrospectivePath, ledger)
	write(t, root, decisionsPath, "已记录当前交付决定。\n")
	req := model.RunRequest{CheckID: "native-save", Argv: argv, Cwd: ".", TimeoutSeconds: 60}
	previous, err := runNative(t, root, req)
	if err != nil || previous.Observation.Result != "passed" {
		t.Fatal("合并前真实 Go 验证失败", err, string(previous.Observation.Details))
	}
	persistVerification(t, root, verificationFromRun(t, root, previous, false))
	merge := check(t, root, "merge", "merged")
	if !merge.Decision.Allowed {
		t.Fatal("合并前验收失败", merge.Decision.Diagnostics)
	}
	merged, err := advance(t, root, "merged", merge.Snapshot.ID())
	if err != nil || !merged.Decision.Allowed || len(merged.WrittenPaths) != 1 {
		t.Fatal("必须通过真实服务推进到 merged", merged, err)
	}
	if d := check(t, root, "archive", ""); !d.Decision.Allowed {
		t.Fatal("治理补记前归档控制组失败", d.Decision.Diagnostics)
	}
	statusBefore := readFixtureBytes(t, root, statusPath)
	oldReceipt := readFixtureBytes(t, root, previous.Path)
	write(t, root, retrospectivePath, ledger+"\n合并后补记：本轮实际验证情况。\n")
	write(t, root, decisionsPath, "已记录当前交付决定。\n合并后补记：复盘结论已核对。\n")
	stale := check(t, root, "archive", "")
	if stale.Decision.Allowed {
		t.Fatal("治理执行输入变更后旧证据仍可归档")
	}
	for _, path := range []string{retrospectivePath, decisionsPath} {
		found := false
		for _, d := range stale.Decision.Diagnostics {
			found = found || strings.Contains(d.Message, path)
		}
		if !found {
			t.Fatalf("旧归档拒绝没有覆盖执行输入 %s: %+v", path, stale.Decision.Diagnostics)
		}
	}
	t.Logf("旧归档拒绝: %+v", stale.Decision.Diagnostics)
	verificationBefore := readFixtureBytes(t, root, verificationPath)
	current, err := runNative(t, root, req)
	if err != nil || current.Observation.Result != "passed" {
		t.Fatal("merged 应允许原生证据重采集", err, string(current.Observation.Details))
	}
	if current.Path == previous.Path || !bytes.Equal(oldReceipt, readFixtureBytes(t, root, previous.Path)) {
		t.Fatal("重采集覆盖了原收据")
	}
	if !bytes.Equal(verificationBefore, readFixtureBytes(t, root, verificationPath)) {
		t.Fatal("运行自行映射 verification 或伪造 review")
	}
	t.Logf("新原生 stdout:\n%s", readFixtureBytes(t, root, filepath.ToSlash(filepath.Join(filepath.Dir(current.Path), "stdout.log"))))
	t.Logf("新原生 stderr:\n%s", readFixtureBytes(t, root, filepath.ToSlash(filepath.Join(filepath.Dir(current.Path), "stderr.log"))))
	data := verificationFromRun(t, root, current, false)
	for _, path := range []string{retrospectivePath, decisionsPath} {
		found := false
		for _, value := range data["inputs"].([]any) {
			found = found || value.(map[string]any)["path"] == path
		}
		if !found {
			t.Fatalf("新收据映射遗漏治理执行输入 %s", path)
		}
	}
	b, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
	write(t, root, verificationPath, "<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->\n"+checks.VerificationStart+"\n```json\n"+string(b)+"\n```\n"+checks.VerificationEnd+"\n")
	if d := check(t, root, "archive", ""); d.Decision.Allowed {
		t.Fatal("新运行映射不能代替 fresh review")
	} else {
		freshMissing := false
		for _, diagnostic := range d.Decision.Diagnostics {
			freshMissing = freshMissing || strings.Contains(diagnostic.Message, "评审")
		}
		if !freshMissing {
			t.Fatal("应由缺少评审阻塞", d.Decision.Diagnostics)
		}
	}
	// 仅自动化协议夹具：绑定真实新收据模拟 fresh 记录，不代表实际 AI 独立评审。
	persistVerification(t, root, data)
	archive := check(t, root, "archive", "")
	if !archive.Decision.Allowed {
		t.Fatal("新证据和夹具 fresh 后仍无法检查归档", archive.Decision.Diagnostics)
	}
	if d := check(t, root, "verify", ""); !d.Decision.Allowed {
		t.Fatal("merged 无目标只读 verify 应消费完整当前验收", d.Decision.Diagnostics)
	}
	for _, target := range []string{"in_dev", "design_ready", "visual_acceptance_passed", "merged"} {
		intent := map[string]string{"in_dev": "implement", "design_ready": "design", "visual_acceptance_passed": "verify", "merged": "merge"}[target]
		targetCheck := check(t, root, intent, target)
		if targetCheck.Decision.Allowed {
			t.Fatalf("merged 不应允许目标动作 %s", target)
		}
		result, err := advance(t, root, target, targetCheck.Snapshot.ID())
		if err == nil && result.Decision.Allowed || len(result.WrittenPaths) != 0 {
			t.Fatalf("证据刷新不能推进或降低状态 %s: %+v %v", target, result, err)
		}
	}
	reader := workspace.Reader{}
	w, err := reader.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	result, err := (service.Service{Reader: reader}).Archive(context.Background(), w, archiveScope, model.ArchiveRequest{ExpectedSnapshot: archive.Snapshot.ID()})
	if err == nil && result.Decision.Allowed || len(result.WrittenPaths) != 0 {
		t.Fatal("重采集不得授予归档确认", result, err)
	}
	if !bytes.Equal(statusBefore, readFixtureBytes(t, root, statusPath)) {
		t.Fatal("重采集/验收/拒绝推进改变了状态或批准字节")
	}
	write(t, root, "src/owner.go", "package owner\nfunc Save() string { return \"broken\" }\n")
	failed, err := runNative(t, root, req)
	if err != nil || failed.Observation.Result == "passed" {
		t.Fatal("merged 执行失败必须如实报告", err, string(failed.Observation.Details))
	}
	t.Logf("失败对照原生 stdout:\n%s", readFixtureBytes(t, root, filepath.ToSlash(filepath.Join(filepath.Dir(failed.Path), "stdout.log"))))
	persistVerification(t, root, verificationFromRun(t, root, failed, false))
	if check(t, root, "archive", "").Decision.Allowed || !bytes.Equal(statusBefore, readFixtureBytes(t, root, statusPath)) {
		t.Fatal("执行失败仍能归档或改变状态")
	}
}

func TestMergedRunStillRejectsStaleDesignWrongMethodMissingSourcesAndArchived(t *testing.T) {
	for _, kind := range []string{"design", "method", "source", "dependency", "ui-index", "archived"} {
		t.Run(kind, func(t *testing.T) {
			root, req := runProject(t, "merged")
			switch kind {
			case "design":
				path := ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md"
				write(t, root, path, string(readFixtureBytes(t, root, path))+"\n未重新授权的设计变更。\n")
			case "method":
				req.Argv = append(req.Argv, "not-reviewed")
			case "source":
				if err := os.Remove(filepath.Join(root, "rules/api.md")); err != nil {
					t.Fatal(err)
				}
			case "dependency":
				write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":["missing"]}}}`)
			case "ui-index":
				const path = ".ai-delivery/requirements/R/status.json"
				var d map[string]any
				if err := json.Unmarshal(readFixtureBytes(t, root, path), &d); err != nil {
					t.Fatal(err)
				}
				e := d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
				e["ui_truth_mode"], e["ui_bearing"] = "runtime-baseline", true
				b, err := json.Marshal(d)
				if err != nil {
					t.Fatal(err)
				}
				write(t, root, path, string(b))
			case "archived":
				updateRunStatus(t, root, "archived")
			}
			before := readFixtureBytes(t, root, ".ai-delivery/requirements/R/status.json")
			if r, err := runNative(t, root, req); err == nil {
				t.Fatal("非法前置被接受", kind, string(r.Observation.Details))
			} else if kind == "ui-index" && !strings.Contains(err.Error(), "ui_index") || kind == "archived" && !strings.Contains(err.Error(), "illegal_transition") {
				t.Fatal("未命中预期门禁", kind, err)
			}
			if !bytes.Equal(before, readFixtureBytes(t, root, ".ai-delivery/requirements/R/status.json")) {
				t.Fatal("拒绝运行改变了状态")
			}
			if _, err := os.Stat(filepath.Join(root, ".ai-delivery/runs")); !os.IsNotExist(err) {
				t.Fatal("前置失败仍然启动原生运行", err)
			}
		})
	}
}
