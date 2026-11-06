package protocol

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"math"
	"math/big"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

// CanonicalJSON 对齐 Python 的 ensure_ascii=False、sort_keys=True 和紧凑分隔符。
// 整数保持任意精度；带小数或指数的原词形按 Python binary64 浮点语义编码。
func CanonicalJSON(value any) ([]byte, error) {
	var b bytes.Buffer
	if err := writeCanonical(&b, value); err != nil {
		return nil, err
	}
	return b.Bytes(), nil
}
func CanonicalSHA256(value any) (string, error) {
	body, err := CanonicalJSON(value)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", sha256.Sum256(body)), nil
}
func InputDigest(inputs []any) (string, error) { return CanonicalSHA256(inputs) }
func ReviewDigest(data map[string]any) (string, error) {
	claims := map[string]any{}
	for _, key := range []string{"version", "subreq_id", "inputs", "checks"} {
		claims[key] = data[key]
	}
	return CanonicalSHA256(claims)
}
func EntryDigest(data map[string]any) (string, error) {
	entry := map[string]any{}
	for key, value := range data {
		if key != "archive_evidence" {
			entry[key] = value
		}
	}
	return CanonicalSHA256(entry)
}

func writeCanonical(b *bytes.Buffer, value any) error {
	switch v := value.(type) {
	case nil:
		b.WriteString("null")
	case bool:
		if v {
			b.WriteString("true")
		} else {
			b.WriteString("false")
		}
	case string:
		return writeString(b, v)
	case json.Number:
		s := string(v)
		if s == "" || strings.TrimSpace(s) != s || !json.Valid([]byte(s)) {
			return fmt.Errorf("非法 JSON 数值: %q", s)
		}
		if strings.ContainsAny(s, ".eE") {
			f, err := strconv.ParseFloat(s, 64)
			if err != nil {
				return err
			}
			return writeFloat(b, f)
		}
		n, ok := new(big.Int).SetString(s, 10)
		if !ok {
			return fmt.Errorf("非法整数: %s", s)
		}
		b.WriteString(n.String())
	case float64:
		return writeFloat(b, v)
	case int:
		b.WriteString(strconv.FormatInt(int64(v), 10))
	case int64:
		b.WriteString(strconv.FormatInt(v, 10))
	case uint64:
		b.WriteString(strconv.FormatUint(v, 10))
	case uint32:
		b.WriteString(strconv.FormatUint(uint64(v), 10))
	case []any:
		if v == nil {
			b.WriteString("null")
			return nil
		}
		b.WriteByte('[')
		for i, item := range v {
			if i > 0 {
				b.WriteByte(',')
			}
			if err := writeCanonical(b, item); err != nil {
				return err
			}
		}
		b.WriteByte(']')
	case map[string]any:
		if v == nil {
			b.WriteString("null")
			return nil
		}
		keys := make([]string, 0, len(v))
		for key := range v {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		b.WriteByte('{')
		for i, key := range keys {
			if i > 0 {
				b.WriteByte(',')
			}
			if err := writeString(b, key); err != nil {
				return err
			}
			b.WriteByte(':')
			if err := writeCanonical(b, v[key]); err != nil {
				return err
			}
		}
		b.WriteByte('}')
	default:
		return fmt.Errorf("不支持 canonical JSON 值类型: %T", value)
	}
	return nil
}

func writeString(b *bytes.Buffer, s string) error {
	if !utf8.ValidString(s) {
		return fmt.Errorf("canonical 字符串不是有效 UTF-8")
	}
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"', '\\':
			b.WriteByte('\\')
			b.WriteRune(r)
		case '\b':
			b.WriteString(`\b`)
		case '\f':
			b.WriteString(`\f`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		default:
			if r < 32 {
				fmt.Fprintf(b, `\u%04x`, r)
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
	return nil
}

func writeFloat(b *bytes.Buffer, f float64) error {
	if math.IsNaN(f) || math.IsInf(f, 0) {
		return fmt.Errorf("canonical JSON 不支持非有限浮点数")
	}
	scientific := strconv.FormatFloat(f, 'e', -1, 64)
	split := strings.LastIndexByte(scientific, 'e')
	exponent, err := strconv.Atoi(scientific[split+1:])
	if err != nil {
		return err
	}
	if exponent < -4 || exponent >= 16 {
		b.WriteString(scientific)
		return nil
	}
	fixed := strconv.FormatFloat(f, 'f', -1, 64)
	if !strings.ContainsRune(fixed, '.') {
		fixed += ".0"
	}
	b.WriteString(fixed)
	return nil
}
