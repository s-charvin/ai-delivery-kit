package cli

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

const hookInputLimit = 1 << 20
const hookContextLimit = 12000

// 原生入口只投影传输协议；阶段、来源选择和权限判断仍调用原 CLI 的同进程服务。
func (a *App) runHook(args []string) int {
	native := false
	for _, arg := range args {
		if arg == "--host" || arg == "-host" || strings.HasPrefix(arg, "--host=") || strings.HasPrefix(arg, "-host=") || arg == "--event" || strings.HasPrefix(arg, "--event=") {
			native = true
		}
	}
	if !native {
		return a.runCheck(args)
	}
	flags := flag.NewFlagSet("hook", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	host := flags.String("host", "", "原生宿主")
	event := flags.String("event", "", "明确事件")
	project := flags.String("project", "", "明确项目绝对路径")
	delivery := flags.String("delivery-root", "", "治理根")
	req := flags.String("req", "", "需求 ID")
	sr := flags.String("subreq", "", "切片 ID")
	role := flags.String("role", "", "SessionStart 上下文角色")
	intent := flags.String("intent", "", "PreToolUse 明确意图")
	target := flags.String("to", "", "明确目标状态")
	budget := flags.Int("budget-chars", 4000, "上下文正文预算，0..64000")
	var paths pathsFlag
	flags.Var(&paths, "path", "SessionStart 声明路径，可重复")
	if err := flags.Parse(args); err != nil {
		return a.hookError(err)
	}
	if flags.NArg() != 0 || *host != "codex" || (*event != "SessionStart" && *event != "PreToolUse") {
		return a.hookError(fmt.Errorf("原生 hook 仅支持 --host codex --event SessionStart|PreToolUse，不接受位置参数"))
	}
	if !filepath.IsAbs(*project) || *budget < 0 || *budget > 64000 {
		return a.hookError(fmt.Errorf("原生 hook 要求明确 --project 绝对路径与 0..64000 的 --budget-chars"))
	}
	if (*req == "") != (*sr == "") {
		return a.hookError(fmt.Errorf("--req 和 --subreq 必须同时提供，不能推断缺失 scope"))
	}
	if *event == "SessionStart" && (*intent != "" || *target != "") {
		return a.hookError(fmt.Errorf("SessionStart 只接受 context 角色/路径，不接受 action"))
	}
	if *event == "PreToolUse" && (*role != "" || len(paths) > 0) {
		return a.hookError(fmt.Errorf("PreToolUse 只接受明确 action，不接受 context 角色/路径"))
	}
	if a.stdin == nil {
		return a.hookError(fmt.Errorf("原生 hook 缺少 stdin"))
	}
	body, err := io.ReadAll(io.LimitReader(a.stdin, hookInputLimit+1))
	if err != nil {
		return a.hookError(err)
	}
	if len(body) > hookInputLimit {
		return a.hookError(fmt.Errorf("原生 hook stdin 超过 1 MiB"))
	}
	input, err := protocol.Object(body)
	if err != nil {
		return a.hookError(err)
	}
	if err = validateCodexEvent(input, *event, *project); err != nil {
		return a.hookError(err)
	}
	if *req == "" {
		return a.hookContext(*event, "未提供明确 scope，未执行任何动作检查或授予权限。请使用 ai-delivery context/check --project <项目> --req <需求> --subreq <切片> 及明确 role/intent；不从 session、transcript 或工具命令推断任务。")
	}
	common := []string{"--project", *project, "--delivery-root", *delivery, "--req", *req, "--subreq", *sr}
	var out, stderr bytes.Buffer
	transport := *a
	transport.stdout, transport.stderr = &out, &stderr
	var code int
	if *event == "SessionStart" {
		command := append(common, "--role", *role, "--budget-chars", strconv.Itoa(*budget))
		for _, p := range paths {
			command = append(command, "--path", p)
		}
		code = transport.runContext(command)
	} else {
		code = transport.runCheck(append(common, "--intent", *intent, "--to", *target))
	}
	var report map[string]any
	if err = json.Unmarshal(out.Bytes(), &report); err != nil {
		return a.hookError(fmt.Errorf("核心响应无效: %w", err))
	}
	if report["snapshot_id"] == nil {
		return a.hookError(fmt.Errorf("核心未完成检查（exit %d）: %s %s", code, out.String(), stderr.String()))
	}
	if *event == "PreToolUse" && (code != 0 || report["allowed"] != true) {
		return a.deliveryJSON(map[string]any{"hookSpecificOutput": map[string]any{
			"hookEventName": *event, "permissionDecision": "deny",
			"permissionDecisionReason": boundedHookText("ai-delivery 核心拒绝当前明确动作：\n" + out.String()),
		}}, 0)
	}
	// context 不完整仍呈现 required/needs_read/missing；它从不产生 action 许可。
	return a.hookContext(*event, "ai-delivery 当前显式 scope 的只读结果；context 完整性不授予实施权限，工具权限仍由宿主决定：\n"+out.String())
}

func (a *App) hookError(err error) int {
	// Codex PreToolUse 的其他非零退出可能继续工具；只用已支持的 exit 2 + stderr。
	fmt.Fprintln(a.stderr, boundedHookText("ai-delivery native hook: "+err.Error()))
	return 2
}

func (a *App) hookContext(event, body string) int {
	return a.deliveryJSON(map[string]any{"hookSpecificOutput": map[string]any{
		"hookEventName": event, "additionalContext": boundedHookText(body),
	}}, 0)
}

func boundedHookText(body string) string {
	runes := []rune(body)
	if len(runes) <= hookContextLimit {
		return body
	}
	note := "\n[输出已截断；必须使用显式 ai-delivery context/check 取得完整来源与诊断，不能把片段视为全部上下文。]"
	return string(runes[:hookContextLimit-len([]rune(note))]) + note
}

func validateCodexEvent(input map[string]any, event, project string) error {
	requireString := func(key string) (string, error) {
		value, ok := input[key].(string)
		if !ok || strings.TrimSpace(value) == "" {
			return "", fmt.Errorf("原生 %s 必须为非空字符串", key)
		}
		return value, nil
	}
	for _, key := range []string{"session_id", "cwd", "hook_event_name"} {
		if _, err := requireString(key); err != nil {
			return err
		}
	}
	if input["hook_event_name"] != event {
		return fmt.Errorf("stdin hook_event_name 与 --event 不匹配")
	}
	if value, present := input["transcript_path"]; present && value != nil {
		if _, valid := value.(string); !valid {
			return fmt.Errorf("原生 transcript_path 必须为字符串或 null")
		}
	}
	for _, key := range []string{"permission_mode", "model", "turn_id"} {
		if value, ok := input[key]; ok {
			if _, valid := value.(string); !valid {
				return fmt.Errorf("原生 %s 必须为字符串", key)
			}
		}
	}
	cwd := input["cwd"].(string)
	if !filepath.IsAbs(cwd) {
		return fmt.Errorf("原生 cwd 必须为绝对路径")
	}
	root, err := filepath.EvalSymlinks(project)
	if err != nil {
		return err
	}
	actual, err := filepath.EvalSymlinks(cwd)
	if err != nil {
		return err
	}
	for _, p := range []string{root, actual} {
		st, e := os.Stat(p)
		if e != nil {
			return e
		}
		if !st.IsDir() {
			return fmt.Errorf("原生项目/cwd 不是目录: %s", p)
		}
	}
	rel, err := filepath.Rel(root, actual)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || filepath.IsAbs(rel) {
		return fmt.Errorf("原生 cwd 超出明确项目范围")
	}
	if event == "SessionStart" {
		source, err := requireString("source")
		if err != nil {
			return err
		}
		switch source {
		case "startup", "resume", "clear", "compact", "fork":
			return nil
		default:
			return fmt.Errorf("未支持的 SessionStart source: %s", source)
		}
	}
	tool, err := requireString("tool_name")
	if err != nil {
		return err
	}
	if _, err = requireString("tool_use_id"); err != nil {
		return err
	}
	toolInput, ok := input["tool_input"]
	if !ok {
		return fmt.Errorf("PreToolUse 缺少 tool_input")
	}
	if tool == "Bash" || tool == "apply_patch" {
		value, ok := toolInput.(map[string]any)
		if !ok {
			return fmt.Errorf("%s tool_input 必须为对象", tool)
		}
		if _, ok := value["command"].(string); !ok {
			return fmt.Errorf("%s tool_input.command 必须为字符串", tool)
		}
	}
	return nil
}
