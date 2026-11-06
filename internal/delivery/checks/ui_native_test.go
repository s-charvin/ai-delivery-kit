package checks

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"image/gif"
	"image/png"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// 只消费已经实际跑出的官方宿主输出。人工批准字段属于协议测试夹具，
// 不能将本测试成功宣称为设备/Figma/用户视觉验收。
func TestUIAndroidNativeEvidenceBinding(t *testing.T) {
	original := os.Getenv("AI_DELIVERY_ANDROID_EVIDENCE")
	if original == "" {
		t.Skip("需要已运行的 Android 官方栈原始输出")
	}
	root := t.TempDir()
	copyUIFixture(t, root, "component-only")
	files := []string{"app/src/main/java/dev/delivery/viewfixture/SampleFragment.kt", "app/src/main/java/dev/delivery/viewfixture/SampleActivity.kt", "app/src/main/res/layout/sample_fragment.xml", "app/src/test/java/dev/delivery/viewfixture/ViewCaptureTest.kt", "app/build/outputs/android-view/static-0.png", "app/build/outputs/android-view/static-1.png", "app/build/outputs/android-view/motion-0.gif", "app/build/outputs/android-view/motion-1.gif", "app/build/test-results/testDebugUnitTest/TEST-dev.delivery.viewfixture.ViewCaptureTest.xml"}
	files = append(files, "app/src/main/java/dev/delivery/viewfixture/SampleViewModel.kt", "app/src/main/java/dev/delivery/viewfixture/LegacyLabel.java", "app/src/main/AndroidManifest.xml", "app/src/main/res/values/strings.xml", "app/src/main/res/values/styles.xml", "app/src/main/res/layout/label_row.xml", "app/src/main/res/drawable/marker.xml")
	for _, p := range files {
		b, e := os.ReadFile(filepath.Join(original, p))
		if e != nil {
			t.Fatal(e)
		}
		if e = os.MkdirAll(filepath.Dir(filepath.Join(root, p)), 0755); e != nil {
			t.Fatal(e)
		}
		if e = os.WriteFile(filepath.Join(root, p), b, 0644); e != nil {
			t.Fatal(e)
		}
	}
	imagePath := "app/build/outputs/android-view/static-0.png"
	motionPath := "app/build/outputs/android-view/motion-0.gif"
	reportPath := "app/build/test-results/testDebugUnitTest/TEST-dev.delivery.viewfixture.ViewCaptureTest.xml"
	testPath := "app/src/test/java/dev/delivery/viewfixture/ViewCaptureTest.kt"
	if uiHashFile(t, root, imagePath) != "169a7a86ae956ffad70a4de95583750fdab90d5514d83e7d8d6bd191830f17ca" || uiHashFile(t, root, motionPath) != "2034f71f0d96e37a36e350337e1d231408e2f1991a8a656fbdea8829dbbc732e" || uiHashFile(t, root, reportPath) != "0d47c4c8f47524b9ed7aae2fd94f15fe14f1313c3ed4a1766e57423e0ed45de7" {
		t.Fatal("与控制者实际 Android 运行身份不一致；先审查新运行来源")
	}
	if uiHashFile(t, root, imagePath) != uiHashFile(t, root, "app/build/outputs/android-view/static-1.png") || uiHashFile(t, root, motionPath) != uiHashFile(t, root, "app/build/outputs/android-view/motion-1.gif") {
		t.Fatal("重复采集不确定")
	}
	b, _ := os.ReadFile(filepath.Join(root, motionPath))
	animation, e := gif.DecodeAll(bytes.NewReader(b))
	if e != nil || len(animation.Image) != 11 {
		t.Fatal("真实 GIF 帧数无效", e)
	}
	duration := 0
	for _, delay := range animation.Delay {
		duration += delay * 10
	}
	if duration != 480 {
		t.Fatalf("GIF 时长 %d != 480ms", duration)
	}
	b, _ = os.ReadFile(filepath.Join(root, imagePath))
	image, e := png.DecodeConfig(bytes.NewReader(b))
	if e != nil || image.Width <= 0 || image.Height <= 0 {
		t.Fatal("实际 PNG 无效", e)
	}
	var report struct {
		Tests    int `xml:"tests,attr"`
		Failures int `xml:"failures,attr"`
		Errors   int `xml:"errors,attr"`
		Skipped  int `xml:"skipped,attr"`
		Cases    []struct {
			Name string `xml:"name,attr"`
		} `xml:"testcase"`
	}
	b, _ = os.ReadFile(filepath.Join(root, reportPath))
	if e = xml.Unmarshal(b, &report); e != nil || report.Tests != 7 || report.Failures != 0 || report.Errors != 0 || report.Skipped != 0 {
		t.Fatal("实际宿主报告未通过", e)
	}
	names := map[string]bool{}
	for _, c := range report.Cases {
		names[c.Name] = true
	}
	for _, name := range []string{"capturesRealAnimationAt25FpsAndCanRepeat", "failureRemovesOldAndPartialOutput", "unmountedViewCannotLeaveStaleEvidence", "nonGridEndpointIsCapturedAndReportsGifQuantization", "encoderIoFailureNeverPublishesEvidenceAndNextCaptureWorks"} {
		if !names[name] {
			t.Fatal("缺少实际原生测试", name)
		}
	}
	index := uiReadJSON(t, root, uiSlice+"contracts/ui-truth-index.json")
	u := uiUnit(index)
	u["stack"] = "android-view"
	u["component_path"] = files[0]
	u["component_sha256"] = uiHashFile(t, root, files[0])
	u["golden_test"] = testPath
	u["golden_test_sha256"] = uiHashFile(t, root, testPath)
	inputs := []any{}
	for _, p := range files {
		if strings.HasPrefix(p, "app/src/main/") {
			inputs = append(inputs, map[string]any{"path": p, "sha256": uiHashFile(t, root, p)})
		}
	}
	u["render_inputs"] = inputs
	scenario := uiScenario(index)
	scenario["preview_path"] = imagePath
	scenario["preview_sha256"] = uiHashFile(t, root, imagePath)
	uiMap(scenario["confirmation"])["reviewed_preview_sha256"] = scenario["preview_sha256"]
	motion := uiMap(u["motion_decision"])
	motion["preview_path"] = motionPath
	motion["preview_sha256"] = uiHashFile(t, root, motionPath)
	uiMap(motion["confirmation"])["reviewed_preview_sha256"] = motion["preview_sha256"]
	uiWriteJSON(t, root, uiSlice+"contracts/ui-truth-index.json", index)
	acceptance := uiReadJSON(t, root, uiSlice+"visual-acceptance.json")
	acceptance["ui_truth_index_sha256"] = uiHashFile(t, root, uiSlice+"contracts/ui-truth-index.json")
	row := uiMap(uiList(acceptance["scenarios"])[0])
	row["evidence"] = []any{map[string]any{"kind": "preview", "path": imagePath, "sha256": scenario["preview_sha256"], "command": "bash scripts/test-android-view.sh", "summary": "既有原生输出绑定；协议夹具不代表人工视觉确认"}, map[string]any{"kind": "test", "path": reportPath, "sha256": uiHashFile(t, root, reportPath), "command": "bash scripts/test-android-view.sh", "summary": "真实 7 项 capture 测试报告"}}
	mr := uiMap(uiList(acceptance["motion_acceptance"])[0])
	mr["evidence"] = []any{map[string]any{"kind": "motion", "path": motionPath, "sha256": motion["preview_sha256"], "command": "bash scripts/test-android-view.sh", "summary": "真实 11 帧 480ms GIF"}}
	uiWriteJSON(t, root, uiSlice+"visual-acceptance.json", acceptance)
	got := collectUIRoot(t, root)
	for _, o := range got.Observations {
		if o.Result != "passed" {
			t.Fatalf("%s: %s", o.CheckID, o.Details)
		}
	}
	resource := files[2]
	if _, ok := got.Snapshot.Document(resource); !ok {
		t.Fatal("真实 XML 资源未登记")
	}
	if e = os.WriteFile(filepath.Join(root, resource), []byte("变更资源"), 0644); e != nil {
		t.Fatal(e)
	}
	if uiVerifyPublication(t, got.Snapshot) == nil {
		t.Fatal("XML 资源漂移被接受")
	}
	if output := os.Getenv("AI_DELIVERY_ANDROID_BINDING_REPORT"); output != "" {
		r := map[string]any{"source_root": original, "png_absolute_path": filepath.Join(original, imagePath), "gif_absolute_path": filepath.Join(original, motionPath), "native_report_absolute_path": filepath.Join(original, reportPath), "png_width": image.Width, "png_height": image.Height, "gif_frames": len(animation.Image), "gif_duration_ms": duration, "native_tests": report.Tests, "scope": "component-only", "limits": "协议夹具确认，不是人工视觉、设备或 Figma 验收；未自动判断任意 wrong-state/region 画面语义"}
		hashes := map[string]string{}
		for _, p := range files {
			hashes[filepath.Join(original, p)] = uiHashFile(t, original, p)
		}
		r["source_sha256"] = hashes
		b, _ := json.MarshalIndent(r, "", "  ")
		if e = os.WriteFile(output, b, 0644); e != nil {
			t.Fatal(e)
		}
	}
}
