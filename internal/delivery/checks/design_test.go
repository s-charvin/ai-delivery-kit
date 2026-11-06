package checks

import (
	"crypto/sha256"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

const designText = `# 中文设计
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
保存数据
<!-- ai-delivery:behavior-contract:behavior -->
B-001 保存
<!-- ai-delivery:behavior-contract:acceptance -->
AC-001 保存成功
<!-- ai-delivery:behavior-contract:traceability -->
B-001 AC-001
<!-- ai-delivery:behavior-contract:end -->
<!-- ai-delivery:user-decisions -->
无需人工决定
`

func reviewedEntry(text string) map[string]any {
	return map[string]any{"state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(text))), "reviewed_by": "当前 AI", "reviewed_at": "2026-11-05T12:00:00+08:00"}}
}

func TestDesignCurrentSelfReviewAndAcceptanceScope(t *testing.T) {
	text := designText + "\n附注 AC-999\n"
	if got := ValidateDesign([]byte(text), reviewedEntry(text)); len(got) > 0 {
		t.Fatal(got)
	}
	acs, err := AcceptanceIDs([]byte(text))
	if err != nil || !reflect.DeepEqual(acs, []string{"AC-001"}) {
		t.Fatal(acs, err)
	}
	for _, text := range []string{strings.ReplaceAll(designText, "\n", "\r\n"), strings.ReplaceAll(designText, "中文设计", "別の見出し")} {
		if ds := ValidateDesign([]byte(text), reviewedEntry(text)); len(ds) > 0 {
			t.Fatal(ds)
		}
	}
}

func TestDesignRejectsStaleHumanAndMalformedMarkers(t *testing.T) {
	for name, change := range map[string]func(string) string{
		"duplicate": func(s string) string { return s + s },
		"unclosed":  func(s string) string { return strings.ReplaceAll(s, "<!-- ai-delivery:behavior-contract:end -->", "") },
		"section": func(s string) string {
			return strings.ReplaceAll(s, "<!-- ai-delivery:behavior-contract:acceptance -->", "")
		},
		"placeholder": func(s string) string { return strings.ReplaceAll(s, "保存数据", "{{scope}}") },
		"trace":       func(s string) string { return strings.ReplaceAll(s, "B-001 AC-001", "B-001") },
	} {
		t.Run(name, func(t *testing.T) {
			s := change(designText)
			if len(ValidateDesign([]byte(s), reviewedEntry(s))) == 0 {
				t.Fatal("错误合同被接受")
			}
		})
	}
	e := reviewedEntry(designText)
	if len(ValidateDesign([]byte(designText+"changed"), e)) == 0 {
		t.Fatal("陈旧评审被接受")
	}
	e["user_decision_required"] = true
	if len(ValidateDesign([]byte(designText), e)) == 0 {
		t.Fatal("self不能替代human")
	}
	s := designText + "D-001 已由用户决定\n"
	e = reviewedEntry(s)
	e["user_decision_required"] = true
	e["design_review"].(map[string]any)["review_mode"] = "human"
	if ds := ValidateDesign([]byte(s), e); len(ds) > 0 {
		t.Fatal(ds)
	}
}

func TestJSONBlockStrictFencesAndDuplicateKeys(t *testing.T) {
	const start = "<!-- contract:start -->"
	const end = "<!-- contract:end -->"
	valid := start + "\n```json\n{\"说明\":\"中文\"}\n```\n" + end
	if _, err := ParseBlock([]byte(valid), start, end); err != nil {
		t.Fatal(err)
	}
	for _, s := range []string{valid + valid, strings.ReplaceAll(valid, end, ""), end + valid, strings.ReplaceAll(valid, "```json", "```"), strings.ReplaceAll(valid, "{\"说明\":\"中文\"}", "{\"x\":1,\"x\":2}"), start + "\n```json\n{}\n```\nextra\n" + end} {
		if _, err := ParseBlock([]byte(s), start, end); err == nil {
			t.Fatalf("接受畸形块 %q", s)
		}
	}
}

func TestContractIDsMustComeFromProseNotCodeExamples(t *testing.T) {
	for _, fence := range []string{"```text", "~~~text"} {
		closing := fence[:3]
		for _, line := range []string{"B-001 保存", "AC-001 保存成功", "B-001 AC-001"} {
			t.Run(fence+"/"+line, func(t *testing.T) {
				text := strings.Replace(designText, "\n"+line+"\n", "\n"+fence+"\n"+line+"\n"+closing+"\n", 1)
				if ds := ValidateDesign([]byte(text), reviewedEntry(text)); len(ds) == 0 {
					t.Fatal("示例ID冒充正式合同")
				}
				if strings.HasPrefix(line, "AC-") {
					acs, err := AcceptanceIDs([]byte(text))
					if err == nil && len(acs) > 0 {
						t.Fatal("代码示例进入验收集合", acs)
					}
				}
			})
		}
	}
	for _, indent := range []string{"    ", "\t"} {
		text := indent + strings.ReplaceAll(designText, "\n", "\n"+indent)
		if ds := ValidateDesign([]byte(text), reviewedEntry(text)); len(ds) == 0 {
			t.Fatal("整份缩进代码冒充正式合同")
		}
		if _, err := AcceptanceIDs([]byte(text)); err == nil {
			t.Fatal("缩进示例提供正式marker")
		}
	}
	text := strings.Replace(designText, "AC-001 保存成功", "AC-001 保存成功\n\n```text\nAC-999 示例\n```\n\n    AC-998 缩进示例", 1)
	acs, err := AcceptanceIDs([]byte(text))
	if err != nil || !reflect.DeepEqual(acs, []string{"AC-001"}) {
		t.Fatal(acs, err)
	}
	if ds := ValidateDesign([]byte(text), reviewedEntry(text)); len(ds) > 0 {
		t.Fatal(ds)
	}
}

func TestTimestampRejectsPermissiveGoParserBoundaries(t *testing.T) {
	for _, value := range []string{"2026-11-05T12:00:00+24:00", "2026-11-05T12:00:00+00:60", "2026-11-05T1:00:00Z", "2026-11-05T12:00:00,123Z", "2026-02-30T12:00:00Z", "2026-11-05T12:00:00"} {
		t.Run(value, func(t *testing.T) {
			if timestamp(value) {
				t.Fatal("当前RFC3339语法接受无效值", value)
			}
		})
	}
	for _, value := range []string{"2026-11-05T12:00:00Z", "2026-11-05T12:00:00+08:00", "2026-11-05T12:00:00-08:00", "2026-11-05T12:00:00+23:59", "2026-11-05T12:00:00.123Z", "2026-11-05T12:00:00.123456789+05:30"} {
		t.Run(value, func(t *testing.T) {
			if !timestamp(value) {
				t.Fatal("拒绝合法RFC3339时间", value)
			}
		})
	}
}
