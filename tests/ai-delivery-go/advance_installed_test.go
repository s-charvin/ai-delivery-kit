package aideliverygo_test

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestInstalledAdvanceWithoutSDKPreservesDraftAndRecovers(t *testing.T) {
	_, file, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "../.."))
	bin := filepath.Join(t.TempDir(), "ai-delivery")
	if runtime.GOOS == "windows" {
		bin += ".exe"
	}
	build := exec.Command("go", "build", "-o", bin, "./cmd/ai-delivery")
	build.Dir = repo
	if b, e := build.CombinedOutput(); e != nil {
		t.Fatal(string(b), e)
	}
	root := t.TempDir()
	files := map[string]string{
		".ai-delivery/meta/project-binding.json":                                   `{"version":3}`,
		".ai-delivery/meta/workflow-policy.json":                                   `{"version":4,"verification_contract_version":2}`,
		".ai-delivery/requirements/R/requirement.md":                               "原需求",
		".ai-delivery/requirements/R/sub-requirements/SR-001/requirement-slice.md": "切片原需求",
		".ai-delivery/requirements/R/status.json":                                  `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"draft","ui_truth_mode":"none","ui_bearing":false,"state_flow_required":false,"user_decision_required":false,"design_review":{}}}}`,
		"notes/preserve.txt":                                                       "用户原稿\r\n不可修改\x00",
	}
	for p, b := range files {
		p = filepath.Join(root, p)
		os.MkdirAll(filepath.Dir(p), 0755)
		if e := os.WriteFile(p, []byte(b), 0600); e != nil {
			t.Fatal(e)
		}
	}
	env := []string{}
	for _, v := range os.Environ() {
		if !strings.HasPrefix(v, "PATH=") && !strings.HasPrefix(v, "GIT_DIR=") && !strings.HasPrefix(v, "GIT_WORK_TREE=") {
			env = append(env, v)
		}
	}
	env = append(env, "PATH="+t.TempDir())
	init := exec.Command(bin, "init", "--upgrade", root)
	init.Env = env
	if out, err := init.CombinedOutput(); err != nil {
		t.Fatalf("实际 CLI 资源安装: %v %s", err, out)
	}
	invoke := func(want int, args ...string) map[string]any {
		t.Helper()
		cmd := exec.Command(bin, append(args, "--project", root, "--req", "R", "--subreq", "SR-001")...)
		cmd.Env = env
		b, e := cmd.CombinedOutput()
		code := 0
		if e != nil {
			if ee, ok := e.(*exec.ExitError); ok {
				code = ee.ExitCode()
			} else {
				t.Fatal(e)
			}
		}
		if code != want {
			t.Fatal(code, string(b))
		}
		var d map[string]any
		if e = json.Unmarshal(b, &d); e != nil {
			t.Fatal(e, string(b))
		}
		return d
	}
	check := invoke(0, "check", "--intent", "analyze", "--to", "split_ready")
	req := filepath.Join(root, ".ai-delivery/requirements/R/requirement.md")
	os.WriteFile(req, []byte("真实需求修订"), 0600)
	status := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	before, _ := os.ReadFile(status)
	invoke(2, "advance", "--to", "split_ready", "--expected-snapshot", check["snapshot_id"].(string))
	after, _ := os.ReadFile(status)
	if string(before) != string(after) {
		t.Fatal("失败改状态")
	}
	check = invoke(0, "check", "--intent", "analyze", "--to", "split_ready")
	result := invoke(0, "advance", "--to", "split_ready", "--expected-snapshot", check["snapshot_id"].(string))
	if result["allowed"] != true {
		t.Fatal(result)
	}
	invoke(2, "advance", "--to", "split_ready", "--expected-snapshot", check["snapshot_id"].(string))
	b, _ := os.ReadFile(filepath.Join(root, "notes/preserve.txt"))
	if string(b) != files["notes/preserve.txt"] {
		t.Fatal("覆盖用户草稿")
	}
}
