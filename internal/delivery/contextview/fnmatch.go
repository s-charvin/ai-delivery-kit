package contextview

import (
	"regexp"
	"strings"
)

// Match 保持 Python fnmatchcase 的当前配置语义：区分大小写、* 跨 /、隐藏文件正常匹配。
func Match(pattern, name string) bool {
	p := []rune(pattern)
	var out strings.Builder
	out.WriteString("(?s)\\A")
	for i := 0; i < len(p); {
		c := p[i]
		i++
		switch c {
		case '*':
			out.WriteString(".*")
		case '?':
			out.WriteByte('.')
		case '[':
			start := i
			j := i
			if j < len(p) && p[j] == '!' {
				j++
			}
			if j < len(p) && p[j] == ']' {
				j++
			}
			for j < len(p) && p[j] != ']' {
				j++
			}
			if j == len(p) {
				out.WriteString(`\[`)
				continue
			}
			stuff := p[start:j]
			chunks := [][]rune{}
			k := start + 1
			if p[start] == '!' {
				k++
			}
			chunkStart := start
			for k < j {
				for k < j && p[k] != '-' {
					k++
				}
				if k >= j {
					break
				}
				chunks = append(chunks, append([]rune{}, p[chunkStart:k]...))
				chunkStart = k + 1
				k += 3
			}
			if chunkStart < j {
				chunks = append(chunks, append([]rune{}, p[chunkStart:j]...))
			} else if len(chunks) > 0 {
				chunks[len(chunks)-1] = append(chunks[len(chunks)-1], '-')
			}
			if strings.ContainsRune(string(stuff), '-') {
				for k := len(chunks) - 1; k > 0; k-- {
					a, b := chunks[k-1], chunks[k]
					if len(a) > 0 && len(b) > 0 && a[len(a)-1] > b[0] {
						chunks[k-1] = append(a[:len(a)-1], b[1:]...)
						chunks = append(chunks[:k], chunks[k+1:]...)
					}
				}
				var b strings.Builder
				for k, chunk := range chunks {
					if k > 0 {
						b.WriteByte('-')
					}
					for _, r := range chunk {
						if r == '\\' || r == '-' {
							b.WriteByte('\\')
						}
						b.WriteRune(r)
					}
				}
				stuff = []rune(b.String())
			} else {
				stuff = []rune(strings.ReplaceAll(string(stuff), `\`, `\\`))
			}
			i = j + 1
			if len(stuff) == 0 {
				return false
			}
			if string(stuff) == "!" {
				out.WriteByte('.')
				continue
			}
			out.WriteByte('[')
			if stuff[0] == '!' {
				out.WriteByte('^')
				stuff = stuff[1:]
			} else if stuff[0] == '^' || stuff[0] == '[' {
				out.WriteByte('\\')
			}
			out.WriteString(string(stuff))
			out.WriteByte(']')
		default:
			out.WriteString(regexp.QuoteMeta(string(c)))
		}
	}
	out.WriteString(`\z`)
	expression, err := regexp.Compile(out.String())
	return err == nil && expression.MatchString(name)
}
