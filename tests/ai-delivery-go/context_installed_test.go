package aideliverygo_test

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
)

func TestInstalledContextWithoutRuntimeToolchains(t *testing.T) {
	_, file, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "../.."))
	root := filepath.Join(t.TempDir(), "项目 '$` 特殊路径")
	if err := os.MkdirAll(root, 0755); err != nil {
		t.Fatal(err)
	}
	binary := filepath.Join(t.TempDir(), "ai-delivery")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	cmd := exec.Command("go", "build", "-o", binary, "./cmd/ai-delivery")
	cmd.Dir = repo
	cmd.Env = append(os.Environ(), "CGO_ENABLED=0")
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("build: %s %v", out, err)
	}
	if err := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root, ProjectID: "fixture"}); err != nil {
		t.Fatal(err)
	}
	files := map[string]string{".ai-delivery/requirements/R/status.json": `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"merged"}}}`, ".ai-delivery/requirements/R/requirement.md": "安装后的原始需求正文", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md": "安装后的 canonical design 正文"}
	for p, b := range files {
		p = filepath.Join(root, p)
		os.MkdirAll(filepath.Dir(p), 0755)
		if err := os.WriteFile(p, []byte(b), 0644); err != nil {
			t.Fatal(err)
		}
	}
	cmd = exec.Command(binary, "context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--budget-chars", "200000", "--format", "json")
	env := []string{}
	for _, e := range os.Environ() {
		if !strings.HasPrefix(e, "PATH=") && !strings.HasPrefix(e, "GIT_DIR=") && !strings.HasPrefix(e, "GIT_WORK_TREE=") {
			env = append(env, e)
		}
	}
	cmd.Env = append(env, "PATH="+t.TempDir())
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("安装后Go程序: %s %v", out, err)
	}
	var result map[string]any
	if err := json.Unmarshal(out, &result); err != nil {
		t.Fatal(err)
	}
	if result["context_complete"] != true {
		t.Fatalf("%s", out)
	}
	if _, err := os.Stat(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md")); !os.IsNotExist(err) {
		t.Fatal("夹具应缺失verification")
	}
	cmd = exec.Command(binary, "check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "merge", "--to", "merged", "--format", "json")
	cmd.Env = append(env, "PATH="+t.TempDir())
	out, err = cmd.CombinedOutput()
	if exit, ok := err.(*exec.ExitError); !ok || exit.ExitCode() != 2 {
		t.Fatalf("安装后check应明确拒绝: %s %v", out, err)
	}
	result = nil
	if err := json.Unmarshal(out, &result); err != nil {
		t.Fatalf("check输出不是单JSON: %s", out)
	}
	if result["allowed"] != false || result["snapshot_id"] == nil {
		t.Fatal(result)
	}
	if _, ok := result["context_complete"]; ok {
		t.Fatal("check与context混淆")
	}
}
