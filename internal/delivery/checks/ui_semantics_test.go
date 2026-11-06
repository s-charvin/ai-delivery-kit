package checks

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func copyUIFixture(t *testing.T, dest, name string) {
	t.Helper()
	src := filepath.Join("../../../tests/migration-oracle/fixtures", name)
	err := filepath.WalkDir(src, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(src, p)
		target := filepath.Join(dest, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0755)
		}
		b, e := os.ReadFile(p)
		if e != nil {
			return e
		}
		return os.WriteFile(target, b, 0644)
	})
	if err != nil {
		t.Fatal(err)
	}
}
func uiReadJSON(t *testing.T, root, p string) map[string]any {
	t.Helper()
	b, e := os.ReadFile(filepath.Join(root, p))
	if e != nil {
		t.Fatal(e)
	}
	m, e := protocol.Object(b)
	if e != nil {
		t.Fatal(e)
	}
	return m
}
func uiWriteJSON(t *testing.T, root, p string, m map[string]any) {
	t.Helper()
	b, e := json.Marshal(m)
	if e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(root, p), b, 0644); e != nil {
		t.Fatal(e)
	}
}
func uiHashFile(t *testing.T, root, p string) string {
	t.Helper()
	b, e := os.ReadFile(filepath.Join(root, p))
	if e != nil {
		t.Fatal(e)
	}
	return fmt.Sprintf("%x", sha256.Sum256(b))
}
func collectUIRoot(t *testing.T, root string) model.ObservationSet {
	t.Helper()
	s, e := (workspace.Reader{}).Load(context.Background(), model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}, model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
	if e != nil {
		t.Fatal(e)
	}
	got, e := (Reader{}).Collect(context.Background(), s, []model.CheckSpec{{ID: "ui_index", InputPaths: []string{uiSlice + "contracts/ui-truth-index.json"}}, {ID: "ui_acceptance", InputPaths: []string{uiSlice + "visual-acceptance.json"}}})
	if e != nil {
		t.Fatal(e)
	}
	return got
}
func uiPut(m map[string]any, p string, value any) {
	parts := strings.Split(p, ".")
	var node any = m
	for _, part := range parts[:len(parts)-1] {
		if a, ok := node.([]any); ok {
			var i int
			fmt.Sscan(part, &i)
			node = a[i]
		} else {
			node = node.(map[string]any)[part]
		}
	}
	node.(map[string]any)[parts[len(parts)-1]] = value
}
func uiUnit(m map[string]any) map[string]any     { return uiMap(uiList(m["units"])[0]) }
func uiScenario(m map[string]any) map[string]any { return uiMap(uiList(uiUnit(m)["scenarios"])[0]) }
func TestUISemanticsAndFixedOracleCorpus(t *testing.T) {
	type row struct {
		name, fixture, document, field string
		value                          any
		valid                          bool
	}
	cases := []row{
		{"component-valid", "component-only", "", "", nil, true}, {"host-runtime-valid", "host-runtime", "", "", nil, true},
		{"host-static-valid", "host-runtime", "index", "units.0.scenarios.0.evidence_scope", "host-static", true},
		{"index-version", "component-only", "index", "schema_version", 2, false},
		{"index-mode", "component-only", "index", "ui_truth_mode", "existing", false},
		{"design-source-origin", "component-only", "index", "design_source.evidence_origin", "project", false},
		{"design-source-time", "component-only", "index", "design_source.captured_at", "2026-11-05", false},
		{"figma-revision", "component-only", "index", "design_source.revision", "", false},
		{"empty-units", "component-only", "index", "units", []any{}, false},
		{"unit-id", "component-only", "index", "units.0.unit_id", "bad_ID", false},
		{"unit-type", "component-only", "index", "units.0.type", "fixture", false},
		{"unit-stack", "component-only", "index", "units.0.stack", "unknown", false},
		{"unit-source-node", "component-only", "index", "units.0.source_node", "", false},
		{"self-dependency", "component-only", "index", "units.0.dependencies", []any{"profile-card"}, false},
		{"unknown-dependency", "component-only", "index", "units.0.dependencies", []any{"missing"}, false},
		{"component-hash", "component-only", "index", "units.0.component_sha256", strings.Repeat("0", 64), false},
		{"component-missing", "component-only", "index", "units.0.component_path", "lib/missing.dart", false},
		{"component-traversal", "component-only", "index", "units.0.component_path", "../missing.dart", false},
		{"golden-suffix", "component-only", "index", "units.0.golden_test", "test/goldens/profile-card-default.png", false},
		{"profile-width-bool", "component-only", "index", "units.0.profiles.0.surface.width", true, false},
		{"profile-zero", "component-only", "index", "units.0.profiles.0.surface.device_pixel_ratio", 0, false},
		{"profile-reduced-motion", "component-only", "index", "units.0.profiles.0.reduced_motion", "false", false},
		{"profile-theme", "component-only", "index", "units.0.profiles.0.theme", "", false},
		{"profile-orientation", "component-only", "index", "units.0.profiles.0.orientation", "wide", false},
		{"state-source-node", "component-only", "index", "units.0.states.0.source_node", "", false},
		{"state-source-ref", "component-only", "index", "units.0.states.0.source_ref", "", false},
		{"wrong-state", "component-only", "index", "units.0.scenarios.0.state_id", "error", false},
		{"wrong-profile", "component-only", "index", "units.0.scenarios.0.profile_id", "tablet", false},
		{"dimensions-empty", "component-only", "index", "units.0.scenarios.0.dimensions", []any{}, false},
		{"dimensions-duplicate", "component-only", "index", "units.0.scenarios.0.dimensions", []any{"state", "state"}, false},
		{"scope-missing", "component-only", "index", "units.0.scenarios.0.evidence_scope", nil, false},
		{"component-supported-host", "component-only", "index", "units.0.scenarios.0.scope_decision.host_capture_supported", true, false},
		{"component-risk", "component-only", "index", "units.0.scenarios.0.scope_decision.uncovered_risk", "", false},
		{"host-unsupported", "host-runtime", "index", "units.0.scenarios.0.scope_decision.host_capture_supported", false, false},
		{"host-test-source", "host-runtime", "index", "units.0.scenarios.0.host_binding.host_component_path", "test/profile_card_golden_test.dart", false},
		{"host-root-governance", "host-runtime", "index", "units.0.scenarios.0.host_binding.evidence_root", ".ai-delivery", false},
		{"host-empty-landmarks", "host-runtime", "index", "units.0.scenarios.0.host_binding.required_landmarks", []any{}, false},
		{"host-constraint-kind", "host-runtime", "index", "units.0.scenarios.0.host_binding.spatial_constraints.0.kind", "guess", false},
		{"preview-hash", "component-only", "index", "units.0.scenarios.0.preview_sha256", strings.Repeat("a", 64), false},
		{"confirmation-stale", "component-only", "index", "units.0.scenarios.0.confirmation.reviewed_preview_sha256", strings.Repeat("a", 64), false},
		{"confirmation-missing", "component-only", "index", "units.0.scenarios.0.confirmation", nil, false},
		{"confirmation-waiver-note", "component-only", "index", "units.0.scenarios.0.confirmation.status", "waived", true},
		{"coverage-missing", "component-only", "index", "units.0.coverage", []any{}, false},
		{"coverage-inconsistent", "component-only", "index", "units.0.coverage.0.status", "not_applicable", false},
		{"motion-missing", "component-only", "index", "units.0.motion_decision", nil, false},
		{"motion-not-applicable", "component-only", "index", "units.0.motion_decision.verification_mode", "not_applicable", false},
		{"motion-confirmation-missing", "component-only", "index", "units.0.motion_decision.confirmation", nil, false},
		{"motion-stale", "component-only", "index", "units.0.motion_decision.confirmation.reviewed_preview_sha256", strings.Repeat("0", 64), false},
		{"motion-preview-png", "component-only", "index", "units.0.motion_decision.preview_path", "test/goldens/profile-card-default.png", false},
		{"motion-conflicting-unavailability", "component-only", "index", "units.0.motion_decision.preview_unavailable_reason", "不可用", false},
		{"acceptance-version", "component-only", "acceptance", "schema_version", 1, false},
		{"acceptance-index-stale", "component-only", "acceptance", "ui_truth_index_sha256", strings.Repeat("0", 64), false},
		{"acceptance-time", "component-only", "acceptance", "generated_at", "2026-11-05", false},
		{"acceptance-missing-scenarios", "component-only", "acceptance", "scenarios", []any{}, false},
		{"acceptance-unknown-scenario", "component-only", "acceptance", "scenarios.0.scenario_id", "wrong-state", false},
		{"acceptance-invalid-result", "component-only", "acceptance", "scenarios.0.result", "invalid", false},
		{"acceptance-missing-evidence", "component-only", "acceptance", "scenarios.0.evidence", []any{}, false},
		{"acceptance-wrong-preview", "component-only", "acceptance", "scenarios.0.evidence.0.path", "test/goldens/unrelated.png", false},
		{"acceptance-wrong-region", "host-runtime", "acceptance", "scenarios.0.evidence.0.capture_boundary_ref", "different-region", false},
		{"acceptance-wrong-host", "host-runtime", "acceptance", "scenarios.0.evidence.0.host_component_path", "lib/profile_card.dart", false},
		{"acceptance-stale-capture-review", "host-runtime", "acceptance", "scenarios.0.evidence.0.reviewed_capture_sha256", strings.Repeat("0", 64), false},
		{"acceptance-landmark-missing", "host-runtime", "acceptance", "scenarios.0.evidence.0.verified_landmarks", []any{}, false},
		{"acceptance-constraint-missing", "host-runtime", "acceptance", "scenarios.0.evidence.0.verified_constraints", []any{}, false},
		{"acceptance-report-stale", "host-runtime", "acceptance", "scenarios.0.evidence.0.assertion_report_sha256", strings.Repeat("0", 64), false},
		{"acceptance-motion-missing", "component-only", "acceptance", "motion_acceptance", []any{}, false},
		{"acceptance-motion-unknown-unit", "component-only", "acceptance", "motion_acceptance.0.unit_id", "missing", false},
		{"acceptance-motion-static-golden", "component-only", "acceptance", "motion_acceptance.0.evidence.0.kind", "test", false},
		{"acceptance-motion-preview-mismatch", "component-only", "acceptance", "motion_acceptance.0.evidence.0.path", "test/goldens/profile-card-default.png", false},
	}
	export := os.Getenv("AI_DELIVERY_UI_CORPUS")
	results := []map[string]any{}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			if export != "" {
				root = filepath.Join(export, tc.name)
			}
			copyUIFixture(t, root, tc.fixture)
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			if tc.document == "index" {
				uiPut(index, tc.field, tc.value)
				uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
				acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			}
			if tc.document == "acceptance" {
				uiPut(acceptance, tc.field, tc.value)
			}
			uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
			got := collectUIRoot(t, root)
			valid := true
			for _, o := range got.Observations {
				valid = valid && o.Result == "passed"
			}
			if valid != tc.valid {
				for _, o := range got.Observations {
					t.Logf("%s: %s", o.CheckID, o.Details)
				}
				t.Fatalf("valid=%v want=%v", valid, tc.valid)
			}
			results = append(results, map[string]any{"name": tc.name, "root": root, "go_valid": valid})
		})
	}
	if export != "" {
		b, _ := json.MarshalIndent(results, "", "  ")
		if err := os.WriteFile(filepath.Join(export, "go-results.json"), b, 0644); err != nil {
			t.Fatal(err)
		}
	}
}

func TestUIStaticRuntimeAndBehaviorVariants(t *testing.T) {
	for _, variant := range []string{"static", "runtime-no-preview", "runtime-baseline", "behavior-only", "scenario-waiver", "motion-waiver", "image-diff"} {
		t.Run(variant, func(t *testing.T) {
			root := t.TempDir()
			copyUIFixture(t, root, "component-only")
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			u := uiUnit(index)
			scenario := uiScenario(index)
			m := uiMap(u["motion_decision"])
			mr := uiMap(uiList(acceptance["motion_acceptance"])[0])
			ar := uiMap(uiList(acceptance["scenarios"])[0])
			manual := map[string]any{"kind": "manual", "summary": "协议测试夹具；不代表真实视觉批准", "reviewed_by": "fixture", "reviewed_at": "2026-11-05T00:00:00Z"}
			switch variant {
			case "static", "runtime-no-preview":
				delete(m, "preview_path")
				delete(m, "preview_sha256")
				delete(uiMap(m["confirmation"]), "reviewed_preview_sha256")
				mr["evidence"] = []any{manual}
				if variant == "static" {
					m["decision"] = "static"
					m["verification_mode"] = "not_applicable"
				} else {
					m["preview_unavailable_reason"] = "宿主暂不能生成确定性动效预览"
				}
			case "runtime-baseline":
				index["ui_truth_mode"] = "runtime-baseline"
				uiMap(index["design_source"])["evidence_origin"] = "project"
				for _, r := range uiList(u["states"]) {
					uiMap(r)["evidence_origin"] = "requirement"
				}
				scenario["evidence_origin"] = "project"
				status := uiReadJSON(t, root, ".ai-delivery/requirements/REQ-UI/status.json")
				uiMap(uiMap(status["sub_requirements"])["SR-001"])["ui_truth_mode"] = "runtime-baseline"
				uiWriteJSON(t, root, ".ai-delivery/requirements/REQ-UI/status.json", status)
			case "behavior-only":
				scenario["review_mode"] = "behavior"
				delete(scenario, "preview_path")
				delete(scenario, "preview_sha256")
				ar["evidence"] = []any{manual}
			case "scenario-waiver":
				ar["result"] = "waived"
				ar["evidence"] = []any{}
				ar["waived_by"] = "fixture"
				ar["waived_at"] = "2026-11-05T00:00:00Z"
				ar["note"] = "测试显式豁免协议"
			case "motion-waiver":
				mr["result"] = "waived"
				mr["evidence"] = []any{}
				mr["waived_by"] = "fixture"
				mr["waived_at"] = "2026-11-05T00:00:00Z"
				mr["note"] = "测试独立动效豁免协议"
			case "image-diff":
				e := map[string]any{"kind": "image-diff", "summary": "协议差分夹具", "metric": "pixel", "threshold": 0, "actual": 0, "command": "fixture-diff"}
				for _, r := range []string{"reference", "candidate", "diff"} {
					e[r+"_path"] = scenario["preview_path"]
					e[r+"_sha256"] = scenario["preview_sha256"]
				}
				ar["evidence"] = []any{e, manual}
			}
			uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
			acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
			got := collectUIRoot(t, root)
			for _, o := range got.Observations {
				if o.Result != "passed" {
					t.Fatalf("%s: %s", o.CheckID, o.Details)
				}
			}
			if variant == "static" {
				uiMap(m["confirmation"])["status"] = "waived"
				uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
				got = collectUIRoot(t, root)
				if got.Observations[0].Result != "invalid" {
					t.Fatal("static 被豁免")
				}
			}
		})
	}
}

func TestUITransitiveEvidencePublicationDrift(t *testing.T) {
	for _, p := range []string{"lib/profile_card.dart", "lib/profile_page.dart", "test/profile_card_golden_test.dart", "test/goldens/profile-card-default.png", "test/motion/profile-card-default.gif", "integration_test/screenshots/profile/profile-page.png", "integration_test/screenshots/profile/profile-page.assertions.json", "integration_test/profile_page_test.dart"} {
		t.Run(p, func(t *testing.T) {
			root := t.TempDir()
			copyUIFixture(t, root, "host-runtime")
			got := collectUIRoot(t, root)
			if e := uiVerifyPublication(t, got.Snapshot); e != nil {
				t.Fatal(e)
			}
			before := got.Snapshot.ID()
			b, e := os.ReadFile(filepath.Join(root, p))
			if e != nil {
				t.Fatal(e)
			}
			if e = os.WriteFile(filepath.Join(root, p), append(b, '!'), 0644); e != nil {
				t.Fatal(e)
			}
			if e = uiVerifyPublication(t, got.Snapshot); e == nil {
				t.Fatal("发布前接受漂移: " + p)
			}
			next := collectUIRoot(t, root)
			if next.Snapshot.ID() == before {
				t.Fatal("同路径正文变化未进入最终身份")
			}
		})
	}
}

// manifest 可来自固定基线或规格反例；Valid 仅代表该 manifest 的预期。
// 候选 Go 不加载解释器，也不把规格预期冒称为 Python 实算结果。
func TestUIFixedOracleGeneratedCases(t *testing.T) {
	manifest := os.Getenv("AI_DELIVERY_UI_ORACLE_MANIFEST")
	if manifest == "" {
		t.Skip("仅开发期固定基线差分")
	}
	b, e := os.ReadFile(manifest)
	if e != nil {
		t.Fatal(e)
	}
	var cases []struct {
		Name, Root string
		Valid      bool
	}
	if e = json.Unmarshal(b, &cases); e != nil {
		t.Fatal(e)
	}
	for _, tc := range cases {
		t.Run(tc.Name, func(t *testing.T) {
			got := collectUIRoot(t, tc.Root)
			valid := true
			for _, o := range got.Observations {
				valid = valid && o.Result == "passed"
			}
			if valid != tc.Valid {
				for _, o := range got.Observations {
					t.Logf("%s: %s", o.CheckID, o.Details)
				}
				t.Fatalf("Go=%v manifest预期=%v", valid, tc.Valid)
			}
		})
	}
}

func uiVerifyPublication(t *testing.T, s model.Snapshot) error {
	t.Helper()
	f, e := os.CreateTemp(filepath.Join(s.Workspace().DeliveryRoot, "requirements/REQ-UI"), ".ai-delivery-write-")
	if e != nil {
		t.Fatal(e)
	}
	p := f.Name()
	if e = f.Close(); e != nil {
		t.Fatal(e)
	}
	defer os.Remove(p)
	return (workspace.Reader{}).VerifyPublication(context.Background(), s, p)
}

func TestUIMotionPathsAndPreviewMasquerade(t *testing.T) {
	for _, kind := range []string{"normalized", "uppercase-preview"} {
		t.Run(kind, func(t *testing.T) {
			root := t.TempDir()
			copyUIFixture(t, root, "component-only")
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			m := uiMap(uiUnit(index)["motion_decision"])
			row := uiMap(uiList(acceptance["motion_acceptance"])[0])
			e := uiMap(uiList(row["evidence"])[0])
			if kind == "normalized" {
				m["preview_path"] = "./" + uiString(m["preview_path"])
				e["path"] = m["preview_path"]
			} else {
				m["decision"] = "static"
				m["verification_mode"] = "not_applicable"
				delete(m, "preview_path")
				delete(m, "preview_sha256")
				b, err := os.ReadFile(filepath.Join(root, "test/goldens/profile-card-default.png"))
				if err != nil {
					t.Fatal(err)
				}
				if err = os.WriteFile(filepath.Join(root, "test/goldens/STATIC.PNG"), b, 0644); err != nil {
					t.Fatal(err)
				}
				e["kind"] = "test"
				e["path"] = "test/goldens/STATIC.PNG"
				e["sha256"] = uiHashFile(t, root, "test/goldens/STATIC.PNG")
			}
			uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
			acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
			got := collectUIRoot(t, root)
			valid := true
			for _, o := range got.Observations {
				valid = valid && o.Result == "passed"
			}
			if valid != (kind == "normalized") {
				t.Fatalf("%s valid=%v", kind, valid)
			}
		})
	}
}

func TestUIEvidenceBoundaryHardening(t *testing.T) {
	export := os.Getenv("AI_DELIVERY_UI_HARDENING")
	results := []map[string]any{}
	for _, kind := range []string{"valid-gif", "invalid-gif-payload", "internal-root-alias", "escaping-root-alias"} {
		t.Run(kind, func(t *testing.T) {
			root := t.TempDir()
			if export != "" {
				root = filepath.Join(export, kind)
			}
			copyUIFixture(t, root, "host-runtime")
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			if kind == "invalid-gif-payload" {
				m := uiMap(uiUnit(index)["motion_decision"])
				p := uiString(m["preview_path"])
				b, e := os.ReadFile(filepath.Join(root, p))
				if e != nil {
					t.Fatal(e)
				}
				if len(b) != 107 || b[62] != 8 {
					t.Fatal("固定 GIF 夹具已变更")
				}
				b[62] = 255
				if e = os.WriteFile(filepath.Join(root, p), b, 0644); e != nil {
					t.Fatal(e)
				}
				m["preview_sha256"] = uiHashFile(t, root, p)
				uiMap(m["confirmation"])["reviewed_preview_sha256"] = m["preview_sha256"]
				uiMap(uiList(uiMap(uiList(acceptance["motion_acceptance"])[0])["evidence"])[0])["sha256"] = m["preview_sha256"]
			}
			if strings.HasSuffix(kind, "root-alias") {
				e := uiMap(uiList(uiMap(uiList(acceptance["scenarios"])[0])["evidence"])[0])
				original := filepath.Join(root, uiString(e["path"]))
				alias := filepath.Join(filepath.Dir(original), "alias.png")
				target := original
				if kind == "escaping-root-alias" {
					target = filepath.Join(root, "outside-indexed-root.png")
					b, err := os.ReadFile(original)
					if err != nil {
						t.Fatal(err)
					}
					if err = os.WriteFile(target, b, 0644); err != nil {
						t.Fatal(err)
					}
				}
				relative, err := filepath.Rel(filepath.Dir(alias), target)
				if err != nil {
					t.Fatal(err)
				}
				if err = os.Symlink(relative, alias); err != nil {
					t.Fatal(err)
				}
				relative, err = filepath.Rel(root, alias)
				if err != nil {
					t.Fatal(err)
				}
				e["path"] = filepath.ToSlash(relative)
			}
			uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
			acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
			got := collectUIRoot(t, root)
			valid := true
			for _, o := range got.Observations {
				valid = valid && o.Result == "passed"
			}
			want := kind == "valid-gif" || kind == "internal-root-alias"
			if valid != want {
				for _, o := range got.Observations {
					t.Logf("%s: %s", o.CheckID, o.Details)
				}
				t.Fatalf("valid=%v want=%v", valid, want)
			}
			results = append(results, map[string]any{"name": kind, "root": root, "go_valid": valid, "baseline_expected_valid": true})
		})
	}
	if export != "" {
		b, _ := json.MarshalIndent(results, "", "  ")
		if e := os.WriteFile(filepath.Join(export, "go-results.json"), b, 0644); e != nil {
			t.Fatal(e)
		}
	}
}

func TestUITimestampCurrentFormatAndBaselineDifference(t *testing.T) {
	export := os.Getenv("AI_DELIVERY_UI_TIMESTAMPS")
	results := []map[string]any{}
	for _, tc := range []struct {
		name, value string
		valid       bool
	}{{"rfc3339-offset", "2026-11-05T12:00:00+08:00", true}, {"rfc3339-z", "2026-11-05T04:00:00Z", true}, {"space-separated", "2026-11-05 12:00:00+08:00", false}, {"reduced-seconds", "2026-11-05T12:00+08:00", false}} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			if export != "" {
				root = filepath.Join(export, tc.name)
			}
			copyUIFixture(t, root, "component-only")
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			uiMap(index["design_source"])["captured_at"] = tc.value
			uiMap(uiScenario(index)["confirmation"])["confirmed_at"] = tc.value
			uiMap(uiMap(uiUnit(index)["motion_decision"])["confirmation"])["confirmed_at"] = tc.value
			acceptance["generated_at"] = tc.value
			uiMap(uiList(uiMap(uiList(acceptance["scenarios"])[0])["evidence"])[1])["reviewed_at"] = tc.value
			uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
			acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
			before := uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
			got := collectUIRoot(t, root)
			valid := true
			for _, o := range got.Observations {
				valid = valid && o.Result == "passed"
				if !tc.valid && (!strings.Contains(string(o.Details), "RFC3339") || !strings.Contains(string(o.Details), "2026-11-05T12:00:00+08:00")) {
					t.Errorf("缺少目标格式与示例: %s", o.Details)
				}
			}
			if valid != tc.valid {
				t.Fatalf("Go valid=%v want=%v", valid, tc.valid)
			}
			if uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json") != before {
				t.Fatal("check 自动转换了原始时间值")
			}
			results = append(results, map[string]any{"name": tc.name, "root": root, "go_valid": valid, "original_timestamp": tc.value})
		})
	}
	if export != "" {
		b, _ := json.MarshalIndent(results, "", "  ")
		if e := os.WriteFile(filepath.Join(export, "go-results.json"), b, 0644); e != nil {
			t.Fatal(e)
		}
	}
}

func TestUINativeReportRemainsOpaqueToUIReferenceParser(t *testing.T) {
	root := t.TempDir()
	copyUIFixture(t, root, "host-runtime")
	acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
	e := uiMap(uiList(uiMap(uiList(acceptance["scenarios"])[0])["evidence"])[0])
	report := uiString(e["assertion_report_path"])
	// 宿主自有schema并不是UI index，不应解释其同名字段为治理引用。
	if err := os.WriteFile(filepath.Join(root, report), []byte(`{"schema_version":1,"units":[{"component_path":"../../not-a-ui-reference"}],"passed":["profile-card-visible"]}`), 0644); err != nil {
		t.Fatal(err)
	}
	e["assertion_report_sha256"] = uiHashFile(t, root, report)
	uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
	got := collectUIRoot(t, root)
	for _, o := range got.Observations {
		if o.Result != "passed" {
			t.Fatalf("宿主报告被误当UI协议 %s", o.Details)
		}
	}
}

func TestUICanonicalDependencyAlreadyReferencedAsEvidence(t *testing.T) {
	root := t.TempDir()
	copyUIFixture(t, root, "host-runtime")
	parentSlice := strings.Replace(uiSlice, "SR-001", "SR-002", 1)
	for _, name := range []string{"contracts/ui-truth-index.json", "visual-acceptance.json", "design.md", "verification.md"} {
		b, e := os.ReadFile(filepath.Join(root, uiSlice+name))
		if e != nil {
			t.Fatal(e)
		}
		p := filepath.Join(root, parentSlice+name)
		if e = os.MkdirAll(filepath.Dir(p), 0755); e != nil {
			t.Fatal(e)
		}
		if e = os.WriteFile(p, b, 0644); e != nil {
			t.Fatal(e)
		}
	}
	status := uiReadJSON(t, root, ".ai-delivery/requirements/REQ-UI/status.json")
	entries := uiMap(status["sub_requirements"])
	parent := uiMap(entries["SR-001"])
	entries["SR-002"] = parent
	child := map[string]any{}
	for k, v := range parent {
		child[k] = v
	}
	child["status"] = "in_dev"
	child["ui_truth_mode"] = "none"
	child["ui_bearing"] = false
	entries["SR-001"] = child
	uiWriteJSON(t, root, ".ai-delivery/requirements/REQ-UI/status.json", status)
	for _, name := range []string{"contracts/ui-truth-index.json", "visual-acceptance.json"} {
		if e := os.Remove(filepath.Join(root, uiSlice+name)); e != nil {
			t.Fatal(e)
		}
	}
	parentVerification, _ := os.ReadFile(filepath.Join(root, parentSlice+"verification.md"))
	data, e := ParseBlock(parentVerification, VerificationStart, VerificationEnd)
	if e != nil {
		t.Fatal(e)
	}
	data["subreq_id"] = "SR-002"
	uiMap(uiList(data["inputs"])[0])["path"] = parentSlice + "design.md"
	inputHash, e := protocol.CanonicalSHA256(data["inputs"])
	if e != nil {
		t.Fatal(e)
	}
	reviewHash, e := protocol.ReviewDigest(data)
	if e != nil {
		t.Fatal(e)
	}
	review := uiMap(uiList(data["reviews"])[0])
	review["input_sha256"] = inputHash
	review["verification_sha256"] = reviewHash
	b, _ := json.Marshal(data)
	body := "<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->\n" + VerificationStart + "\n```json\n" + string(b) + "\n```\n" + VerificationEnd
	if e = os.WriteFile(filepath.Join(root, parentSlice+"verification.md"), []byte(body), 0644); e != nil {
		t.Fatal(e)
	}
	childVerification, _ := os.ReadFile(filepath.Join(root, uiSlice+"verification.md"))
	data, e = ParseBlock(childVerification, VerificationStart, VerificationEnd)
	if e != nil {
		t.Fatal(e)
	}
	data["inputs"] = append(uiList(data["inputs"]), map[string]any{"path": parentSlice + "contracts/ui-truth-index.json", "sha256": uiHashFile(t, root, parentSlice+"contracts/ui-truth-index.json")})
	b, _ = json.Marshal(data)
	if e = os.WriteFile(filepath.Join(root, uiSlice+"verification.md"), []byte(VerificationStart+"\n```json\n"+string(b)+"\n```\n"+VerificationEnd), 0644); e != nil {
		t.Fatal(e)
	}
	graph := ".ai-delivery/requirements/REQ-UI/dependency-graph.json"
	uiWriteJSON(t, root, graph, map[string]any{"nodes": map[string]any{"SR-001": map[string]any{"depends_on": []any{"SR-002"}}, "SR-002": map[string]any{"depends_on": []any{}}}})
	s, e := (workspace.Reader{}).Load(context.Background(), model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}, model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
	if e != nil {
		t.Fatal(e)
	}
	got, e := (Reader{}).Collect(context.Background(), s, []model.CheckSpec{{ID: "dependencies", InputPaths: []string{graph, uiSlice + "verification.md"}}})
	if e != nil {
		t.Fatal(e)
	}
	if got.Observations[0].Result != "passed" {
		t.Fatalf("已读取文件被确认为canonical上游后仍未展开引用: %s", got.Observations[0].Details)
	}
	// 活跃上游设计即便评审和 verification 摘要均已更新，也须引用真实 scenario_id。
	designPath := parentSlice + "design.md"
	original, err := os.ReadFile(filepath.Join(root, designPath))
	if err != nil {
		t.Fatal(err)
	}
	changed := strings.ReplaceAll(string(original), "default-phone", "default-phone-extra")
	if err = os.WriteFile(filepath.Join(root, designPath), []byte(changed), 0644); err != nil {
		t.Fatal(err)
	}
	parent["design_review"] = reviewedEntry(changed)["design_review"]
	uiWriteJSON(t, root, ".ai-delivery/requirements/REQ-UI/status.json", status)
	parentRaw, err := os.ReadFile(filepath.Join(root, parentSlice+"verification.md"))
	if err != nil {
		t.Fatal(err)
	}
	parentData, err := ParseBlock(parentRaw, VerificationStart, VerificationEnd)
	if err != nil {
		t.Fatal(err)
	}
	for _, input := range uiList(parentData["inputs"]) {
		if uiMap(input)["path"] == designPath {
			uiMap(input)["sha256"] = uiHashFile(t, root, designPath)
		}
	}
	review = uiMap(uiList(parentData["reviews"])[0])
	review["input_sha256"], _ = protocol.InputDigest(uiList(parentData["inputs"]))
	review["verification_sha256"], _ = protocol.ReviewDigest(parentData)
	bytes, err := json.Marshal(parentData)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(root, parentSlice+"verification.md"), []byte(VerificationStart+"\n```json\n"+string(bytes)+"\n```\n"+VerificationEnd), 0644); err != nil {
		t.Fatal(err)
	}
	s, err = (workspace.Reader{}).Load(context.Background(), model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}, model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
	if err != nil {
		t.Fatal(err)
	}
	got, err = (Reader{}).Collect(context.Background(), s, []model.CheckSpec{{ID: "dependencies", InputPaths: []string{graph}}})
	if err != nil {
		t.Fatal(err)
	}
	if got.Observations[0].Result != "invalid" || !strings.Contains(string(got.Observations[0].Details), "scenario_id") {
		t.Fatalf("活跃上游漏检场景引用: %s", got.Observations[0].Details)
	}
}
