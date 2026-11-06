package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func reviewCommand(t *testing.T, root string, args ...string) map[string]any {
	t.Helper()
	var out, stderr bytes.Buffer
	code := New(&out, &stderr).Run(append(args, "--project", root, "--req", "R", "--subreq", "SR-001"))
	if code != 2 {
		t.Fatalf("应拒绝动作/材料: code=%d %s %s", code, &out, &stderr)
	}
	var result map[string]any
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	return result
}
func TestMissingUIContractNeverSuggestsMigrationOrInventsFields(t *testing.T) {
	root, _ := cliRunProject(t, "native-pass")
	p := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
	body, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	var status map[string]any
	json.Unmarshal(body, &status)
	entry := status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
	entry["status"] = "split_ready"
	entry["ui_truth_mode"] = "figma"
	entry["ui_bearing"] = true
	body, _ = json.Marshal(status)
	if err = os.WriteFile(p, body, 0644); err != nil {
		t.Fatal(err)
	}
	result := reviewCommand(t, root, "check", "--intent", "ui", "--to", "acceptance_frozen")
	missing := false
	for _, raw := range result["diagnostics"].([]any) {
		d := raw.(map[string]any)
		recovery, _ := d["recovery"].(string)
		message, _ := d["message"].(string)
		if strings.Contains(recovery, "reset-data") || strings.Contains(recovery, "逐字段迁移") {
			t.Fatalf("缺合同被建议迁移/重建: %+v", d)
		}
		if strings.Contains(message, "captured_at") || strings.Contains(message, "schema_version") {
			t.Fatalf("为不存在的合同虚构字段诊断: %+v", d)
		}
		missing = missing || d["code"] == "missing_ui_index"
	}
	if !missing {
		t.Fatalf("缺少局部missing原因: %+v", result["diagnostics"])
	}
	indexPath := filepath.Join(filepath.Dir(p), "sub-requirements/SR-001/contracts/ui-truth-index.json")
	if err := os.MkdirAll(filepath.Dir(indexPath), 0755); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct{ name, body, field string }{
		{"invalid-json", `{`, "ui-truth-index.json"},
		{"old-version", `{"schema_version":2,"design_source":{"captured_at":"2026-11-05T12:00:00+08:00"}}`, "#/schema_version"},
		{"naive-time", `{"schema_version":3,"design_source":{"captured_at":"2026-11-05T12:00:00"}}`, "#/design_source.captured_at"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if err := os.WriteFile(indexPath, []byte(tc.body), 0644); err != nil {
				t.Fatal(err)
			}
			result := reviewCommand(t, root, "check", "--intent", "ui", "--to", "acceptance_frozen")
			found := false
			for _, raw := range result["diagnostics"].([]any) {
				d := raw.(map[string]any)
				p, _ := d["path"].(string)
				r, _ := d["recovery"].(string)
				if strings.HasSuffix(p, tc.field) && strings.Contains(r, "A.") && strings.Contains(r, "B.") {
					found = true
				}
			}
			if !found {
				t.Fatalf("已有合同真实格式错误丢失 A/B 恢复: %+v", result["diagnostics"])
			}
			got, err := os.ReadFile(indexPath)
			if err != nil || string(got) != tc.body {
				t.Fatalf("检查重写了原文件: %s %v", got, err)
			}
		})
	}
}
func TestStatusObjectTypeErrorHasSharedFieldRecoveryButMissingSliceDoesNot(t *testing.T) {
	for _, tc := range []struct {
		name, entries string
		format        bool
	}{{"wrong-string", `"wrong"`, true}, {"wrong-array", `[]`, true}, {"missing-slice", `{}`, false}} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			installCLIProject(t, root)
			p := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(p, []byte(`{"_schema":"2.0","sub_requirements":`+tc.entries+`}`), 0644); err != nil {
				t.Fatal(err)
			}
			for _, args := range [][]string{{"context", "--role", "analysis"}, {"check", "--intent", "analyze"}} {
				result := reviewCommand(t, root, args...)
				found := false
				for _, raw := range result["diagnostics"].([]any) {
					d := raw.(map[string]any)
					recovery, _ := d["recovery"].(string)
					message, _ := d["message"].(string)
					path, _ := d["path"].(string)
					if !tc.format && (strings.Contains(recovery, "reset-data") || strings.Contains(recovery, "逐字段迁移")) {
						t.Fatalf("缺切片被分类格式迁移: %+v", d)
					}
					if tc.format && strings.HasSuffix(path, "status.json#/sub_requirements") && strings.Contains(message, "实际类型=") && strings.Contains(message, "实际值=") && strings.Contains(message, "JSON 对象") && strings.Contains(recovery, "A.") && strings.Contains(recovery, "B.") {
						found = true
					}
				}
				if tc.format && !found {
					t.Fatalf("%s 缺少共享字段格式诊断: %+v", args[0], result["diagnostics"])
				}
			}
		})
	}
}
