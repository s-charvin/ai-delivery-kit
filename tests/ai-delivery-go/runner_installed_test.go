package aideliverygo_test

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestInstalledRunUsesOnlyCompiledKitAndNativeHost(t *testing.T) {
	_, file, _, _ := runtime.Caller(0)
	repo := filepath.Clean(filepath.Join(filepath.Dir(file), "../.."))
	binDir := t.TempDir()
	binary := filepath.Join(binDir, "ai-delivery")
	helper := filepath.Join(binDir, "native helper")
	if runtime.GOOS == "windows" {
		binary += ".exe"
		helper += ".exe"
	}
	for _, build := range [][2]string{{binary, "./cmd/ai-delivery"}, {helper, "./internal/delivery/runner/testdata/native-helper"}} {
		cmd := exec.Command("go", "build", "-o", build[0], build[1])
		cmd.Dir = repo
		cmd.Env = append(os.Environ(), "CGO_ENABLED=0")
		if b, e := cmd.CombinedOutput(); e != nil {
			t.Fatal(string(b), e)
		}
	}
	env := []string{}
	for _, v := range os.Environ() {
		if !strings.HasPrefix(v, "PATH=") && !strings.HasPrefix(v, "GIT_DIR=") && !strings.HasPrefix(v, "GIT_WORK_TREE=") {
			env = append(env, v)
		}
	}
	env = append(env, "PATH="+t.TempDir())
	for _, mode := range []string{"pass", "interrupt"} {
		t.Run(mode, func(t *testing.T) {
			if mode == "interrupt" && runtime.GOOS == "windows" {
				t.Skip("Windows 的 os.Interrupt 发送需控制台；Job/子树由原生 runner 用例覆盖，不能用交叉构建代替")
			}
			root := filepath.Join(t.TempDir(), "真实项目 '$` 空格")
			os.MkdirAll(root, 0755)
			if e := (bootstrap.Engine{}).Run(bootstrap.Config{RepoRoot: root, ProjectID: "runner-host"}); e != nil {
				t.Fatal(e)
			}
			argv := []string{helper, "echo", "literal $HOME", `a"b`, "中文🙂"}
			var listener net.Listener
			if mode == "interrupt" {
				var e error
				listener, e = net.Listen("tcp", "127.0.0.1:0")
				if e != nil {
					t.Fatal(e)
				}
				defer listener.Close()
				argv = []string{helper, "tree", listener.Addr().String()}
			}
			methods, _ := json.Marshal(map[string]any{"version": 1, "checks": []any{map[string]any{"id": "host-check", "argv": argv, "cwd": ".", "parser_id": "exit-code", "input_paths": []string{"owner.txt"}, "source_refs": []string{"owner.txt"}, "report_paths": []string{}, "acceptance_ids": []string{"AC-001"}}}})
			design := "<!-- ai-delivery:behavior-contract:start -->\n<!-- ai-delivery:behavior-contract:scope -->\n范围\n<!-- ai-delivery:behavior-contract:behavior -->\nB-001 保存\n<!-- ai-delivery:behavior-contract:acceptance -->\nAC-001 保存成功\n<!-- ai-delivery:native-methods:v1 -->\n```json\n" + string(methods) + "\n```\n<!-- /ai-delivery:native-methods:v1 -->\n<!-- ai-delivery:behavior-contract:traceability -->\nB-001 AC-001\n<!-- ai-delivery:behavior-contract:end -->\n<!-- ai-delivery:user-decisions -->\n无需人工决定\n"
			status, _ := json.Marshal(map[string]any{"_schema": "2.0", "sub_requirements": map[string]any{"SR-001": map[string]any{"status": "in_dev", "ui_truth_mode": "none", "ui_bearing": false, "state_flow_required": false, "user_decision_required": false, "design_review": map[string]any{"review_mode": "self", "reviewed_by": "安装场景设计评审夹具", "reviewed_at": "2026-11-05T12:00:00+08:00", "reviewed_design_sha256": fmt.Sprintf("%x", sha256.Sum256([]byte(design)))}}}})
			for p, body := range map[string]string{"owner.txt": "同一宿主所有者", ".ai-delivery/requirements/R/status.json": string(status), ".ai-delivery/requirements/R/requirement.md": "原始需求", ".ai-delivery/requirements/R/sub-requirements/SR-001/requirement-slice.md": "切片需求", ".ai-delivery/requirements/R/sub-requirements/SR-001/design.md": design} {
				p = filepath.Join(root, p)
				os.MkdirAll(filepath.Dir(p), 0755)
				if e := os.WriteFile(p, []byte(body), 0644); e != nil {
					t.Fatal(e)
				}
			}
			args := append([]string{"run", "--project", root, "--req", "R", "--subreq", "SR-001", "--check", "host-check", "--timeout", "20", "--"}, argv...)
			cmd := exec.Command(binary, args...)
			cmd.Env = env
			var stdout, stderr bytes.Buffer
			cmd.Stdout = &stdout
			cmd.Stderr = &stderr
			if e := cmd.Start(); e != nil {
				t.Fatal(e)
			}
			if mode == "interrupt" {
				listener.(*net.TCPListener).SetDeadline(time.Now().Add(15 * time.Second))
				conn, e := listener.Accept()
				if e != nil {
					cmd.Process.Kill()
					t.Fatal(e)
				}
				defer conn.Close()
				if e = cmd.Process.Signal(os.Interrupt); e != nil {
					cmd.Process.Kill()
					t.Fatal(e)
				}
				conn.SetReadDeadline(time.Now().Add(10 * time.Second))
				if _, e = conn.Read(make([]byte, 1)); e != io.EOF {
					cmd.Process.Kill()
					t.Fatal("实际中断后子树仍活跃", e)
				}
			}
			err := cmd.Wait()
			if mode == "pass" && err != nil {
				t.Fatal(err, stdout.String(), stderr.String())
			}
			if mode == "interrupt" {
				if e, ok := err.(*exec.ExitError); !ok || e.ExitCode() != 2 {
					t.Fatal(err, stdout.String(), stderr.String())
				}
			}
			var result map[string]any
			if e := json.Unmarshal(stdout.Bytes(), &result); e != nil {
				t.Fatal("不是单JSON", e, stdout.String())
			}
			if stderr.Len() != 0 {
				t.Fatal(stderr.String())
			}
			receipt := result["receipt"].(map[string]any)
			if receipt["process_tree_cleaned"] != true || receipt["interrupted"] != (mode == "interrupt") {
				t.Fatal(receipt)
			}
			if mode == "pass" && result["result"] != "passed" {
				t.Fatal(result)
			}
			if _, e := os.Stat(filepath.Join(root, result["receipt_path"].(string))); e != nil {
				t.Fatal(e)
			}
		})
	}
}
