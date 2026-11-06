package service_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func gitFixtureCommand(t *testing.T, root string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %v: %v\n%s", args, err, out)
	}
}

func TestActiveParentReceiptUsesItsOwnCanonicalArtifacts(t *testing.T) {
	for _, custom := range []bool{false, true} {
		t.Run(fmt.Sprint(custom), func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			parentDir := ".ai-delivery/requirements/R/sub-requirements/SR-001/"
			childDir := ".ai-delivery/requirements/R/sub-requirements/SR-002/"
			designName, verificationName := "design.md", "verification.md"
			if custom {
				designName, verificationName = "plan.md", "checks.md"
				write(t, root, ".ai-delivery/meta/project-binding.json", `{"version":3,"layout":{"sub_requirement_artifacts":{"solution_design":"requirements/{req_id}/sub-requirements/{sr_id}/plan.md","verification":"requirements/{req_id}/sub-requirements/{sr_id}/checks.md"}}}`)
				if err := os.Rename(filepath.Join(root, parentDir+"design.md"), filepath.Join(root, parentDir+designName)); err != nil {
					t.Fatal(err)
				}
			}
			write(t, root, childDir+designName, validDesign)
			write(t, root, childDir+"requirement-slice.md", "后续切片原文")
			write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":["SR-001"]}}}`)
			statusPath := ".ai-delivery/requirements/R/status.json"
			status, err := protocol.Object(readFixtureBytes(t, root, statusPath))
			if err != nil {
				t.Fatal(err)
			}
			status["sub_requirements"].(map[string]any)["SR-002"] = map[string]any{"status": "design_ready", "ui_bearing": false, "ui_truth_mode": "none", "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(validDesign))), "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_by": "夹具评审"}}
			b, _ := json.Marshal(status)
			write(t, root, statusPath, string(b))
			gitFixtureCommand(t, root, "init", "-q")
			gitFixtureCommand(t, root, "add", ".")
			gitFixtureCommand(t, root, "-c", "user.name=fixture", "-c", "user.email=fixture@invalid", "commit", "-qm", "多切片基线")
			receipt, err := runNative(t, root, req)
			if err != nil || receipt.Observation.Result != "passed" {
				t.Fatal(err, string(receipt.Observation.Details))
			}
			persistVerification(t, root, verificationFromRun(t, root, receipt, false))
			if custom {
				if err := os.Rename(filepath.Join(root, parentDir+"verification.md"), filepath.Join(root, parentDir+verificationName)); err != nil {
					t.Fatal(err)
				}
			}
			checked := check(t, root, "merge", "merged")
			result, err := advance(t, root, "merged", checked.Snapshot.ID())
			if err != nil || !result.Decision.Allowed {
				t.Fatal("parent 控制未推进", result, err)
			}
			// 后续切片的已审阅设计和生成材料不是 parent 当次执行的输入。
			childDesign := validDesign + "\n后续切片的独立实现范围\n"
			write(t, root, childDir+designName, childDesign)
			write(t, root, childDir+verificationName, "后续切片的生成验证材料")
			status, err = protocol.Object(readFixtureBytes(t, root, statusPath))
			if err != nil {
				t.Fatal(err)
			}
			status["sub_requirements"].(map[string]any)["SR-002"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(childDesign)))
			b, _ = json.Marshal(status)
			write(t, root, statusPath, string(b))
			reader := workspace.Reader{}
			w, err := reader.Resolve(context.Background(), root, "")
			if err != nil {
				t.Fatal(err)
			}
			checkChild := func() model.CheckReport {
				r, e := (service.Service{Reader: reader}).CheckAction(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-002"}, model.Action{Intent: "implement", TargetStatus: "in_dev"})
				if e != nil {
					t.Fatal(e)
				}
				return r
			}
			if checked := checkChild(); !checked.Decision.Allowed {
				t.Fatal("主切片生成材料错误失效 parent 收据", checked.Decision.Diagnostics)
			}
			write(t, root, "src/owner.txt", "parent 已记录的执行输入改变")
			if checked := checkChild(); checked.Decision.Allowed {
				t.Fatal("scoped parent 漏掉旧输入漂移")
			}
		})
	}
}

func readFixtureBytes(t *testing.T, root, path string) []byte {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(root, path))
	if err != nil {
		t.Fatal(err)
	}
	return b
}

// 正常运行与独立评审夹具先通过；新输入不能靠旧收据和新 snapshot 推进。
func assertStaleReceiptCannotAdvance(t *testing.T, root string, receipt model.RunReceipt, oldReceipt, oldVerification []byte, changed ...string) {
	t.Helper()
	verificationPath := ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"
	statusPath := ".ai-delivery/requirements/R/status.json"
	before := readFixtureBytes(t, root, statusPath)
	checked := check(t, root, "merge", "merged")
	for _, path := range changed {
		found := false
		for _, f := range checked.Snapshot.Files() {
			found = found || f.Path == path
		}
		if !found {
			t.Fatalf("当前已知输入未进入实际快照: %s", path)
		}
	}
	if checked.Decision.Allowed {
		t.Fatal("旧执行未覆盖当前输入却允许 merge")
	}
	result, err := advance(t, root, "merged", checked.Snapshot.ID())
	if err != nil || result.Decision.Allowed || len(result.WrittenPaths) != 0 {
		t.Fatal("陈旧收据推进状态", result, err)
	}
	if !bytes.Equal(before, readFixtureBytes(t, root, statusPath)) {
		t.Fatal("拒绝后 status 字节发生改变")
	}
	if !bytes.Equal(oldReceipt, readFixtureBytes(t, root, receipt.Path)) || !bytes.Equal(oldVerification, readFixtureBytes(t, root, verificationPath)) {
		t.Fatal("校验改写了原收据或 verification")
	}
	found := false
	for _, d := range checked.Decision.Diagnostics {
		found = found || strings.Contains(d.Message, "运行收据")
	}
	if !found {
		t.Fatal("未由执行收据失效阻断", checked.Decision.Diagnostics)
	}
}

func successfulGoReceipt(t *testing.T) (string, []string, model.RunReceipt) {
	t.Helper()
	root := actionProject(t, "in_dev")
	write(t, root, "go.mod", "module probe\n\ngo 1.22.0\n")
	write(t, root, "src/owner.go", "package owner\nfunc Save() string { return \"saved\" }\n")
	write(t, root, "src/owner_test.go", "package owner\nimport \"testing\"\nfunc TestSave(t *testing.T) { if Save()!=\"saved\" { t.Fatal(\"not saved\") } }\n")
	goexe, err := exec.LookPath("go")
	if err != nil {
		t.Fatal(err)
	}
	argv := []string{goexe, "test", "-json", "-count=1", "./src"}
	method := map[string]any{"version": 1, "checks": []any{map[string]any{"id": "native-save", "argv": argv, "cwd": ".", "parser_id": "go-test-json", "acceptance_ids": []string{"AC-001"}, "input_paths": []string{"go.mod", "src/owner.go", "src/owner_test.go"}, "report_paths": []string{}, "source_refs": []string{"src/owner_test.go"}}}}
	b, _ := json.Marshal(method)
	block := checks.NativeMethodsStart + "\n```json\n" + string(b) + "\n```\n" + checks.NativeMethodsEnd + "\n"
	design := strings.Replace(validDesign, "<!-- ai-delivery:behavior-contract:traceability -->", block+"<!-- ai-delivery:behavior-contract:traceability -->", 1)
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", design)
	setStatus(t, root, "in_dev", func(d map[string]any) {
		d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(design)))
	})
	gitFixtureCommand(t, root, "init", "-q")
	receipt, err := runNative(t, root, model.RunRequest{CheckID: "native-save", Argv: argv, Cwd: ".", TimeoutSeconds: 60})
	if err != nil || receipt.Observation.Result != "passed" {
		t.Fatal(err, string(receipt.Observation.Details))
	}
	persistVerification(t, root, verificationFromRun(t, root, receipt, false))
	if checked := check(t, root, "merge", "merged"); !checked.Decision.Allowed {
		t.Fatal("合法控制", checked.Decision.Diagnostics)
	}
	return root, argv, receipt
}

func TestReceiptRejectsNewProductionThatBreaksActualGoCommand(t *testing.T) {
	root, argv, receipt := successfulGoReceipt(t)
	oldReceipt := readFixtureBytes(t, root, receipt.Path)
	oldVerification := readFixtureBytes(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")
	write(t, root, "src/broken.go", "package owner\nTHIS IS INVALID GO\n")
	cmd := exec.Command(argv[0], argv[1:]...)
	cmd.Dir = root
	out, err := cmd.CombinedOutput()
	if err == nil || !bytes.Contains(out, []byte("src/broken.go")) {
		t.Fatalf("相同原生命令应失败: %v\n%s", err, out)
	}
	assertStaleReceiptCannotAdvance(t, root, receipt, oldReceipt, oldVerification, "src/broken.go")
}

func TestReceiptCoversCurrentAddedDeletedRenamedAndAliasedInputs(t *testing.T) {
	for _, kind := range []string{"add", "delete", "rename", "new-alias", "unchanged-alias"} {
		t.Run(kind, func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			write(t, root, "src/previous.txt", "未被方法显式声明的已跟踪生产文件")
			if kind == "unchanged-alias" {
				if err := os.Symlink("src/owner.txt", filepath.Join(root, "owner-alias.txt")); err != nil {
					t.Fatal(err)
				}
				req.InputPaths = []string{"owner-alias.txt"}
			}
			gitFixtureCommand(t, root, "init", "-q")
			gitFixtureCommand(t, root, "add", ".")
			gitFixtureCommand(t, root, "-c", "user.name=fixture", "-c", "user.email=fixture@invalid", "commit", "-qm", "执行输入基线")
			receipt, err := runNative(t, root, req)
			if err != nil || receipt.Observation.Result != "passed" {
				t.Fatal(err, string(receipt.Observation.Details))
			}
			persistVerification(t, root, verificationFromRun(t, root, receipt, false))
			if checked := check(t, root, "merge", "merged"); !checked.Decision.Allowed {
				t.Fatal("合法控制", checked.Decision.Diagnostics)
			}
			oldReceipt := readFixtureBytes(t, root, receipt.Path)
			oldVerification := readFixtureBytes(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")
			var changed []string
			switch kind {
			case "add":
				write(t, root, "src/new.txt", "新生产输入")
				changed = []string{"src/new.txt"}
			case "delete":
				if err := os.Remove(filepath.Join(root, "src/previous.txt")); err != nil {
					t.Fatal(err)
				}
				changed = []string{"src/previous.txt"}
			case "rename":
				gitFixtureCommand(t, root, "mv", "src/previous.txt", "src/renamed.txt")
				changed = []string{"src/previous.txt", "src/renamed.txt"}
			case "new-alias":
				if err := os.Symlink("src/owner.txt", filepath.Join(root, "new-alias.txt")); err != nil {
					t.Fatal(err)
				}
				changed = []string{"new-alias.txt"}
			case "unchanged-alias":
				checked := check(t, root, "merge", "merged")
				result, err := advance(t, root, "merged", checked.Snapshot.ID())
				if err != nil || !result.Decision.Allowed || len(result.WrittenPaths) != 1 {
					t.Fatal("合法 alias 推进失败", result, err)
				}
				afterMerge := check(t, root, "archive", "archived")
				data, err := checks.ParseBlock(oldVerification, checks.VerificationStart, checks.VerificationEnd)
				if err != nil {
					t.Fatal(err)
				}
				if problems := checks.ValidateVerification(data, afterMerge.Snapshot, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", []string{"AC-001"}); len(problems) != 0 {
					t.Fatal("合法 Git 状态推进使收据自失效", problems)
				}
				return
			}
			assertStaleReceiptCannotAdvance(t, root, receipt, oldReceipt, oldVerification, changed...)
		})
	}
}

func TestReceiptRejectsProductionAliasToGeneratedOutput(t *testing.T) {
	for _, output := range []string{"receipt", "verification", "stdout"} {
		t.Run(output, func(t *testing.T) {
			root, argv, receipt := successfulGoReceipt(t)
			verification := ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"
			oldReceipt := readFixtureBytes(t, root, receipt.Path)
			oldVerification := readFixtureBytes(t, root, verification)
			target := receipt.Path
			if output == "verification" {
				target = verification
			}
			if output == "stdout" {
				data, err := protocol.Object(receipt.Observation.Details)
				if err != nil {
					t.Fatal(err)
				}
				target = data["stdout"].(map[string]any)["path"].(string)
			}
			if err := os.Symlink("../"+target, filepath.Join(root, "src/broken.go")); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command(argv[0], argv[1:]...)
			cmd.Dir = root
			out, err := cmd.CombinedOutput()
			if err == nil || !bytes.Contains(out, []byte("src/broken.go")) {
				t.Fatalf("输出 alias 必须使相同 Go 命令失败: %v\n%s", err, out)
			}
			assertStaleReceiptCannotAdvance(t, root, receipt, oldReceipt, oldVerification, "src/broken.go")
			if _, err := runNative(t, root, model.RunRequest{CheckID: "native-save", Argv: argv, Cwd: ".", TimeoutSeconds: 60}); err == nil {
				t.Fatal("运行入口未拒绝生产输入与自身输出混用")
			}
		})
	}
}
