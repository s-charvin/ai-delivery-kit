package checks

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func persistUIReviewFixture(t *testing.T, root string, index, acceptance map[string]any) {
	t.Helper()
	uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
	acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
	uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
}
func requireUIReviewResult(t *testing.T, root string, want bool) {
	t.Helper()
	got := collectUIRoot(t, root)
	valid := true
	for _, o := range got.Observations {
		valid = valid && o.Result == "passed"
	}
	if valid != want {
		for _, o := range got.Observations {
			t.Logf("%s: %s", o.CheckID, o.Details)
		}
		t.Fatalf("实际valid=%v，规格预期=%v", valid, want)
	}
}
func TestUICapturePathsUseSharedNormalization(t *testing.T) {
	for _, name := range []string{"capture-dot", "root-dot", "capture-redundant-separator", "root-redundant-separator", "both-dot-separators", "lexical-outside"} {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			copyUIFixture(t, root, "host-runtime")
			index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
			acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
			binding := uiMap(uiScenario(index)["host_binding"])
			e := uiMap(uiList(uiMap(uiList(acceptance["scenarios"])[0])["evidence"])[0])
			switch name {
			case "capture-dot":
				e["path"] = "./" + uiString(e["path"])
			case "root-dot":
				binding["evidence_root"] = "./" + uiString(binding["evidence_root"])
			case "capture-redundant-separator":
				e["path"] = strings.ReplaceAll(uiString(e["path"]), "/", "//")
			case "root-redundant-separator":
				binding["evidence_root"] = strings.ReplaceAll(uiString(binding["evidence_root"]), "/", "//") + "/./"
			case "both-dot-separators":
				e["path"] = "./" + strings.ReplaceAll(uiString(e["path"]), "/", "//")
				binding["evidence_root"] = "./" + uiString(binding["evidence_root"]) + "/./"
			case "lexical-outside":
				b, err := os.ReadFile(filepath.Join(root, uiString(e["path"])))
				if err != nil {
					t.Fatal(err)
				}
				p := "integration_test/screenshots/profile-other/capture.png"
				if err = os.MkdirAll(filepath.Dir(filepath.Join(root, p)), 0755); err != nil {
					t.Fatal(err)
				}
				if err = os.WriteFile(filepath.Join(root, p), b, 0644); err != nil {
					t.Fatal(err)
				}
				e["path"] = p
			}
			persistUIReviewFixture(t, root, index, acceptance)
			requireUIReviewResult(t, root, name != "lexical-outside")
		})
	}
}
func motionReportFixture(t *testing.T, decision string) (string, map[string]any, map[string]any) {
	t.Helper()
	root := t.TempDir()
	copyUIFixture(t, root, "component-only")
	index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
	acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
	m := uiMap(uiUnit(index)["motion_decision"])
	delete(m, "preview_path")
	delete(m, "preview_sha256")
	m["decision"] = decision
	if decision == "static" {
		m["verification_mode"] = "not_applicable"
	} else {
		m["verification_mode"] = "runtime"
		m["preview_unavailable_reason"] = "协议测试：需以原生运行报告验证动效"
	}
	return root, index, acceptance
}
func bindMotionTestReport(t *testing.T, root, p string, index, acceptance map[string]any) {
	t.Helper()
	uiMap(uiList(acceptance["motion_acceptance"])[0])["evidence"] = []any{map[string]any{"kind": "test", "path": p, "sha256": uiHashFile(t, root, p), "command": "native-test", "summary": "验证已登记运行报告；不代表人工视觉批准"}}
	persistUIReviewFixture(t, root, index, acceptance)
}
func TestUIMotionReportRejectsPreviewAliasesAndCopies(t *testing.T) {
	for _, decision := range []string{"static", "animated"} {
		for _, kind := range []string{"direct-png", "png-alias", "png-copy", "normalized-png-copy", "preview-alias-png-copy", "fixture-report-alias", "fixture-report-copy"} {
			t.Run(decision+"/"+kind, func(t *testing.T) {
				root, index, acceptance := motionReportFixture(t, decision)
				image := "test/goldens/profile-card-default.png"
				report := "test/goldens/report.log"
				source := image
				want := strings.HasPrefix(kind, "fixture-report")
				if want {
					source = "native.log"
				}
				if kind == "direct-png" {
					report = image
				} else if strings.HasSuffix(kind, "alias") {
					relative, err := filepath.Rel(filepath.Dir(filepath.Join(root, report)), filepath.Join(root, source))
					if err != nil {
						t.Fatal(err)
					}
					if err = os.Symlink(relative, filepath.Join(root, report)); err != nil {
						t.Fatal(err)
					}
				} else {
					b, err := os.ReadFile(filepath.Join(root, source))
					if err != nil {
						t.Fatal(err)
					}
					if err = os.WriteFile(filepath.Join(root, report), b, 0644); err != nil {
						t.Fatal(err)
					}
				}
				if kind == "normalized-png-copy" {
					report = "./test//goldens/report.log"
				}
				if kind == "preview-alias-png-copy" {
					alias := "test/goldens/preview.log"
					if err := os.Symlink("profile-card-default.png", filepath.Join(root, alias)); err != nil {
						t.Fatal(err)
					}
					uiScenario(index)["preview_path"] = alias
					uiMap(uiList(uiMap(uiList(acceptance["scenarios"])[0])["evidence"])[0])["path"] = alias
				}
				bindMotionTestReport(t, root, report, index, acceptance)
				requireUIReviewResult(t, root, want)
			})
		}
	}
}
func TestUIMotionActualNativeReportAliasRemainsValid(t *testing.T) {
	native := os.Getenv("AI_DELIVERY_ANDROID_EVIDENCE")
	if native == "" {
		t.Skip("需要已有原生XML报告")
	}
	source := "app/build/test-results/testDebugUnitTest/TEST-dev.delivery.viewfixture.ViewCaptureTest.xml"
	if uiHashFile(t, native, source) != "0d47c4c8f47524b9ed7aae2fd94f15fe14f1313c3ed4a1766e57423e0ed45de7" {
		t.Fatal("原native报告身份已变")
	}
	for _, decision := range []string{"static", "animated"} {
		t.Run(decision, func(t *testing.T) {
			root, index, acceptance := motionReportFixture(t, decision)
			b, err := os.ReadFile(filepath.Join(native, source))
			if err != nil {
				t.Fatal(err)
			}
			if err = os.WriteFile(filepath.Join(root, "capture-report.xml"), b, 0644); err != nil {
				t.Fatal(err)
			}
			if err = os.Symlink("capture-report.xml", filepath.Join(root, "report.log")); err != nil {
				t.Fatal(err)
			}
			bindMotionTestReport(t, root, "./report.log", index, acceptance)
			requireUIReviewResult(t, root, true)
		})
	}
}
