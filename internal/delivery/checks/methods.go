package checks

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

const NativeMethodsStart = "<!-- ai-delivery:native-methods:v1 -->"
const NativeMethodsEnd = "<!-- /ai-delivery:native-methods:v1 -->"

// NativeMethods 只读取设计验收节中的显式方法，不推测自然语言命令。
func NativeMethods(raw []byte) ([]model.CheckSpec, error) {
	text := string(raw)
	if !strings.Contains(text, NativeMethodsStart) && !strings.Contains(text, NativeMethodsEnd) {
		return nil, nil
	}
	data, err := ParseBlock(raw, NativeMethodsStart, NativeMethodsEnd)
	if err != nil {
		return nil, err
	}
	body, err := markedBody(raw, behaviorStart, behaviorEnd)
	if err != nil {
		return nil, err
	}
	sections, err := sections(body, behaviorMarkers)
	if err != nil {
		return nil, err
	}
	if !strings.Contains(sections[behaviorMarkers[2]], NativeMethodsStart) || !strings.Contains(sections[behaviorMarkers[2]], NativeMethodsEnd) {
		return nil, fmt.Errorf("native-methods 必须在设计验收节内")
	}
	acs, err := AcceptanceIDs(raw)
	if err != nil {
		return nil, err
	}
	if data["version"] != json.Number("1") {
		return nil, fmt.Errorf("native-methods version 必须为 1")
	}
	for key := range data {
		if key != "version" && key != "checks" {
			return nil, fmt.Errorf("native-methods 未知字段: %s", key)
		}
	}
	values, ok := data["checks"].([]any)
	if !ok || len(values) == 0 {
		return nil, fmt.Errorf("native-methods checks 必须为非空列表")
	}
	out := []model.CheckSpec{}
	seen := map[string]bool{"inputs": true, "status": true, "dependencies": true, "design": true, "verification": true}
	for _, value := range values {
		c, ok := value.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("native-method 必须为对象")
		}
		for key := range c {
			if !contains([]string{"id", "acceptance_ids", "argv", "cwd", "parser_id", "input_paths", "report_paths", "source_refs"}, key) {
				return nil, fmt.Errorf("native-method 未知字段: %s", key)
			}
		}
		id, ok := c["id"].(string)
		if !ok || strings.TrimSpace(id) == "" || seen[id] {
			return nil, fmt.Errorf("native-method id 缺失、重复或占用核心命名空间: %s", id)
		}
		seen[id] = true
		list := func(key string, required, paths bool) ([]string, error) {
			values, ok := c[key].([]any)
			if !ok || required && len(values) == 0 {
				return nil, fmt.Errorf("%s 必须为%s字符串列表", key, map[bool]string{true: "非空", false: ""}[required])
			}
			out := []string{}
			seen := map[string]bool{}
			for _, value := range values {
				s, ok := value.(string)
				if !ok || strings.ContainsRune(s, 0) || key != "argv" && strings.TrimSpace(s) == "" {
					return nil, fmt.Errorf("%s 含非法字符串", key)
				}
				if paths {
					p, e := workspace.NormalizePath(s)
					if e != nil || p != s || p == "." {
						return nil, fmt.Errorf("%s 路径必须为规范项目相对文件: %s", key, s)
					}
				}
				if key != "argv" && seen[s] {
					return nil, fmt.Errorf("%s 条目重复", key)
				}
				seen[s] = true
				out = append(out, s)
			}
			return out, nil
		}
		acceptance, e := list("acceptance_ids", true, false)
		if e != nil {
			return nil, e
		}
		for _, ac := range acceptance {
			if !contains(acs, ac) {
				return nil, fmt.Errorf("方法引用未知 AC: %s", ac)
			}
		}
		argv, e := list("argv", true, false)
		if e != nil {
			return nil, e
		}
		if strings.TrimSpace(argv[0]) == "" {
			return nil, fmt.Errorf("argv 程序不能为空")
		}
		inputs, e := list("input_paths", true, true)
		if e != nil {
			return nil, e
		}
		reports, e := list("report_paths", false, true)
		if e != nil {
			return nil, e
		}
		refs, e := list("source_refs", true, true)
		if e != nil {
			return nil, e
		}
		cwd, ok := c["cwd"].(string)
		normalized, e := workspace.NormalizePath(cwd)
		if !ok || e != nil || normalized != cwd {
			return nil, fmt.Errorf("cwd 必须为规范项目相对目录")
		}
		parser, ok := c["parser_id"].(string)
		if !ok || parser != "go-test-json" && parser != "exit-code" {
			return nil, fmt.Errorf("未知 parser_id")
		}
		out = append(out, model.CheckSpec{ID: id, Applicability: "required", AcceptanceIDs: acceptance, SourceRefs: refs, InputPaths: inputs, Method: &model.CheckMethod{ID: id, Argv: argv, Cwd: cwd, ParserID: parser, ReportPaths: reports, SourceRefs: refs}})
	}
	return out, nil
}
