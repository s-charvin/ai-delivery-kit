package checks

import (
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

func markedBody(raw []byte, start, end string) (string, error) {
	if !utf8.Valid(raw) {
		return "", fmt.Errorf("合同不是有效 UTF-8")
	}
	text := strings.ReplaceAll(string(raw), "\r\n", "\n")
	if err := markerPositions(text, []string{start, end}); err != nil {
		return "", err
	}
	if strings.Count(text, start) != 1 || strings.Count(text, end) != 1 {
		return "", fmt.Errorf("需要唯一且完整的机器标记: %s", start)
	}
	a, b := strings.Index(text, start)+len(start), strings.Index(text, end)
	if b < a {
		return "", fmt.Errorf("合同结束标记先于开始标记")
	}
	return text[a:b], nil
}

func markerPositions(text string, markers []string) error {
	return markdownLines(text, func(line string, fenced bool) error {
		for _, marker := range markers {
			if strings.Contains(line, marker) && (fenced || strings.TrimSpace(line) != marker) {
				return fmt.Errorf("机器标记必须位于代码示例之外的独立行: %s", marker)
			}
		}
		return nil
	})
}

func outsideMarker(text, marker string) bool {
	found := false
	_ = markdownLines(text, func(line string, fenced bool) error {
		if !fenced && strings.TrimSpace(line) == marker {
			found = true
		}
		return nil
	})
	return found
}

// markdownLines 标识示例代码行；正式 marker/编号共享同一正文视图。
// 原文仍保留给 JSON 与 Mermaid 的专用解析，不修改被 review 绑定的字节。
func markdownLines(text string, visit func(string, bool) error) error {
	var fence byte
	width := 0
	for _, line := range strings.Split(text, "\n") {
		trimmed := strings.TrimSpace(line)
		indent := 0
		for _, char := range line {
			if char == ' ' {
				indent++
			} else if char == '\t' {
				indent += 4 - indent%4
			} else {
				break
			}
		}
		n := 0
		if indent < 4 && len(trimmed) >= 3 && (trimmed[0] == '`' || trimmed[0] == '~') {
			for n < len(trimmed) && trimmed[n] == trimmed[0] {
				n++
			}
		}
		if err := visit(line, fence != 0 || indent >= 4 || n >= 3); err != nil {
			return err
		}
		if n < 3 {
			continue
		}
		if fence == 0 {
			fence, width = trimmed[0], n
		} else if trimmed[0] == fence && n >= width && strings.TrimSpace(trimmed[n:]) == "" {
			fence, width = 0, 0
		}
	}
	return nil
}

func prose(text string) string {
	var out strings.Builder
	_ = markdownLines(text, func(line string, code bool) error {
		if !code {
			out.WriteString(line)
		}
		out.WriteByte('\n')
		return nil
	})
	return out.String()
}

var jsonFence = regexp.MustCompile("(?s)^```json[ \\t]*\\n(.*?)\\n```$")

// ParseBlock 只接受机器标记内的唯一完整 JSON fence，不依赖人读标题。
func ParseBlock(raw []byte, start, end string) (map[string]any, error) {
	body, err := markedBody(raw, start, end)
	if err != nil {
		return nil, err
	}
	match := jsonFence.FindStringSubmatch(strings.TrimSpace(body))
	if match == nil {
		return nil, fmt.Errorf("合同需要完整 JSON fenced block")
	}
	return protocol.Object([]byte(match[1]))
}

func sections(body string, markers []string) (map[string]string, error) {
	if err := markerPositions(body, markers); err != nil {
		return nil, err
	}
	out := map[string]string{}
	last := -1
	for i, marker := range markers {
		p := strings.Index(body, marker)
		if strings.Count(body, marker) != 1 || p <= last {
			return nil, fmt.Errorf("节标记缺失、重复或顺序错误: %s", marker)
		}
		last = p
		end := len(body)
		if i+1 < len(markers) {
			end = strings.Index(body, markers[i+1])
			if end < p {
				return nil, fmt.Errorf("节标记顺序错误: %s", marker)
			}
		}
		out[marker] = body[p+len(marker) : end]
	}
	return out, nil
}
