package checks

import (
	"errors"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

func TestRecoveryUsesCauseInsteadOfHumanMessage(t *testing.T) {
	_, s := verificationFixture(t)
	message := "证据文件 RFC3339.txt 缺失；备注包含 实际类型="
	d := diagnosticCause(s, "ui_index", "index.json", errors.New(message))
	if strings.Contains(d.Recovery, "reset-data") {
		t.Fatalf("普通材料文案被推断为格式迁移: %+v", d)
	}
	d = diagnosticCause(s, "ui_index", "index.json", &protocol.FormatError{Path: "index.json#/schema_version", Cause: errors.New("unsupported version")})
	if d.Path != "index.json#/schema_version" || !strings.Contains(d.Recovery, "A.") || !strings.Contains(d.Recovery, "B.") {
		t.Fatalf("明确格式原因丢失字段或恢复方向: %+v", d)
	}
}

func TestTypedUIDiagnosticsAreSortedWithoutLosingCauses(t *testing.T) {
	root := t.TempDir()
	copyUIFixture(t, root, "component-only")
	index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
	acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
	uiPut(index, "design_source.captured_at", "bad-time")
	uiPut(index, "units.0.motion_decision.confirmation.confirmed_at", "bad-time")
	uiPut(index, "units.0.scenarios.0.confirmation.confirmed_at", "bad-time")
	uiPut(index, "units.0.coverage", []any{})
	acceptance["generated_at"] = "bad-time"
	uiPut(acceptance, "scenarios.0.evidence.1.reviewed_at", "bad-time")
	persistUIReviewFixture(t, root, index, acceptance)
	s := collectUIRoot(t, root).Snapshot
	for name, issues := range map[string][]error{
		"index":      validateUIIndex(s, uiSlice+"contracts/ui-truth-index.json", "figma"),
		"acceptance": validateUIAcceptance(s, uiSlice+"contracts/ui-truth-index.json", uiSlice+"visual-acceptance.json"),
	} {
		t.Run(name, func(t *testing.T) {
			messages := []string{}
			typed := 0
			for _, issue := range issues {
				messages = append(messages, issue.Error())
				var format *protocol.FormatError
				if errors.As(issue, &format) {
					typed++
					d := diagnosticCause(s, "ui_"+name, "unused", issue)
					if d.Path != format.Path || !strings.Contains(d.Recovery, "A.") || !strings.Contains(d.Recovery, "B.") {
						t.Fatal("排序丢失原始格式原因", d)
					}
				}
			}
			if typed < 2 || !sort.StringsAreSorted(messages) {
				t.Fatalf("typed=%d，诊断未保持类型与稳定排序: %v", typed, messages)
			}
		})
	}
}

func TestExistingFormatProducersRetainBothRecoveryChoices(t *testing.T) {
	_, s := verificationFixture(t)
	entry := reviewedEntry(designText)
	entry["design_review"].(map[string]any)["reviewed_at"] = "2026-11-05T12:00:00"
	_, retrospectiveErr := RetrospectiveEntries([]byte(strings.Replace(ledger, "2026-11-05T10:00:00+08:00", "2026-11-05T10:00:00", 1)), time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC))
	for name, issues := range map[string][]error{
		"design-review-time": validateDesign([]byte(designText), entry),
		"retrospective-time": {retrospectiveErr},
		"status-entry-type":  entryErrors(map[string]any{"status": 9}),
	} {
		t.Run(name, func(t *testing.T) {
			found := false
			for _, issue := range issues {
				if issue == nil {
					continue
				}
				var format *protocol.FormatError
				if !errors.As(issue, &format) {
					continue
				}
				d := diagnosticCause(s, name, "existing-file", issue)
				if d.Path != "existing-file" || !strings.Contains(d.Recovery, "A.") || !strings.Contains(d.Recovery, "B.") {
					t.Fatalf("已有格式诊断丢失文件/恢复方向: %+v", d)
				}
				found = true
			}
			if !found {
				t.Fatalf("真实格式生产点没有保留原因: %v", issues)
			}
		})
	}
}

func TestMissingUIAcceptanceStopsBeforeFieldValidation(t *testing.T) {
	_, s := verificationFixture(t)
	issues := validateUIAcceptance(s, "index.json", "acceptance.json")
	if len(issues) != 2 {
		t.Fatalf("缺文件后仍继续制造字段错误: %v", issues)
	}
	for _, issue := range issues {
		var missing *missingContractError
		if !errors.As(issue, &missing) {
			t.Fatalf("缺文件被分类为其他原因: %v", issue)
		}
		d := diagnosticCause(s, "ui_acceptance", "acceptance.json", issue)
		if d.Code != "missing_ui_acceptance" || strings.Contains(d.Recovery, "reset-data") {
			t.Fatalf("错误恢复: %+v", d)
		}
	}
}
