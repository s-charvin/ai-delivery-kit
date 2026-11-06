package workspace_test

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestVerifyScopeTypeAndAbsenceWithoutReadingBusinessBytes(t *testing.T) {
	for _, initial := range []string{"file", "absent", "directory"} {
		t.Run(initial, func(t *testing.T) {
			root := fixture(t)
			switch initial {
			case "file":
				put(t, root, "scope", "business bytes")
			case "directory":
				os.Mkdir(filepath.Join(root, "scope"), 0755)
			}
			r := workspace.Reader{}
			w, err := r.Resolve(context.Background(), root, "")
			if err != nil {
				t.Fatal(err)
			}
			s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis", DeclaredPaths: []string{"scope"}}})
			if err != nil {
				t.Fatal(err)
			}
			if _, ok := s.Document("scope"); ok {
				t.Fatal("范围类型观察不应读取业务正文")
			}
			if initial == "directory" {
				os.Remove(filepath.Join(root, "scope"))
				put(t, root, "scope", "now file")
			} else {
				os.Remove(filepath.Join(root, "scope"))
				os.Mkdir(filepath.Join(root, "scope"), 0755)
				put(t, root, "scope/AGENTS.md", "new rule")
			}
			if err := r.Verify(context.Background(), s); err == nil {
				t.Fatal("选择类型改变未使旧快照失效")
			}
			if _, err := r.Extend(context.Background(), s, []string{"AGENTS.md"}); err == nil {
				t.Fatal("Extend接受过期选择事实")
			}
		})
	}
}

func TestSystemAliasAllowsInternalAbsoluteLinkAndKeepsBoundary(t *testing.T) {
	if runtime.GOOS != "darwin" {
		t.Skip("使用macOS真实/tmp系统别名")
	}
	root, err := os.MkdirTemp("/private/tmp", "t2-alias-")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(root)
	put(t, root, ".ai-delivery/meta/project-binding.json", `{"version":3}`)
	put(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2}`)
	put(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"draft"}}}`)
	put(t, root, "rules.md", "internal")
	alias := "/tmp/" + filepath.Base(root)
	if err := os.Symlink(filepath.Join(root, "rules.md"), filepath.Join(root, "link.md")); err != nil {
		t.Fatal(err)
	}
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), alias, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	s, err = r.Extend(context.Background(), s, []string{"link.md"})
	if err != nil {
		t.Fatal(err)
	}
	body, ok := s.Document("link.md")
	if !ok || string(body) != "internal" {
		t.Fatal(string(body))
	}
	put(t, root, "real/rules.md", "ancestor")
	if err := os.Symlink("real", filepath.Join(root, "inner")); err != nil {
		t.Fatal(err)
	}
	os.Remove(filepath.Join(root, "link.md"))
	if err := os.Symlink(filepath.Join(alias, "inner/rules.md"), filepath.Join(root, "link.md")); err != nil {
		t.Fatal(err)
	}
	physical, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	second, err := r.Load(context.Background(), physical, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	second, err = r.Extend(context.Background(), second, []string{"link.md"})
	if err != nil {
		t.Fatal(err)
	}
	ancestor := false
	for _, f := range second.Files() {
		ancestor = ancestor || f.Path == "inner" && f.Kind == "symlink"
	}
	if !ancestor {
		t.Fatal("系统别名规范化丢失项目内祖先链接身份")
	}
	os.Remove(filepath.Join(root, "link.md"))
	os.Symlink("/etc/hosts", filepath.Join(root, "link.md"))
	if err := r.Verify(context.Background(), s); err == nil {
		t.Fatal("外部链接换入未拒绝")
	}
}

func TestProjectRootLinkRemainsVisibleAndRetargetInvalidatesSnapshot(t *testing.T) {
	left := fixture(t)
	right := fixture(t)
	alias := filepath.Join(t.TempDir(), "project")
	if err := os.Symlink(left, alias); err != nil {
		t.Fatal(err)
	}
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), alias, "")
	if err != nil {
		t.Fatal(err)
	}
	if w.ProjectRoot != alias {
		t.Fatal("原始项目根链接不能从后续写边界消失")
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	os.Remove(alias)
	if err := os.Symlink(right, alias); err != nil {
		t.Fatal(err)
	}
	if err := r.Verify(context.Background(), s); err == nil {
		t.Fatal("原始项目根重定向未使快照失效")
	}
}

func TestNestedGitRenamesKeepEachProjectEndpoint(t *testing.T) {
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("环境没有Git")
	}
	root := fixture(t)
	top := filepath.Dir(root)
	prefix := filepath.Base(root) + "/"
	run := func(args ...string) {
		t.Helper()
		cmd := exec.Command(git, append([]string{"-C", top}, args...)...)
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("%s %v", out, err)
		}
	}
	put(t, root, "old.go", "old")
	put(t, root, "exit.go", "exit")
	put(t, top, "outside.go", "enter")
	run("init", "-q")
	run("add", ".")
	run("-c", "user.name=fixture", "-c", "user.email=f@invalid", "commit", "-qm", "fixture")
	run("mv", prefix+"old.go", prefix+"new.go")
	run("mv", "outside.go", prefix+"entered.go")
	run("mv", prefix+"exit.go", "outside2.go")
	paths, known, err := workspace.ObservedChanges(context.Background(), root)
	if err != nil || !known {
		t.Fatal(err)
	}
	want := []string{"entered.go", "exit.go", "new.go", "old.go"}
	if !reflect.DeepEqual(paths, want) {
		t.Fatalf("%q != %q", paths, want)
	}
}

func put(t *testing.T, root, path, body string) {
	t.Helper()
	p := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(body), 0644); err != nil {
		t.Fatal(err)
	}
}
func fixture(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	put(t, root, ".ai-delivery/meta/project-binding.json", `{"version":3}`)
	put(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2}`)
	put(t, root, ".ai-delivery/requirements/R/status.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"merged"}}}`)
	return root
}
func TestResolveRequiresBindingAndRejectsAmbiguity(t *testing.T) {
	r := workspace.Reader{}
	ctx := context.Background()
	if _, err := r.Resolve(ctx, t.TempDir(), ""); err == nil {
		t.Fatal("未初始化目录被当成已初始化项目")
	}
	root := fixture(t)
	put(t, root, "other/meta/project-binding.json", `{"version":3,"ai_delivery_path":"other"}`)
	if _, err := r.Resolve(ctx, root, ""); err == nil {
		t.Fatal("多个候选未拒绝")
	}
	w, err := r.Resolve(ctx, root, ".ai-delivery")
	if err != nil {
		t.Fatal(err)
	}
	if w.DeliveryRoot != filepath.Join(root, ".ai-delivery") {
		t.Fatal(w)
	}
}
func TestCustomLayoutAndInternalSymlinkIdentity(t *testing.T) {
	root := fixture(t)
	put(t, root, "nested/delivery/meta/project-binding.json", `{"version":3,"ai_delivery_path":"nested/delivery","layout":{"requirement_artifacts":{"status":"cases/{req_id}.json"}}}`)
	put(t, root, "nested/delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2}`)
	put(t, root, "nested/delivery/cases/R.json", `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"draft"}}}`)
	put(t, root, "rules/real.md", "原文")
	if err := os.Symlink("real.md", filepath.Join(root, "rules/hop.md")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("hop.md", filepath.Join(root, "rules/read.md")); err != nil {
		t.Fatal(err)
	}
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "nested/delivery")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis", BudgetChars: 100000}})
	if err != nil {
		t.Fatal(err)
	}
	s, err = r.Extend(context.Background(), s, []string{"rules/read.md", "absent.md"})
	if err != nil {
		t.Fatal(err)
	}
	body, ok := s.Document("rules/read.md")
	if !ok || string(body) != "原文" {
		t.Fatal(string(body))
	}
	seen := map[string]string{}
	for _, f := range s.Files() {
		seen[f.Path] = f.Kind
	}
	for _, p := range []string{"rules/read.md", "rules/hop.md", "rules/real.md"} {
		if seen[p] == "" {
			t.Fatalf("没有登记传递身份 %s", p)
		}
	}
	if seen["absent.md"] != "absent" {
		t.Fatal(seen)
	}
	body[0] = 'x'
	again, _ := s.Document("rules/read.md")
	if string(again) != "原文" {
		t.Fatal("正文共享")
	}
	req := s.Request()
	req.Context.Role = "finish"
	if s.Request().Context.Role != "analysis" {
		t.Fatal("请求共享")
	}
	files := s.Files()
	for i := range files {
		if files[i].Mode != nil {
			*files[i].Mode = 0
			break
		}
	}
	if reflect.DeepEqual(files, s.Files()) {
		t.Fatal("文件身份共享")
	}
	old := s.ID()
	put(t, root, "absent.md", "出现")
	changed, err := r.Extend(context.Background(), s, []string{"absent.md"})
	if err == nil && changed.ID() == old {
		t.Fatal("缺失变为存在未影响身份")
	}
}
func TestReaderRejectsEscapeAndCycles(t *testing.T) {
	root := fixture(t)
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	os.Symlink("loop", filepath.Join(root, "loop"))
	os.Symlink(t.TempDir(), filepath.Join(root, "outside"))
	for _, p := range []string{"../escape", "loop", "outside/file"} {
		if _, err := r.Extend(context.Background(), s, []string{p}); err == nil {
			t.Fatalf("未拒绝 %s", p)
		}
	}
}
func TestGitChangesAndNoGitExecutable(t *testing.T) {
	root := fixture(t)
	r := workspace.Reader{}
	ctx := context.Background()
	w, err := r.Resolve(ctx, root, "")
	if err != nil {
		t.Fatal(err)
	}
	req := model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}}
	t.Setenv("PATH", t.TempDir())
	s, err := r.Load(ctx, w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, req)
	if err != nil || len(s.Diagnostics()) != 0 {
		t.Fatalf("非Git项目不应依赖Git: %v %v", err, s.Diagnostics())
	}
	os.Mkdir(filepath.Join(root, ".git"), 0755)
	s, err = r.Load(ctx, w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, req)
	if err != nil {
		t.Fatal(err)
	}
	if len(s.Diagnostics()) == 0 {
		t.Fatal("已有Git仓库无法发现范围必须诊断")
	}
}
func TestRealGitRenameAndDeletedPaths(t *testing.T) {
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("环境没有Git")
	}
	oldPaths := []string{"old/旧 文件.go"}
	if runtime.GOOS != "windows" {
		oldPaths = append(oldPaths, "old/a\nfile.go")
	}
	for _, oldPath := range oldPaths {
		t.Run(oldPath, func(t *testing.T) {
			root := fixture(t)
			run := func(args ...string) {
				t.Helper()
				cmd := exec.Command(git, append([]string{"-C", root}, args...)...)
				if out, err := cmd.CombinedOutput(); err != nil {
					t.Fatalf("%s: %v", out, err)
				}
			}
			put(t, root, oldPath, "old")
			put(t, root, "deleted.go", "del")
			run("init", "-q")
			run("add", ".")
			run("-c", "user.name=fixture", "-c", "user.email=f@invalid", "commit", "-qm", "fixture")
			os.Mkdir(filepath.Join(root, "new"), 0755)
			run("mv", oldPath, "new/a file.go")
			put(t, root, "new/a file.go", "modified")
			put(t, root, "new.go", "new")
			os.Remove(filepath.Join(root, "deleted.go"))
			paths, known, err := workspace.ObservedChanges(context.Background(), root)
			if err != nil || !known {
				t.Fatal(err)
			}
			want := []string{"deleted.go", "new.go", "new/a file.go", oldPath}
			if !reflect.DeepEqual(paths, want) {
				t.Fatalf("%q != %q", paths, want)
			}
		})
	}
}

func TestExtendRejectsDriftEvenWhenPathAlreadyConsumed(t *testing.T) {
	root := fixture(t)
	put(t, root, "rules.md", "first")
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	s, err = r.Extend(context.Background(), s, []string{"rules.md"})
	if err != nil {
		t.Fatal(err)
	}
	put(t, root, "rules.md", "second")
	if _, err := r.Extend(context.Background(), s, []string{"rules.md"}); err == nil {
		t.Fatal("已消费输入被静默覆盖")
	}
}

func TestAutomaticDiscoveryFromNestedCustomDelivery(t *testing.T) {
	root := t.TempDir()
	put(t, root, "tooling/delivery/meta/project-binding.json", `{"version":3,"ai_delivery_path":"tooling/delivery"}`)
	start := filepath.Join(root, "tooling/delivery/requirements/R")
	os.MkdirAll(start, 0755)
	original, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(start); err != nil {
		t.Fatal(err)
	}
	defer os.Chdir(original)
	w, err := (workspace.Reader{}).Resolve(context.Background(), "", "")
	if err != nil {
		t.Fatal(err)
	}
	expectedRoot, err := os.Stat(root)
	if err != nil {
		t.Fatal(err)
	}
	actualRoot, err := os.Stat(w.ProjectRoot)
	if err != nil {
		t.Fatal(err)
	}
	if !os.SameFile(actualRoot, expectedRoot) {
		t.Fatalf("项目根不是同一目录: %q != %q", w.ProjectRoot, root)
	}
}

func TestAncestorSymlinkIdentityCannotChangeUnobserved(t *testing.T) {
	root := fixture(t)
	put(t, root, "real/file.md", "same")
	put(t, root, "other/file.md", "same")
	os.Symlink("real", filepath.Join(root, "alias"))
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	s, err = r.Extend(context.Background(), s, []string{"alias/file.md"})
	if err != nil {
		t.Fatal(err)
	}
	os.Remove(filepath.Join(root, "alias"))
	os.Symlink("other", filepath.Join(root, "alias"))
	if err := r.Verify(context.Background(), s); err == nil {
		t.Fatal("父链接改变未发现")
	}
}

func TestDanglingLinkRecordsLinkAndAbsentTarget(t *testing.T) {
	root := fixture(t)
	os.Symlink("missing.md", filepath.Join(root, "source.md"))
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	s, err = r.Extend(context.Background(), s, []string{"source.md"})
	if err != nil {
		t.Fatal(err)
	}
	seen := map[string]string{}
	for _, f := range s.Files() {
		seen[f.Path] = f.Kind
	}
	if seen["source.md"] != "symlink" || seen["missing.md"] != "absent" {
		t.Fatalf("链接与目标身份必须分别保留: %v", seen)
	}
}

func TestVerifyRejectsChangedGitSelectionFacts(t *testing.T) {
	root := fixture(t)
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("环境没有Git")
	}
	if out, err := exec.Command(git, "-C", root, "init", "-q").CombinedOutput(); err != nil {
		t.Fatalf("%s %v", out, err)
	}
	r := workspace.Reader{}
	w, err := r.Resolve(context.Background(), root, "")
	if err != nil {
		t.Fatal(err)
	}
	s, err := r.Load(context.Background(), w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Context: &model.ContextRequest{Role: "analysis"}})
	if err != nil {
		t.Fatal(err)
	}
	put(t, root, "new-module/new.go", "new")
	if err := r.Verify(context.Background(), s); err == nil {
		t.Fatal("实际Git范围改变未发现")
	}
}
