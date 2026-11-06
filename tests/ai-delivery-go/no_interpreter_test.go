package aideliverygo_test

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestNoInterpreterRealCLIInitAndResourceIdentity(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(source), "../.."))
	external := t.TempDir()
	binary := filepath.Join(external, "ai-delivery")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	build := exec.Command("go", "build", "-o", binary, "./cmd/ai-delivery")
	build.Dir = repo
	build.Env = append(os.Environ(), "CGO_ENABLED=0")
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build %v %s", err, out)
	}
	root := filepath.Join(external, "项目 '$` 特殊路径")
	if err := os.Mkdir(root, 0755); err != nil {
		t.Fatal(err)
	}
	env := []string{}
	for _, v := range os.Environ() {
		if !strings.HasPrefix(v, "PATH=") && !strings.HasPrefix(v, "GIT_") {
			env = append(env, v)
		}
	}
	env = append(env, "PATH="+filepath.Join(external, "empty-path"))
	run := func(args ...string) ([]byte, error) {
		cmd := exec.Command(binary, args...)
		cmd.Dir = external
		cmd.Env = env
		return cmd.CombinedOutput()
	}
	// 实际程序在未初始化 cwd、无 SDK/解释器 PATH 下自助恢复，不能触碰项目。
	for _, prefix := range [][]string{{"check"}, {"advance"}, {"context"}, {"run"}, {"evidence"}, {"evidence", "fingerprint"}, {"evidence", "review-digest"}} {
		args := append(append([]string{}, prefix...), "--help")
		cmd := exec.Command(binary, args...)
		cmd.Dir, cmd.Env = root, env
		var stdout, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &stdout, &stderr
		if err := cmd.Run(); err != nil || stderr.Len() != 0 {
			t.Fatalf("未初始化帮助 %v: %v stdout=%s stderr=%s", args, err, &stdout, &stderr)
		}
		var help map[string]any
		dec := json.NewDecoder(&stdout)
		if err := dec.Decode(&help); err != nil {
			t.Fatal(err)
		}
		if err := dec.Decode(new(any)); err != io.EOF {
			t.Fatalf("不是单 JSON: %v", err)
		}
		for _, key := range []string{"allowed", "snapshot_id", "context_complete"} {
			if _, exists := help[key]; exists {
				t.Fatal("帮助伪装业务判断", key, help)
			}
		}
		entries, err := os.ReadDir(root)
		if err != nil || len(entries) != 0 {
			t.Fatal("帮助写入了未初始化项目", entries, err)
		}
	}
	if out, err := run("init", root); err != nil {
		t.Fatalf("真实无 Git/解释器 init: %v %s", err, out)
	}
	manifest := filepath.Join(root, ".ai-delivery/meta/kit-assets.json")
	b, err := os.ReadFile(manifest)
	if err != nil {
		t.Fatal(err)
	}
	var v map[string]any
	if err = json.Unmarshal(b, &v); err != nil {
		t.Fatal(err)
	}
	if v["asset_manifest_version"] != float64(1) || v["runtime_root"] != nil || v["dispatch_version"] != nil {
		t.Fatalf("资源合同错误: %s", b)
	}
	if out, err := run("info", "--project", root); err != nil {
		t.Fatalf("info: %v %s", err, out)
	}
	for _, body := range []string{`{"version":2,"inputs":"wrong","checks":[]}`, `{"version":2,"inputs":[],"inputs":[]}`, `{"version":"2","inputs":[],"checks":[]}`} {
		if err = os.WriteFile(filepath.Join(root, "bad-verification.json"), []byte(body), 0644); err != nil {
			t.Fatal(err)
		}
		out, e := run("evidence", "review-digest", "--project", root, "--file", "bad-verification.json")
		if exit, ok := e.(*exec.ExitError); !ok || exit.ExitCode() != 2 {
			t.Fatalf("真实 CLI 错误类型未拒绝: %v %s", e, out)
		}
		var response map[string]any
		if e = json.Unmarshal(out, &response); e != nil {
			t.Fatal(e)
		}
		ds := response["diagnostics"].([]any)
		if len(ds) == 0 || !strings.Contains(fmt.Sprint(ds[0].(map[string]any)["path"]), "bad-verification.json") {
			t.Fatalf("真实 CLI 丢失格式文件: %s", out)
		}
	}
	if err = os.Remove(manifest); err != nil {
		t.Fatal(err)
	}
	out, err := run("info", "--project", root)
	if exit, ok := err.(*exec.ExitError); !ok || exit.ExitCode() != 3 || !strings.Contains(string(out), "init --upgrade") || strings.Contains(string(out), "reset-data") {
		t.Fatalf("缺清单应仅提示刷新: %v %s", err, out)
	}
	if out, err := run("init", "--upgrade", root); err != nil {
		t.Fatalf("显式刷新: %v %s", err, out)
	}
}

// 所有评审/确认均为协议夹具，不代表本项目或任何产品的真实人工批准。
func TestNoInterpreterFullCLILifecycleAndIndependentProjects(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(source), "../.."))
	outside := t.TempDir()
	bin := filepath.Join(outside, "ai-delivery")
	helper := filepath.Join(outside, "native host")
	if runtime.GOOS == "windows" {
		bin += ".exe"
		helper += ".exe"
	}
	for _, v := range [][2]string{{bin, "./cmd/ai-delivery"}, {helper, "./internal/delivery/runner/testdata/native-helper"}} {
		cmd := exec.Command("go", "build", "-o", v[0], v[1])
		cmd.Dir = repo
		cmd.Env = append(os.Environ(), "CGO_ENABLED=0")
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("编译测试前置: %v %s", err, out)
		}
	}
	env := []string{}
	for _, v := range os.Environ() {
		if !strings.HasPrefix(v, "PATH=") && !strings.HasPrefix(v, "GIT_") {
			env = append(env, v)
		}
	}
	env = append(env, "PATH="+filepath.Join(outside, "empty-path"))
	serial := 0
	invoke := func(want int, args ...string) map[string]any {
		t.Helper()
		cmd := exec.Command(bin, args...)
		cmd.Dir = outside
		cmd.Env = env
		out, err := cmd.CombinedOutput()
		code := 0
		if err != nil {
			if exit, ok := err.(*exec.ExitError); ok {
				code = exit.ExitCode()
			} else {
				t.Fatal(err)
			}
		}
		serial++
		if evidence := os.Getenv("AI_DELIVERY_TEST_EVIDENCE_DIR"); evidence != "" {
			if e := os.MkdirAll(evidence, 0755); e != nil {
				t.Fatal(e)
			}
			raw, _ := json.MarshalIndent(map[string]any{"argv": args, "exit_code": code, "output": string(out)}, "", "  ")
			if e := os.WriteFile(filepath.Join(evidence, fmt.Sprintf("lifecycle-%02d.json", serial)), raw, 0644); e != nil {
				t.Fatal(e)
			}
		}
		t.Logf("CLI %02d %s exit=%d", serial, args[0], code)
		if code != want {
			t.Fatalf("%v: exit=%d want=%d %s", args, code, want, out)
		}
		var result map[string]any
		if len(out) > 0 && out[0] == '{' {
			if err = json.Unmarshal(out, &result); err != nil {
				t.Fatal(err, string(out))
			}
		}
		return result
	}
	root := filepath.Join(outside, "实际项目 '$` 空格")
	other := filepath.Join(outside, "second project")
	for _, p := range []string{root, other} {
		if err := os.Mkdir(p, 0755); err != nil {
			t.Fatal(err)
		}
		invoke(0, "init", p)
	}
	put := func(p string, b []byte) {
		t.Helper()
		p = filepath.Join(root, p)
		if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, b, 0644); err != nil {
			t.Fatal(err)
		}
	}
	agents, _ := os.ReadFile(filepath.Join(root, "AGENTS.md"))
	put("AGENTS.md", append(agents, []byte("\n用户非受管正文\n")...))
	put(".claude/settings.json", []byte(`{"hooks":{},"third_party":{"keep":"原配置"}}`))
	otherManifest, _ := os.ReadFile(filepath.Join(other, ".ai-delivery/meta/kit-assets.json"))
	invoke(0, "init", "--upgrade", root)
	otherAfter, _ := os.ReadFile(filepath.Join(other, ".ai-delivery/meta/kit-assets.json"))
	if !bytes.Equal(otherManifest, otherAfter) {
		t.Fatal("刷新影响另一个项目")
	}
	third, _ := os.ReadFile(filepath.Join(root, ".claude/settings.json"))
	if !bytes.Contains(third, []byte("third_party")) {
		t.Fatal("第三方IDE字段丢失")
	}
	argv := []string{helper, "echo", "literal $HOME `value` 中文"}
	methods, _ := json.Marshal(map[string]any{"version": 1, "checks": []any{map[string]any{"id": "native-save", "argv": argv, "cwd": ".", "parser_id": "exit-code", "acceptance_ids": []string{"AC-001"}, "input_paths": []string{"owner.txt"}, "report_paths": []string{}, "source_refs": []string{"owner.txt"}}}})
	design := []byte("<!-- ai-delivery:behavior-contract:start -->\n<!-- ai-delivery:behavior-contract:scope -->\n范围\n<!-- ai-delivery:behavior-contract:behavior -->\nB-001 原生运行\n<!-- ai-delivery:behavior-contract:acceptance -->\nAC-001 宿主退出成功\n<!-- ai-delivery:native-methods:v1 -->\n```json\n" + string(methods) + "\n```\n<!-- /ai-delivery:native-methods:v1 -->\n<!-- ai-delivery:behavior-contract:traceability -->\nB-001 AC-001\n<!-- ai-delivery:behavior-contract:end -->\n<!-- ai-delivery:user-decisions -->\n协议夹具没有真实产品决定\n")
	status := map[string]any{"_schema": "2.0", "requirement_id": "R", "sub_requirements": map[string]any{"SR-001": map[string]any{"status": "draft", "ui_truth_mode": "none", "ui_bearing": false, "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_by": "协议夹具", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256(design))}}}}
	raw, _ := json.Marshal(status)
	put(".ai-delivery/requirements/R/status.json", raw)
	sub := ".ai-delivery/requirements/R/sub-requirements/SR-001/"
	put(sub+"design.md", design)
	put(sub+"requirement-slice.md", []byte("协议夹具切片"))
	put(".ai-delivery/requirements/R/requirement.md", []byte("完整链路协议夹具"))
	put("owner.txt", []byte("编译宿主的输入"))
	invoke(0, "context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--budget-chars", "200000")
	action := func(intent, target string) map[string]any {
		return invoke(0, "check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", intent, "--to", target)
	}
	advance := func(intent, target string) {
		t.Helper()
		checked := action(intent, target)
		invoke(0, "advance", "--project", root, "--req", "R", "--subreq", "SR-001", "--to", target, "--expected-snapshot", checked["snapshot_id"].(string))
	}
	checked := action("analyze", "split_ready")
	resource := ".agents/skills/requirement-breakdown/SKILL.md"
	original, _ := os.ReadFile(filepath.Join(root, resource))
	put(resource, []byte("漂移的受管资源"))
	invoke(3, "advance", "--project", root, "--req", "R", "--subreq", "SR-001", "--to", "split_ready", "--expected-snapshot", checked["snapshot_id"].(string))
	now, _ := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/status.json"))
	if !bytes.Equal(now, raw) {
		t.Fatal("资源拒绝仍改状态")
	}
	put(resource, original)
	advance("analyze", "split_ready")
	advance("design", "design_ready")
	advance("implement", "in_dev")
	args := append([]string{"run", "--project", root, "--req", "R", "--subreq", "SR-001", "--check", "native-save", "--timeout", "10", "--"}, argv...)
	executed := invoke(0, args...)
	contract := map[string]any{"version": 2, "subreq_id": "SR-001", "inputs": executed["inputs"], "checks": []any{executed["check"]}, "reviews": []any{}}
	persist := func() {
		raw, _ := json.Marshal(contract)
		put(sub+"verification.md", []byte("<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->\n<!-- ai-delivery-verification:contract:v2 -->\n```json\n"+string(raw)+"\n```\n<!-- /ai-delivery-verification:contract:v2 -->\n"))
	}
	persist()
	digests := invoke(0, "evidence", "review-digest", "--project", root, "--file", sub+"verification.md")
	contract["reviews"] = []any{map[string]any{"reviewer": "协议独立评审夹具，非产品验收", "context": "fresh", "result": "clean", "input_sha256": digests["input_sha256"], "verification_sha256": digests["verification_sha256"], "findings": []any{}}}
	persist()
	advance("merge", "merged")
	put(".ai-delivery/requirements/R/retrospective.md", []byte("<!-- ai-delivery-retrospective:reviewed-at:"+time.Now().UTC().Format(time.RFC3339Nano)+" -->\n"))
	put("report-template.md", []byte("# <req-id>\n<archived_at>\n<subreq_count>\n<subreq_rows>\n"))
	checked = action("archive", "")
	invoke(0, "archive", "--project", root, "--req", "R", "--subreq", "SR-001", "--confirm-archive", "--expected-snapshot", checked["snapshot_id"].(string), "--delivery-report-template", "report-template.md")
	invoke(0, "init", "--upgrade", "--reset-data", root)
	if _, err := os.Stat(filepath.Join(root, "owner.txt")); err != nil {
		t.Fatal("reset触及宿主输入", err)
	}
	backups, err := os.ReadDir(filepath.Join(root, ".ai-delivery-backups"))
	if err != nil || len(backups) != 1 {
		t.Fatal("明确重建没有完整备份", err)
	}
	invoke(0, "info", "--project", root)
}
