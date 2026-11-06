package aideliverygo_test

import (
	"bytes"
	"encoding/json"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// UI 与人工确认字段只是协议夹具；不冒充真实用户 CP-ARCHIVE 或视觉验收。
func TestInstalledArchiveAndUIHistoryWithoutPythonOrSDK(t *testing.T) {
	_, file, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "../.."))
	binary := filepath.Join(t.TempDir(), "ai-delivery")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	build := exec.Command("go", "build", "-o", binary, "./cmd/ai-delivery")
	build.Dir = repo
	build.Env = append(os.Environ(), "CGO_ENABLED=0")
	if b, e := build.CombinedOutput(); e != nil {
		t.Fatal(string(b), e)
	}
	env := []string{}
	for _, v := range os.Environ() {
		if !strings.HasPrefix(v, "PATH=") && !strings.HasPrefix(v, "GIT_DIR=") && !strings.HasPrefix(v, "GIT_WORK_TREE=") {
			env = append(env, v)
		}
	}
	env = append(env, "PATH="+t.TempDir())
	for _, fixture := range []string{"component-only", "host-runtime"} {
		t.Run(fixture, func(t *testing.T) {
			root := t.TempDir()
			source := filepath.Join(repo, "tests/migration-oracle/fixtures", fixture)
			if err := filepath.WalkDir(source, func(p string, d fs.DirEntry, err error) error {
				if err != nil {
					return err
				}
				rel, _ := filepath.Rel(source, p)
				target := filepath.Join(root, rel)
				if d.IsDir() {
					return os.MkdirAll(target, 0755)
				}
				b, err := os.ReadFile(p)
				if err != nil {
					return err
				}
				return os.WriteFile(target, b, 0644)
			}); err != nil {
				t.Fatal(err)
			}
			init := exec.Command(binary, "init", "--upgrade", root)
			init.Env = env
			if out, err := init.CombinedOutput(); err != nil {
				t.Fatalf("实际 CLI 资源安装: %v %s", err, out)
			}
			for p, b := range map[string]string{
				".ai-delivery/requirements/REQ-UI/requirement.md":                               "协议夹具原始需求",
				".ai-delivery/requirements/REQ-UI/sub-requirements/SR-001/requirement-slice.md": "协议夹具切片需求",
				".ai-delivery/requirements/REQ-UI/retrospective.md":                             "<!-- ai-delivery-retrospective:reviewed-at:" + time.Now().UTC().Format("2006-01-02") + " -->\n",
				"report.md": "# <req-id>\n<archived_at>\n<subreq_count>\n<subreq_rows>\n",
			} {
				if err := os.WriteFile(filepath.Join(root, p), []byte(b), 0644); err != nil {
					t.Fatal(err)
				}
			}
			statusPath := filepath.Join(root, ".ai-delivery/requirements/REQ-UI/status.json")
			raw, _ := os.ReadFile(statusPath)
			var status map[string]any
			json.Unmarshal(raw, &status)
			status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["status"] = "merged"
			raw, _ = json.Marshal(status)
			os.WriteFile(statusPath, raw, 0644)
			invoke := func(want int, args ...string) map[string]any {
				t.Helper()
				cmd := exec.Command(binary, append(args, "--project", root, "--req", "REQ-UI", "--subreq", "SR-001")...)
				cmd.Env = env
				b, e := cmd.CombinedOutput()
				code := 0
				if e != nil {
					if exit, ok := e.(*exec.ExitError); ok {
						code = exit.ExitCode()
					} else {
						t.Fatal(e)
					}
				}
				if code != want {
					t.Fatalf("%v: code=%d want=%d %s", args, code, want, b)
				}
				var out map[string]any
				if e = json.Unmarshal(b, &out); e != nil {
					t.Fatal(e, string(b))
				}
				return out
			}
			// init 已创建合作锁；清理测试准备遗留，单独观察未确认 archive 是否创建锁。
			if err := os.Remove(filepath.Join(root, ".ai-delivery.lock")); err != nil {
				t.Fatal(err)
			}
			ledgerPath := filepath.Join(root, ".ai-delivery/requirements/REQ-UI/retrospective.md")
			originalLedger, err := os.ReadFile(ledgerPath)
			if err != nil {
				t.Fatal(err)
			}
			naiveLedger := []byte("<!-- ai-delivery-retrospective:reviewed-at:" + time.Now().UTC().Format("2006-01-02") + "T10:00:00 -->\n")
			if err = os.WriteFile(ledgerPath, naiveLedger, 0644); err != nil {
				t.Fatal(err)
			}
			rejected := invoke(2, "check", "--intent", "archive")
			rendered, _ := json.Marshal(rejected)
			if !bytes.Contains(rendered, []byte("YYYY-MM-DD")) || !bytes.Contains(rendered, []byte("RFC3339Nano")) || !bytes.Contains(rendered, []byte("retrospective.md")) {
				t.Fatalf("真实 CLI 未暴露复盘目标格式: %s", rendered)
			}
			afterRejected, err := os.ReadFile(ledgerPath)
			if err != nil || !bytes.Equal(afterRejected, naiveLedger) {
				t.Fatal("复盘时间被自动转换", err)
			}
			if err = os.WriteFile(ledgerPath, originalLedger, 0644); err != nil {
				t.Fatal(err)
			}
			checked := invoke(0, "check", "--intent", "archive")
			id := checked["snapshot_id"].(string)
			invoke(2, "archive", "--expected-snapshot", id, "--delivery-report-template", "report.md")
			if _, e := os.Stat(filepath.Join(root, ".ai-delivery.lock")); !os.IsNotExist(e) {
				t.Fatal("缺少确认仍写锁")
			}
			png := filepath.Join(root, "test/goldens/profile-card-default.png")
			original, _ := os.ReadFile(png)
			os.WriteFile(png, append(append([]byte{}, original...), '!'), 0644)
			invoke(2, "archive", "--confirm-archive", "--expected-snapshot", id, "--delivery-report-template", "report.md")
			current, _ := os.ReadFile(statusPath)
			if !bytes.Equal(current, raw) {
				t.Fatal("当前 UI 漂移仍写状态")
			}
			os.WriteFile(png, original, 0644)
			invoke(0, "archive", "--confirm-archive", "--expected-snapshot", id, "--delivery-report-template", "report.md")
			for _, p := range []string{"native.log", "test/goldens/profile-card-default.png", "test/motion/profile-card-default.gif", "integration_test/screenshots/profile/profile-page.assertions.json", "integration_test/screenshots/profile/profile-page.png"} {
				os.Remove(filepath.Join(root, p))
			}
			os.WriteFile(filepath.Join(root, "lib/profile_card.dart"), []byte("合法后续生产版本"), 0644)
			invoke(0, "check", "--intent", "archive")
			contract := filepath.Join(root, ".ai-delivery/requirements/REQ-UI/sub-requirements/SR-001/contracts/ui-truth-index.json")
			b, _ := os.ReadFile(contract)
			os.WriteFile(contract, append(b, '\n'), 0644)
			invoke(2, "check", "--intent", "archive")
		})
	}
}
