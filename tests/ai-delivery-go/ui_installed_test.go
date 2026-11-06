package aideliverygo_test

import (
	"encoding/json"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
)

// 使用固定协议夹具测试安装后路由；夹具批准/评审不代表真实产品验收。
func TestInstalledUIWorkflowWithoutPythonOrSDK(t *testing.T) {
	_, file, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "../.."))
	binary := filepath.Join(t.TempDir(), "ai-delivery")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	cmd := exec.Command("go", "build", "-o", binary, "./cmd/ai-delivery")
	cmd.Dir = repo
	cmd.Env = append(os.Environ(), "CGO_ENABLED=0")
	if b, e := cmd.CombinedOutput(); e != nil {
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
			if e := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root, ProjectID: "ui-protocol-fixture"}); e != nil {
				t.Fatal(e)
			}
			source := filepath.Join(repo, "tests/migration-oracle/fixtures", fixture)
			e := filepath.WalkDir(source, func(p string, d fs.DirEntry, e error) error {
				if e != nil {
					return e
				}
				rel, _ := filepath.Rel(source, p)
				if rel == ".ai-delivery/meta" {
					return filepath.SkipDir
				}
				target := filepath.Join(root, rel)
				if d.IsDir() {
					return os.MkdirAll(target, 0755)
				}
				b, e := os.ReadFile(p)
				if e != nil {
					return e
				}
				return os.WriteFile(target, b, 0644)
			})
			if e != nil {
				t.Fatal(e)
			}
			statusPath := filepath.Join(root, ".ai-delivery/requirements/REQ-UI/status.json")
			b, e := os.ReadFile(statusPath)
			if e != nil {
				t.Fatal(e)
			}
			var status map[string]any
			if e = json.Unmarshal(b, &status); e != nil {
				t.Fatal(e)
			}
			entry := status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)
			entry["status"] = "split_ready"
			b, _ = json.Marshal(status)
			if e = os.WriteFile(statusPath, b, 0644); e != nil {
				t.Fatal(e)
			}
			for p, body := range map[string]string{".ai-delivery/requirements/REQ-UI/requirement.md": "协议夹具原始需求", ".ai-delivery/requirements/REQ-UI/sub-requirements/SR-001/requirement-slice.md": "协议夹具切片需求"} {
				if e = os.WriteFile(filepath.Join(root, p), []byte(body), 0644); e != nil {
					t.Fatal(e)
				}
			}
			invoke := func(want int, args ...string) map[string]any {
				t.Helper()
				cmd := exec.Command(binary, append(args, "--project", root, "--req", "REQ-UI", "--subreq", "SR-001")...)
				cmd.Env = env
				b, e := cmd.CombinedOutput()
				code := 0
				if e != nil {
					exit, ok := e.(*exec.ExitError)
					if !ok {
						t.Fatal(e)
					}
					code = exit.ExitCode()
				}
				if code != want {
					t.Fatalf("code=%d want=%d: %s", code, want, b)
				}
				var result map[string]any
				if e = json.Unmarshal(b, &result); e != nil {
					t.Fatal(e, string(b))
				}
				return result
			}
			for _, step := range [][2]string{{"ui", "acceptance_frozen"}, {"design", "design_ready"}, {"implement", "in_dev"}, {"verify", "visual_acceptance_passed"}, {"merge", "merged"}} {
				check := invoke(0, "check", "--intent", step[0], "--to", step[1])
				id := check["snapshot_id"].(string)
				if step[0] == "implement" {
					p := filepath.Join(root, "test/goldens/profile-card-default.png")
					original, e := os.ReadFile(p)
					if e != nil {
						t.Fatal(e)
					}
					before, e := os.ReadFile(statusPath)
					if e != nil {
						t.Fatal(e)
					}
					if e = os.WriteFile(p, append(append([]byte{}, original...), '!'), 0644); e != nil {
						t.Fatal(e)
					}
					invoke(2, "advance", "--to", step[1], "--expected-snapshot", id)
					after, e := os.ReadFile(statusPath)
					if e != nil || string(before) != string(after) {
						t.Fatal("漂移拒绝修改了 status", e)
					}
					if e = os.WriteFile(p, original, 0644); e != nil {
						t.Fatal(e)
					}
				}
				result := invoke(0, "advance", "--to", step[1], "--expected-snapshot", id)
				if result["allowed"] != true {
					t.Fatal(result)
				}
			}
			b, e = os.ReadFile(statusPath)
			if e != nil {
				t.Fatal(e)
			}
			if e = json.Unmarshal(b, &status); e != nil {
				t.Fatal(e)
			}
			if status["sub_requirements"].(map[string]any)["SR-001"].(map[string]any)["status"] != "merged" {
				t.Fatal("没有完成 Go UI loop")
			}
		})
	}
}
