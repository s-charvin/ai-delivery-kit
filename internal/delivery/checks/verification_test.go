package checks

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func verificationFixture(t *testing.T) (map[string]any, model.Snapshot) {
	t.Helper()
	docs := map[string][]byte{"design.md": []byte(designText), "result.log": []byte("passed AC-001"), "src.go": []byte("source")}
	files := []model.FileIdentity{}
	entry := func(p string) map[string]any {
		return map[string]any{"path": p, "sha256": fmt.Sprintf("%x", sha256.Sum256(docs[p]))}
	}
	for p, b := range docs {
		hash := fmt.Sprintf("%x", sha256.Sum256(b))
		files = append(files, model.FileIdentity{Path: p, ResolvedPath: p, Kind: "file", SHA256: &hash})
	}
	a := model.Action{Intent: "merge", TargetStatus: "merged"}
	s, e := workspace.NewSnapshot(model.Workspace{}, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &a}, docs, files, nil)
	if e != nil {
		t.Fatal(e)
	}
	data := map[string]any{"version": json.Number("2"), "subreq_id": "SR-001", "inputs": []any{entry("design.md"), entry("src.go")}, "checks": []any{map[string]any{"id": "save", "required": true, "result": "passed", "mode": "executed", "command": "go test ./...", "exit_code": json.Number("0"), "acceptance_ids": []any{"AC-001"}, "evidence": []any{entry("result.log")}}}}
	refreshReview(data)
	return data, s
}
func refreshReview(data map[string]any) {
	id, _ := protocol.InputDigest(data["inputs"].([]any))
	vd, _ := protocol.ReviewDigest(data)
	data["reviews"] = []any{map[string]any{"reviewer": "独立评审者", "context": "fresh", "result": "clean", "input_sha256": id, "verification_sha256": vd, "findings": []any{}}}
}
func TestVerificationRequiresCurrentFilesACAndFreshReview(t *testing.T) {
	data, s := verificationFixture(t)
	if ds := ValidateVerification(data, s, "design.md", []string{"AC-001"}); len(ds) > 0 {
		t.Fatal(ds)
	}
	cases := map[string]func(map[string]any){
		"false": func(d map[string]any) {
			c := d["checks"].([]any)[0].(map[string]any)
			c["required"] = false
			c["result"] = "failed"
			refreshReview(d)
		},
		"deleted":      func(d map[string]any) { d["checks"] = []any{}; refreshReview(d) },
		"empty-inputs": func(d map[string]any) { d["inputs"] = []any{}; refreshReview(d) },
		"stale-file": func(d map[string]any) {
			d["inputs"].([]any)[1].(map[string]any)["sha256"] = strings.Repeat("0", 64)
			refreshReview(d)
		},
		"stale-review": func(d map[string]any) { d["checks"].([]any)[0].(map[string]any)["command"] = "changed" },
		"wrong-slice":  func(d map[string]any) { d["subreq_id"] = "SR-002"; refreshReview(d) },
		"no-AC": func(d map[string]any) {
			d["checks"].([]any)[0].(map[string]any)["acceptance_ids"] = []any{}
			refreshReview(d)
		},
		"invalid-waiver": func(d map[string]any) {
			c := d["checks"].([]any)[0].(map[string]any)
			c["result"] = "waived"
			c["waiver"] = map[string]any{"by": "AI"}
			refreshReview(d)
		},
		"not-fresh": func(d map[string]any) { d["reviews"].([]any)[0].(map[string]any)["context"] = "same" },
		"unknown": func(d map[string]any) {
			d["checks"].([]any)[0].(map[string]any)["result"] = "unknown"
			refreshReview(d)
		},
		"escape": func(d map[string]any) {
			d["inputs"].([]any)[1].(map[string]any)["path"] = "../outside"
			refreshReview(d)
		},
	}
	for name, change := range cases {
		t.Run(name, func(t *testing.T) {
			d, s := verificationFixture(t)
			change(d)
			if len(ValidateVerification(d, s, "design.md", []string{"AC-001"})) == 0 {
				t.Fatal("无效验证被接受")
			}
		})
	}
}
func TestValidManualWaiverAndAbsentInputs(t *testing.T) {
	for _, mode := range []string{"manual", "waived"} {
		d, s := verificationFixture(t)
		c := d["checks"].([]any)[0].(map[string]any)
		authority := map[string]any{"by": "用户", "at": "2026-11-05T10:00:00Z", "reason": "批准步骤", "source_ref": "decisions.md#D-001"}
		if mode == "manual" {
			c["mode"] = "manual"
			delete(c, "exit_code")
			c["confirmation"] = authority
		} else {
			c["result"] = "waived"
			c["waiver"] = authority
		}
		refreshReview(d)
		if ds := ValidateVerification(d, s, "design.md", []string{"AC-001"}); len(ds) > 0 {
			t.Fatal(ds)
		}
	}
}
func TestMarkdownExamplesAndInvalidUTF8DoNotAuthorize(t *testing.T) {
	for _, raw := range [][]byte{[]byte("````markdown\n" + designText + "````\n"), append([]byte(designText), 0xff)} {
		if len(ValidateDesign(raw, reviewedEntry(string(raw)))) == 0 {
			t.Fatal("示例/非法UTF8不应成为当前合同")
		}
	}
}

func TestReferenceExpansionRejectsOversizedSetBeforeReading(t *testing.T) {
	items := make([]any, 10001)
	for i := range items {
		items[i] = map[string]any{"path": fmt.Sprintf("inputs/%d", i)}
	}
	if _, err := VerificationReferences(map[string]any{"inputs": items, "checks": []any{}}); err == nil {
		t.Fatal("超过10000的引用集不能进入逐文件读取")
	}
}

func TestAbsenceRequiresExplicitNullDigest(t *testing.T) {
	d, s := verificationFixture(t)
	a := *s.Request().Action
	docs := map[string][]byte{}
	for _, p := range []string{"design.md", "result.log", "src.go"} {
		docs[p], _ = s.Document(p)
	}
	files := append(s.Files(), model.FileIdentity{Path: "deleted.go", ResolvedPath: "deleted.go", Kind: "absent"})
	s, e := workspace.NewSnapshot(s.Workspace(), s.Scope(), model.ReadRequest{Action: &a}, docs, files, nil)
	if e != nil {
		t.Fatal(e)
	}
	d["inputs"] = append(d["inputs"].([]any), map[string]any{"path": "deleted.go", "state": "absent"})
	refreshReview(d)
	if len(ValidateVerification(d, s, "design.md", []string{"AC-001"})) == 0 {
		t.Fatal("缺失sha256不等于显式null")
	}
}

func TestStateFlowMatrixAndDiagramConsistency(t *testing.T) {
	flow := "<!-- ai-delivery:state-flow:start -->\n"
	for _, section := range []string{"taxonomy", "mvi-loop", "lifecycle", "projection", "matrix", "sequences", "invariants", "traceability"} {
		flow += "<!-- ai-delivery:state-flow:" + section + " -->\n"
		switch section {
		case "taxonomy":
			flow += "UiEffect\n"
		case "mvi-loop":
			flow += "```mermaid\nflowchart LR\nA -->|T-001| B\n```\n"
		case "lifecycle":
			flow += "```mermaid\nstateDiagram-v2\nA --> B: T-001\n```\n"
		case "matrix":
			flow += "| T-001 | 保存事件 |\n"
		case "sequences":
			flow += "not_applicable：没有跨系统交互\n"
		case "invariants":
			flow += "<!-- ai-delivery:state-flow:stale-result -->\n忽略过期结果\n<!-- ai-delivery:state-flow:concurrency -->\n顺序处理\n"
		}
	}
	flow += "<!-- ai-delivery:state-flow:end -->\n"
	for _, bad := range []bool{false, true} {
		s := designText + flow
		if bad {
			s = strings.Replace(s, "A -->|T-001| B", "A -->|T-999| B", 1)
		}
		e := reviewedEntry(s)
		e["state_flow_required"] = true
		ds := ValidateDesign([]byte(s), e)
		if (len(ds) > 0) != bad {
			t.Fatal(ds)
		}
	}
}
