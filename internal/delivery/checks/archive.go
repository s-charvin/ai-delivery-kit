package checks

import (
	"fmt"
	"html"
	"reflect"
	"regexp"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

var archiveContractNames = []string{"solution_design", "verification", "ui_truth_index", "visual_acceptance"}

// ArchiveEvidence 保持 version 1 的三个文件身份字段及 canonical entry 摘要。
func ArchiveEvidence(s model.Snapshot, paths map[string]string, entry map[string]any) (map[string]any, error) {
	canonical := map[string]any{}
	for k, v := range entry {
		if k != "archive_evidence" {
			canonical[k] = v
		}
	}
	hash, err := protocol.CanonicalSHA256(canonical)
	if err != nil {
		return nil, err
	}
	files := []any{}
	for _, name := range archiveContractNames {
		id, ok, err := workspace.Identity(s, paths[name])
		if err != nil {
			return nil, err
		}
		if !ok {
			return nil, fmt.Errorf("固定合同未消费: %s", paths[name])
		}
		if id.Kind != "file" && id.Kind != "absent" {
			return nil, fmt.Errorf("固定合同不是文件: %s", paths[name])
		}
		var hash any
		if id.SHA256 != nil {
			hash = *id.SHA256
		}
		files = append(files, map[string]any{"path": paths[name], "resolved_path": id.ResolvedPath, "sha256": hash})
	}
	return map[string]any{"version": protocol.Version("archive_evidence"), "entry_sha256": hash, "files": files}, nil
}

func ValidateArchiveEvidence(s model.Snapshot, paths map[string]string, entry map[string]any) []string {
	saved, ok := entry["archive_evidence"].(map[string]any)
	if !ok {
		return []string{"缺少当前 archive_evidence；不能重建历史批准"}
	}
	if err := protocol.RequireVersion(saved, "version", "archive_evidence"); err != nil {
		return []string{err.Error()}
	}
	expected, err := ArchiveEvidence(s, paths, entry)
	if err != nil {
		return []string{err.Error()}
	}
	if !reflect.DeepEqual(saved, expected) {
		return []string{"归档终态记录或固定合同已变化；不得以当前源码重验替代历史完整性"}
	}
	for _, name := range []string{"solution_design", "verification"} {
		if _, ok := s.Document(paths[name]); !ok {
			return []string{"归档固定设计或验证材料缺失"}
		}
	}
	raw, _ := s.Document(paths["verification"])
	data, err := ParseBlock(raw, VerificationStart, VerificationEnd)
	if err != nil {
		return []string{err.Error()}
	}
	if err := protocol.RequireVersion(data, "version", "verification"); err != nil {
		return []string{err.Error()}
	}
	if entry["ui_truth_mode"] == "figma" || entry["ui_truth_mode"] == "runtime-baseline" {
		for _, p := range []struct{ name, kind string }{{"ui_truth_index", "ui_index"}, {"visual_acceptance", "visual_acceptance"}} {
			raw, _ := s.Document(paths[p.name])
			data, err := protocol.Object(raw)
			if err != nil {
				return []string{err.Error()}
			}
			if err := protocol.RequireVersion(data, "schema_version", p.kind); err != nil {
				return []string{err.Error()}
			}
		}
	}
	return nil
}

const RetrospectiveStart = "<!-- ai-delivery-retrospective:problem-index:v2 -->"
const RetrospectiveEnd = "<!-- /ai-delivery-retrospective:problem-index:v2 -->"
const ProjectIndexStart = "<!-- ai-delivery-retrospective:index:v1 -->"
const ProjectIndexEnd = "<!-- /ai-delivery-retrospective:index:v1 -->"

type RetrospectiveEntry struct{ ID, Trigger, Scenario, Path, KnowledgeType, ReuseScope, IndexDecision, Confidence, Importance, Status, Details, Anchor string }

func (e RetrospectiveEntry) Indexable() bool {
	return strings.EqualFold(e.KnowledgeType, "reusable") && (strings.EqualFold(e.ReuseScope, "project") || strings.EqualFold(e.ReuseScope, "domain")) && strings.EqualFold(e.IndexDecision, "include") && strings.EqualFold(e.Confidence, "confirmed") && (strings.EqualFold(e.Importance, "high") || strings.EqualFold(e.Importance, "critical"))
}

var reviewedAtRE = regexp.MustCompile(`<!--\s*ai-delivery-retrospective:reviewed-at:([^\s]+)\s*-->`)
var retrospectiveIDRE = regexp.MustCompile(`^RET-[0-9]{3,}$`)
var detailLinkRE = regexp.MustCompile(`\]\(\s*<?(#[^<>\s)]+)>?(?:\s+["'][^"']*["'])?\s*\)`)
var retrospectiveHeadingRE = regexp.MustCompile(`^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$`)
var detailIDRE = regexp.MustCompile(`^(RET-[0-9]{3,})(?:$|[\s:：])`)
var anchorTagRE = regexp.MustCompile(`(?i)<a\b[^>]*>`)
var anchorAttributeRE = regexp.MustCompile(`(?i)\b(?:id|name)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))`)
var anchorOnlyRE = regexp.MustCompile(`(?i)</?a\b[^>]*>`)
var batchPrefixRE = regexp.MustCompile(`^(?:[0-9]+[.)]\s*|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}\s*[:|\-]?\s*)+`)
var batchTitleRE = regexp.MustCompile(`(?i)^(?:this (?:round|session)(?:'s)? (?:additions|findings)|(?:supplemental|additional|appended) (?:retrospective|review)|retrospective addendum|本轮新增|追加复盘|补充复盘|补审)`)

// RetrospectiveEntries 只检查原台账的结构、日期和显式资格，不生成复盘判断。
func RetrospectiveEntries(body []byte, now time.Time) ([]RetrospectiveEntry, error) {
	if !utf8.Valid(body) {
		return nil, fmt.Errorf("复盘不是有效 UTF-8")
	}
	text := string(body)
	matches := reviewedAtRE.FindAllStringSubmatch(text, -1)
	if len(matches) != 1 {
		return nil, fmt.Errorf("复盘必须恰有一个 reviewed-at 标记")
	}
	raw := matches[0][1]
	parsed, err := time.Parse("2006-01-02", raw)
	if err != nil && timestamp(raw) {
		parsed, err = time.Parse(time.RFC3339Nano, raw)
	}
	if err != nil {
		return nil, &protocol.FormatError{Cause: fmt.Errorf("复盘 reviewed-at=%q 必须为 YYYY-MM-DD（例如 2026-11-05）或带时区 RFC3339Nano（例如 2026-11-05T12:00:00+08:00）；原值未自动转换", raw)}
	}
	if parsed.Format("2006-01-02") != now.Format("2006-01-02") {
		return nil, fmt.Errorf("复盘 reviewed-at 不是归档当日: %s", raw)
	}
	lines := strings.Split(strings.ReplaceAll(text, "\r\n", "\n"), "\n")
	start, end := -1, -1
	for i, line := range lines {
		if strings.TrimSpace(line) == RetrospectiveStart {
			if start != -1 {
				return nil, fmt.Errorf("重复 problem-index:v2")
			}
			start = i
		}
		if strings.TrimSpace(line) == RetrospectiveEnd {
			if end != -1 {
				return nil, fmt.Errorf("重复 problem-index:v2")
			}
			end = i
		}
	}
	if start < 0 && end < 0 && strings.TrimSpace(reviewedAtRE.ReplaceAllString(text, "")) == "" {
		return []RetrospectiveEntry{}, nil
	}
	if start < 0 || end <= start {
		return nil, fmt.Errorf("需要有序且唯一 problem-index:v2 标记")
	}
	entries := []RetrospectiveEntry{}
	rows := map[string]bool{}
	header := false
	for _, line := range lines[start+1 : end] {
		if !strings.HasPrefix(strings.TrimSpace(line), "|") {
			continue
		}
		cells := strings.Split(strings.Trim(strings.TrimSpace(line), "|"), "|")
		for i := range cells {
			cells[i] = strings.TrimSpace(cells[i])
		}
		if len(cells) < 6 {
			continue
		}
		if strings.EqualFold(cells[0], "problem") || strings.EqualFold(cells[0], "id") {
			set := map[string]bool{}
			for _, v := range cells {
				set[strings.ToLower(v)] = true
			}
			for _, v := range []string{"knowledge_type", "reuse_scope", "index_decision", "confidence", "importance"} {
				if !set[v] {
					return nil, fmt.Errorf("复盘表缺少 %s", v)
				}
			}
			header = true
			continue
		}
		if !strings.HasPrefix(cells[0], "RET-") {
			continue
		}
		if len(cells) < 11 || !retrospectiveIDRE.MatchString(cells[0]) || rows[cells[0]] {
			return nil, fmt.Errorf("复盘行无效或重复: %s", cells[0])
		}
		rows[cells[0]] = true
		links := detailLinkRE.FindAllStringSubmatch(cells[10], -1)
		if len(links) != 1 {
			return nil, fmt.Errorf("%s 必须链接自己的本地详情", cells[0])
		}
		entries = append(entries, RetrospectiveEntry{cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6], cells[7], cells[8], cells[9], cells[10], strings.TrimPrefix(links[0][1], "#")})
	}
	if !header {
		return nil, fmt.Errorf("复盘缺少 v2 资格表头")
	}
	type section struct {
		line, level, start int
		id, slug           string
	}
	sections := []section{}
	details := map[string]section{}
	anchors := map[string]int{}
	prose := retrospectiveProse(lines)
	for i, p := range prose {
		for _, tag := range anchorTagRE.FindAllString(p.text, -1) {
			seen := map[string]bool{}
			for _, m := range anchorAttributeRE.FindAllStringSubmatch(tag, -1) {
				value := html.UnescapeString(m[1] + m[2] + m[3])
				if value == "" || seen[value] {
					continue
				}
				seen[value] = true
				if _, ok := anchors[value]; ok {
					return nil, fmt.Errorf("重复详情锚点: %s", value)
				}
				anchors[value] = p.line
			}
		}
		m := retrospectiveHeadingRE.FindStringSubmatch(p.text)
		if m == nil {
			continue
		}
		title := m[2]
		if batchTitleRE.MatchString(batchPrefixRE.ReplaceAllString(title, "")) {
			return nil, fmt.Errorf("禁止按修订批次追加复盘章节: %s", title)
		}
		begin := p.line
		for j := i - 1; j >= 0; j-- {
			prior := strings.TrimSpace(prose[j].text)
			if prior == "" {
				continue
			}
			if anchorTagRE.MatchString(prior) && strings.TrimSpace(anchorOnlyRE.ReplaceAllString(prior, "")) == "" {
				begin = prose[j].line
			} else {
				break
			}
		}
		sec := section{line: p.line, level: len(m[1]), start: begin}
		if id := detailIDRE.FindStringSubmatch(title); id != nil {
			sec.id = id[1]
			if !rows[sec.id] {
				return nil, fmt.Errorf("孤立详情: %s", sec.id)
			}
			if _, ok := details[sec.id]; ok {
				return nil, fmt.Errorf("重复详情: %s", sec.id)
			}
			var slug strings.Builder
			for _, r := range strings.ToLower(title) {
				if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' {
					slug.WriteRune(r)
				} else if r == ' ' {
					slug.WriteRune('-')
				}
			}
			sec.slug = slug.String()
			details[sec.id] = sec
		}
		sections = append(sections, sec)
	}
	for _, entry := range entries {
		detail, ok := details[entry.ID]
		if !ok {
			return nil, fmt.Errorf("%s 缺少详情", entry.ID)
		}
		end := len(lines) + 1
		for _, sec := range sections {
			if sec.line > detail.line && (sec.level <= detail.level || sec.id != "") && sec.start < end {
				end = sec.start
			}
		}
		at, ok := anchors[entry.Anchor]
		if entry.Anchor != detail.slug && !(ok && at >= detail.start && at < end) {
			return nil, fmt.Errorf("%s 锚点不属于自身详情: %s", entry.ID, entry.Anchor)
		}
	}
	return entries, nil
}

type proseLine struct {
	line int
	text string
}

func retrospectiveProse(lines []string) []proseLine {
	out := []proseLine{}
	fence := ""
	comment := false
	for i, line := range lines {
		trim := strings.TrimLeft(line, " ")
		indent := len(line) - len(trim)
		if fence != "" {
			if indent <= 3 && strings.Trim(trim, string(fence[0])+" \t") == "" && strings.Count(trim, string(fence[0])) >= len(fence) {
				fence = ""
			}
			continue
		}
		if !comment && indent <= 3 && (strings.HasPrefix(trim, "```") || strings.HasPrefix(trim, "~~~")) {
			size := 0
			for size < len(trim) && trim[size] == trim[0] {
				size++
			}
			fence = trim[:size]
			continue
		}
		visible := ""
		rest := line
		for rest != "" {
			if comment {
				at := strings.Index(rest, "-->")
				if at < 0 {
					break
				}
				rest = rest[at+3:]
				comment = false
			} else {
				at := strings.Index(rest, "<!--")
				if at < 0 {
					visible += rest
					break
				}
				visible += rest[:at]
				rest = rest[at+4:]
				comment = true
			}
		}
		out = append(out, proseLine{i + 1, visible})
	}
	return out
}
