package cli

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// 帮助必须在读取项目或执行原生命令前返回；错误参数不能被后面的 help 吞掉。
func TestDeliveryHelpWithoutProjectAndParseOrder(t *testing.T) {
	root := t.TempDir()
	t.Setenv("PATH", t.TempDir())
	commands := []struct {
		args     []string
		name     string
		defaults map[string]string
	}{
		{[]string{"check"}, "check", map[string]string{"intent": "", "to": "", "format": "json"}},
		{[]string{"advance"}, "advance", map[string]string{"expected-snapshot": "", "to": ""}},
		{[]string{"context"}, "context", map[string]string{"role": "", "budget-chars": "64000", "changed-path": "[]"}},
		{[]string{"run"}, "run", map[string]string{"check": "", "cwd": ".", "timeout": "120", "input": "[]"}},
		{[]string{"evidence", "fingerprint"}, "evidence fingerprint", map[string]string{"input": "[]", "file": ""}},
		{[]string{"evidence", "review-digest"}, "evidence review-digest", map[string]string{"input": "[]", "file": ""}},
	}
	for _, command := range commands {
		t.Run(command.name, func(t *testing.T) {
			for _, tail := range [][]string{{"--help"}, {"--project", filepath.Join(root, "missing"), "--help"}, {"--help", "--bad"}, {"-h"}} {
				args := append(append([]string{}, command.args...), tail...)
				var out, stderr bytes.Buffer
				if code := New(&out, &stderr).Run(args); code != 0 || stderr.Len() != 0 {
					t.Fatalf("%v: code=%d stdout=%s stderr=%s", args, code, &out, &stderr)
				}
				var help struct {
					Command string `json:"command"`
					Usage   string `json:"usage"`
					Options []struct {
						Name, Usage, Default string
						Choices              []string
					} `json:"options"`
				}
				dec := json.NewDecoder(&out)
				if err := dec.Decode(&help); err != nil {
					t.Fatal(err)
				}
				if err := dec.Decode(new(any)); err != io.EOF {
					t.Fatalf("必须只有一个 JSON: %v", err)
				}
				if help.Command != command.name || help.Usage == "" {
					t.Fatalf("缺少可用命令帮助: %+v", help)
				}
				options := map[string]string{}
				for _, option := range help.Options {
					if option.Usage == "" {
						t.Fatal("参数缺说明", option.Name)
					}
					options[option.Name] = option.Default
					if option.Name == "intent" && !reflect.DeepEqual(option.Choices, []string{"analyze", "design", "ui", "implement", "verify", "merge", "archive"}) {
						t.Fatal("无法发现实际意图", option.Choices)
					}
				}
				for name, want := range command.defaults {
					if got, ok := options[name]; !ok || got != want {
						t.Fatalf("%s 默认值: %q, 存在=%v", name, got, ok)
					}
				}
			}
			for _, tail := range [][]string{{"--bad"}, {"--bad", "--help"}, {"--format", "text"}, {"--", "--help"}} {
				var out, stderr bytes.Buffer
				args := append(append([]string{}, command.args...), tail...)
				if code := New(&out, &stderr).Run(args); code != 2 {
					t.Fatalf("非法请求被放行 %v: %d %s", args, code, &out)
				}
			}
		})
	}
	for _, args := range [][]string{{"evidence", "--help"}, {"evidence", "-h"}} {
		var out, stderr bytes.Buffer
		if code := New(&out, &stderr).Run(args); code != 0 || stderr.Len() != 0 {
			t.Fatalf("%v: %d %s %s", args, code, &out, &stderr)
		}
		var result map[string]any
		if err := json.Unmarshal(out.Bytes(), &result); err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(result["operations"], []any{"fingerprint", "review-digest"}) {
			t.Fatal(result)
		}
	}
	for _, args := range [][]string{{"evidence", "--bad", "--help"}, {"evidence", "receipt", "--help"}} {
		var out, stderr bytes.Buffer
		if code := New(&out, &stderr).Run(args); code != 2 {
			t.Fatalf("%v: %d %s", args, code, &out)
		}
	}
	entries, err := os.ReadDir(root)
	if err != nil || len(entries) != 0 {
		t.Fatal("帮助触碰项目", entries, err)
	}
}

func TestUnknownIntentOffersRecoveryBeforeProjectRead(t *testing.T) {
	for _, intent := range []string{"resume", "bootstrap", "breakdown", "requirement-breakdown", "finish", "analysis", "Analyze", "analyze "} {
		var out, stderr bytes.Buffer
		args := []string{"check", "--project", filepath.Join(t.TempDir(), "missing"), "--req", "R", "--subreq", "SR-001", "--intent", intent}
		if code := New(&out, &stderr).Run(args); code != 2 || stderr.Len() != 0 {
			t.Fatal(code, &out, &stderr)
		}
		var result struct {
			Diagnostics []struct{ Code, Message, Recovery string }
		}
		if err := json.Unmarshal(out.Bytes(), &result); err != nil {
			t.Fatal(err)
		}
		if len(result.Diagnostics) != 1 {
			t.Fatal(result)
		}
		d := result.Diagnostics[0]
		if d.Code != "invalid_input" || !strings.Contains(d.Recovery, "check --help") {
			t.Fatal("无法恢复未知意图", d)
		}
		for _, choice := range []string{"analyze", "design", "ui", "implement", "verify", "merge", "archive"} {
			if !strings.Contains(d.Message, choice) {
				t.Fatal("诊断未给出合法意图", d)
			}
		}
	}
}
