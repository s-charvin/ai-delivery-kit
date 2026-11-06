package cli

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestCLINativeHelper(t *testing.T) {
	if os.Args[len(os.Args)-1] == "native-pass" {
		fmt.Println("原生stdout🙂")
		fmt.Fprintln(os.Stderr, "原生stderr")
	}
	if os.Args[len(os.Args)-1] == "native-fail" {
		os.Exit(7)
	}
}
func cliRunProject(t *testing.T, mode string) (string, []string) {
	t.Helper()
	root := t.TempDir()
	installCLIProject(t, root)
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	argv := []string{exe, "-test.run=^TestCLINativeHelper$", "--", mode}
	if mode == "missing" {
		argv = []string{filepath.Join(root, "missing-binary")}
	}
	m, _ := json.Marshal(map[string]any{"version": 1, "checks": []any{map[string]any{"id": "native-save", "argv": argv, "cwd": ".", "parser_id": "exit-code", "acceptance_ids": []string{"AC-001"}, "input_paths": []string{"owner.txt"}, "report_paths": []string{}, "source_refs": []string{"owner.txt"}}}})
	design := "<!-- ai-delivery:behavior-contract:start -->\n<!-- ai-delivery:behavior-contract:scope -->\n保存\n<!-- ai-delivery:behavior-contract:behavior -->\nB-001 保存\n<!-- ai-delivery:behavior-contract:acceptance -->\nAC-001 保存成功\n<!-- ai-delivery:native-methods:v1 -->\n```json\n" + string(m) + "\n```\n<!-- /ai-delivery:native-methods:v1 -->\n<!-- ai-delivery:behavior-contract:traceability -->\nB-001 AC-001\n<!-- ai-delivery:behavior-contract:end -->\n<!-- ai-delivery:user-decisions -->\n无人工决定\n"
	status, _ := json.Marshal(map[string]any{"_schema": "2.0", "sub_requirements": map[string]any{"SR-001": map[string]any{"status": "in_dev", "ui_truth_mode": "none", "ui_bearing": false, "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_by": "实际设计评审夹具", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(design)))}}}})
	for p, b := range map[string]string{".ai-delivery/meta/project-binding.json": `{"version":3}`, ".ai-delivery/meta/workflow-policy.json": `{"version":4,"verification_contract_version":2}`, ".ai-delivery/requirements/R/status.json": string(status), ".ai-delivery/requirements/R/requirement.md": "需求", ".ai-delivery/requirements/R/sub-requirements/SR-001/requirement-slice.md": "切片需求", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md": design, "owner.txt": "实际宿主输入"} {
		p = filepath.Join(root, p)
		os.MkdirAll(filepath.Dir(p), 0755)
		if e = os.WriteFile(p, []byte(b), 0644); e != nil {
			t.Fatal(e)
		}
	}
	return root, argv
}
func TestRunCLIUsesSingleJSONAndStableExitCodes(t *testing.T) {
	for _, tc := range []struct {
		mode string
		want int
	}{{"native-pass", 0}, {"native-fail", 2}, {"missing", 3}} {
		t.Run(tc.mode, func(t *testing.T) {
			root, argv := cliRunProject(t, tc.mode)
			args := append([]string{"run", "--project", root, "--req", "R", "--subreq", "SR-001", "--check", "native-save", "--timeout", "10", "--"}, argv...)
			var out, stderr bytes.Buffer
			code := New(&out, &stderr).Run(args)
			if code != tc.want {
				t.Fatal(code, out.String(), stderr.String())
			}
			var d map[string]any
			if e := json.Unmarshal(out.Bytes(), &d); e != nil {
				t.Fatal("stdout不是单一JSON", out.String(), e)
			}
			if _, ok := d["receipt_path"].(string); !ok {
				t.Fatal(d)
			}
			if stderr.Len() != 0 {
				t.Fatal("原生日志混入CLI stderr", stderr.String())
			}
			r := d["receipt"].(map[string]any)
			if tc.mode == "native-pass" {
				inputs, ok := d["inputs"].([]any)
				if !ok || len(inputs) == 0 {
					t.Fatal("未提供实际执行inputs投影", d)
				}
				for _, v := range inputs {
					if v.(map[string]any)["path"] == ".ai-delivery/requirements/R/status.json" {
						t.Fatal("默认前置不应进入v2执行inputs")
					}
				}
			}
			if tc.mode == "native-fail" && r["exit_code"] != float64(7) {
				t.Fatal(r)
			}
		})
	}
	for _, args := range [][]string{{"run"}, {"run", "--bad"}, {"run", "--req", "../escape", "--subreq", "SR-001", "--check", "native-save", "--", "go", "test"}} {
		var out, stderr bytes.Buffer
		if code := New(&out, &stderr).Run(args); code != 2 || !json.Valid(out.Bytes()) {
			t.Fatal(code, out.String(), stderr.String())
		}
	}
}
func TestEvidenceCLISharesCanonicalDigests(t *testing.T) {
	root, _ := cliRunProject(t, "native-pass")
	var out, stderr bytes.Buffer
	code := New(&out, &stderr).Run([]string{"evidence", "fingerprint", "--project", root, "--input", "owner.txt", "--input", "absent.txt"})
	if code != 0 {
		t.Fatal(code, out.String(), stderr.String())
	}
	var d map[string]any
	if e := json.Unmarshal(out.Bytes(), &d); e != nil {
		t.Fatal(e)
	}
	files := d["inputs"].([]any)
	if len(files) != 2 || files[1].(map[string]any)["state"] != "absent" {
		t.Fatal(d)
	}
	os.WriteFile(filepath.Join(root, "verification.json"), []byte(`{"version":2,"checks":[],"inputs":[],"reviews":[]}`), 0644)
	out.Reset()
	stderr.Reset()
	code = New(&out, &stderr).Run([]string{"evidence", "review-digest", "--project", root, "--file", "verification.json"})
	if code != 0 || !json.Valid(out.Bytes()) {
		t.Fatal(code, out.String(), stderr.String())
	}
}
