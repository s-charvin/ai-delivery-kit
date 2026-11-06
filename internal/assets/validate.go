package assets

import (
	"fmt"
	"path"
	"regexp"
	"strings"
	"unicode/utf8"
)

// ValidateSources 只检查人读资源结构与引用，不执行模型或重写领域门禁。
func ValidateSources(kind string, read func(string) ([]byte, bool, error)) error {
	names := []string{"ai-delivery-orchestrator", "requirement-breakdown", "ui-truth-mapping"}
	for _, name := range names {
		p := ".agents/skills/" + name + "/SKILL.md"
		b, ok, err := read(p)
		if err != nil {
			return err
		}
		if !ok {
			return fmt.Errorf("缺少 %s", p)
		}
		s := string(b)
		if !strings.HasPrefix(s, "---\n") || !strings.Contains(s, "\nname: "+name+"\n") || !strings.Contains(s, "\ndescription:") {
			return fmt.Errorf("%s: 缺少当前 skill frontmatter", p)
		}
		p = ".agents/skills/" + name + "/agents/openai.yaml"
		b, ok, err = read(p)
		if err != nil {
			return err
		}
		if !ok {
			return fmt.Errorf("缺少 %s", p)
		}
		for _, key := range []string{"interface:", "display_name:", "short_description:", "default_prompt:", "$" + name} {
			if !strings.Contains(string(b), key) {
				return fmt.Errorf("%s: 缺少 %s", p, key)
			}
		}
		match := regexp.MustCompile(`(?m)^  short_description: "([^"]*)"`).FindSubmatch(b)
		if len(match) != 2 || utf8.RuneCount(match[1]) < 25 || utf8.RuneCount(match[1]) > 64 {
			return fmt.Errorf("%s: short_description 应为 25–64 字符", p)
		}
	}
	if kind == "api-policy" {
		for _, v := range [][2]string{{"ai-delivery-orchestrator", "API docs pass directly to `design.md` and implementation"}, {"ai-delivery-orchestrator", "integration_deferred"}, {"ui-truth-mapping", "Do not invent visual truth"}, {"requirement-breakdown", "Do not split requirements without source line-range coverage for every slice"}} {
			p := ".agents/skills/" + v[0] + "/SKILL.md"
			b, _, err := read(p)
			if err != nil {
				return err
			}
			if !strings.Contains(string(b), v[1]) {
				return fmt.Errorf("%s: API/来源政策缺少 %q", p, v[1])
			}
		}
		return nil
	}
	paths, err := Paths()
	if err != nil {
		return err
	}
	links := regexp.MustCompile(`\[[^\]\n]*\]\(([^)\n]+)\)`)
	fences := regexp.MustCompile("(?s)```.*?```")
	for _, p := range paths {
		if !strings.HasSuffix(p, ".md") || !strings.HasPrefix(p, ".agents/") {
			continue
		}
		b, _, err := read(p)
		if err != nil {
			return err
		}
		for _, m := range links.FindAllSubmatch(fences.ReplaceAll(b, nil), -1) {
			link := strings.Trim(string(m[1]), "<>")
			link = strings.SplitN(link, "#", 2)[0]
			if link == "" || strings.Contains(link, "://") || strings.HasPrefix(link, "mailto:") {
				continue
			}
			target := path.Clean(path.Join(path.Dir(p), link))
			_, ok, err := read(target)
			if err != nil {
				return fmt.Errorf("%s: %s: %w", p, link, err)
			}
			if !ok {
				return fmt.Errorf("%s: 断开的资源引用 %s", p, link)
			}
		}
	}
	return nil
}
