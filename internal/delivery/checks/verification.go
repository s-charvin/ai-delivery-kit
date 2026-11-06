package checks

import (
	"encoding/json"
	"fmt"
	"path"
	"reflect"
	"sort"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

const VerificationStart = "<!-- ai-delivery-verification:contract:v2 -->"
const VerificationEnd = "<!-- /ai-delivery-verification:contract:v2 -->"

func authority(v any) bool {
	a, ok := v.(map[string]any)
	if !ok {
		return false
	}
	for _, k := range []string{"by", "at", "reason", "source_ref"} {
		if !nonempty(a[k]) {
			return false
		}
	}
	return true
}

func ValidateVerification(data map[string]any, s model.Snapshot, design string, acs []string) []string {
	errors := []string{}
	if err := protocol.RequireVersion(data, "version", "verification"); err != nil {
		return []string{err.Error()}
	}
	if data["subreq_id"] != s.Scope().SubrequirementID {
		errors = append(errors, "verification subreq_id 不匹配")
	}
	files := map[string]model.FileIdentity{}
	for _, f := range s.Files() {
		if f.Kind != "symlink" {
			files[f.Path] = f
		}
	}
	checkFiles := func(v any, label string, allowAbsent bool) map[string]bool {
		seen := map[string]bool{}
		entries, ok := v.([]any)
		if !ok || len(entries) == 0 {
			errors = append(errors, label+" 缺少文件证据")
			return seen
		}
		for _, value := range entries {
			e, ok := value.(map[string]any)
			p, valid := e["path"].(string)
			if !ok || !valid {
				errors = append(errors, label+" 非法文件条目")
				continue
			}
			normalized, err := workspace.NormalizePath(p)
			if err != nil {
				errors = append(errors, err.Error())
				continue
			}
			if seen[normalized] {
				errors = append(errors, label+" 路径重复: "+normalized)
			}
			seen[normalized] = true
			f, observed := files[normalized]
			if identity, ok, err := workspace.Identity(s, normalized); err != nil {
				errors = append(errors, err.Error())
			} else if ok {
				f, observed = identity, true
			}
			_, hasDigest := e["sha256"]
			if allowAbsent && e["state"] == "absent" && hasDigest && e["sha256"] == nil {
				if !observed || f.Kind != "absent" {
					errors = append(errors, label+" 已删除输入重新出现或未观察: "+p)
				}
				continue
			}
			digest, _ := e["sha256"].(string)
			if !hexDigest.MatchString(digest) || !observed || f.Kind != "file" || f.SHA256 == nil || *f.SHA256 != digest {
				errors = append(errors, label+" 文件摘要无效或已变化: "+p)
			}
		}
		return seen
	}
	inputs, ok := data["inputs"].([]any)
	if !ok || len(inputs) == 0 {
		errors = append(errors, "verification inputs 不能为空")
	}
	inputPaths := checkFiles(data["inputs"], "inputs", true)
	if !inputPaths[design] {
		errors = append(errors, "inputs 必须绑定当前 design.md")
	}
	checks, ok := data["checks"].([]any)
	if !ok || len(checks) == 0 {
		errors = append(errors, "verification checks 不能为空")
	}
	covered := map[string]bool{}
	seen := map[string]bool{}
	native := map[string]model.CheckSpec{}
	designRaw, _ := s.Document(design)
	methods, methodErr := NativeMethods(designRaw)
	if methodErr != nil {
		errors = append(errors, methodErr.Error())
	} else {
		for _, spec := range methods {
			native[spec.ID] = spec
		}
	}
	for _, value := range checks {
		c, ok := value.(map[string]any)
		if !ok {
			errors = append(errors, "非法 check")
			continue
		}
		id, _ := c["id"].(string)
		if !nonempty(id) || seen[id] {
			errors = append(errors, "check ID 缺失或重复")
		}
		seen[id] = true
		required, ok := c["required"].(bool)
		if !ok {
			errors = append(errors, id+" required 必须明确为布尔值")
		}
		values, ok := c["acceptance_ids"].([]any)
		if !ok {
			errors = append(errors, id+" acceptance_ids 必须为列表")
		}
		checkACs := []string{}
		for _, value := range values {
			ac, ok := value.(string)
			if !ok || !contains(acs, ac) {
				errors = append(errors, id+" acceptance_ids 非法")
			} else {
				checkACs = append(checkACs, ac)
			}
		}
		// 每个由当前设计 AC 派生的检查都保留义务，声明 false 不能关闭它。
		nativeSpec, isNative := native[id]
		required = required || len(checkACs) > 0 || isNative
		accepted := false
		before := len(errors)
		if isNative && !reflect.DeepEqual(checkACs, nativeSpec.AcceptanceIDs) {
			errors = append(errors, id+" 当前 native 方法的 AC 覆盖不一致")
		}
		switch c["result"] {
		case "passed":
			mode := c["mode"]
			if mode != "executed" && mode != "reused" && mode != "manual" {
				errors = append(errors, id+" 缺少合法 mode")
			}
			if !nonempty(c["command"]) {
				errors = append(errors, id+" 缺少实际命令/步骤")
			}
			if mode != "manual" && c["exit_code"] != json.Number("0") {
				errors = append(errors, id+" passed 与退出码不一致")
			}
			if mode == "reused" && !nonempty(c["reuse_reason"]) {
				errors = append(errors, id+" 缺少复用依据")
			}
			if mode == "manual" && !authority(c["confirmation"]) {
				errors = append(errors, id+" 手工验证缺少确认来源")
			}
			evidence := checkFiles(c["evidence"], id, false)
			receipts := map[string]bool{}
			if value, exists := c["receipt_path"]; exists {
				p, ok := value.(string)
				if !ok || p == "" {
					errors = append(errors, id+" receipt_path 必须为非空路径")
				} else {
					receipts[p] = true
				}
			}
			for p := range evidence {
				if path.Base(p) == "verification.md" {
					errors = append(errors, id+" 不能自引用 verification.md 作为运行证据")
				}
			}
			ordered := []string{}
			for p := range receipts {
				ordered = append(ordered, p)
			}
			sort.Strings(ordered)
			if isNative && mode != "manual" && len(ordered) == 0 {
				errors = append(errors, id+" 当前 native 方法的 executed/reused 证据必须绑定真实运行收据，不能退成普通日志")
			}
			for _, p := range ordered {
				errors = append(errors, validateRunnerReceipt(s, design, c, p)...)
			}
			accepted = true
		case "waived":
			if !authority(c["waiver"]) {
				errors = append(errors, id+" 豁免缺少明确授权来源")
			}
			accepted = true
		case "not_applicable":
			if !nonempty(c["source_ref"]) || !nonempty(c["reason"]) {
				errors = append(errors, id+" 不适用缺少范围依据")
			}
			if required {
				errors = append(errors, id+" 核心必需检查不能声明不适用")
			}
		case "failed", "invalid", "not_run", "blocked":
			if required {
				errors = append(errors, id+" 必需检查未通过")
			}
		default:
			errors = append(errors, id+" 未知 result")
		}
		if accepted && len(errors) == before {
			for _, ac := range checkACs {
				covered[ac] = true
			}
		}
	}
	for _, spec := range methods {
		if !seen[spec.ID] {
			errors = append(errors, "当前设计声明的 native 检查缺失: "+spec.ID)
		}
	}
	if len(acs) == 0 {
		errors = append(errors, "design 没有可定位 AC")
	}
	for _, ac := range acs {
		if !covered[ac] {
			errors = append(errors, "AC 缺少通过/有效豁免证据: "+ac)
		}
	}
	reviews, ok := data["reviews"].([]any)
	if !ok || len(reviews) == 0 {
		return append(errors, "缺少新鲜上下文评审记录")
	}
	review, ok := reviews[len(reviews)-1].(map[string]any)
	if !ok {
		return append(errors, "非法评审条目")
	}
	if !nonempty(review["reviewer"]) {
		errors = append(errors, "缺少实际可见 reviewer")
	}
	if review["context"] != "fresh" || review["result"] != "clean" {
		errors = append(errors, "最新适用评审不为 fresh/clean")
	}
	inputHash, err := protocol.InputDigest(inputs)
	if err != nil || review["input_sha256"] != inputHash {
		errors = append(errors, "评审输入摘要已失效")
	}
	reviewHash, err := protocol.ReviewDigest(data)
	if err != nil || review["verification_sha256"] != reviewHash {
		errors = append(errors, "评审验证结果摘要已失效")
	}
	findings, ok := review["findings"].([]any)
	if !ok {
		errors = append(errors, "评审 findings 必须为列表")
	}
	for _, v := range findings {
		f, ok := v.(map[string]any)
		disposition, _ := f["disposition"].(string)
		if !ok || !contains([]string{"resolved", "rejected", "advisory", "waived"}, disposition) || !nonempty(f["source_ref"]) {
			errors = append(errors, "存在未处置或无来源 finding")
		}
	}
	return errors
}

// VerificationReferences 只读取当前协议定义的文件引用；坏路径绝不取消义务。
func VerificationReferences(data map[string]any) ([]string, error) {
	out := []string{}
	seen := map[string]bool{}
	add := func(v any) error {
		items, ok := v.([]any)
		if !ok {
			return fmt.Errorf("文件引用必须为列表")
		}
		for _, v := range items {
			e, ok := v.(map[string]any)
			if !ok {
				return fmt.Errorf("非法文件引用")
			}
			p, ok := e["path"].(string)
			if !ok {
				return fmt.Errorf("文件引用缺少 path")
			}
			p, err := workspace.NormalizePath(p)
			if err != nil {
				return err
			}
			if !seen[p] {
				seen[p] = true
				if len(seen) > 10000 {
					return fmt.Errorf("治理引用文件数超过 10000")
				}
				out = append(out, p)
			}
		}
		return nil
	}
	if err := add(data["inputs"]); err != nil {
		return nil, err
	}
	checks, ok := data["checks"].([]any)
	if !ok {
		return nil, fmt.Errorf("checks 必须为列表")
	}
	for _, v := range checks {
		c, ok := v.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("非法 check")
		}
		if evidence, exists := c["evidence"]; exists {
			if err := add(evidence); err != nil {
				return nil, err
			}
		}
		if p, exists := c["receipt_path"]; exists {
			if err := add([]any{map[string]any{"path": p}}); err != nil {
				return nil, err
			}
		}
	}
	return out, nil
}
