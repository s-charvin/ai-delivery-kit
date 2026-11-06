package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestCheckCLISeparatesDecisionFromContext(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	files := map[string]string{".ai-delivery/meta/project-binding.json": `{"version":3}`, ".ai-delivery/meta/workflow-policy.json": `{"version":4,"verification_contract_version":2}`, ".ai-delivery/requirements/R/status.json": `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"in_dev"}}}`, ".ai-delivery/requirements/R/requirement.md": "需求", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md": "设计"}
	for p, b := range files {
		p = filepath.Join(root, p)
		os.MkdirAll(filepath.Dir(p), 0755)
		if err := os.WriteFile(p, []byte(b), 0644); err != nil {
			t.Fatal(err)
		}
	}
	for _, args := range [][]string{{"check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "merge", "--to", "merged"}, {"check", "--intent", "unknown"}, {"check", "--bad"}, {"check", "--project", root, "--req", "../R", "--subreq", "SR-001", "--intent", "merge"}} {
		var out, stderr bytes.Buffer
		code := New(&out, &stderr).Run(args)
		if code != 2 {
			t.Fatalf("%d %s %s", code, &out, &stderr)
		}
		var d map[string]any
		if err := json.Unmarshal(out.Bytes(), &d); err != nil {
			t.Fatal(err, &out)
		}
		if d["allowed"] != false {
			t.Fatal(d)
		}
		if _, ok := d["context_complete"]; ok {
			t.Fatal("check不能冒充context报告")
		}
		if len(d["diagnostics"].([]any)) == 0 {
			t.Fatal(d)
		}
	}
	var out, stderr bytes.Buffer
	if code := New(&out, &stderr).Run([]string{"check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "archive", "--to", "archived"}); code != 2 {
		t.Fatalf("未满足归档门禁应退出2: %d %s", code, &out)
	}
}
