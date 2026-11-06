package checks

import (
	"bytes"
	"encoding/json"
	"fmt"
	"path"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func receiptStrings(value any) ([]string, error) {
	values, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("收据字段必须为字符串列表")
	}
	out := []string{}
	for _, v := range values {
		s, ok := v.(string)
		if !ok {
			return nil, fmt.Errorf("收据字符串列表含错误类型")
		}
		out = append(out, s)
	}
	return out, nil
}
func receiptFiles(value any) ([]model.FileIdentity, error) {
	values, ok := value.([]any)
	if !ok || len(values) == 0 {
		return nil, fmt.Errorf("收据缺少执行输入身份")
	}
	out := []model.FileIdentity{}
	seen := map[string]bool{}
	for _, v := range values {
		f, ok := v.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("收据输入身份必须为对象")
		}
		p, ok := f["path"].(string)
		normalized, e := workspace.NormalizePath(p)
		if !ok || e != nil || normalized != p || seen[p] {
			return nil, fmt.Errorf("收据输入路径错误或重复: %s", p)
		}
		seen[p] = true
		kind, _ := f["kind"].(string)
		resolved, _ := f["resolved_path"].(string)
		if kind != "symlink" {
			if normalized, e := workspace.NormalizePath(resolved); e != nil || normalized != resolved {
				return nil, fmt.Errorf("收据缺少解析目标: %s", p)
			}
		}
		id := model.FileIdentity{Path: p, ResolvedPath: resolved, Kind: kind}
		hash, hasHash := f["sha256"]
		if !hasHash {
			return nil, fmt.Errorf("收据输入缺少 sha256: %s", p)
		}
		if hash != nil {
			v, ok := hash.(string)
			if !ok || !hexDigest.MatchString(v) {
				return nil, fmt.Errorf("收据输入摘要无效")
			}
			id.SHA256 = &v
		}
		if mode, exists := f["mode"]; exists {
			n, ok := mode.(json.Number)
			if !ok {
				return nil, fmt.Errorf("收据 mode 类型错误")
			}
			v, e := strconv.ParseUint(string(n), 10, 32)
			if e != nil {
				return nil, e
			}
			bits := uint32(v)
			id.Mode = &bits
		}
		if target, exists := f["link_target"]; exists {
			v, ok := target.(string)
			if !ok || v == "" {
				return nil, fmt.Errorf("收据 link_target 类型错误")
			}
			id.LinkTarget = &v
		}
		switch kind {
		case "file":
			if id.SHA256 == nil || id.Mode == nil || id.LinkTarget != nil {
				return nil, fmt.Errorf("收据文件身份不完整")
			}
		case "absent":
			if id.SHA256 != nil || id.Mode != nil || id.LinkTarget != nil {
				return nil, fmt.Errorf("收据 absence 身份无效")
			}
		case "directory":
			if id.Mode == nil || id.SHA256 != nil || id.LinkTarget != nil {
				return nil, fmt.Errorf("收据目录身份无效")
			}
		case "symlink":
			if id.LinkTarget == nil || id.Mode == nil || id.SHA256 != nil {
				return nil, fmt.Errorf("收据链接身份不完整")
			}
		default:
			return nil, fmt.Errorf("收据输入 kind 无效")
		}
		out = append(out, id)
	}
	return out, nil
}

func receiptInputData(data map[string]any) ([]model.FileIdentity, map[string]string, []string, error) {
	if data["receipt_version"] != json.Number("1") {
		return nil, nil, nil, fmt.Errorf("收据要求当前 receipt_version=1")
	}
	before, e := receiptFiles(data["inputs_before"])
	if e != nil {
		return nil, nil, nil, e
	}
	after, e := receiptFiles(data["inputs_after"])
	if e != nil {
		return nil, nil, nil, e
	}
	if data["result"] == "passed" && !reflect.DeepEqual(before, after) {
		return nil, nil, nil, fmt.Errorf("passed 收据的前后输入并不一致")
	}
	values, ok := data["input_roles"].(map[string]any)
	if !ok || len(values) != len(before) {
		return nil, nil, nil, fmt.Errorf("收据 input_roles 缺失或不完整")
	}
	roles := map[string]string{}
	for _, f := range before {
		role, ok := values[f.Path].(string)
		if !ok || role != "execution" && role != "prerequisite" {
			return nil, nil, nil, fmt.Errorf("收据输入角色非法: %s", f.Path)
		}
		roles[f.Path] = role
	}
	extra, e := receiptStrings(data["extra_input_paths"])
	if e != nil {
		return nil, nil, nil, e
	}
	for _, p := range extra {
		if normalized, e := workspace.NormalizePath(p); e != nil || normalized != p {
			return nil, nil, nil, fmt.Errorf("收据额外输入路径无效")
		}
	}
	return before, roles, extra, nil
}

// ReceiptReferences 扩展真实执行输入、显式来源及原始输出，不把 receipt 当作 opaque evidence。
func ReceiptReferences(data map[string]any) ([]string, error) {
	files, _, extra, e := receiptInputData(data)
	if e != nil {
		return nil, e
	}
	out := []string{}
	for _, f := range files {
		out = append(out, f.Path)
	}
	out = append(out, extra...)
	spec, ok := data["check_spec"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("收据缺少 check_spec")
	}
	for _, key := range []string{"input_paths", "source_refs"} {
		paths, e := receiptStrings(spec[key])
		if e != nil {
			return nil, e
		}
		out = append(out, paths...)
	}
	reports, ok := data["reports"].([]any)
	if !ok {
		return nil, fmt.Errorf("收据 reports 必须为列表")
	}
	for _, v := range append([]any{data["stdout"], data["stderr"]}, reports...) {
		f, ok := v.(map[string]any)
		p, valid := f["path"].(string)
		if !ok || !valid {
			return nil, fmt.Errorf("收据输出缺少路径")
		}
		out = append(out, p)
	}
	for _, p := range out {
		if normalized, e := workspace.NormalizePath(p); e != nil || normalized != p {
			return nil, fmt.Errorf("收据引用路径无效: %s", p)
		}
	}
	if len(out) > 10000 {
		return nil, fmt.Errorf("收据引用文件数超过 10000")
	}
	return out, nil
}

func currentSpecValue(spec model.CheckSpec) map[string]any {
	method := spec.Method
	value := map[string]any{"id": spec.ID, "applicability": spec.Applicability, "acceptance_ids": append([]string{}, spec.AcceptanceIDs...), "source_refs": append([]string{}, spec.SourceRefs...), "input_paths": append([]string{}, spec.InputPaths...), "method": map[string]any{"id": method.ID, "argv": append([]string{}, method.Argv...), "cwd": method.Cwd, "parser_id": method.ParserID, "report_paths": append([]string{}, method.ReportPaths...), "source_refs": append([]string{}, method.SourceRefs...)}}
	raw, _ := json.Marshal(value)
	out, _ := protocol.Object(raw)
	return out
}

func validateRunnerReceipt(s model.Snapshot, design string, check map[string]any, receiptPath string) []string {
	fail := func(message string) []string { return []string{"运行收据 " + receiptPath + ": " + message} }
	raw, ok := s.Document(receiptPath)
	if !ok {
		return fail("当前引用未读取")
	}
	data, e := protocol.Object(raw)
	if e != nil {
		return fail(e.Error())
	}
	checkID, _ := data["check_id"].(string)
	result, _ := data["result"].(string)
	r := model.RunReceipt{Path: receiptPath, Observation: model.CheckObservation{CheckID: checkID, Result: result, Provenance: "runner", Details: bytes.TrimSuffix(raw, []byte{'\n'})}}
	mapped, e := ReceiptToCheck(r)
	if e != nil {
		return fail(e.Error())
	}
	mapping, e := protocol.Object(mapped)
	if e != nil {
		return fail(e.Error())
	}
	for _, key := range []string{"id", "required", "result", "mode", "command", "cwd", "exit_code", "acceptance_ids"} {
		if !reflect.DeepEqual(check[key], mapping[key]) {
			return fail("verification check 与收据实际事实不一致: " + key)
		}
	}
	w := s.Workspace()
	if data["requirement_id"] != s.Scope().RequirementID || data["subrequirement_id"] != s.Scope().SubrequirementID || data["program_id"] != w.ProgramID || data["protocol_digest"] != w.ProtocolDigest || data["resource_digest"] != w.ResourceDigest {
		return fail("作用域/程序/协议/资源身份与当前不一致")
	}
	designRaw, _ := s.Document(design)
	methods, e := NativeMethods(designRaw)
	if e != nil {
		return fail(e.Error())
	}
	var current *model.CheckSpec
	for _, spec := range methods {
		if spec.ID == checkID {
			copy := spec
			current = &copy
		}
	}
	if current == nil || !reflect.DeepEqual(data["check_spec"], currentSpecValue(*current)) {
		return fail("当前 design 的完整方法/check spec 已改变或不存在")
	}
	actualArgs, e := receiptStrings(data["argv"])
	if e != nil {
		return fail(e.Error())
	}
	expectedArgs := append([]string{}, current.Method.Argv...)
	runDir := filepath.Join(w.ProjectRoot, filepath.FromSlash(path.Dir(receiptPath)))
	for i, arg := range expectedArgs {
		expectedArgs[i] = strings.ReplaceAll(arg, "{run_dir}", runDir)
	}
	if !reflect.DeepEqual(actualArgs, expectedArgs) || data["cwd"] != current.Method.Cwd {
		return fail("实际 argv/cwd 与当前方法模板不一致")
	}
	before, roles, extra, e := receiptInputData(data)
	if e != nil {
		return fail(e.Error())
	}
	explicit := append(append(append([]string{}, current.InputPaths...), current.SourceRefs...), extra...)
	expectedRoles, e := workspace.RunInputRoles(s, before, explicit)
	if e != nil {
		return fail(e.Error())
	}
	if !reflect.DeepEqual(roles, expectedRoles) {
		return fail("input_roles 与核心从当前 binding/方法/额外输入推导的角色不一致")
	}
	known := map[string]model.FileIdentity{}
	for _, f := range s.Files() {
		known[f.Path] = f
	}
	recorded := map[string]model.FileIdentity{}
	for _, f := range before {
		recorded[f.Path] = f
		if roles[f.Path] == "execution" {
			actual, exists := known[f.Path]
			if !exists || !reflect.DeepEqual(f, actual) {
				return fail("执行输入已漂移或未读取: " + f.Path)
			}
		}
	}
	paths, e := workspace.KnownRunInputPaths(s, explicit, design)
	if e != nil {
		return fail(e.Error())
	}
	currentInputs, e := workspace.RunInputIdentities(s, paths)
	if e != nil {
		return fail(e.Error())
	}
	currentRoles, e := workspace.RunInputRoles(s, currentInputs, explicit)
	if e != nil {
		return fail(e.Error())
	}
	for _, id := range currentInputs {
		if currentRoles[id.Path] != "execution" {
			continue
		}
		previous, ok := recorded[id.Path]
		if !ok || roles[id.Path] != "execution" {
			return fail("收据遗漏当前必需执行输入，请重新运行: " + id.Path)
		}
		if !reflect.DeepEqual(previous, id) {
			return fail("当前必需执行输入已漂移，请重新运行: " + id.Path)
		}
	}
	evidence, ok := check["evidence"].([]any)
	if !ok {
		return fail("check evidence 缺失")
	}
	for _, expected := range mapping["evidence"].([]any) {
		found := false
		for _, actual := range evidence {
			found = found || reflect.DeepEqual(expected, actual)
		}
		if !found {
			return fail("check evidence 遗漏原始收据/输出身份")
		}
	}
	return nil
}

// ReceiptExecutionInputs 提供 v2 顶层 inputs 的默认投影；最终 consumer 仍重算角色。
func ReceiptExecutionInputs(r model.RunReceipt) ([]byte, error) {
	if _, e := ReceiptToCheck(r); e != nil {
		return nil, e
	}
	data, e := protocol.Object(r.Observation.Details)
	if e != nil {
		return nil, e
	}
	files, roles, _, e := receiptInputData(data)
	if e != nil {
		return nil, e
	}
	out := []any{}
	for _, f := range files {
		if roles[f.Path] != "execution" {
			continue
		}
		switch f.Kind {
		case "file":
			out = append(out, map[string]any{"path": f.Path, "sha256": *f.SHA256})
		case "absent":
			out = append(out, map[string]any{"path": f.Path, "sha256": nil, "state": "absent"})
		}
	}
	return json.Marshal(out)
}
