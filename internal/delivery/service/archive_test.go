package service_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/mutation"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestArchiveCheckUsesCurrentContracts(t *testing.T) {
	root := actionProject(t, "merged")
	writeVerification(t, root, nil)
	setStatus(t, root, "merged", func(d map[string]any) { d["current_checkpoint"] = "CP-ARCHIVE" })
	date := time.Now().UTC().Format("2006-01-02")
	write(t, root, ".ai-delivery/requirements/R/retrospective.md", "<!-- ai-delivery-retrospective:reviewed-at:"+date+"T00:00:00Z -->\n")
	report := check(t, root, "archive", "")
	if !report.Decision.Allowed {
		t.Fatal(report.Decision.Diagnostics)
	}
	write(t, root, "result.log", "原生日志漂移")
	if check(t, root, "archive", "").Decision.Allowed {
		t.Fatal("待归档使用了历史豁免")
	}
}

// Confirmed=true 仅为协议夹具，不代表真实用户授权。
func archiveFixture(t *testing.T, git bool) (string, model.Workspace, model.ArchiveRequest) {
	t.Helper()
	root := actionProject(t, "merged")
	writeVerification(t, root, nil)
	write(t, root, ".ai-delivery/requirements/R/retrospective.md", strings.ReplaceAll(archiveLedger, "2026-11-05", time.Now().UTC().Format("2006-01-02")))
	write(t, root, "report-template.md", "# <req-id> 交付\n<archived_at>\n共 <subreq_count> 项\n<subreq_rows>\n")
	write(t, root, "index-template.md", "# 项目复盘\n<!-- ai-delivery-retrospective:index:v1 -->\n| Problem | Trigger | Scenario | Path | Status | Archived | Details |\n| --- | --- | --- | --- | --- | --- | --- |\n<retrospective_rows>\n<!-- /ai-delivery-retrospective:index:v1 -->\n")
	if git {
		cmd := exec.Command("git", "init", "-b", "main")
		cmd.Dir = root
		if b, e := cmd.CombinedOutput(); e != nil {
			t.Fatal(string(b), e)
		}
	}
	w, e := (workspace.Reader{}).Resolve(context.Background(), root, "")
	if e != nil {
		t.Fatal(e)
	}
	report := check(t, root, "archive", "")
	if !report.Decision.Allowed {
		t.Fatal(report.Decision.Diagnostics)
	}
	return root, w, model.ArchiveRequest{ExpectedSnapshot: report.Snapshot.ID(), Confirmed: true, DeliveryReportTemplate: "report-template.md", RetrospectiveIndexTemplate: "index-template.md"}
}

const archiveLedger = `<!-- ai-delivery-retrospective:reviewed-at:2026-11-05T00:00:00Z -->
<!-- ai-delivery-retrospective:problem-index:v2 -->
| Problem | Trigger | Scenario | Path | knowledge_type | reuse_scope | index_decision | confidence | importance | Status | Details |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RET-001 | 保存失败 | 重试 | src/save.go | reusable | project | include | confirmed | high | resolved | [详情](#ret-001) |
<!-- /ai-delivery-retrospective:problem-index:v2 -->
<a id="ret-001"></a>
## RET-001 保存失败
原因与修复。
`

var archiveScope = model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}

func TestArchivePublishesStatusLastAndOriginalCommandRetries(t *testing.T) {
	for _, git := range []bool{false, true} {
		for failAt := 1; failAt <= 3; failAt++ {
			t.Run(fmt.Sprintf("git=%v/publish=%d", git, failAt), func(t *testing.T) {
				root, w, req := archiveFixture(t, git)
				statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
				before, _ := os.ReadFile(statusPath)
				service := service.Service{Reader: workspace.Reader{}}
				calls := 0
				archiver := mutation.Archiver{Check: service.CheckAction, Publish: func(p string, b []byte, m os.FileMode, verify func(string) error) error {
					calls++
					if calls == failAt {
						return projectfs.AtomicWriteFileChecked(p, b, m, func(tmp string) error {
							if e := verify(tmp); e != nil {
								return e
							}
							return os.Rename(tmp, filepath.Join(root, "missing-parent", "cannot-publish"))
						})
					}
					return projectfs.AtomicWriteFileChecked(p, b, m, verify)
				}}
				result, err := archiver.Archive(context.Background(), w, archiveScope, req)
				if err == nil {
					t.Fatal("发布故障未触发", result)
				}
				current, _ := os.ReadFile(statusPath)
				if !bytes.Equal(before, current) {
					t.Fatal("必要输出失败却写了终态")
				}
				if err := filepath.WalkDir(root, func(p string, entry os.DirEntry, err error) error {
					if err != nil {
						return err
					}
					if strings.HasPrefix(entry.Name(), ".ai-delivery-write-") {
						return fmt.Errorf("归档失败遗留暂存文件: %s", p)
					}
					return nil
				}); err != nil {
					t.Fatal(err)
				}
				if report := check(t, root, "archive", ""); report.Snapshot.ID() != req.ExpectedSnapshot {
					t.Fatalf("自身输出破坏原命令身份: %s / %s", report.Snapshot.ID(), req.ExpectedSnapshot)
				}
				result, err = service.Archive(context.Background(), w, archiveScope, req)
				if err != nil || !result.Decision.Allowed {
					t.Fatal(result, err)
				}
				raw, _ := os.ReadFile(statusPath)
				status, _ := protocol.Object(raw)
				entry := status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
				if entry["status"] != "archived" {
					t.Fatal(entry)
				}
				if _, e := os.Stat(filepath.Join(root, ".ai-delivery/retrospectives/index.md")); e != nil {
					t.Fatal(e)
				}
				if _, e := os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/delivery-report.md")); e != nil {
					t.Fatal(e)
				}
				os.Remove(filepath.Join(root, "result.log"))
				write(t, root, "src/save.go", "后续合法生产版本")
				if report := check(t, root, "archive", ""); !report.Decision.Allowed {
					t.Fatal("历史错误消费当前源码/原生日志", report.Decision.Diagnostics)
				}
				write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", validDesign+"篡改")
				if check(t, root, "archive", "").Decision.Allowed {
					t.Fatal("历史固定合同篡改被接受")
				}
			})
		}
	}
}
func TestArchiveUnconfirmedHasNoSideEffects(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	req.Confirmed = false
	os.Remove(filepath.Join(root, ".ai-delivery.lock"))
	result, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
	if err == nil || len(result.WrittenPaths) != 0 {
		t.Fatal(result, err)
	}
	if _, e := os.Stat(filepath.Join(root, ".ai-delivery.lock")); !os.IsNotExist(e) {
		t.Fatal("无授权仍创建锁", e)
	}
}
func TestArchiveRejectsConcurrentGateAndOutputEdits(t *testing.T) {
	for _, kind := range []string{"gate", "unwritten-output", "written-output"} {
		t.Run(kind, func(t *testing.T) {
			root, w, req := archiveFixture(t, false)
			service := service.Service{Reader: workspace.Reader{}}
			calls := 0
			a := mutation.Archiver{Check: service.CheckAction, Publish: func(p string, b []byte, m os.FileMode, v func(string) error) error {
				calls++
				if calls == 2 {
					switch kind {
					case "gate":
						write(t, root, "result.log", "并发门禁编辑")
					case "unwritten-output":
						write(t, root, ".ai-delivery/retrospectives/index.md", "用户索引")
					case "written-output":
						write(t, root, ".ai-delivery/requirements/R/delivery-report.md", "用户报告")
					}
				}
				return projectfs.AtomicWriteFileChecked(p, b, m, v)
			}}
			_, err := a.Archive(context.Background(), w, archiveScope, req)
			if err == nil {
				t.Fatal("并发编辑被吞")
			}
			raw, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/status.json"))
			if strings.Contains(string(raw), `"archived"`) {
				t.Fatal("发生漂移仍终态")
			}
		})
	}
}

func TestArchiveCrossRetryPreservesForeignIndexAndRejectsOwnConflict(t *testing.T) {
	for _, conflict := range []bool{false, true} {
		t.Run(fmt.Sprint(conflict), func(t *testing.T) {
			root, w, req := archiveFixture(t, false)
			svc := service.Service{Reader: workspace.Reader{}}
			a := mutation.Archiver{Check: svc.CheckAction, Publish: func(p string, b []byte, m os.FileMode, v func(string) error) error {
				if filepath.Base(p) == "status.json" {
					return os.ErrPermission
				}
				return projectfs.AtomicWriteFileChecked(p, b, m, v)
			}}
			if _, err := a.Archive(context.Background(), w, archiveScope, req); err == nil {
				t.Fatal("未注入中断")
			}
			p := filepath.Join(root, ".ai-delivery/retrospectives/index.md")
			body, _ := os.ReadFile(p)
			if conflict {
				body = bytes.ReplaceAll(body, []byte("保存失败"), []byte("用户改变本需求判断"))
			} else {
				body = bytes.Replace(body, []byte(checks.ProjectIndexEnd), []byte("| OTHER/RET-002 | 用户新增 | 场景 | path | open | 2026 | [用户](other.md) |\n"+checks.ProjectIndexEnd), 1)
			}
			os.WriteFile(p, body, 0644)
			result, err := svc.Archive(context.Background(), w, archiveScope, req)
			if conflict {
				if err == nil {
					t.Fatal("本REQ冲突被覆盖", result)
				}
				current, _ := os.ReadFile(p)
				if !bytes.Equal(current, body) {
					t.Fatal("冲突内容被改写")
				}
			} else {
				if err != nil || !result.Decision.Allowed {
					t.Fatal(result, err)
				}
				current, _ := os.ReadFile(p)
				if !strings.Contains(string(current), "OTHER/RET-002") || strings.Count(string(current), "| R/RET-001 |") != 1 {
					t.Fatal(string(current))
				}
			}
		})
	}
}
func TestArchiveRejectsExplicitOutputConsumption(t *testing.T) {
	for _, kind := range []string{"policy", "requirement", "design", "agents"} {
		t.Run(kind, func(t *testing.T) {
			root, w, req := archiveFixture(t, false)
			p := ".ai-delivery/retrospectives/index.md"
			write(t, root, p, "用户维护的必读索引")
			switch kind {
			case "policy":
				write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":".ai-delivery/retrospectives/index.md","required":true}]}}`)
			case "requirement":
				write(t, root, ".ai-delivery/requirements/R/requirement.md", "原需求必须阅读 "+p)
			case "design":
				body := validDesign + "\n规范引用 " + p
				write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", body)
				setStatus(t, root, "merged", func(d map[string]any) {
					d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(body)))
				})
				writeVerification(t, root, nil)
			case "agents":
				write(t, root, ".ai-delivery/retrospectives/AGENTS.md", "必读规范 "+p)
			}
			checked := check(t, root, "archive", "")
			if !checked.Decision.Allowed {
				t.Fatal("夹具门禁应就绪", checked.Decision.Diagnostics)
			}
			req.ExpectedSnapshot = checked.Snapshot.ID()
			_, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
			if err == nil {
				t.Fatal("输出覆盖显式规范输入")
			}
			body, _ := os.ReadFile(filepath.Join(root, p))
			if string(body) != "用户维护的必读索引" {
				t.Fatal("必读索引被改写")
			}
		})
	}
}

func TestNativeReportReceiptNamedFieldRemainsOpaque(t *testing.T) {
	root := actionProject(t, "in_dev")
	d := writeVerification(t, root, nil)
	report := `{"receipt_version":"host-vendor-v7","stdout":{"path":"do-not-read-private.log"},"result":"passed"}`
	write(t, root, "result.log", report)
	d["checks"].([]any)[0].(map[string]any)["evidence"].([]any)[0].(map[string]any)["sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(report)))
	persistVerification(t, root, d)
	checked := check(t, root, "merge", "merged")
	if !checked.Decision.Allowed {
		t.Fatal("原生报告被误判 kit receipt", checked.Decision.Diagnostics)
	}
	for _, id := range checked.Snapshot.Files() {
		if id.Path == "do-not-read-private.log" {
			t.Fatal("opaque报告被扩引用")
		}
	}
}
func TestGitDiscoveredOldBackupReceiptRemainsOpaque(t *testing.T) {
	root := actionProject(t, "in_dev")
	writeVerification(t, root, nil)
	cmd := exec.Command("git", "init", "-b", "main")
	cmd.Dir = root
	if b, e := cmd.CombinedOutput(); e != nil {
		t.Fatal(string(b), e)
	}
	write(t, root, "backups/old-run/receipt.json", `{"receipt_version":0,"inputs":[{"path":"retired/source.go","sha256":null}]}`)
	checked := check(t, root, "merge", "merged")
	if !checked.Decision.Allowed {
		t.Fatal("未引用备份被当 kit receipt", checked.Decision.Diagnostics)
	}
	for _, id := range checked.Snapshot.Files() {
		if id.Path == "retired/source.go" {
			t.Fatal("旧备份扩引用")
		}
	}
}

func TestArchiveCustomNestedGovernanceAndProjectLock(t *testing.T) {
	root, _, req := archiveFixture(t, false)
	custom := "governance/delivery"
	raw, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"))
	v, err := checks.ParseBlock(raw, checks.VerificationStart, checks.VerificationEnd)
	if err != nil {
		t.Fatal(err)
	}
	for _, value := range v["inputs"].([]any) {
		e := value.(map[string]any)
		e["path"] = strings.Replace(e["path"].(string), ".ai-delivery", custom, 1)
	}
	persistVerification(t, root, v)
	write(t, root, ".ai-delivery/meta/project-binding.json", `{"version":3,"ai_delivery_path":"governance/delivery"}`)
	os.MkdirAll(filepath.Join(root, "governance"), 0755)
	if err := os.Rename(filepath.Join(root, ".ai-delivery"), filepath.Join(root, custom)); err != nil {
		t.Fatal(err)
	}
	w, err := (workspace.Reader{}).Resolve(context.Background(), root, custom)
	if err != nil {
		t.Fatal(err)
	}
	svc := service.Service{Reader: workspace.Reader{}}
	checked, err := svc.CheckAction(context.Background(), w, archiveScope, model.Action{Intent: "archive"})
	if err != nil || !checked.Decision.Allowed {
		t.Fatal(checked.Decision, err)
	}
	req.ExpectedSnapshot = checked.Snapshot.ID()
	result, err := svc.Archive(context.Background(), w, archiveScope, req)
	if err != nil || !result.Decision.Allowed {
		t.Fatal(result, err)
	}
	for _, p := range []string{custom + "/requirements/R/delivery-report.md", custom + "/retrospectives/index.md", ".ai-delivery.lock"} {
		if _, err := os.Stat(filepath.Join(root, p)); err != nil {
			t.Fatal(p, err)
		}
	}
	if _, err := os.Stat(filepath.Join(root, ".ai-delivery")); !os.IsNotExist(err) {
		t.Fatal("重建了错误默认根", err)
	}
}
func TestArchiveConcurrentSameProjectPublishesOnce(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	svc := service.Service{Reader: workspace.Reader{}}
	results := make(chan bool, 2)
	for i := 0; i < 2; i++ {
		go func() {
			r, e := svc.Archive(context.Background(), w, archiveScope, req)
			results <- e == nil && r.Decision.Allowed
		}()
	}
	success := 0
	for i := 0; i < 2; i++ {
		if <-results {
			success++
		}
	}
	if success != 1 {
		t.Fatalf("并发成功次数=%d", success)
	}
	body, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/retrospectives/index.md"))
	if strings.Count(string(body), "| R/RET-001 |") != 1 {
		t.Fatal("索引重复", string(body))
	}
}
func TestArchiveNonFinalPreservesDraftSibling(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	path := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	raw, _ := os.ReadFile(path)
	status, _ := protocol.Object(raw)
	sibling := map[string]any{"status": "draft", "note": "用户草稿", "large": json.Number("9007199254740993")}
	status["sub_requirements"].(map[string]any)["SR-002"] = sibling
	raw, _ = json.Marshal(status)
	os.WriteFile(path, raw, 0644)
	req.DeliveryReportTemplate = ""
	req.RetrospectiveIndexTemplate = ""
	req.ExpectedSnapshot = check(t, root, "archive", "").Snapshot.ID()
	r, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
	if err != nil || !r.Decision.Allowed {
		t.Fatal(r, err)
	}
	raw, _ = os.ReadFile(path)
	got, _ := protocol.Object(raw)
	if !reflect.DeepEqual(got["sub_requirements"].(map[string]any)["SR-002"], sibling) {
		t.Fatal("覆盖兄弟切片")
	}
	if _, err := os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/delivery-report.md")); !os.IsNotExist(err) {
		t.Fatal("非最终切片产生汇总报告")
	}
}

func TestArchiveSnapshotProtectsAbsenceModeAndLinkTarget(t *testing.T) {
	for _, kind := range []string{"absence", "mode", "link"} {
		t.Run(kind, func(t *testing.T) {
			root, w, req := archiveFixture(t, false)
			v := writeVerification(t, root, []any{map[string]any{"path": "absent.txt", "state": "absent", "sha256": nil}})
			if kind == "link" {
				if e := os.Symlink("result.log", filepath.Join(root, "result-link.log")); e != nil {
					t.Skipf("链接创建能力不可用: %v", e)
				}
				v["checks"].([]any)[0].(map[string]any)["evidence"].([]any)[0].(map[string]any)["path"] = "result-link.log"
				persistVerification(t, root, v)
			}
			req.ExpectedSnapshot = check(t, root, "archive", "").Snapshot.ID()
			switch kind {
			case "absence":
				write(t, root, "absent.txt", "重新出现")
			case "mode":
				if runtime.GOOS == "windows" {
					t.Skip("Unix mode 位断言")
				}
				os.Chmod(filepath.Join(root, "result.log"), 0600)
			case "link":
				body, _ := os.ReadFile(filepath.Join(root, "result.log"))
				write(t, root, "same.log", string(body))
				os.Remove(filepath.Join(root, "result-link.log"))
				os.Symlink("same.log", filepath.Join(root, "result-link.log"))
			}
			result, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
			if err == nil && result.Decision.Allowed {
				t.Fatal("文件身份漂移被接受")
			}
		})
	}
}

func TestArchivedDependencyDoesNotRebindDeletedExecutionEvidence(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	svc := service.Service{Reader: workspace.Reader{}}
	result, err := svc.Archive(context.Background(), w, archiveScope, req)
	if err != nil || !result.Decision.Allowed {
		t.Fatal(result, err)
	}
	raw, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/status.json"))
	status, _ := protocol.Object(raw)
	entries := status["sub_requirements"].(map[string]any)
	entries["SR-002"] = map[string]any{"status": "design_ready", "ui_truth_mode": "none", "ui_bearing": false, "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(validDesign))), "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_by": "协议夹具"}}
	raw, _ = json.Marshal(status)
	write(t, root, ".ai-delivery/requirements/R/status.json", string(raw))
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-002/design.md", validDesign)
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-002/requirement-slice.md", "下游切片需求")
	write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":["SR-001"]}}}`)
	os.Remove(filepath.Join(root, "result.log"))
	action := model.Action{Intent: "implement", TargetStatus: "in_dev"}
	scope := model.Scope{RequirementID: "R", SubrequirementID: "SR-002"}
	checked, err := svc.CheckAction(context.Background(), w, scope, action)
	if err != nil || !checked.Decision.Allowed {
		t.Fatal("历史上游重新消费运行证据", checked.Decision.Diagnostics, err)
	}
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md", "篡改固定验证合同")
	checked, err = svc.CheckAction(context.Background(), w, scope, action)
	if err == nil && checked.Decision.Allowed {
		t.Fatal("篡改历史上游未阻塞下游")
	}
}

func TestArchiveCheckRejectsStaleRetrospectiveBeforeMutation(t *testing.T) {
	root, _, _ := archiveFixture(t, false)
	write(t, root, ".ai-delivery/requirements/R/retrospective.md", "<!-- ai-delivery-retrospective:reviewed-at:2000-01-01 -->\n")
	if check(t, root, "archive", "").Decision.Allowed {
		t.Fatal("只读 archive check 错称过期复盘已就绪")
	}
}

func TestArchivedHistorySnapshotDoesNotDiscoverNewProductionScope(t *testing.T) {
	root, w, req := archiveFixture(t, true)
	svc := service.Service{Reader: workspace.Reader{}}
	result, err := svc.Archive(context.Background(), w, archiveScope, req)
	if err != nil || !result.Decision.Allowed {
		t.Fatal(result, err)
	}
	before := check(t, root, "archive", "")
	write(t, root, "future/deep/new-source.go", "新一轮合法生产代码")
	after := check(t, root, "archive", "")
	if !after.Decision.Allowed || before.Snapshot.ID() != after.Snapshot.ID() {
		t.Fatal("历史固定身份重新发现当前生产范围", after.Decision.Diagnostics)
	}
}

func TestArchiveMalformedIndexTemplateCannotPublishUnretryableOutput(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	write(t, root, "index-template.md", checks.ProjectIndexStart+"\n<retrospective_rows>\n"+checks.ProjectIndexEnd+"\n")
	result, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
	if err == nil {
		t.Fatal("无表分隔符模板产生无法幂等合并的索引", result)
	}
	if _, err := os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/delivery-report.md")); !os.IsNotExist(err) {
		t.Fatal("模板预检失败后仍发布报告")
	}
}

func TestArchiveIndexOwnershipIgnoresCellWhitespace(t *testing.T) {
	for _, whitespace := range []struct {
		name, before, after       string
		omitLeading, omitTrailing bool
	}{
		{"standard", " ", " ", false, false}, {"none", "", "", false, false}, {"multiple", "   ", "  ", false, false}, {"tab", "\t", "\t", false, false},
		{"optional-leading-border", "", " ", true, false}, {"optional-borders", "", " ", true, true},
	} {
		for _, edit := range []string{"equivalent", "conflict", "duplicate"} {
			t.Run(whitespace.name+"/"+edit, func(t *testing.T) {
				root, w, req := archiveFixture(t, false)
				svc := service.Service{Reader: workspace.Reader{}}
				a := mutation.Archiver{Check: svc.CheckAction, Publish: func(p string, b []byte, m os.FileMode, verify func(string) error) error {
					if filepath.Base(p) == "status.json" {
						return os.ErrPermission
					}
					return projectfs.AtomicWriteFileChecked(p, b, m, verify)
				}}
				if _, err := a.Archive(context.Background(), w, archiveScope, req); err == nil {
					t.Fatal("状态发布故障未触发")
				}
				indexPath := filepath.Join(root, ".ai-delivery/retrospectives/index.md")
				body, err := os.ReadFile(indexPath)
				if err != nil {
					t.Fatal(err)
				}
				var original string
				for _, line := range strings.Split(string(body), "\n") {
					if strings.HasPrefix(line, "| R/RET-001 |") {
						original = line
						break
					}
				}
				if original == "" {
					t.Fatal("夹具未发布本需求索引行")
				}
				row := strings.Replace(original, "| R/RET-001 |", "|"+whitespace.before+"R/RET-001"+whitespace.after+"|", 1)
				if whitespace.omitLeading {
					row = strings.TrimPrefix(row, "|")
				}
				if whitespace.omitTrailing {
					row = strings.TrimSuffix(row, "|")
				}
				if edit == "conflict" {
					row = strings.Replace(row, "保存失败", "用户冲突内容", 1)
				}
				if edit == "duplicate" {
					row = original + "\n" + row
				}
				foreign := "|\tOTHER/RET-002\t| 用户行 | 场景 | path | open | 2026 | [用户](other.md) |"
				body = []byte(strings.Replace(string(body), original, row+"\n"+foreign, 1) + "\n用户外围正文\n")
				if err := os.WriteFile(indexPath, body, 0644); err != nil {
					t.Fatal(err)
				}
				statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
				statusBefore, err := os.ReadFile(statusPath)
				if err != nil {
					t.Fatal(err)
				}
				result, err := svc.Archive(context.Background(), w, archiveScope, req)
				current, readErr := os.ReadFile(indexPath)
				if readErr != nil {
					t.Fatal(readErr)
				}
				if edit != "equivalent" {
					if err == nil {
						t.Fatal("本需求冲突或重复被空白变体绕过")
					}
					statusAfter, readErr := os.ReadFile(statusPath)
					if readErr != nil {
						t.Fatal(readErr)
					}
					if !bytes.Equal(current, body) || !bytes.Equal(statusBefore, statusAfter) || len(result.WrittenPaths) != 0 {
						t.Fatal("拒绝冲突时改变了索引或状态")
					}
					return
				}
				if err != nil || !result.Decision.Allowed {
					t.Fatalf("等价空白不能改变行归属: %v", err)
				}
				if strings.Count(string(current), "[R/RET-001](") != 1 || !bytes.Contains(current, []byte(foreign)) || !bytes.HasSuffix(current, []byte("\n用户外围正文\n")) {
					t.Fatal("重复本需求行或改写其他需求/外围正文")
				}
			})
		}
	}
}

func TestArchiveIndexPlaceholderMustOwnWritableLine(t *testing.T) {
	for _, inline := range []string{"<retrospective_rows> <!-- 模板说明 -->", "<!-- 模板说明 --> <retrospective_rows>", "说明 <retrospective_rows>"} {
		t.Run(inline, func(t *testing.T) {
			root, w, req := archiveFixture(t, false)
			p := filepath.Join(root, "index-template.md")
			template, err := os.ReadFile(p)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(p, bytes.Replace(template, []byte("<retrospective_rows>"), []byte(inline), 1), 0644); err != nil {
				t.Fatal(err)
			}
			index := ".ai-delivery/retrospectives/index.md"
			write(t, root, index, "用户保留的索引前言\n")
			statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			before, err := os.ReadFile(statusPath)
			if err != nil {
				t.Fatal(err)
			}
			result, err := (service.Service{Reader: workspace.Reader{}}).Archive(context.Background(), w, archiveScope, req)
			if err == nil {
				t.Fatal("行内模板未在发布前拒绝")
			}
			if len(result.WrittenPaths) != 0 {
				t.Fatal("错误模板已发布中间输出")
			}
			after, readErr := os.ReadFile(statusPath)
			if readErr != nil || !bytes.Equal(before, after) {
				t.Fatal("错误模板改变 status", readErr)
			}
			body, readErr := os.ReadFile(filepath.Join(root, index))
			if readErr != nil || string(body) != "用户保留的索引前言\n" {
				t.Fatal("错误模板改变既有索引", readErr)
			}
			if _, err := os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/delivery-report.md")); !os.IsNotExist(err) {
				t.Fatal("错误模板仍发布报告", err)
			}
		})
	}
}

func TestArchivePaddedStandalonePlaceholderRetries(t *testing.T) {
	root, w, req := archiveFixture(t, false)
	p := filepath.Join(root, "index-template.md")
	body, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, bytes.Replace(body, []byte("<retrospective_rows>"), []byte("  <retrospective_rows>\t "), 1), 0644); err != nil {
		t.Fatal(err)
	}
	svc := service.Service{Reader: workspace.Reader{}}
	a := mutation.Archiver{Check: svc.CheckAction, Publish: func(p string, b []byte, m os.FileMode, verify func(string) error) error {
		if filepath.Base(p) == "status.json" {
			return os.ErrPermission
		}
		return projectfs.AtomicWriteFileChecked(p, b, m, verify)
	}}
	if _, err := a.Archive(context.Background(), w, archiveScope, req); err == nil {
		t.Fatal("状态发布故障未触发")
	}
	if _, err := os.Stat(filepath.Join(root, ".ai-delivery/retrospectives/index.md")); err != nil {
		t.Fatal("合法独占占位符没有发布索引", err)
	}
	result, err := svc.Archive(context.Background(), w, archiveScope, req)
	if err != nil || !result.Decision.Allowed {
		t.Fatal("合法独占占位符无法原命令重试", err)
	}
}
