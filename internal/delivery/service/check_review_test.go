package service_test

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReviewF1ExampleDesignCannotAuthorizeImplementation(t *testing.T) {
	for _, kind := range []string{"fenced-IDs", "indented-contract"} {
		t.Run(kind, func(t *testing.T) {
			root := actionProject(t, "design_ready")
			text := validDesign
			if kind == "fenced-IDs" {
				for _, line := range []string{"B-001 保存", "AC-001 数据保存成功", "B-001 AC-001"} {
					text = strings.Replace(text, "\n"+line+"\n", "\n```text\n"+line+"\n```\n", 1)
				}
			} else {
				text = "    " + strings.ReplaceAll(text, "\n", "\n    ")
			}
			write(t, root, ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md", text)
			setStatus(t, root, "design_ready", func(d map[string]any) {
				d["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["design_review"].(map[string]any)["reviewed_design_sha256"] = fmt.Sprintf("%x", sha256.Sum256([]byte(text)))
			})
			if check(t, root, "implement", "in_dev").Decision.Allowed {
				t.Fatal("当前hash不能让示例成为正式设计")
			}
		})
	}
}

func TestReviewF2ReachableUpstreamUsesSameArtifactRules(t *testing.T) {
	for _, tc := range []struct {
		mode, artifact     string
		transitive, linked bool
	}{
		{"none", "ui_truth_index", false, false}, {"existing", "visual_acceptance", false, false}, {"none", "ui_truth_index", true, true},
	} {
		t.Run(fmt.Sprintf("%s/%s/transitive=%v/linked=%v", tc.mode, tc.artifact, tc.transitive, tc.linked), func(t *testing.T) {
			root := actionProject(t, "design_ready")
			parentIDs := []string{"SR-002"}
			if tc.transitive {
				parentIDs = append(parentIDs, "SR-003")
			}
			setStatus(t, root, "design_ready", func(d map[string]any) {
				entries := d["sub_requirements"].(map[string]any)
				raw, _ := json.Marshal(entries["SR-001"])
				for _, id := range parentIDs {
					var e map[string]any
					_ = json.Unmarshal(raw, &e)
					e["status"] = "merged"
					e["ui_truth_mode"] = tc.mode
					e["ui_bearing"] = tc.mode != "none"
					entries[id] = e
				}
			})
			for _, id := range parentIDs {
				prefix := ".ai-delivery/requirements/R/sub-requirements/" + id + "/"
				write(t, root, prefix+"design.md", validDesign)
				write(t, root, prefix+"requirement-slice.md", "上游需求")
				d := writeVerification(t, root, nil)
				d["subreq_id"] = id
				d["inputs"].([]any)[0].(map[string]any)["path"] = prefix + "design.md"
				persistVerification(t, root, d)
				body, e := os.ReadFile(filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-001/verification.md"))
				if e != nil {
					t.Fatal(e)
				}
				write(t, root, prefix+"verification.md", string(body))
			}
			graph := `{"nodes":{"SR-001":{"depends_on":["SR-002"]},"SR-002":{"depends_on":[]}}}`
			if tc.transitive {
				graph = `{"nodes":{"SR-001":{"depends_on":["SR-003"]},"SR-003":{"depends_on":["SR-002"]},"SR-002":{"depends_on":[]}}}`
			}
			write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", graph)
			if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
				t.Fatal("合法上游对照", d.Decision.Diagnostics)
			}
			p := ".ai-delivery/requirements/R/sub-requirements/SR-002/visual-acceptance.json"
			if tc.artifact == "ui_truth_index" {
				p = ".ai-delivery/requirements/R/sub-requirements/SR-002/contracts/ui-truth-index.json"
			}
			if tc.linked {
				write(t, root, ".ai-delivery/shared-contracts/ui-truth-index.json", `{}`)
				if e := os.Symlink("../../../../shared-contracts", filepath.Join(root, ".ai-delivery/requirements/R/sub-requirements/SR-002/contracts")); e != nil {
					t.Fatal(e)
				}
			} else {
				write(t, root, p, `{}`)
			}
			d := check(t, root, "implement", "in_dev")
			if d.Decision.Allowed {
				t.Fatal("可达坏上游被放行")
			}
			found := false
			for _, diag := range d.Decision.Diagnostics {
				found = found || diag.Scope == "SR-002" && diag.Path == p && strings.Contains(diag.Message, tc.artifact)
			}
			if !found {
				t.Fatal("上游诊断缺少真实作用域/产物路径", d.Decision.Diagnostics)
			}
			write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":[]}}}`)
			if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
				t.Fatal("独立切片被误阻", d.Decision.Diagnostics)
			}
		})
	}
}

func TestReviewF3RemovedRootFieldsAreRequirementScoped(t *testing.T) {
	for _, nested := range []bool{false, true} {
		root := actionProject(t, "design_ready")
		setStatus(t, root, "design_ready", func(d map[string]any) {
			if nested {
				d["metadata"] = map[string]any{"design_approved": true}
			} else {
				d["design_approved"] = true
			}
		})
		d := check(t, root, "implement", "in_dev")
		if d.Decision.Allowed {
			t.Fatal("移除的根字段被接受")
		}
		found := false
		for _, diag := range d.Decision.Diagnostics {
			found = found || diag.Scope == "R" && strings.Contains(diag.Message, "design_approved")
		}
		if !found {
			t.Fatal("根字段错误应为requirement作用域", d.Decision.Diagnostics)
		}
	}
	root := actionProject(t, "design_ready")
	setStatus(t, root, "design_ready", func(d map[string]any) {
		d["sub_requirements"].(map[string]any)["SR-002"] = map[string]any{"status": "in_dev", "design_approved": true}
	})
	write(t, root, ".ai-delivery/requirements/R/dependency-graph.json", `{"nodes":{"SR-001":{"depends_on":[]},"SR-002":{"depends_on":[]}}}`)
	if d := check(t, root, "implement", "in_dev"); !d.Decision.Allowed {
		t.Fatal("无关entry移除字段不能成为global错误", d.Decision.Diagnostics)
	}
}
