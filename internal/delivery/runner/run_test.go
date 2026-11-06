package runner_test

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

var helper string

func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "native-helper-")
	if err != nil {
		panic(err)
	}
	helper = filepath.Join(dir, "native-helper")
	if os.PathSeparator == '\\' {
		helper += ".exe"
	}
	out, err := exec.Command("go", "build", "-o", helper, "./testdata/native-helper").CombinedOutput()
	if err != nil {
		panic(string(out) + err.Error())
	}
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}
func setup(t *testing.T, args []string, parser string, reports []string) (model.Snapshot, model.CheckSpec, model.RunRequest) {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".ai-delivery"), 0755); err != nil {
		t.Fatal(err)
	}
	os.WriteFile(filepath.Join(root, "owner.txt"), []byte("当前生产输入"), 0644)
	w := model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery"), ProgramID: "test-program", ProtocolDigest: "test-protocol", ResourceDigest: "test-resources"}
	s, err := workspace.NewSnapshot(w, model.Scope{RequirementID: "R", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}}, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	s, err = (workspace.Reader{}).Extend(context.Background(), s, []string{"owner.txt"})
	if err != nil {
		t.Fatal(err)
	}
	argv := append([]string{helper}, args...)
	spec := model.CheckSpec{ID: "native-owner", Applicability: "required", AcceptanceIDs: []string{"AC-001"}, InputPaths: []string{"owner.txt"}, SourceRefs: []string{"owner.txt"}, Method: &model.CheckMethod{ID: "native-owner", Argv: argv, Cwd: ".", ParserID: parser, ReportPaths: reports, SourceRefs: []string{"owner.txt"}}}
	return s, spec, model.RunRequest{CheckID: spec.ID, Argv: argv, Cwd: ".", TimeoutSeconds: 10}
}
func receipt(t *testing.T, r model.RunReceipt) map[string]any {
	t.Helper()
	var d map[string]any
	if err := json.Unmarshal(r.Observation.Details, &d); err != nil {
		t.Fatal(err)
	}
	return d
}
func TestLiteralArgumentsLogsAndUniqueReceipts(t *testing.T) {
	args := []string{"echo", "a b", `a"b`, `$HOME`, "中文🙂", ""}
	s, spec, req := setup(t, args, "exit-code", nil)
	first, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
	if err != nil {
		t.Fatal(err)
	}
	if first.Observation.Result != "passed" {
		t.Fatal(string(first.Observation.Details))
	}
	d := receipt(t, first)
	out, err := os.ReadFile(filepath.Join(s.Workspace().ProjectRoot, d["stdout"].(map[string]any)["path"].(string)))
	if err != nil {
		t.Fatal(err)
	}
	var got struct {
		Args []string `json:"args"`
		Cwd  string   `json:"cwd"`
	}
	if err = json.Unmarshal(out, &got); err != nil {
		t.Fatal(err)
	}
	physical, _ := filepath.EvalSymlinks(s.Workspace().ProjectRoot)
	actual, _ := filepath.EvalSymlinks(got.Cwd)
	if !reflect.DeepEqual(got.Args, args[1:]) || actual != physical {
		t.Fatalf("%+v", got)
	}
	stderr, _ := os.ReadFile(filepath.Join(s.Workspace().ProjectRoot, d["stderr"].(map[string]any)["path"].(string)))
	if len(stderr) < 1024*1024 || !strings.HasPrefix(string(stderr), "原生错误流🙂") {
		t.Fatal("错误流缺失或截断")
	}
	second, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
	if err != nil || first.Path == second.Path {
		t.Fatal(second, err)
	}
	if _, err = os.Stat(filepath.Join(s.Workspace().ProjectRoot, first.Path)); err != nil {
		t.Fatal(err)
	}
}
func TestWrongMethodRejectedBeforeExecution(t *testing.T) {
	for _, kind := range []string{"argv", "cwd", "id", "parser", "reserved"} {
		t.Run(kind, func(t *testing.T) {
			s, spec, req := setup(t, []string{"touch", "started"}, "exit-code", nil)
			switch kind {
			case "argv":
				req.Argv = append(req.Argv, "wrong")
			case "cwd":
				req.Cwd = "sub"
			case "id":
				req.CheckID = "other"
			case "parser":
				spec.Method.ParserID = "unknown"
			case "reserved":
				spec.ID = "verification"
				spec.Method.ID = spec.ID
				req.CheckID = spec.ID
			}
			if _, err := (runner.Runner{}).Run(context.Background(), s, spec, req); err == nil {
				t.Fatal("错误方法执行")
			}
			if _, err := os.Stat(filepath.Join(s.Workspace().ProjectRoot, "started")); !os.IsNotExist(err) {
				t.Fatal("拒绝前执行了程序")
			}
		})
	}
}
func TestExitStartFailureAndTimeoutAreNotPassed(t *testing.T) {
	for _, mode := range []string{"fail", "start", "timeout"} {
		t.Run(mode, func(t *testing.T) {
			s, spec, req := setup(t, []string{mode}, "exit-code", nil)
			if mode == "start" {
				spec.Method.Argv = []string{filepath.Join(t.TempDir(), "missing")}
				req.Argv = spec.Method.Argv
			}
			if mode == "timeout" {
				req.TimeoutSeconds = 1
			}
			r, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
			if err != nil {
				t.Fatal(err)
			}
			if r.Observation.Result == "passed" {
				t.Fatal(string(r.Observation.Details))
			}
			d := receipt(t, r)
			if mode == "fail" && d["exit_code"] != float64(7) {
				t.Fatal(d)
			}
			if mode == "timeout" && d["timed_out"] != true {
				t.Fatal(d)
			}
		})
	}
}
func TestHandshakeInputDriftAndCancellation(t *testing.T) {
	for _, mode := range []string{"drift", "cancel", "publish-failure", "missing-log"} {
		t.Run(mode, func(t *testing.T) {
			listener, err := net.Listen("tcp", "127.0.0.1:0")
			if err != nil {
				t.Fatal(err)
			}
			defer listener.Close()
			s, spec, req := setup(t, []string{"handshake", listener.Addr().String()}, "exit-code", nil)
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			type result struct {
				r model.RunReceipt
				e error
			}
			done := make(chan result, 1)
			go func() { r, e := (runner.Runner{}).Run(ctx, s, spec, req); done <- result{r, e} }()
			listener.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
			conn, err := listener.Accept()
			if err != nil {
				t.Fatal(err)
			}
			defer conn.Close()
			if mode == "drift" {
				os.WriteFile(filepath.Join(s.Workspace().ProjectRoot, "owner.txt"), []byte("执行中改变"), 0644)
			}
			if mode == "cancel" {
				cancel()
			}
			if mode == "publish-failure" {
				dirs, _ := filepath.Glob(filepath.Join(s.Workspace().DeliveryRoot, "runs", "*"))
				if len(dirs) != 1 {
					t.Fatal(dirs)
				}
				os.Mkdir(filepath.Join(dirs[0], "receipt.json"), 0755)
			}
			if mode == "missing-log" {
				dirs, _ := filepath.Glob(filepath.Join(s.Workspace().DeliveryRoot, "runs", "*"))
				if len(dirs) != 1 {
					t.Fatal(dirs)
				}
				if err := os.Remove(filepath.Join(dirs[0], "stdout.log")); err != nil {
					t.Fatal(err)
				}
			}
			conn.Write([]byte("continue\n"))
			select {
			case got := <-done:
				if mode == "publish-failure" {
					if got.e == nil || got.r.Observation.Result == "passed" {
						t.Fatal("发布失败仍返回成功")
					}
					return
				}
				if got.e != nil {
					t.Fatal(got.e)
				}
				if got.r.Observation.Result == "passed" {
					t.Fatal(string(got.r.Observation.Details))
				}
				d := receipt(t, got.r)
				if mode == "drift" && d["inputs_stable"] != false {
					t.Fatal(d)
				}
				if mode == "cancel" && d["interrupted"] != true {
					t.Fatal(d)
				}
			case <-time.After(15 * time.Second):
				t.Fatal("取消未终止实际进程")
			}
		})
	}
}
func TestReportOwnershipAndInputOutputConflicts(t *testing.T) {
	for _, mode := range []string{"fresh", "missing", "stale", "input-conflict"} {
		t.Run(mode, func(t *testing.T) {
			report := "{run_dir}/native.json"
			args := []string{"report", report}
			if mode == "missing" {
				args = []string{"touch", "started"}
			}
			if mode == "stale" {
				report = "old.json"
				args = []string{"touch", "started"}
			}
			if mode == "input-conflict" {
				report = "owner.txt"
				args = []string{"report", report}
			}
			s, spec, req := setup(t, args, "exit-code", []string{report})
			os.WriteFile(filepath.Join(s.Workspace().ProjectRoot, "old.json"), []byte(`{"passed":true}`), 0644)
			r, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
			if mode == "fresh" {
				if err != nil || r.Observation.Result != "passed" {
					t.Fatal(r, err)
				}
				again, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
				if e != nil || again.Observation.Result != "passed" {
					t.Fatal(again, e)
				}
			} else if err == nil && r.Observation.Result == "passed" {
				t.Fatal("陈旧/缺失/输入冲突报告通过")
			}
		})
	}
}

func TestGoParserRealHostTestsRejectZeroFailureAndCached(t *testing.T) {
	goexe, err := exec.LookPath("go")
	if err != nil {
		t.Fatal(err)
	}
	for _, mode := range []string{"pass", "zero", "fail", "cached", "wrong-parser-report"} {
		t.Run(mode, func(t *testing.T) {
			s, spec, req := setup(t, nil, "go-test-json", nil)
			root := s.Workspace().ProjectRoot
			os.WriteFile(filepath.Join(root, "go.mod"), []byte("module host\n\ngo 1.22.0\n"), 0644)
			owner, err := os.ReadFile("testdata/owner/owner.go")
			if err != nil {
				t.Fatal(err)
			}
			os.WriteFile(filepath.Join(root, "owner.go"), owner, 0644)
			test := `package owner; import "testing";func TestSave(t *testing.T){if Save("value")!="value" {t.Fatal("save")}}`
			if mode == "fail" {
				test = `package owner;import "testing";func TestSave(t *testing.T){t.Fatal("真实失败")}`
			}
			if mode != "zero" {
				os.WriteFile(filepath.Join(root, "owner_test.go"), []byte(test), 0644)
			}
			argv := []string{goexe, "test", "-json", "-count=1", "./..."}
			if mode == "cached" {
				argv = []string{goexe, "test", "-json", "./..."}
				cmd := exec.Command(argv[0], argv[1:]...)
				cmd.Dir = root
				if out, e := cmd.CombinedOutput(); e != nil {
					t.Fatalf("%s %v", out, e)
				}
			}
			if mode == "wrong-parser-report" {
				argv = []string{helper, "report", "unrelated.json"}
			}
			spec.Method.Argv = argv
			req.Argv = argv
			req.TimeoutSeconds = 30
			r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
			if e != nil {
				t.Fatal(e)
			}
			if (r.Observation.Result == "passed") != (mode == "pass") {
				t.Fatal(mode, string(r.Observation.Details))
			}
		})
	}
}

func TestReceiptMappingDoesNotInventAuthority(t *testing.T) {
	s, spec, req := setup(t, []string{"touch", "started"}, "exit-code", nil)
	r, err := (runner.Runner{}).Run(context.Background(), s, spec, req)
	if err != nil {
		t.Fatal(err)
	}
	b, err := checks.ReceiptToCheck(r)
	if err != nil {
		t.Fatal(err)
	}
	var c map[string]any
	json.Unmarshal(b, &c)
	if c["result"] != "passed" || c["mode"] != "executed" || c["id"] != "native-owner" || c["exit_code"] != float64(0) {
		t.Fatal(c)
	}
	for _, key := range []string{"reviews", "reviewer", "waiver", "confirmation"} {
		if _, ok := c[key]; ok {
			t.Fatal("伪造权限", key)
		}
	}
	_ = fmt.Sprint(c)
}

func TestCancellationCleansActualDescendant(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	s, spec, req := setup(t, []string{"tree", listener.Addr().String()}, "exit-code", nil)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan model.RunReceipt, 1)
	go func() {
		r, e := (runner.Runner{}).Run(ctx, s, spec, req)
		if e != nil {
			t.Error(e)
		}
		done <- r
	}()
	listener.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
	conn, err := listener.Accept()
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	cancel()
	conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	one := make([]byte, 1)
	_, err = conn.Read(one)
	if !errors.Is(err, io.EOF) && !errors.Is(err, peerResetError) {
		t.Fatalf("后代进程未关闭真实连接: %v", err)
	}
	select {
	case r := <-done:
		if r.Observation.Result == "passed" {
			t.Fatal("取消被映射成功")
		}
	case <-time.After(10 * time.Second):
		t.Fatal("父进程未清理")
	}
}

func TestNewProductionPathDuringRunInvalidatesGitReceipt(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	s, spec, req := setup(t, []string{"handshake", listener.Addr().String()}, "exit-code", nil)
	root := s.Workspace().ProjectRoot
	cmd := exec.Command("git", "init", root)
	if out, e := cmd.CombinedOutput(); e != nil {
		t.Fatal(string(out), e)
	}
	done := make(chan model.RunReceipt, 1)
	go func() {
		r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
		if e != nil {
			t.Error(e)
		}
		done <- r
	}()
	listener.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
	conn, err := listener.Accept()
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	os.WriteFile(filepath.Join(root, "new-production.go"), []byte("package production"), 0644)
	conn.Write([]byte("continue\n"))
	r := <-done
	if r.Observation.Result != "invalid" || receipt(t, r)["inputs_stable"] != false {
		t.Fatal(string(r.Observation.Details))
	}
}

func TestExitedParentCannotPublishWhileDescendantHoldsOutput(t *testing.T) {
	leaf, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		t.Fatal(e)
	}
	defer leaf.Close()
	parent, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		t.Fatal(e)
	}
	defer parent.Close()
	s, spec, req := setup(t, []string{"orphan", leaf.Addr().String(), parent.Addr().String()}, "exit-code", nil)
	done := make(chan model.RunReceipt, 1)
	go func() {
		r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
		if e != nil {
			t.Error(e)
		}
		done <- r
	}()
	leaf.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
	lc, e := leaf.Accept()
	if e != nil {
		t.Fatal(e)
	}
	defer lc.Close()
	parent.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
	pc, e := parent.Accept()
	if e != nil {
		t.Fatal(e)
	}
	defer pc.Close()
	pc.Write([]byte("parent exits now\n"))
	r := <-done
	d := receipt(t, r)
	if d["process_tree_cleaned"] != true || d["exit_code"] != float64(0) {
		t.Fatal("未证明进程树完成", d)
	}
	if r.Observation.Result == "passed" || d["complete"] != false || d["forced_termination"] != true {
		t.Fatal("强杀未完成后代不能冒充正常完整执行", d)
	}
	lc.SetReadDeadline(time.Now().Add(time.Second))
	_, e = lc.Read(make([]byte, 1))
	if !errors.Is(e, io.EOF) && !errors.Is(e, peerResetError) {
		t.Fatalf("发布时后代仍活跃: %v", e)
	}
}

func TestActualCapturedLogsCannotBeReplacedOrTruncated(t *testing.T) {
	for _, mode := range []string{"replace-stdout", "replace-stderr", "truncate-stdout"} {
		t.Run(mode, func(t *testing.T) {
			listener, e := net.Listen("tcp", "127.0.0.1:0")
			if e != nil {
				t.Fatal(e)
			}
			defer listener.Close()
			s, spec, req := setup(t, []string{"logged-handshake", listener.Addr().String()}, "exit-code", nil)
			done := make(chan model.RunReceipt, 1)
			go func() {
				r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
				if e != nil {
					t.Error(e)
				}
				done <- r
			}()
			listener.(*net.TCPListener).SetDeadline(time.Now().Add(10 * time.Second))
			conn, e := listener.Accept()
			if e != nil {
				t.Fatal(e)
			}
			defer conn.Close()
			dirs, _ := filepath.Glob(filepath.Join(s.Workspace().DeliveryRoot, "runs", "*"))
			if len(dirs) != 1 {
				t.Fatal(dirs)
			}
			name := "stdout.log"
			if mode == "replace-stderr" {
				name = "stderr.log"
			}
			p := filepath.Join(dirs[0], name)
			if strings.HasPrefix(mode, "replace-") {
				if e = os.Rename(p, p+".original"); e != nil {
					t.Fatal(e)
				}
				e = os.WriteFile(p, []byte("替换文件不是原始流"), 0600)
			} else {
				e = os.Truncate(p, 0)
			}
			if e != nil {
				t.Fatal(e)
			}
			conn.Write([]byte("continue\n"))
			r := <-done
			d := receipt(t, r)
			if r.Observation.Result == "passed" || d["complete"] != false {
				t.Fatal("丢失了真实日志归属", d)
			}
		})
	}
}

func TestNativeReportCannotOverwriteReceiptOrRawLogs(t *testing.T) {
	for _, name := range []string{"receipt.json", "stdout.log", "stderr.log"} {
		t.Run(name, func(t *testing.T) {
			p := "{run_dir}/" + name
			s, spec, req := setup(t, []string{"report", p}, "exit-code", []string{p})
			if r, e := (runner.Runner{}).Run(context.Background(), s, spec, req); e == nil {
				t.Fatal("报告覆盖运行器原始证据", string(r.Observation.Details))
			}
		})
	}
}
func TestNativeReportAndLiteralCwdInSubdirectory(t *testing.T) {
	p := "{run_dir}/native.json"
	s, spec, req := setup(t, []string{"report", p}, "exit-code", []string{p})
	os.Mkdir(filepath.Join(s.Workspace().ProjectRoot, "sub directory"), 0755)
	spec.Method.Cwd = "sub directory"
	req.Cwd = spec.Method.Cwd
	r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
	if e != nil || r.Observation.Result != "passed" {
		t.Fatal(e, string(r.Observation.Details))
	}
}
