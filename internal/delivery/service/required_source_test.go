package service_test

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRequiredSourceHealthGatesActionAndAdvance(t *testing.T) {
	for _, tt := range []struct {
		name, body       string
		missing, allowed bool
	}{
		{name: "empty"},
		{name: "whitespace", body: " \n\t\u2003"},
		{name: "invalid-utf8", body: string([]byte{0xff})},
		{name: "missing", missing: true},
		{name: "healthy", body: "有效规范正文", allowed: true},
	} {
		t.Run(tt.name, func(t *testing.T) {
			root := actionProject(t, "design_ready")
			write(t, root, "rules/api.md", tt.body)
			if tt.missing {
				if err := os.Remove(filepath.Join(root, "rules/api.md")); err != nil {
					t.Fatal(err)
				}
			}
			view := prepare(t, root, request()).View
			if view.ContextComplete != tt.allowed {
				t.Fatal("正文健康与呈现状态不一致", view)
			}
			statusPath := filepath.Join(root, ".ai-delivery/requirements/R/status.json")
			before, err := os.ReadFile(statusPath)
			if err != nil {
				t.Fatal(err)
			}
			checked := check(t, root, "implement", "in_dev")
			if checked.Decision.Allowed != tt.allowed {
				t.Fatal("动作忽略正文健康", checked.Decision)
			}
			result, err := advance(t, root, "in_dev", checked.Snapshot.ID())
			if err != nil || result.Decision.Allowed != tt.allowed {
				t.Fatal(result, err)
			}
			after, err := os.ReadFile(statusPath)
			if err != nil {
				t.Fatal(err)
			}
			if !tt.allowed {
				if len(result.WrittenPaths) != 0 || !bytes.Equal(before, after) {
					t.Fatal("拒绝后写入了状态", result)
				}
				found := false
				for _, d := range checked.Decision.Diagnostics {
					if d.Path == "rules/api.md" {
						found = true
						if strings.Contains(d.Recovery, "reset") || strings.Contains(d.Recovery, "迁移") {
							t.Fatal("缺正文误报格式迁移", d)
						}
					}
				}
				if !found {
					t.Fatal("未报告真正缺材料路径", checked.Decision)
				}
			} else if len(result.WrittenPaths) != 1 || bytes.Equal(before, after) {
				t.Fatal("合法控制未推进", result)
			}
		})
	}
}

func TestRequiredSourceHealthPreservesApplicabilityAndBudgetBoundary(t *testing.T) {
	for _, kind := range []string{"optional", "other-role", "other-path", "empty-production", "zero-budget", "design-no-target"} {
		t.Run(kind, func(t *testing.T) {
			root := actionProject(t, "design_ready")
			intent, target := "implement", "in_dev"
			source := `{"path":"rules/api.md","required":false}`
			switch kind {
			case "optional":
				write(t, root, "rules/api.md", "")
			case "other-role":
				write(t, root, "rules/api.md", "")
				source = `{"path":"rules/api.md","required":true,"roles":["finish"]}`
			case "other-path":
				write(t, root, "rules/api.md", "")
				write(t, root, "src/empty.txt", "")
				gitFixtureCommand(t, root, "init", "-q")
				source = `{"path":"rules/api.md","required":true,"paths":["unrelated/*"]}`
			case "empty-production":
				write(t, root, "src/empty.txt", "")
				gitFixtureCommand(t, root, "init", "-q")
			case "zero-budget":
				req := request()
				req.BudgetChars = 0
				if prepare(t, root, req).View.ContextComplete {
					t.Fatal("零预算应保留补读义务")
				}
			case "design-no-target":
				intent, target = "design", ""
				write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", "")
			}
			if kind == "optional" || kind == "other-role" || kind == "other-path" {
				write(t, root, ".ai-delivery/meta/workflow-policy.json", `{"version":4,"verification_contract_version":2,"context":{"sources":[`+source+`]}}`)
			}
			if checked := check(t, root, intent, target); !checked.Decision.Allowed {
				t.Fatal("错误扩大正文健康门禁", checked.Decision.Diagnostics)
			}
		})
	}
}
