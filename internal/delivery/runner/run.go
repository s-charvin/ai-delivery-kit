package runner

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

type Runner struct{ Reader workspace.Reader }

var ErrCapability = errors.New("原生进程能力不可用")

func (r Runner) Run(ctx context.Context, s model.Snapshot, spec model.CheckSpec, req model.RunRequest) (model.RunReceipt, error) {
	spec = model.CloneCheckSpecs([]model.CheckSpec{spec})[0]
	m := spec.Method
	reserved := map[string]bool{"inputs": true, "status": true, "dependencies": true, "design": true, "verification": true}
	if m == nil || spec.ID == "" || reserved[spec.ID] || m.ID != spec.ID || req.CheckID != spec.ID || len(m.Argv) == 0 || strings.TrimSpace(m.Argv[0]) == "" || !reflect.DeepEqual(req.Argv, m.Argv) || req.Cwd != m.Cwd || req.TimeoutSeconds <= 0 || req.TimeoutSeconds > 86400 || len(spec.InputPaths) == 0 || len(spec.SourceRefs) == 0 || len(spec.AcceptanceIDs) == 0 {
		return model.RunReceipt{}, fmt.Errorf("运行请求必须精确匹配已绑定的方法、cwd、输入、AC 与有效超时")
	}
	if m.ParserID != "exit-code" && m.ParserID != "go-test-json" {
		return model.RunReceipt{}, fmt.Errorf("未知结果解析器: %s", m.ParserID)
	}
	cwd, err := workspace.NormalizePath(m.Cwd)
	if err != nil || cwd != m.Cwd {
		return model.RunReceipt{}, fmt.Errorf("非法方法 cwd")
	}
	if err = ctx.Err(); err != nil {
		return model.RunReceipt{}, err
	}
	w := s.Workspace()
	if err = r.Reader.Verify(ctx, s); err != nil {
		return model.RunReceipt{}, err
	}
	release, err := projectfs.ProjectLock(w.ProjectRoot)
	if err != nil {
		return model.RunReceipt{}, err
	}
	defer release()
	inputs := append(append(append([]string{}, spec.InputPaths...), spec.SourceRefs...), req.InputPaths...)
	inputs = append(inputs, m.Cwd)
	s, err = r.Reader.Extend(ctx, s, inputs)
	if err != nil {
		return model.RunReceipt{}, err
	}
	cwdID, ok, err := workspace.Identity(s, m.Cwd)
	if err != nil || !ok || cwdID.Kind != "directory" {
		return model.RunReceipt{}, fmt.Errorf("cwd 不是项目内实际目录")
	}
	for _, p := range append(append([]string{}, spec.InputPaths...), spec.SourceRefs...) {
		id, ok, e := workspace.Identity(s, p)
		if e != nil || !ok || id.Kind != "file" {
			return model.RunReceipt{}, fmt.Errorf("明确方法输入/来源不存在或不是文件: %s", p)
		}
	}
	before := s.Files()
	extra := []string{}
	for _, p := range req.InputPaths {
		normalized, e := workspace.NormalizePath(p)
		if e != nil {
			return model.RunReceipt{}, e
		}
		extra = append(extra, normalized)
	}
	explicit := append(append(append([]string{}, spec.InputPaths...), spec.SourceRefs...), extra...)
	roles, err := workspace.RunInputRoles(s, before, explicit)
	if err != nil {
		return model.RunReceipt{}, err
	}
	paths := []string{}
	for _, f := range before {
		paths = append(paths, f.Path)
	}
	observed, known, err := workspace.ObservedChanges(ctx, w.ProjectRoot)
	if err != nil {
		return model.RunReceipt{}, err
	}
	runs := filepath.Join(w.DeliveryRoot, "runs")
	if err = projectfs.NoLinkedParents(w.ProjectRoot, runs); err != nil {
		return model.RunReceipt{}, err
	}
	if err = os.MkdirAll(runs, 0755); err != nil {
		return model.RunReceipt{}, err
	}
	dir, err := os.MkdirTemp(runs, "run-")
	if err != nil {
		return model.RunReceipt{}, err
	}
	for _, f := range before {
		if f.Kind != "directory" && overlaps(filepath.Join(w.ProjectRoot, filepath.FromSlash(f.Path)), dir) {
			return model.RunReceipt{}, fmt.Errorf("本轮输出与输入冲突: %s", f.Path)
		}
	}
	relative, _ := filepath.Rel(w.ProjectRoot, dir)
	runDir := filepath.ToSlash(relative)
	runID := filepath.Base(dir)
	expand := func(v string) string { return strings.ReplaceAll(v, "{run_dir}", runDir) }
	reportPaths := []string{}
	for _, template := range m.ReportPaths {
		if !strings.HasPrefix(template, "{run_dir}/") {
			return model.RunReceipt{}, fmt.Errorf("固定报告路径未证明可再生与排他归属，执行被阻塞: %s；使用显式 {run_dir}/ 独立报告路径", template)
		}
		p := expand(template)
		normalized, e := workspace.NormalizePath(p)
		if e != nil || normalized != p {
			return model.RunReceipt{}, fmt.Errorf("非法报告路径: %s", p)
		}
		for _, reserved := range []string{"stdout.log", "stderr.log", "receipt.json"} {
			if overlaps(filepath.Join(w.ProjectRoot, p), filepath.Join(dir, reserved)) {
				return model.RunReceipt{}, fmt.Errorf("原生报告不能覆盖运行器日志或收据: %s", template)
			}
		}
		for _, previous := range reportPaths {
			if overlaps(filepath.Join(w.ProjectRoot, p), filepath.Join(w.ProjectRoot, previous)) {
				return model.RunReceipt{}, fmt.Errorf("原生报告路径重叠: %s", template)
			}
		}
		for _, f := range before {
			if f.Kind != "directory" && overlaps(filepath.Join(w.ProjectRoot, p), filepath.Join(w.ProjectRoot, f.Path)) {
				return model.RunReceipt{}, fmt.Errorf("报告输出与输入冲突: %s", p)
			}
		}
		absolute := filepath.Join(w.ProjectRoot, p)
		if err = projectfs.NoLinkedParents(w.ProjectRoot, absolute); err != nil {
			return model.RunReceipt{}, err
		}
		if _, e = os.Lstat(absolute); !os.IsNotExist(e) {
			return model.RunReceipt{}, fmt.Errorf("本轮报告路径并非 absence: %s", p)
		}
		if err = os.MkdirAll(filepath.Dir(absolute), 0755); err != nil {
			return model.RunReceipt{}, err
		}
		reportPaths = append(reportPaths, p)
	}
	argv := append([]string{}, m.Argv...)
	for i, v := range argv {
		argv[i] = strings.ReplaceAll(v, "{run_dir}", dir)
	}
	stdoutPath, stderrPath := filepath.Join(dir, "stdout.log"), filepath.Join(dir, "stderr.log")
	stdout, err := newCapturedLog(stdoutPath)
	if err != nil {
		return model.RunReceipt{}, err
	}
	defer stdout.close()
	stderr, err := newCapturedLog(stderrPath)
	if err != nil {
		return model.RunReceipt{}, err
	}
	defer stderr.close()
	d := Receipt{Version: 1, RunID: runID, CheckID: spec.ID, RequirementID: s.Scope().RequirementID, SubrequirementID: s.Scope().SubrequirementID, ProgramID: w.ProgramID, ProtocolDigest: w.ProtocolDigest, ResourceDigest: w.ResourceDigest, SnapshotID: s.ID(), Spec: specDTO(spec), Argv: argv, Cwd: cwd, InputsBefore: filesDTO(before), InputScope: "核心已知设计/规范/生产/配置与显式输入；不声称已自动发现宿主完整依赖", Reports: []File{}, TestsRun: []string{}, Problems: []string{}}
	d.InputRoles = roles
	d.ExtraInputPaths = extra
	d.SpecSHA256, err = digest(d.Spec)
	if err != nil {
		return model.RunReceipt{}, err
	}
	d.MethodSHA256, err = digest(d.Spec.Method)
	if err != nil {
		return model.RunReceipt{}, err
	}
	runCtx, cancel := context.WithTimeout(ctx, time.Duration(req.TimeoutSeconds)*time.Second)
	defer cancel()
	cmd := exec.Command(argv[0], argv[1:]...)
	cmd.Dir = filepath.Join(w.ProjectRoot, filepath.FromSlash(cwd))
	cmd.Stdout = stdout.writer
	cmd.Stderr = stderr.writer
	if strings.ContainsAny(argv[0], "/\\") && !filepath.IsAbs(argv[0]) {
		cmd.Path = filepath.Join(cmd.Dir, argv[0])
	}
	d.Executable = cmd.Path
	if err = prepareProcess(cmd); err != nil {
		return model.RunReceipt{}, fmt.Errorf("%w: %v", ErrCapability, err)
	}
	prestart, readErr := r.Reader.CaptureFiles(ctx, w, paths)
	if readErr != nil {
		return model.RunReceipt{}, readErr
	}
	if !reflect.DeepEqual(before, prestart) {
		return model.RunReceipt{}, fmt.Errorf("启动前运行输入已漂移")
	}
	start := time.Now()
	d.StartedAt = start.UTC().Format(time.RFC3339Nano)
	startErr := cmd.Start()
	stdout.writer.Close()
	stderr.writer.Close()
	if startErr != nil {
		d.Problems = append(d.Problems, "启动失败: "+startErr.Error())
	} else {
		d.Started = true
		cleanup, e := startedProcess(cmd)
		if e != nil {
			cmd.Process.Kill()
			cmd.Wait()
			d.Problems = append(d.Problems, "进程隔离失败: "+e.Error())
		} else {
			done := make(chan error, 1)
			go func() { done <- cmd.Wait() }()
			select {
			case e = <-done:
			case <-runCtx.Done():
				d.TimedOut = errors.Is(runCtx.Err(), context.DeadlineExceeded)
				d.Interrupted = !d.TimedOut
				forced, stopErr := cleanup()
				d.ForcedTermination = d.ForcedTermination || forced
				if stopErr != nil {
					d.Problems = append(d.Problems, "进程树清理失败: "+stopErr.Error())
				}
				e = <-done
			}
			forced, stopErr := cleanup()
			d.ForcedTermination = d.ForcedTermination || forced
			if stopErr != nil {
				d.Problems = append(d.Problems, "残留进程清理失败: "+stopErr.Error())
			} else {
				d.ProcessTreeCleaned = true
			}
			if e != nil {
				d.Problems = append(d.Problems, "原生进程: "+e.Error())
			}
			if d.ForcedTermination {
				d.Problems = append(d.Problems, "运行器强制终止了仍活跃的进程，不能声明正常输出完整")
			}
		}
		code := cmd.ProcessState.ExitCode()
		d.ExitCode = &code
		d.Signal = processSignal(cmd)
	}
	d.EndedAt = time.Now().UTC().Format(time.RFC3339Nano)
	d.DurationMS = time.Since(start).Milliseconds()
	if ctx.Err() != nil {
		d.Interrupted = true
	}
	if errors.Is(runCtx.Err(), context.DeadlineExceeded) {
		d.TimedOut = true
	}
	finishCtx, finishCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer finishCancel()
	captureComplete := true
	for _, stream := range []*capturedLog{stdout, stderr} {
		if err = stream.finish(finishCtx); err != nil {
			captureComplete = false
			d.Problems = append(d.Problems, err.Error())
		}
	}
	d.StdoutCapture = stdout.capture
	d.StderrCapture = stderr.capture
	after, err := r.Reader.CaptureFiles(finishCtx, w, paths)
	d.InputsAfter = filesDTO(after)
	d.InputsStable = err == nil && reflect.DeepEqual(before, after)
	if err != nil {
		d.Problems = append(d.Problems, "输入复核失败: "+err.Error())
	}
	if !d.InputsStable {
		d.Problems = append(d.Problems, "运行期间输入漂移")
	}
	current, currentKnown, e := workspace.ObservedChanges(finishCtx, w.ProjectRoot)
	filter := func(list []string) []string {
		out := []string{}
		for _, p := range list {
			absolute := filepath.Join(w.ProjectRoot, p)
			if !within(runs, absolute) && p != ".ai-delivery.lock" {
				out = append(out, p)
			}
		}
		return out
	}
	if e != nil || known != currentKnown || !reflect.DeepEqual(filter(observed), filter(current)) {
		d.InputsStable = false
		d.Problems = append(d.Problems, "运行期间实际生产变更范围漂移")
	}
	outputPaths := append([]string{runDir + "/stdout.log", runDir + "/stderr.log"}, reportPaths...)
	for _, p := range outputPaths {
		if err = projectfs.NoLinkedParents(w.ProjectRoot, filepath.Join(w.ProjectRoot, p)); err != nil {
			return model.RunReceipt{}, err
		}
	}
	outputIDs, err := r.Reader.CaptureFiles(finishCtx, w, outputPaths)
	if err != nil {
		return model.RunReceipt{}, err
	}
	outputs := map[string]File{}
	for _, f := range filesDTO(outputIDs) {
		outputs[f.Path] = f
	}
	d.Stdout = outputs[outputPaths[0]]
	d.Stderr = outputs[outputPaths[1]]
	logsComplete := captureComplete && d.Stdout.Kind == "file" && d.Stderr.Kind == "file" && d.Stdout.SHA256 != nil && d.Stderr.SHA256 != nil && *d.Stdout.SHA256 == d.StdoutCapture.SHA256 && *d.Stderr.SHA256 == d.StderrCapture.SHA256
	if !logsComplete {
		d.Problems = append(d.Problems, "原始 stdout/stderr 缺失，输出不完整")
	}
	d.ReportsFresh = true
	for _, p := range reportPaths {
		f := outputs[p]
		d.Reports = append(d.Reports, f)
		if f.Kind != "file" {
			d.ReportsFresh = false
			d.Problems = append(d.Problems, "本轮未产生必需报告: "+p)
		}
	}
	d.Result = "failed"
	if !d.Started {
		d.Result = "not_run"
	} else if d.ExitCode != nil && *d.ExitCode == 0 && d.ProcessTreeCleaned && !d.Interrupted && !d.TimedOut && d.Signal == "" && len(d.Problems) == 0 {
		d.Result = "passed"
	}
	if !d.InputsStable || !d.ReportsFresh || !logsComplete {
		d.Result = "invalid"
	}
	if d.Result == "passed" && m.ParserID == "go-test-json" {
		d.TestsRun, err = parseGoTests(stdoutPath)
		if err != nil {
			d.Result = "invalid"
			d.Problems = append(d.Problems, err.Error())
		}
	}
	if err = projectfs.NoLinkedParents(w.ProjectRoot, filepath.Join(dir, "receipt.json")); err != nil {
		return model.RunReceipt{}, err
	}
	for _, stream := range []*capturedLog{stdout, stderr} {
		if err = stream.validate(); err != nil {
			logsComplete = false
			d.Result = "invalid"
			d.Problems = append(d.Problems, err.Error())
		}
	}
	d.Complete = logsComplete && !d.ForcedTermination && (!d.Started || d.ProcessTreeCleaned)
	body, err := json.MarshalIndent(d, "", "  ")
	if err != nil {
		return model.RunReceipt{}, err
	}
	if err = projectfs.AtomicWriteFile(filepath.Join(dir, "receipt.json"), append(body, '\n'), 0600); err != nil {
		return model.RunReceipt{}, err
	}
	return model.RunReceipt{Path: runDir + "/receipt.json", Observation: model.CheckObservation{CheckID: spec.ID, Result: d.Result, Provenance: "runner", Evidence: outputIDs, Details: body}}, nil
}
func within(root, p string) bool {
	rel, err := filepath.Rel(root, p)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}
func overlaps(a, b string) bool { return within(a, b) || within(b, a) }

func parseGoTests(p string) ([]string, error) {
	f, err := os.Open(p)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	decoder := json.NewDecoder(f)
	runs := map[string]bool{}
	passed := map[string]bool{}
	type packageState struct {
		hasTests bool
		finished bool
	}
	packages := map[string]*packageState{}
	for {
		var raw json.RawMessage
		if err = decoder.Decode(&raw); err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("go-test-json 不是本轮合法事件流: %w", err)
		}
		event, e := protocol.Object(raw)
		if e != nil {
			return nil, e
		}
		action, ok := event["Action"].(string)
		pkg, pkgOK := event["Package"].(string)
		if !ok || !pkgOK || pkg == "" {
			return nil, fmt.Errorf("go-test-json 事件缺少 Action/Package")
		}
		testValue, hasTest := event["Test"]
		test, testOK := testValue.(string)
		// 官方包级事件省略 Test；错误类型或显式空值不能冒充无测试包。
		if hasTest && (!testOK || test == "") {
			return nil, fmt.Errorf("go-test-json Test 必须是非空字符串或省略")
		}
		key := pkg + "/" + test
		output, _ := event["Output"].(string)
		if strings.Contains(output, "(cached)") {
			return nil, fmt.Errorf("缓存结果不能声称本轮 executed；需要单独复用依据")
		}
		if action == "start" {
			if hasTest || packages[pkg] != nil {
				return nil, fmt.Errorf("非法或重复测试包 start 事件: %s", pkg)
			}
			packages[pkg] = &packageState{}
			continue
		}
		state := packages[pkg]
		if state == nil || state.finished {
			return nil, fmt.Errorf("测试包事件缺少 start 或出现在终结后: %s", pkg)
		}
		if hasTest {
			state.hasTests = true
		}
		switch action {
		case "run":
			if test == "" || runs[key] {
				return nil, fmt.Errorf("非法或重复测试 run 事件")
			}
			runs[key] = true
		case "pass":
			if test == "" {
				state.finished = true
			} else {
				if !runs[key] || passed[key] {
					return nil, fmt.Errorf("测试通过前没有本轮 run 或重复 pass")
				}
				passed[key] = true
			}
		case "skip":
			if state.hasTests {
				return nil, fmt.Errorf("实际测试被跳过或有测试的包错误报告无测试: %s", pkg)
			}
			// 无测试包可以终结，但不能贡献任何实际 run/pass 测试。
			state.finished = true
		case "fail":
			return nil, fmt.Errorf("原生事件报告失败")
		case "pause", "cont":
			if !hasTest || !runs[key] || passed[key] {
				return nil, fmt.Errorf("暂停或继续事件缺少运行中的实际测试")
			}
		case "output":
		default:
			return nil, fmt.Errorf("未知 go-test-json Action: %s", action)
		}
	}
	if len(runs) == 0 || len(passed) == 0 {
		return nil, fmt.Errorf("本轮没有实际成功运行的测试")
	}
	for key := range runs {
		if !passed[key] {
			return nil, fmt.Errorf("测试未成功完成: %s", key)
		}
	}
	for pkg, state := range packages {
		if !state.finished {
			return nil, fmt.Errorf("测试包未成功完成: %s", pkg)
		}
	}
	if len(packages) == 0 {
		return nil, fmt.Errorf("缺少本轮测试包 start")
	}
	out := []string{}
	for key := range passed {
		out = append(out, key)
	}
	sort.Strings(out)
	return out, nil
}
