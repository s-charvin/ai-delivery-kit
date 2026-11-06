package service_test

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/service"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestEquivalentDeclaredPathsSelectRequiredSources(t *testing.T) {
	root := project(t)
	os.Remove(filepath.Join(root, "rules/api.md"))
	for _, p := range []string{"src/a.go", "./src/a.go", "src//a.go", "./src//"} {
		req := request()
		req.DeclaredPaths = []string{p}
		report := prepare(t, root, req)
		if report.View.ContextComplete {
			t.Errorf("%q 绕过必读来源", p)
		}
		found := false
		for _, source := range report.View.Sources {
			if source.Path == "rules/api.md" && source.Required && source.Delivery == "missing" {
				found = true
			}
		}
		if !found {
			t.Errorf("%q 未保留规范义务", p)
		}
	}
}

func TestEquivalentSourcePathsUseOneCanonicalBody(t *testing.T) {
	root := project(t)
	write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"./rules//api.md","required":false},{"path":"rules/api.md","required":true}]}}`)
	report := prepare(t, root, request())
	if !report.View.ContextComplete {
		t.Fatal(report.View.Diagnostics)
	}
	count := 0
	for _, source := range report.View.Sources {
		if strings.Contains(source.Path, "rules") {
			count++
			if source.Path != "rules/api.md" || source.Delivery != "provided" || !source.Required || source.Body == nil || *source.Body != "接口规范" {
				t.Fatal(source)
			}
		}
	}
	if count != 1 {
		t.Fatalf("等价来源重复: %d", count)
	}
}

func TestFutureDirectoryHintSurvivesPathNormalization(t *testing.T) {
	root := project(t)
	write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"missing.md","paths":["future/*"]}]}}`)
	req := request()
	req.DeclaredPaths = []string{"./future//"}
	report := prepare(t, root, req)
	if report.View.ContextComplete {
		t.Fatal("目录尾斜线阅读义务丢失")
	}
	found := false
	for _, source := range report.View.Sources {
		found = found || source.Path == "missing.md" && source.Required
	}
	if !found {
		t.Fatal("目录范围未选择来源")
	}
}

func TestNestedGitProjectUsesProjectRelativeChanges(t *testing.T) {
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("环境没有Git")
	}
	root := project(t)
	top := filepath.Dir(root)
	run := func(args ...string) {
		t.Helper()
		cmd := exec.Command(git, append([]string{"-C", top}, args...)...)
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("%s %v", out, err)
		}
	}
	write(t, root, "src/a.go", "old")
	write(t, top, "sibling/file.go", "outside")
	run("init", "-q")
	run("add", ".")
	run("-c", "user.name=fixture", "-c", "user.email=f@invalid", "commit", "-qm", "fixture")
	write(t, root, "src/a.go", "new")
	write(t, top, "sibling/file.go", "outside-new")
	os.Remove(filepath.Join(root, "rules/api.md"))
	req := request()
	req.DeclaredPaths = nil
	report := prepare(t, root, req)
	if report.View.ContextComplete {
		t.Fatal("Git子目录坐标错误漏必读来源")
	}
	facts, err := workspace.Facts(report.Snapshot)
	if err != nil {
		t.Fatal(err)
	}
	for _, p := range facts.ObservedChangedPaths {
		if strings.HasPrefix(p, filepath.Base(root)+"/") || strings.HasPrefix(p, "sibling/") {
			t.Fatalf("错误项目坐标: %s", p)
		}
	}
	agents := false
	required := false
	for _, source := range report.View.Sources {
		agents = agents || source.Path == "src/AGENTS.md" && source.Delivery == "provided"
		required = required || source.Path == "rules/api.md" && source.Required && source.Delivery == "missing"
	}
	if !agents || !required {
		t.Fatalf("AGENTS=%v required=%v", agents, required)
	}
}

func write(t *testing.T, root, p, b string) {
	t.Helper()
	p = filepath.Join(root, p)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(b), 0644); err != nil {
		t.Fatal(err)
	}
}
func project(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	write(t, root, ".ai-delivery/meta/project-binding.json", `{"version":3}`)
	write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"rules/api.md","paths":["src/*"],"roles":["implement","review"],"required":true}]}}`)
	write(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"merged"},"SR-002":{"status":17,"ui_bearing":"invalid"}}}`)
	write(t, root, ".ai-delivery/requirements/R/requirement.md", "原始需求正文")
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", "当前设计参见 requirement.md 和 requirement-slice.md。")
	write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/requirement-slice.md", "切片原文")
	write(t, root, "AGENTS.md", "根规范")
	write(t, root, "src/AGENTS.md", "模块规范")
	write(t, root, "rules/api.md", "接口规范")
	return root
}
func prepare(t *testing.T, root string, req model.ContextRequest) model.ContextReport {
	t.Helper()
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	report, err := (service.Service{Reader: r}).PrepareContext(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, req)
	if err != nil {
		t.Fatal(err)
	}
	return report
}
func request() model.ContextRequest {
	return model.ContextRequest{Role: "implement", DeclaredPaths: []string{"src/deep/file.go"}, BudgetChars: 200000}
}
func TestCompleteContextDoesNotValidateMissingVerificationOrOtherSlice(t *testing.T) {
	root := project(t)
	report := prepare(t, root, request())
	if !report.View.ContextComplete {
		t.Fatalf("仅消费材料应完整: %#v", report.View.Diagnostics)
	}
	sources := map[string]model.ContextSource{}
	for _, s := range report.View.Sources {
		sources[s.Path] = s
		if strings.Contains(s.Path, "verification") {
			t.Fatal("context 不应消费 verification")
		}
	}
	for _, p := range []string{"AGENTS.md", "src/AGENTS.md", "rules/api.md", ".ai-delivery/requirements/R/requirement.md"} {
		s, ok := sources[p]
		if !ok || s.Delivery != "provided" || s.Body == nil || s.SHA256 == nil {
			t.Fatalf("缺少正文 %s: %#v", p, s)
		}
	}
	if report.Snapshot.Request().Action != nil {
		t.Fatal("context 产生动作授权")
	}
}
func TestBudgetMissingAndRoleFiltering(t *testing.T) {
	root := project(t)
	req := request()
	req.BudgetChars = 1
	r := prepare(t, root, req)
	if r.View.ContextComplete {
		t.Fatal("预算不足却完整")
	}
	found := false
	for _, s := range r.View.Sources {
		found = found || s.Required && s.Delivery == "needs_read"
	}
	if !found {
		t.Fatal("未保留补读义务")
	}
	os.Remove(filepath.Join(root, "rules/api.md"))
	r = prepare(t, root, request())
	if r.View.ContextComplete {
		t.Fatal("必需规范缺失")
	}
	req = request()
	req.Role = "recovery"
	r = prepare(t, root, req)
	if !r.View.ContextComplete {
		t.Fatal(r.View.Diagnostics)
	}
	for _, s := range r.View.Sources {
		if s.Path == "rules/api.md" {
			t.Fatal("角色过滤未生效")
		}
	}
}
func TestUnselectedSourceDoesNotConsumeBytesAndDuplicateKeepsRequired(t *testing.T) {
	root := project(t)
	write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"rules/missing.md","required":false},{"path":"rules/missing.md","required":true},{"path":"bad.md","roles":["review"]}]}}`)
	os.Symlink("/etc/hosts", filepath.Join(root, "bad.md"))
	r := prepare(t, root, request())
	count := 0
	for _, s := range r.View.Sources {
		if s.Path == "rules/missing.md" {
			count++
			if !s.Required || s.Delivery != "missing" {
				t.Fatal(s)
			}
		}
		if s.Path == "bad.md" {
			t.Fatal("未匹配来源被读取")
		}
	}
	if count != 1 || r.View.ContextComplete {
		t.Fatal(r.View)
	}
}
func TestSnapshotIdentityDomainsAndConcurrentCopies(t *testing.T) {
	root := project(t)
	a := prepare(t, root, request())
	req := request()
	req.BudgetChars--
	b := prepare(t, root, req)
	if a.Snapshot.ID() == b.Snapshot.ID() {
		t.Fatal("预算未绑定")
	}
	req = request()
	req.Role = "review"
	b = prepare(t, root, req)
	if a.Snapshot.ID() == b.Snapshot.ID() {
		t.Fatal("角色未绑定")
	}
	req = request()
	req.DeclaredPaths = []string{"src/other.go"}
	b = prepare(t, root, req)
	if a.Snapshot.ID() == b.Snapshot.ID() {
		t.Fatal("声明范围未绑定")
	}
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for n := 0; n < 100; n++ {
				b, _ := workspace.Fact(a.Snapshot, "status")
				b[0] = 'x'
				req := a.Snapshot.Request()
				req.Context.DeclaredPaths[0] = "mutated"
				files := a.Snapshot.Files()
				for i := range files {
					if files[i].SHA256 != nil {
						*files[i].SHA256 = "mutated"
					}
				}
			}
		}()
	}
	wg.Wait()
	body, _ := workspace.Fact(a.Snapshot, "status")
	if body[0] != '{' || a.Snapshot.Request().Context.DeclaredPaths[0] != "src/deep/file.go" {
		t.Fatal("共享存储被改")
	}
}

func TestCurrentRecoveryStatusAndUnknownStatusIsolation(t *testing.T) {
	root := project(t)
	write(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"blocked_verification_failure"},"SR-002":{"status":null}}}`)
	req := request()
	req.Role = "recovery"
	r := prepare(t, root, req)
	if !r.View.ContextComplete {
		t.Fatal(r.View.Diagnostics)
	}
	write(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"invented"}}}`)
	r = prepare(t, root, req)
	if r.View.ContextComplete {
		t.Fatal("未知所选切片状态必须诊断")
	}
}

func TestProjectSourceNamedStatusDoesNotOverwriteLogicalFact(t *testing.T) {
	root := project(t)
	write(t, root, "status", "同名规范原文")
	write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"status"}]}}`)
	r := prepare(t, root, request())
	if !r.View.ContextComplete {
		t.Fatal(r.View.Diagnostics)
	}
	found := false
	for _, s := range r.View.Sources {
		if s.Path == "status" && s.Body != nil && *s.Body == "同名规范原文" {
			found = true
		}
	}
	if !found {
		t.Fatal("同名实际文件未提供")
	}
}

func TestDesignBeforeDesignFileStillRequiresOriginalRequirement(t *testing.T) {
	root := project(t)
	write(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"split_ready"}}}`)
	os.Remove(filepath.Join(root, ".ai-delivery/requirements/R/requirement.md"))
	os.Remove(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md"))
	req := request()
	req.Role = "design"
	r := prepare(t, root, req)
	if r.View.ContextComplete {
		t.Fatal("缺原始需求不能声称设计材料完整")
	}
	found := false
	for _, source := range r.View.Sources {
		if source.Path == ".ai-delivery/requirements/R/requirement.md" && source.Required && source.Delivery == "missing" {
			found = true
		}
	}
	if !found {
		t.Fatal("原始需求阅读义务被省略")
	}
}

func TestInstructionDirectoryCannotStandInForBody(t *testing.T) {
	root := project(t)
	os.Remove(filepath.Join(root, "src/AGENTS.md"))
	os.Mkdir(filepath.Join(root, "src/AGENTS.md"), 0755)
	r := prepare(t, root, request())
	if r.View.ContextComplete {
		t.Fatal("目录不能代替必需规范正文")
	}
}
