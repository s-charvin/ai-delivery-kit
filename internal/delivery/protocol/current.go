package protocol

import (
	"crypto/sha256"
	_ "embed"
	"fmt"
	"strings"
	"unicode/utf8"
)

//go:embed current.json
var currentJSON []byte

// Defaults 每次返回独立对象；默认值只在嵌入资源中定义。
func Defaults(kind string) map[string]any {
	data, err := Object(currentJSON)
	if err != nil {
		panic(err)
	}
	m, ok := data[kind].(map[string]any)
	if !ok {
		panic("未知默认配置: " + kind)
	}
	return m
}
func Digest() string          { return fmt.Sprintf("%x", sha256.Sum256(currentJSON)) }
func Version(kind string) any { return Defaults("versions")[kind] }
func RequireVersion(data map[string]any, field, kind string) error {
	expected := Version(kind)
	if expected == nil {
		return fmt.Errorf("未知协议类型: %s", kind)
	}
	actual, exists := data[field]
	if !exists || actual != expected {
		return fmt.Errorf("字段 %s 实际类型=%T，实际值=%v，要求当前 %s 类型=%T，值=%v", field, actual, actual, kind, expected, expected)
	}
	return nil
}

func ValidateMetadata(kind string, data map[string]any) error {
	if kind != "binding" && kind != "policy" {
		return fmt.Errorf("未知元数据类型: %s", kind)
	}
	if err := RequireVersion(data, "version", kind); err != nil {
		return err
	}
	if kind == "policy" {
		if err := RequireVersion(data, "verification_contract_version", "verification"); err != nil {
			return err
		}
	}
	for _, key := range []string{"context", "layout", "verification_policy"} {
		if v, exists := data[key]; exists {
			m, ok := v.(map[string]any)
			if !ok {
				return fmt.Errorf("字段 %s 实际类型=%T，实际值=%v；当前要求 JSON 对象", key, v, v)
			}
			if key == "context" {
				if sources, exists := m["sources"]; exists {
					if _, ok := sources.([]any); !ok {
						return fmt.Errorf("字段 context.sources 实际类型=%T，实际值=%v；当前要求数组", sources, sources)
					}
				}
			}
			if key == "layout" {
				for _, scalar := range []string{"requirement_root", "sub_requirement_dir"} {
					if v, exists := m[scalar]; exists {
						if s, ok := v.(string); !ok || !SafeMetadataTemplate(s) {
							return fmt.Errorf("字段 layout.%s 实际类型=%T，实际值=%v；当前要求项目内路径模板", scalar, v, v)
						}
					}
				}
				for _, group := range []string{"project_artifacts", "requirement_artifacts", "sub_requirement_artifacts"} {
					if v, exists := m[group]; exists {
						paths, ok := v.(map[string]any)
						if !ok {
							return fmt.Errorf("字段 layout.%s 实际类型=%T，实际值=%v；当前要求 JSON 对象", group, v, v)
						}
						for name, v := range paths {
							if s, ok := v.(string); !ok || !SafeMetadataTemplate(s) {
								return fmt.Errorf("字段 layout.%s.%s 实际类型=%T，实际值=%v；当前要求项目内路径模板", group, name, v, v)
							}
						}
					}
				}
			}
		}
	}
	if v, exists := data["ai_delivery_path"]; exists {
		if s, ok := v.(string); !ok || !SafeMetadataTemplate(s) {
			return fmt.Errorf("字段 ai_delivery_path 实际类型=%T，实际值=%v；当前要求项目内路径", v, v)
		}
	}
	return RejectRemovedFields(data)
}

func RejectRemovedFields(data any) error {
	switch v := data.(type) {
	case map[string]any:
		for k, item := range v {
			switch k {
			case "legacy_terminal_slices", "migration_source_sha256", "ui_contract_exempt", "no_design_client", "design_mode", "design_approved":
				return fmt.Errorf("已移除字段: %s", k)
			case "participation":
				if text, ok := item.(string); ok && text == "no_design_client" {
					return fmt.Errorf("已移除 participation 值: %s", text)
				}
			}
			if err := RejectRemovedFields(item); err != nil {
				return err
			}
		}
	case []any:
		for _, item := range v {
			if err := RejectRemovedFields(item); err != nil {
				return err
			}
		}
	}
	return nil
}

func SafeMetadataTemplate(s string) bool {
	if s == "" || !utf8.ValidString(s) || strings.HasPrefix(s, "/") || strings.ContainsAny(s, "\\:") {
		return false
	}
	for _, r := range s {
		if r < 32 {
			return false
		}
	}
	for _, part := range strings.Split(s, "/") {
		if part == ".." {
			return false
		}
	}
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '{':
			if i+1 < len(s) && s[i+1] == '{' {
				i++
				continue
			}
			end := strings.IndexByte(s[i+1:], '}')
			if end < 0 {
				return false
			}
			token := s[i+1 : i+1+end]
			switch token {
			case "req_id", "sr_id", "unit_id", "ts":
			default:
				return false
			}
			i += end + 1
		case '}':
			if i+1 < len(s) && s[i+1] == '}' {
				i++
				continue
			}
			return false
		}
	}
	return true
}
