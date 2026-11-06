package service_test

import (
	"bytes"
	"context"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sync"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/mutation"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func advance(t *testing.T, root, target, id string) (model.MutationResult, error) {
	t.Helper()
	r := workspace.Reader{}
	w, e := r.Resolve(context.Background(), root, "")
	if e != nil {
		t.Fatal(e)
	}
	return (service.Service{Reader: r}).Advance(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, target, id)
}

func TestAdvanceGitPublicationAndCooperativeConcurrency(t *testing.T) {
	root := actionProject(t, "design_ready")
	for _, args := range [][]string{{"init", "-b", "main"}, {"add", "."}, {"-c", "user.name=fixture", "-c", "user.email=fixture@invalid", "commit", "-qm", "测试基线"}} {
		cmd := exec.Command("git", args...)
		cmd.Dir = root
		if b, e := cmd.CombinedOutput(); e != nil {
			t.Fatal(string(b), e)
		}
	}
	d := check(t, root, "implement", "in_dev")
	if !d.Decision.Allowed {
		t.Fatal(d.Decision.Diagnostics)
	}
	var wg sync.WaitGroup
	results := make(chan bool, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r, e := advance(t, root, "in_dev", d.Snapshot.ID())
			results <- e == nil && r.Decision.Allowed
		}()
	}
	wg.Wait()
	close(results)
	successes := 0
	for ok := range results {
		if ok {
			successes++
		}
	}
	if successes != 1 {
		t.Fatalf("一次且仅一次成功，实际 %d", successes)
	}
	d = check(t, root, "implement", "in_dev")
	r, e := advance(t, root, "in_dev", d.Snapshot.ID())
	if e != nil || !r.Decision.Allowed || len(r.WrittenPaths) != 0 {
		t.Fatal("同态应无写", r, e)
	}
}

func TestAdvanceRejectsChangedInputsOrWrongIdentity(t *testing.T) {
	for _, kind := range []string{"design", "rules", "production", "intent", "target", "denied", "cancel"} {
		t.Run(kind, func(t *testing.T) {
			root := actionProject(t, "design_ready")
			if kind == "production" {
				cmd := exec.Command("git", "init", "-b", "main")
				cmd.Dir = root
				if b, e := cmd.CombinedOutput(); e != nil {
					t.Fatal(string(b), e)
				}
				write(t, root, "src/a.go", "原生产输入")
			}
			d := check(t, root, "implement", "in_dev")
			switch kind {
			case "design":
				write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", validDesign+"新设计")
			case "rules":
				write(t, root, "rules/api.md", "新规范")
			case "production":
				write(t, root, "src/a.go", "新生产输入")
			case "intent":
				d = check(t, root, "design", "")
			case "target":
				d = check(t, root, "design", "design_ready")
			case "denied":
				setStatus(t, root, "design_ready", func(v map[string]any) {
					v["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"] = map[string]any{}
				})
				d = check(t, root, "implement", "in_dev")
			}
			path := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			before, _ := os.ReadFile(path)
			var result model.MutationResult
			var err error
			if kind == "cancel" {
				ctx, cancel := context.WithCancel(context.Background())
				cancel()
				r := workspace.Reader{}
				w, _ := r.Resolve(context.Background(), root, "")
				result, err = (service.Service{Reader: r}).Advance(ctx, w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, "in_dev", d.Snapshot.ID())
			} else {
				result, err = advance(t, root, "in_dev", d.Snapshot.ID())
			}
			if err == nil && result.Decision.Allowed {
				t.Fatal("错误推进", kind)
			}
			after, _ := os.ReadFile(path)
			if !bytes.Equal(before, after) {
				t.Fatal("拒绝时写了status")
			}
		})
	}
}

func TestAdvanceRechecksNonCooperativeDriftAfterDecision(t *testing.T) {
	root := actionProject(t, "design_ready")
	d := check(t, root, "implement", "in_dev")
	path := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	before, _ := os.ReadFile(path)
	r := workspace.Reader{}
	w, _ := r.Resolve(context.Background(), root, "")
	svc := service.Service{Reader: r}
	checkWithDrift := func(ctx context.Context, w model.Workspace, s model.Scope, a model.Action) (model.CheckReport, error) {
		report, e := svc.CheckAction(ctx, w, s, a)
		write(t, root, "rules/api.md", "非合作修改")
		return report, e
	}
	result, e := mutation.Advance(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, "in_dev", d.Snapshot.ID(), checkWithDrift)
	if e == nil {
		t.Fatal("写前漂移未拒绝", result)
	}
	after, _ := os.ReadFile(path)
	if !bytes.Equal(before, after) {
		t.Fatal("漂移修改了status")
	}
}

func TestAdvanceReceiptRemainsValidAfterMergeUnlessStatusIsExecutionInput(t *testing.T) {
	for _, explicit := range []bool{false, true} {
		t.Run(fmt.Sprint(explicit), func(t *testing.T) {
			root, req := runProject(t, "in_dev")
			if explicit {
				req.InputPaths = []string{".ai-delivery/requirements/R/status.json"}
			}
			receipt, e := runNative(t, root, req)
			if e != nil {
				t.Fatal(e)
			}
			data := verificationFromRun(t, root, receipt, false)
			persistVerification(t, root, data)
			before := check(t, root, "merge", "merged")
			if !before.Decision.Allowed {
				t.Fatal(before.Decision.Diagnostics)
			}
			result, e := advance(t, root, "merged", before.Snapshot.ID())
			if e != nil || !result.Decision.Allowed {
				t.Fatal(result, e)
			}
			after := check(t, root, "archive", "archived")
			raw, _ := after.Snapshot.Document(".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")
			parsed, parseErr := checks.ParseBlock(raw, checks.VerificationStart, checks.VerificationEnd)
			if parseErr != nil {
				t.Fatal(parseErr)
			}
			problems := checks.ValidateVerification(parsed, after.Snapshot, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", []string{"AC-001"})
			if (len(problems) == 0) == explicit {
				t.Fatal("合法推进后的输入角色错误", explicit, problems)
			}
		})
	}
}

func TestPublicationRejectsConcurrentProductionEdit(t *testing.T) {
	for _, kind := range []string{"same-path-bytes", "new-path", "rename", "delete"} {
		t.Run(kind, func(t *testing.T) {
			root := actionProject(t, "design_ready")
			cmd := exec.Command("git", "init", "-b", "main")
			cmd.Dir = root
			if b, e := cmd.CombinedOutput(); e != nil {
				t.Fatal(string(b), e)
			}
			write(t, root, "src/a.go", "旧生产正文")
			d := check(t, root, "implement", "in_dev")
			path := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			before, _ := os.ReadFile(path)
			e := projectfs.AtomicWriteFileChecked(path, []byte("不得发布"), 0600, func(tmp string) error {
				switch kind {
				case "same-path-bytes":
					write(t, root, "src/a.go", "暂存期间非合作正文修改")
				case "new-path":
					write(t, root, "src/new.go", "新的生产文件")
				case "rename":
					if e := os.Rename(filepath.Join(root, "src/a.go"), filepath.Join(root, "src/renamed.go")); e != nil {
						return e
					}
				case "delete":
					if e := os.Remove(filepath.Join(root, "src/a.go")); e != nil {
						return e
					}
				}
				return (workspace.Reader{}).VerifyPublication(context.Background(), d.Snapshot, tmp)
			})
			if e == nil {
				t.Fatal("临时路径豁免吞掉了生产漂移")
			}
			after, _ := os.ReadFile(path)
			if !bytes.Equal(before, after) {
				t.Fatal("修改了status")
			}
		})
	}
}

func TestAdvancePreservesOtherSlicesAndRecordedAuthority(t *testing.T) {
	root := actionProject(t, "design_ready")
	setStatus(t, root, "design_ready", func(d map[string]any) {
		d["current_checkpoint"] = "CP-DESIGN"
		entries := d["sub_requirements"].(map[string]any)
		entries["SR-002"] = map[string]any{"status": "draft", "user_note": "保持用户原稿"}
		entry := entries["SR-001"].(map[string]any)
		entry["blocked_from_status"] = "design_ready"
		entry["resume_target_status"] = "in_dev"
	})
	write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":[]}}}`)
	path := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	raw, _ := os.ReadFile(path)
	before, e := protocol.Object(raw)
	if e != nil {
		t.Fatal(e)
	}
	d := check(t, root, "implement", "in_dev")
	result, e := advance(t, root, "in_dev", d.Snapshot.ID())
	if e != nil || !result.Decision.Allowed {
		t.Fatal(result, e)
	}
	raw, _ = os.ReadFile(path)
	after, e := protocol.Object(raw)
	if e != nil {
		t.Fatal(e)
	}
	after["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["status"] = "design_ready"
	if !reflect.DeepEqual(before, after) {
		t.Fatal("推进覆盖其他字段", before, after)
	}
}
