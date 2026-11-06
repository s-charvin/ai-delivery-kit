package cli

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// 真实进程仅证明原生 transport 字节协议，不代表 Codex 已启用、信任或回调。
func TestCodexHookProcess(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	binary := filepath.Join(t.TempDir(), "ai-delivery")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	build := exec.Command("go", "build", "-o", binary, "./cmd/ai-delivery")
	build.Dir = filepath.Clean(filepath.Join(filepath.Dir(source), "../.."))
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build: %v %s", err, out)
	}
	root, _ := cliRunProject(t, "native-pass")
	subdir := filepath.Join(root, "子目录")
	if err := os.Mkdir(subdir, 0755); err != nil {
		t.Fatal(err)
	}
	serial := 0
	run := func(input string, args ...string) (int, map[string]any, string) {
		t.Helper()
		cmd := exec.Command(binary, args...)
		cmd.Dir = subdir
		cmd.Env = append(os.Environ(), "PATH=")
		cmd.Stdin = strings.NewReader(input)
		var out, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &out, &stderr
		err := cmd.Run()
		code := 0
		if err != nil {
			if e, ok := err.(*exec.ExitError); ok {
				code = e.ExitCode()
			} else {
				t.Fatal(err)
			}
		}
		var value map[string]any
		if out.Len() > 0 {
			if err := json.Unmarshal(out.Bytes(), &value); err != nil {
				t.Fatalf("stdout 非单 JSON: %s", &out)
			}
		}
		serial++
		if dir := os.Getenv("AI_DELIVERY_TEST_EVIDENCE_DIR"); dir != "" {
			if err := os.MkdirAll(dir, 0755); err != nil {
				t.Fatal(err)
			}
			body, _ := json.MarshalIndent(map[string]any{"argv": args, "stdin": input, "stdout": out.String(), "stderr": stderr.String(), "exit_code": code}, "", "  ")
			if err := os.WriteFile(filepath.Join(dir, fmt.Sprintf("codex-hook-%02d.json", serial)), body, 0644); err != nil {
				t.Fatal(err)
			}
		}
		return code, value, stderr.String()
	}
	event := func(name string) map[string]any {
		v := map[string]any{"session_id": "test-session", "cwd": subdir, "hook_event_name": name, "extension": map[string]any{"future": true}}
		if name == "SessionStart" {
			v["source"] = "compact"
		} else {
			v["tool_name"] = "apply_patch"
			v["tool_use_id"] = "tool-1"
			v["tool_input"] = map[string]any{"command": "*** Begin Patch\n*** End Patch"}
		}
		return v
	}
	encode := func(v any) string {
		b, err := json.Marshal(v)
		if err != nil {
			t.Fatal(err)
		}
		return string(b)
	}
	args := func(name string) []string {
		base := []string{"hook", "--host", "codex", "--event", name, "--project", root, "--req", "R", "--subreq", "SR-001"}
		if name == "SessionStart" {
			return append(base, "--role", "implement", "--path", "owner.txt", "--budget-chars", "4000")
		}
		return append(base, "--intent", "implement", "--to", "in_dev")
	}
	output := func(value map[string]any, name string) map[string]any {
		t.Helper()
		v, ok := value["hookSpecificOutput"].(map[string]any)
		if !ok || v["hookEventName"] != name || value["continue"] != nil || v["permissionDecision"] == "allow" {
			t.Fatalf("不是安全的原生形状: %v", value)
		}
		return v
	}
	t.Run("transcript-path-types", func(t *testing.T) {
		for _, name := range []string{"SessionStart", "PreToolUse"} {
			for _, scoped := range []bool{false, true} {
				for _, tc := range []struct {
					name           string
					value          any
					present, valid bool
				}{
					{"absent", nil, false, true}, {"null", nil, true, true}, {"string", "/unused/transcript", true, true},
					{"bool", false, true, false}, {"number", 7, true, false}, {"object", map[string]any{}, true, false}, {"array", []any{}, true, false},
				} {
					t.Run(fmt.Sprintf("%s/scoped=%t/%s", name, scoped, tc.name), func(t *testing.T) {
						v := event(name)
						if tc.present {
							v["transcript_path"] = tc.value
						}
						command := []string{"hook", "--host", "codex", "--event", name, "--project", root}
						if scoped {
							command = args(name)
						}
						code, result, stderr := run(encode(v), command...)
						if !tc.valid {
							if code != 2 || len(result) != 0 || stderr == "" {
								t.Fatalf("非法 transcript 未拒绝: %d %v %s", code, result, stderr)
							}
							return
						}
						if code != 0 || stderr != "" {
							t.Fatalf("合法 transcript 被拒绝: %d %v %s", code, result, stderr)
						}
						v = output(result, name)
						if v["permissionDecision"] != nil {
							t.Fatal(v)
						}
						if scoped && !strings.Contains(fmt.Sprint(v["additionalContext"]), "snapshot_id") {
							t.Fatal("未走 scoped 核心", v)
						}
					})
				}
			}
		}
	})
	t.Run("optional-host-files", func(t *testing.T) {
		paths := []string{".codex/hooks.json", ".claude/settings.json", ".cursor/hooks.json"}
		for _, p := range paths {
			if _, err := os.Stat(filepath.Join(root, p)); !os.IsNotExist(err) {
				t.Fatalf("默认安装可选文件 %s: %v", p, err)
			}
		}
		for _, tc := range []struct {
			name  string
			files map[string]string
		}{
			{"absent", nil},
			{"permissions-only", map[string]string{".claude/settings.json": `{"permissions":{"allow":[]}}`}},
			{"empty-hooks", map[string]string{".codex/hooks.json": `{"hooks":{}}`, ".cursor/hooks.json": `{"version":1,"hooks":{}}`}},
			{"user-config", map[string]string{".codex/hooks.json": `{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"ai-delivery hook --host codex"}]}]},"third_party":9007199254740993}`, ".claude/settings.json": `{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"third-party"}]}]}}`}},
		} {
			t.Run(tc.name, func(t *testing.T) {
				for _, p := range paths {
					if err := os.Remove(filepath.Join(root, p)); err != nil && !os.IsNotExist(err) {
						t.Fatal(err)
					}
				}
				for p, body := range tc.files {
					full := filepath.Join(root, p)
					if err := os.MkdirAll(filepath.Dir(full), 0755); err != nil {
						t.Fatal(err)
					}
					if err := os.WriteFile(full, []byte(body), 0600); err != nil {
						t.Fatal(err)
					}
				}
				for _, command := range [][]string{
					{"validate", "--kind", "sources", "--project", root},
					{"context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--budget-chars", "64000"},
					{"check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "implement", "--to", "in_dev"},
				} {
					code, value, stderr := run("", command...)
					if code != 0 || stderr != "" {
						t.Fatalf("完整合法任务被可选宿主配置阻断: %d %v %s", code, value, stderr)
					}
					if command[0] == "context" && value["context_complete"] != true {
						t.Fatal(value)
					}
					if command[0] == "check" && value["allowed"] != true {
						t.Fatal(value)
					}
				}
				for p, body := range tc.files {
					got, err := os.ReadFile(filepath.Join(root, p))
					if err != nil || string(got) != body {
						t.Fatalf("只读CLI改写用户配置 %s", p)
					}
				}
			})
		}
	})
	t.Run("session-context", func(t *testing.T) {
		baseCode, baseline, baseErr := run("", "context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--path", "owner.txt", "--budget-chars", "4000")
		if baseCode != 2 || baseline["context_complete"] != false || baseErr != "" {
			t.Fatalf("无 hook 显式 context: %d %v %s", baseCode, baseline, baseErr)
		}
		fullCode, full, fullErr := run("", "context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement", "--path", "owner.txt", "--budget-chars", "64000")
		if fullCode != 0 || full["context_complete"] != true || fullErr != "" {
			t.Fatalf("无 hook 完整 context: %d %v %s", fullCode, full, fullErr)
		}
		code, result, stderr := run(encode(event("SessionStart")), args("SessionStart")...)
		if code != 0 || stderr != "" {
			t.Fatalf("%d %v %s", code, result, stderr)
		}
		v := output(result, "SessionStart")
		body, ok := v["additionalContext"].(string)
		if !ok || !strings.Contains(body, fmt.Sprint(baseline["snapshot_id"])) || !strings.Contains(body, "needs_read") || len([]rune(body)) > 12000 {
			t.Fatalf("缺少有界来源上下文: %v", v)
		}
	})
	t.Run("same-core-allowed", func(t *testing.T) {
		code, checked, stderr := run("", "check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "implement", "--to", "in_dev")
		if code != 0 || checked["allowed"] != true {
			t.Fatalf("显式入口: %d %v %s", code, checked, stderr)
		}
		code, result, stderr := run(encode(event("PreToolUse")), args("PreToolUse")...)
		if code != 0 || stderr != "" {
			t.Fatalf("%d %v %s", code, result, stderr)
		}
		v := output(result, "PreToolUse")
		if v["permissionDecision"] != nil || !strings.Contains(fmt.Sprint(v["additionalContext"]), fmt.Sprint(checked["snapshot_id"])) {
			t.Fatalf("没有复用同一核心结果: %v", v)
		}
	})
	t.Run("large-context-is-labeled-and-bounded", func(t *testing.T) {
		p := filepath.Join(root, "AGENTS.md")
		original, err := os.ReadFile(p)
		if err != nil {
			t.Fatal(err)
		}
		defer func() {
			if err := os.WriteFile(p, original, 0644); err != nil {
				t.Fatal(err)
			}
		}()
		if err := os.WriteFile(p, append(append([]byte{}, original...), []byte(strings.Repeat("可审查的项目规范", 4000))...), 0644); err != nil {
			t.Fatal(err)
		}
		code, result, stderr := run(encode(event("SessionStart")), append(args("SessionStart"), "--budget-chars", "64000")...)
		if code != 0 || stderr != "" {
			t.Fatalf("%d %v %s", code, result, stderr)
		}
		body := fmt.Sprint(output(result, "SessionStart")["additionalContext"])
		if len([]rune(body)) > 12000 || !strings.Contains(body, "输出已截断") || !strings.Contains(body, "ai-delivery context/check") {
			t.Fatalf("截断没有完整来源指向: %d %s", len([]rune(body)), body)
		}
	})
	t.Run("same-core-denied", func(t *testing.T) {
		deny := args("PreToolUse")
		deny[len(deny)-1] = "merged"
		code, result, stderr := run(encode(event("PreToolUse")), deny...)
		if code != 0 || stderr != "" {
			t.Fatalf("%d %v %s", code, result, stderr)
		}
		v := output(result, "PreToolUse")
		if v["permissionDecision"] != "deny" || !strings.Contains(fmt.Sprint(v["permissionDecisionReason"]), "diagnostics") {
			t.Fatal(v)
		}
	})
	t.Run("no-scope-is-only-reminder", func(t *testing.T) {
		code, result, stderr := run(encode(event("PreToolUse")), "hook", "--host", "codex", "--event", "PreToolUse", "--project", root)
		if code != 0 || stderr != "" {
			t.Fatalf("%d %v %s", code, result, stderr)
		}
		v := output(result, "PreToolUse")
		if v["permissionDecision"] != nil || !strings.Contains(fmt.Sprint(v["additionalContext"]), "--req") {
			t.Fatal(v)
		}
	})
	bad := []struct {
		name   string
		mutate func(map[string]any)
		raw    string
		extra  []string
	}{
		{name: "wrong-event", mutate: func(v map[string]any) { v["hook_event_name"] = "Stop" }},
		{name: "wrong-type", mutate: func(v map[string]any) { v["cwd"] = 7 }},
		{name: "outside-cwd", mutate: func(v map[string]any) { v["cwd"] = t.TempDir() }},
		{name: "relative-cwd", mutate: func(v map[string]any) { v["cwd"] = "." }},
		{name: "missing-session", mutate: func(v map[string]any) { delete(v, "session_id") }},
		{name: "wrong-command", mutate: func(v map[string]any) { v["tool_input"] = map[string]any{"command": 3} }},
		{name: "wrong-tool-name", mutate: func(v map[string]any) { v["tool_name"] = []any{} }},
		{name: "wrong-tool-id", mutate: func(v map[string]any) { v["tool_use_id"] = false }},
		{name: "missing-tool-input", mutate: func(v map[string]any) { delete(v, "tool_input") }},
		{name: "wrong-optional-type", mutate: func(v map[string]any) { v["permission_mode"] = false }},
		{name: "duplicate", raw: `{"session_id":"x","session_id":"y"}`},
		{name: "duplicate-nested", raw: `{"extension":{"a":1,"a":2}}`},
		{name: "trailing", raw: `{} {}`},
		{name: "oversize", raw: strings.Repeat(" ", (1<<20)+1)},
		{name: "partial-scope", extra: []string{"--subreq", ""}},
		{name: "unsupported-host", extra: []string{"--host", "claude"}},
		{name: "unsupported-event", extra: []string{"--event", "Stop"}},
		{name: "unknown-flag", extra: []string{"--unknown"}},
	}
	for _, tc := range bad {
		t.Run(tc.name, func(t *testing.T) {
			v := event("PreToolUse")
			if tc.mutate != nil {
				tc.mutate(v)
			}
			input := encode(v)
			if tc.raw != "" {
				input = tc.raw
			}
			code, result, stderr := run(input, append(args("PreToolUse"), tc.extra...)...)
			if code != 2 || len(result) != 0 || stderr == "" {
				t.Fatalf("未用原生 exit2+stderr 阻断: %d %v %s", code, result, stderr)
			}
		})
	}
	t.Run("invalid-session-source", func(t *testing.T) {
		v := event("SessionStart")
		v["source"] = "future-source"
		code, result, stderr := run(encode(v), args("SessionStart")...)
		if code != 2 || len(result) != 0 || stderr == "" {
			t.Fatalf("未拒绝未知 source: %d %v %s", code, result, stderr)
		}
	})
	t.Run("linked-cwd-outside", func(t *testing.T) {
		link := filepath.Join(root, "outside-link")
		if err := os.Symlink(t.TempDir(), link); err != nil {
			t.Skipf("无法创建 symlink: %v", err)
		}
		v := event("PreToolUse")
		v["cwd"] = link
		code, result, stderr := run(encode(v), args("PreToolUse")...)
		if code != 2 || len(result) != 0 || stderr == "" {
			t.Fatalf("链接 cwd 未拒绝: %d %v %s", code, result, stderr)
		}
	})
	t.Run("core-format-error-blocks", func(t *testing.T) {
		p := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
		original, err := os.ReadFile(p)
		if err != nil {
			t.Fatal(err)
		}
		defer func() {
			if err := os.WriteFile(p, original, 0644); err != nil {
				t.Fatal(err)
			}
		}()
		if err := os.WriteFile(p, []byte(`{"_schema":2,"sub_requirements":[]}`), 0644); err != nil {
			t.Fatal(err)
		}
		code, result, stderr := run(encode(event("PreToolUse")), args("PreToolUse")...)
		if code == 2 && len(result) == 0 && stderr != "" {
			return
		}
		if code != 0 || stderr != "" {
			t.Fatalf("核心格式错误未阻断: %d %v %s", code, result, stderr)
		}
		v := output(result, "PreToolUse")
		if v["permissionDecision"] != "deny" || !strings.Contains(fmt.Sprint(v["permissionDecisionReason"]), "status.json") {
			t.Fatalf("核心格式诊断未映射为 deny: %v", v)
		}
	})
	t.Run("resource-drift-blocks", func(t *testing.T) {
		p := filepath.Join(root, ".agents/skills/requirement-breakdown/SKILL.md")
		if err := os.WriteFile(p, []byte("漂移"), 0644); err != nil {
			t.Fatal(err)
		}
		code, result, stderr := run(encode(event("PreToolUse")), args("PreToolUse")...)
		if code != 2 || len(result) != 0 || !strings.Contains(stderr, "init --upgrade") {
			t.Fatalf("资源错误未阻断: %d %v %s", code, result, stderr)
		}
		for _, command := range [][]string{
			{"context", "--project", root, "--req", "R", "--subreq", "SR-001", "--role", "implement"},
			{"check", "--project", root, "--req", "R", "--subreq", "SR-001", "--intent", "implement", "--to", "in_dev"},
		} {
			code, result, stderr := run("", command...)
			if code != 3 || !strings.Contains(fmt.Sprint(result), "resource_mismatch") {
				t.Fatalf("真实受管skill漂移未阻断显式CLI: %d %v %s", code, result, stderr)
			}
		}
	})
}
