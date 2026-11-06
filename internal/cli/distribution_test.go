package cli

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func installCLIProject(t *testing.T, root string) {
	t.Helper()
	if err := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root, AllowManagedUpdate: true}); err != nil {
		t.Fatal(err)
	}
}
func TestReviewDigestReturnsDeclaredInputsAndRejectsMalformedContent(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	file := "verification.json"
	inputs := []any{map[string]any{"path": "owner.txt", "sha256": strings.Repeat("a", 64)}}
	good := map[string]any{"version": 2, "subreq_id": "SR-001", "inputs": inputs, "checks": []any{}}
	b, _ := json.Marshal(good)
	for _, tc := range []struct {
		body string
		want int
	}{{string(b), 0}, {`{"version":2,"inputs":"wrong","checks":[]}`, 2}, {`{"version":2,"inputs":[],"inputs":[]}`, 2}, {`{"version":"2","inputs":[],"checks":[]}`, 2}} {
		os.WriteFile(filepath.Join(root, file), []byte(tc.body), 0644)
		var out, stderr bytes.Buffer
		code := New(&out, &stderr).Run([]string{"evidence", "review-digest", "--project", root, "--file", file})
		if code != tc.want {
			t.Fatalf("%d: %s", code, out.String())
		}
		if code == 0 {
			var result map[string]any
			json.Unmarshal(out.Bytes(), &result)
			want, _ := protocol.InputDigest(inputs)
			if result["input_sha256"] != want || result["verification_sha256"] == nil {
				t.Fatalf("缺少纯合同双摘要: %s", out.String())
			}
		}
	}
}
func TestValidationAndHookUseOneProgram(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	for _, kind := range []string{"skills", "sources", "api-policy", "layout"} {
		var out, err bytes.Buffer
		if code := New(&out, &err).Run([]string{"validate", "--project", root, "--kind", kind}); code != 0 {
			t.Fatalf("%s %d %s %s", kind, code, &out, &err)
		}
	}
	var out, err bytes.Buffer
	if code := New(&out, &err).Run([]string{"hook", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "implement", "--to", "in_dev"}); code != 2 {
		t.Fatalf("hook 应复用真实缺材料门禁: %d %s %s", code, &out, &err)
	}
	if !json.Valid(out.Bytes()) {
		t.Fatalf("hook 不是单 JSON: %s", out.String())
	}
}

func TestStatusValidationDoesNotInventAnAnalyzeTransition(t *testing.T) {
	root, _ := cliRunProject(t, "native-pass")
	var out, stderr bytes.Buffer
	if code := New(&out, &stderr).Run([]string{"validate", "--kind", "status", "--project", root, "--req", "R", "--subreq", "SR-001"}); code != 0 {
		t.Fatalf("有效 in_dev status 的格式校验被动作边拒绝: %d %s", code, &out)
	}
}

func TestOrdinaryFormatDiagnosticsKeepFileAndBothRecoveryChoices(t *testing.T) {
	root := t.TempDir()
	installCLIProject(t, root)
	policy := filepath.Join(root, ".ai-delivery/meta/workflow-policy.json")
	if err := os.WriteFile(policy, []byte(`{"version":"4","verification_contract_version":2}`), 0644); err != nil {
		t.Fatal(err)
	}
	var out, stderr bytes.Buffer
	code := New(&out, &stderr).Run([]string{"context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "analysis"})
	if code != 2 {
		t.Fatalf("%d %s", code, &out)
	}
	var data map[string]any
	if err := json.Unmarshal(out.Bytes(), &data); err != nil {
		t.Fatal(err)
	}
	found := false
	for _, v := range data["diagnostics"].([]any) {
		d := v.(map[string]any)
		if strings.Contains(fmt.Sprint(d["path"]), "meta/workflow-policy.json") && strings.Contains(fmt.Sprint(d["recovery"]), "A.") && strings.Contains(fmt.Sprint(d["recovery"]), "B.") {
			found = true
		}
	}
	if !found {
		t.Fatalf("实际文件/两种选择丢失: %s", &out)
	}
}

func TestValidateScopedLayoutDelegatesToCurrentAction(t *testing.T) {
	root, _ := cliRunProject(t, "native-pass")
	base := []string{"validate", "--kind", "layout", "--project", root}
	for _, extra := range [][]string{{"--req", "R", "--subreq", "SR-001"}, {"--to", "in_dev"}, {"--intent", "implement"}, {"--req", "R", "--subreq", "SR-001", "--intent", "implement", "--to", "in_dev"}} {
		var out, stderr bytes.Buffer
		code := New(&out, &stderr).Run(append(append([]string{}, base...), extra...))
		want := 2
		if len(extra) == 8 {
			want = 0
		}
		if code != want {
			t.Fatalf("%v code=%d want=%d %s", extra, code, want, &out)
		}
		if want == 0 {
			var result map[string]any
			json.Unmarshal(out.Bytes(), &result)
			if result["allowed"] != true || result["intent"] != "implement" {
				t.Fatalf("未委托真实检查: %s", &out)
			}
		}
	}
}
