package runner_test

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func TestGoFullPackageRunDistinguishesNoTestsFromSkippedTests(t *testing.T) {
	goexe, err := exec.LookPath("go")
	if err != nil {
		t.Fatal(err)
	}
	for _, mode := range []string{"pass", "skip-same-package", "skip-other-package"} {
		t.Run(mode, func(t *testing.T) {
			s, spec, req := setup(t, nil, "go-test-json", nil)
			root := s.Workspace().ProjectRoot
			files := map[string]string{
				"go.mod":             "module host\n\ngo 1.22.0\n",
				"api/save.go":        "package api\nfunc Save(value string) string { return value }\n",
				"api/save_test.go":   "package api\nimport \"testing\"\nfunc TestSave(t *testing.T) { if Save(\"value\") != \"value\" { t.Fatal(\"save\") } }\n",
				"cmd/server/main.go": "package main\nimport \"host/api\"\nfunc main() { _ = api.Save(\"value\") }\n",
			}
			if mode == "skip-same-package" {
				files["api/save_test.go"] += "func TestSkipped(t *testing.T) { t.Skip(\"真实跳过\") }\n"
			}
			if mode == "skip-other-package" {
				files["other/skip_test.go"] = "package other\nimport \"testing\"\nfunc TestSkipped(t *testing.T) { t.Skip(\"真实跳过\") }\n"
			}
			for name, source := range files {
				path := filepath.Join(root, filepath.FromSlash(name))
				if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(path, []byte(source), 0644); err != nil {
					t.Fatal(err)
				}
				spec.InputPaths = append(spec.InputPaths, name)
			}
			s, err = (workspace.Reader{}).Extend(context.Background(), s, spec.InputPaths)
			if err != nil {
				t.Fatal(err)
			}
			argv := []string{goexe, "test", "-json", "-count=1", "./..."}
			spec.Method.Argv, req.Argv = argv, argv
			req.TimeoutSeconds = 30
			r, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
			if err != nil {
				t.Fatal(err)
			}
			d := receipt(t, r)
			stdout, err := os.ReadFile(filepath.Join(root, d["stdout"].(map[string]any)["path"].(string)))
			if err != nil {
				t.Fatal(err)
			}
			t.Logf("真实 go test -json -count=1 ./... 输出：\n%s", stdout)
			noTestPackage := false
			for _, line := range strings.Split(strings.TrimSpace(string(stdout)), "\n") {
				var event map[string]any
				if err := json.Unmarshal([]byte(line), &event); err != nil {
					t.Fatal(err)
				}
				if event["Action"] == "skip" && event["Package"] == "host/cmd/server" {
					_, hasTest := event["Test"]
					noTestPackage = !hasTest
				}
			}
			if !noTestPackage || d["exit_code"] != float64(0) || d["inputs_stable"] != true {
				t.Fatal("未复现无测试包真实终结或运行条件异常", string(r.Observation.Details))
			}
			if (r.Observation.Result == "passed") != (mode == "pass") {
				t.Fatal(mode, string(r.Observation.Details))
			}
			if mode == "pass" {
				if !reflect.DeepEqual(d["tests_run"], []any{"host/api/TestSave"}) {
					t.Fatal("无测试包混入实际测试集合", d["tests_run"])
				}
				mapped, err := checks.ReceiptToCheck(r)
				if err != nil {
					t.Fatal(err)
				}
				var check map[string]any
				if err := json.Unmarshal(mapped, &check); err != nil {
					t.Fatal(err)
				}
				if check["result"] != "passed" || check["mode"] != "executed" || !reflect.DeepEqual(check["acceptance_ids"], []any{"AC-001"}) {
					t.Fatal("收据映射丢失或扩大实际验收范围", check)
				}
			}
		})
	}
}
