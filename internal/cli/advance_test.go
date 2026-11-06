package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestAdvancePublishesOnlySelectedStatusAndRejectsReplay(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	files := map[string]string{
		".ai-delivery/meta/project-binding.json":                                   `{"version":3}`,
		".ai-delivery/meta/workflow-policy.json":                                   `{"version":4,"verification_contract_version":2}`,
		".ai-delivery/requirements/R/requirement.md":                               "原始需求",
		".ai-delivery/requirements/R/sub-requirements/SR-001/requirement-slice.md": "当前切片",
		".ai-delivery/requirements/R/status.json":                                  `{"_schema":"2.0","custom":{"large":9007199254740993},"sub_requirements":{"SR-001":{"status":"draft","ui_truth_mode":"none","ui_bearing":false,"state_flow_required":false,"user_decision_required":false,"design_review":{},"note":"用户草稿"}}}`,
	}
	for p, b := range files {
		p = filepath.Join(root, p)
		if e := os.MkdirAll(filepath.Dir(p), 0755); e != nil {
			t.Fatal(e)
		}
		if e := os.WriteFile(p, []byte(b), 0600); e != nil {
			t.Fatal(e)
		}
	}
	invoke := func(args ...string) (int, map[string]any) {
		t.Helper()
		var out, stderr bytes.Buffer
		code := New(&out, &stderr).Run(append(args, "--project", root, "--req", "R", "--subreq", "SR-001"))
		var d map[string]any
		if e := json.Unmarshal(out.Bytes(), &d); e != nil {
			t.Fatalf("code=%d output=%s stderr=%s: %v", code, &out, &stderr, e)
		}
		return code, d
	}
	code, checked := invoke("check", "--intent", "analyze", "--to", "split_ready")
	if code != 0 {
		t.Fatal(code, checked)
	}
	statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	code, result := invoke("advance", "--to", "split_ready", "--expected-snapshot", checked["snapshot_id"].(string))
	if code != 0 || result["allowed"] != true {
		t.Fatal(code, result)
	}
	body, e := os.ReadFile(statusPath)
	if e != nil {
		t.Fatal(e)
	}
	if !bytes.Contains(body, []byte(`9007199254740993`)) || !bytes.Contains(body, []byte(`用户草稿`)) || !bytes.Contains(body, []byte(`"split_ready"`)) {
		t.Fatal(string(body))
	}
	info, _ := os.Stat(statusPath)
	if info.Mode().Perm() != 0600 {
		t.Fatal(info.Mode())
	}
	code, result = invoke("advance", "--to", "split_ready", "--expected-snapshot", checked["snapshot_id"].(string))
	if code != 2 || result["allowed"] != false {
		t.Fatal("重放应拒绝", code, result)
	}
	after, _ := os.ReadFile(statusPath)
	if !bytes.Equal(body, after) {
		t.Fatal("重放修改状态")
	}
}
