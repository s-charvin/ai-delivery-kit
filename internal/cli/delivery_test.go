package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestContextProducesOneJSONWithoutVerification(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	files := map[string]string{".ai-delivery/meta/project-binding.json": `{"version":3}`, ".ai-delivery/meta/workflow-policy.json": `{"version":4,"verification_contract_version":2}`, ".ai-delivery/requirements/R/status.json": `{"_schema":"2.0","sub_requirements":{"SR-001":{"status":"merged"}}}`, ".ai-delivery/requirements/R/requirement.md": "需求正文", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md": "设计正文"}
	for p, b := range files {
		p = filepath.Join(root, p)
		os.MkdirAll(filepath.Dir(p), 0755)
		if err := os.WriteFile(p, []byte(b), 0644); err != nil {
			t.Fatal(err)
		}
	}
	var stdout, stderr bytes.Buffer
	app := New(&stdout, &stderr)
	code := app.Run([]string{"context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--format", "json", "--budget-chars", "200000"})
	if code != 0 {
		t.Fatalf("code=%d %s %s", code, &stdout, &stderr)
	}
	var got map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got["context_complete"] != true || got["snapshot_id"] == nil {
		t.Fatal(got)
	}
	if _, ok := got["allowed"]; ok {
		t.Fatal("材料报告不能授予动作权限")
	}
	policy := `{"version":4,"verification_contract_version":2,"context":{"sources":[{"path":"missing.md","paths":["src/*"]}]}}`
	if err := os.WriteFile(filepath.Join(root, ".ai-delivery/meta/workflow-policy.json"), []byte(policy), 0644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	stderr.Reset()
	code = app.Run([]string{"context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--path", "./src//a.go", "--budget-chars", "200000"})
	if code != 2 {
		t.Fatalf("CLI路径别名绕过规范: %d %s", code, &stdout)
	}
	if err := json.Unmarshal(stdout.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got["context_complete"] != false || got["declared_paths"].([]any)[0] != "src/a.go" {
		t.Fatal(got)
	}
}
func TestContextArgumentErrorsAndMissingBindingAreJSON(t *testing.T) {
	for _, args := range [][]string{{"context", "--bad"}, {"context", "--project", t.TempDir(), "--req", "R", "--subreq", "SR-001", "--role", "implement"}, {"context", "--role", "wrong"}, {"context", "--role", "implement", "--budget-chars", "-1"}} {
		var out, stderr bytes.Buffer
		code := New(&out, &stderr).Run(args)
		if code != 2 {
			t.Fatalf("%q => %d %s", args, code, &out)
		}
		var result map[string]any
		if err := json.Unmarshal(out.Bytes(), &result); err != nil {
			t.Fatalf("输出不是单JSON: %s", &out)
		}
	}
}
func TestInfoReadsIdentifiedEmbeddedResource(t *testing.T) {
	var out, stderr bytes.Buffer
	code := New(&out, &stderr).Run([]string{"info", "--resource", "kit://ai-delivery-orchestrator/references/stage-implementation.md"})
	if code != 0 {
		t.Fatalf("%d %s %s", code, &out, &stderr)
	}
	var result map[string]any
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["body"] == "" || len(result["sha256"].(string)) != 64 {
		t.Fatal(result)
	}
}
