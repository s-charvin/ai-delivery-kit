package protocol

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"strconv"
	"strings"
	"unicode/utf8"
)

// ParseJSON 保留数值原词形，并拒绝重复键、非法编码和非有限浮点数。
func ParseJSON(body []byte) (any, error) {
	if !utf8.Valid(body) {
		return nil, fmt.Errorf("JSON 不是有效 UTF-8")
	}
	if err := validateSurrogates(body); err != nil {
		return nil, err
	}
	d := json.NewDecoder(bytes.NewReader(body))
	d.UseNumber()
	v, err := jsonValue(d, 0)
	if err != nil {
		return nil, err
	}
	if _, err = d.Token(); err != io.EOF {
		return nil, fmt.Errorf("JSON 末尾存在额外内容")
	}
	return v, nil
}

func Object(body []byte) (map[string]any, error) {
	v, err := ParseJSON(body)
	if err != nil {
		return nil, err
	}
	m, ok := v.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("实际类型=%T，实际值=%v；当前要求 JSON 对象", v, v)
	}
	return m, nil
}

func jsonValue(d *json.Decoder, depth int) (any, error) {
	if depth > 10000 {
		return nil, fmt.Errorf("JSON 嵌套深度超过 10000")
	}
	t, err := d.Token()
	if err != nil {
		return nil, err
	}
	delim, compound := t.(json.Delim)
	if !compound {
		if n, ok := t.(json.Number); ok && strings.ContainsAny(string(n), ".eE") {
			f, err := strconv.ParseFloat(string(n), 64)
			if err != nil || math.IsInf(f, 0) || math.IsNaN(f) {
				return nil, fmt.Errorf("JSON 浮点数无法有限表示: %s", n)
			}
		}
		return t, nil
	}
	switch delim {
	case '{':
		m := map[string]any{}
		for d.More() {
			k, err := d.Token()
			if err != nil {
				return nil, err
			}
			key, ok := k.(string)
			if !ok {
				return nil, fmt.Errorf("无效 JSON 键")
			}
			if _, exists := m[key]; exists {
				return nil, fmt.Errorf("重复 JSON 键 %s", key)
			}
			v, err := jsonValue(d, depth+1)
			if err != nil {
				return nil, err
			}
			m[key] = v
		}
		_, err := d.Token()
		return m, err
	case '[':
		a := []any{}
		for d.More() {
			v, err := jsonValue(d, depth+1)
			if err != nil {
				return nil, err
			}
			a = append(a, v)
		}
		_, err := d.Token()
		return a, err
	default:
		return nil, fmt.Errorf("无效 JSON 分隔符")
	}
}

// encoding/json 会替换孤立代理码点；在解码前拒绝，避免无声改变摘要。
func validateSurrogates(body []byte) error {
	quoted := false
	for i := 0; i < len(body); i++ {
		if body[i] == '"' {
			quoted = !quoted
			continue
		}
		if !quoted || body[i] != '\\' {
			continue
		}
		i++
		if i >= len(body) {
			break
		}
		if body[i] != 'u' {
			continue
		}
		if i+4 >= len(body) {
			continue
		}
		n, err := strconv.ParseUint(string(body[i+1:i+5]), 16, 16)
		if err != nil {
			continue
		}
		i += 4
		if n >= 0xdc00 && n <= 0xdfff {
			return fmt.Errorf("JSON 含孤立 Unicode 代理码点")
		}
		if n < 0xd800 || n > 0xdbff {
			continue
		}
		if i+6 >= len(body) || body[i+1] != '\\' || body[i+2] != 'u' {
			return fmt.Errorf("JSON 含孤立 Unicode 代理码点")
		}
		next, err := strconv.ParseUint(string(body[i+3:i+7]), 16, 16)
		if err != nil || next < 0xdc00 || next > 0xdfff {
			return fmt.Errorf("JSON 含孤立 Unicode 代理码点")
		}
		i += 6
	}
	return nil
}
