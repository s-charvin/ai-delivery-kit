package checks

import (
	"strings"
	"testing"
)

func TestDesignGoRecursivePackagesDoNotHidePlaceholders(t *testing.T) {
	cases := []struct {
		name  string
		text  string
		valid bool
	}{
		{"all-packages", "执行 `go test -count=1 ./...`。", true},
		{"nested-packages", "执行 `go test -race ./api/...`。", true},
		{"multiple-packages", "go test ./... ./api/... example.com/team/pkg/... net/http/...", true},
		{"module-version", "go test gopkg.in/yaml.v3/...", true},
		{"parent-path", "go test ../api/...", true},
		{"multiple-parent-path", "go test ../../api/...", true},
		{"mixed-dot-parent-path", "go test ./../api/...", true},
		{"mixed-parent-dot-path", "go test .././../api/...", true},
		{"multiple-parent-root", "go test ../../...", true},
		{"internal-parent-segment", "go test ./api/../api/...", true},
		{"internal-current-segment", "go test ./api/./...", true},
		{"mixed-relative-segments", "go test ../api/./../api/../...", true},
		{"repeated-internal-segments", "go test ./api/././../api/...", true},
		{"bare-path", "./...", true},
		{"quoted-path", "go test './...' \"./api/...\"", true},
		{"punctuation", "包（./...）、[net/http/...]；完成。", true},
		{"whitespace", "go test\t./...\n./api/...", true},
		{"standalone", "...", false},
		{"unfinished-sentence", "回归验收 ...", false},
		{"unfinished-chinese", "保存...", false},
		{"template", "{{scope}}", false},
		{"inline-template", "执行 `{{scope}}`。", false},
		{"spaced-template", "{{scope to fill}}", false},
		{"ellipsis-after", "go test ./... ...", false},
		{"ellipsis-before", "... go test ./...", false},
		{"unfinished-after-command", "执行 `go test ./...`；保存...", false},
		{"template-in-command", "执行 `go test ./... {{scope}}`。", false},
		{"four-dots", "go test ./....", false},
		{"five-dots", "go test ./.....", false},
		{"trailing-word", "go test ./...suffix", false},
		{"trailing-chinese", "go test ./...待补", false},
		{"trailing-path", "go test ./.../suffix", false},
		{"empty-segment", "go test ./api//...", false},
		{"parent-empty-segment", "go test ..//../api/...", false},
		{"parent-four-dots", "go test ../../api/....", false},
		{"parent-trailing-word", "go test ./../api/...suffix", false},
		{"parent-template", "go test ../../api/... {{scope}}", false},
		{"parent-unfinished", "go test ./../api/...；保存...", false},
		{"internal-empty-segment", "go test ./api/..//api/...", false},
		{"internal-four-dots", "go test ./api/../api/....", false},
		{"internal-trailing-word", "go test ./api/./...suffix", false},
		{"internal-template", "go test ./api/../api/... {{scope}}", false},
		{"internal-unfinished", "go test ./api/./...；保存...", false},
		{"ellipsis-in-prefix", "go test foo.../bar/...", false},
		{"template-in-prefix", "go test {{scope}}/...", false},
		{"unbounded-prefix", "执行./...", false},
	}
	for _, section := range []string{"behavior", "human-decision"} {
		for _, tc := range cases {
			t.Run(section+"/"+tc.name, func(t *testing.T) {
				text := strings.Replace(designText, "保存数据", tc.text, 1)
				message := "行为合同含未解决占位符"
				if section == "human-decision" {
					text = strings.Replace(designText, "无需人工决定", "D-001 "+tc.text, 1)
					message = "人工决定包含占位符"
				}
				entry := reviewedEntry(text)
				if section == "human-decision" {
					entry["user_decision_required"] = true
					entry["design_review"].(map[string]any)["review_mode"] = "human"
				}
				issues := ValidateDesign([]byte(text), entry)
				if tc.valid && len(issues) != 0 {
					t.Fatalf("合法包路径被拒: %v", issues)
				}
				if !tc.valid && !contains(issues, message) {
					t.Fatalf("未拒绝占位符 %q: %v", tc.text, issues)
				}
			})
		}
	}
}

func TestDesignGoRecursivePackagesStillRequireCurrentHumanReview(t *testing.T) {
	text := strings.Replace(designText, "无需人工决定", "D-001 执行 `go test ./...`", 1)
	entry := reviewedEntry(text)
	entry["user_decision_required"] = true
	if issues := ValidateDesign([]byte(text), entry); !contains(issues, "当前设计要求 design_review.review_mode=human") {
		t.Fatal("包路径豁免绕过了人工评审", issues)
	}
	entry["design_review"].(map[string]any)["review_mode"] = "human"
	if issues := ValidateDesign([]byte(text+"\n当前修订"), entry); !contains(issues, "design_review 摘要未绑定当前 design.md") {
		t.Fatal("包路径豁免绕过了当前摘要", issues)
	}
}
