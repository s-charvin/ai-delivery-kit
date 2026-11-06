package checks

import (
	"crypto/sha256"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode"
)

const behaviorStart = "<!-- ai-delivery:behavior-contract:start -->"
const behaviorEnd = "<!-- ai-delivery:behavior-contract:end -->"
const userDecisions = "<!-- ai-delivery:user-decisions -->"
const timestampFormat = "必须使用带时区的 RFC3339 时间（可含纳秒），例如 2026-11-05T12:00:00+08:00；原值未自动转换"

var behaviorMarkers = []string{"<!-- ai-delivery:behavior-contract:scope -->", "<!-- ai-delivery:behavior-contract:behavior -->", "<!-- ai-delivery:behavior-contract:acceptance -->", "<!-- ai-delivery:behavior-contract:traceability -->"}
var scaffold = regexp.MustCompile(`\{\{[^}\n]+\}\}|\.\.\.`)
var goPackageSegment = regexp.MustCompile(`^[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?$`)
var hexDigest = regexp.MustCompile(`^[0-9a-f]{64}$`)
var timestampSyntax = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$`)

func goPackageBoundary(r rune) bool {
	// 点和斜杠不是边界，避免把四点或额外路径截成合法 suffix。
	return unicode.IsSpace(r) || strings.ContainsRune("`\"'()[]{}<>,;:|，。；：！？（）【】《》、", r)
}

func isGoRecursivePackage(token string) bool {
	if !strings.HasSuffix(token, "/...") {
		return false
	}
	segments := strings.Split(strings.TrimSuffix(token, "/..."), "/")
	relative := segments[0] == "." || segments[0] == ".."
	for _, segment := range segments {
		// 相对包路径中的点目录可出现在任意位置，不先清理路径而隐藏空段或占位符。
		if relative && (segment == "." || segment == "..") {
			continue
		}
		if !goPackageSegment.MatchString(segment) {
			return false
		}
	}
	return true
}

func hasScaffoldPlaceholder(text string) bool {
	for _, match := range scaffold.FindAllStringIndex(text, -1) {
		if text[match[0]:match[1]] != "..." {
			return true
		}
		if match[1] < len(text) && strings.IndexFunc(text[match[1]:], goPackageBoundary) != 0 {
			return true
		}
		prefix := text[:match[0]]
		if boundary := strings.LastIndexFunc(prefix, goPackageBoundary); boundary >= 0 {
			prefix = strings.TrimLeftFunc(prefix[boundary:], goPackageBoundary)
		}
		// 仅豁免完整 Go 递归包路径末尾的这一个命中，继续检查同句其他占位符。
		if !isGoRecursivePackage(prefix + "...") {
			return true
		}
	}
	return false
}

func ids(text, prefix string) []string {
	seen := map[string]bool{}
	for _, id := range regexp.MustCompile(`\b`+prefix+`-[0-9]{3,}\b`).FindAllString(text, -1) {
		seen[id] = true
	}
	out := make([]string, 0, len(seen))
	for id := range seen {
		out = append(out, id)
	}
	sort.Strings(out)
	return out
}
func AcceptanceIDs(raw []byte) ([]string, error) {
	body, err := markedBody(raw, behaviorStart, behaviorEnd)
	if err != nil {
		return nil, err
	}
	parts, err := sections(body, behaviorMarkers)
	if err != nil {
		return nil, err
	}
	return ids(prose(parts[behaviorMarkers[2]]), "AC"), nil
}
func nonempty(v any) bool { s, ok := v.(string); return ok && strings.TrimSpace(s) != "" }
func timestamp(v any) bool {
	s, ok := v.(string)
	if !ok || !timestampSyntax.MatchString(s) {
		return false
	}
	_, err := time.Parse(time.RFC3339Nano, s)
	return err == nil
}

// ValidateDesign 校验目标所需的当前设计与评审，不把旧状态的 review=none 规则套到目标。
func ValidateDesign(raw []byte, entry map[string]any) []string {
	return errorStrings(validateDesign(raw, entry))
}
func validateDesign(raw []byte, entry map[string]any) []error {
	errors := []string{}
	issues := []error{}
	finish := func() []error {
		for _, message := range errors {
			issues = append(issues, fmt.Errorf("%s", message))
		}
		return issues
	}
	if _, err := NativeMethods(raw); err != nil {
		errors = append(errors, err.Error())
	}
	body, err := markedBody(raw, behaviorStart, behaviorEnd)
	if err != nil {
		errors = append(errors, err.Error())
	} else {
		parts, err := sections(body, behaviorMarkers)
		if err != nil {
			errors = append(errors, err.Error())
		} else {
			bs, acs := ids(prose(parts[behaviorMarkers[1]]), "B"), ids(prose(parts[behaviorMarkers[2]]), "AC")
			if len(bs) == 0 || len(acs) == 0 {
				errors = append(errors, "行为合同必须包含 B-### 与 AC-###")
			}
			trace := prose(parts[behaviorMarkers[3]])
			for _, id := range append(bs, acs...) {
				if !contains(ids(trace, strings.Split(id, "-")[0]), id) {
					errors = append(errors, "traceability 缺少 "+id)
				}
			}
		}
		if hasScaffoldPlaceholder(prose(body)) {
			errors = append(errors, "行为合同含未解决占位符")
		}
	}
	text := string(raw)
	if strings.Count(text, userDecisions) != 1 {
		errors = append(errors, "需要唯一 user-decisions 标记")
	}
	if err := markerPositions(text, []string{userDecisions}); err != nil {
		errors = append(errors, err.Error())
	}
	if entry["user_decision_required"] == true {
		if len(ids(prose(text), "D")) == 0 {
			errors = append(errors, "人工决定必须有 D-###")
		}
		if i := strings.Index(text, userDecisions); i >= 0 && hasScaffoldPlaceholder(prose(text[i:])) {
			errors = append(errors, "人工决定包含占位符")
		}
	}
	errors = append(errors, validateStateFlow(raw, entry["state_flow_required"] == true)...)
	review, ok := entry["design_review"].(map[string]any)
	if !ok {
		issues = append(issues, &protocol.FormatError{Cause: fmt.Errorf("design_review 实际类型=%T，实际值=%v；当前要求 JSON 对象", entry["design_review"], entry["design_review"])})
		return finish()
	}
	expected := "self"
	if entry["user_decision_required"] == true {
		expected = "human"
	}
	if review["review_mode"] != expected {
		errors = append(errors, "当前设计要求 design_review.review_mode="+expected)
	}
	digest, _ := review["reviewed_design_sha256"].(string)
	if !hexDigest.MatchString(digest) || digest != fmt.Sprintf("%x", sha256.Sum256(raw)) {
		errors = append(errors, "design_review 摘要未绑定当前 design.md")
	}
	if !timestamp(review["reviewed_at"]) {
		issues = append(issues, &protocol.FormatError{Cause: fmt.Errorf("reviewed_at 实际类型=%T，实际值=%v；%s", review["reviewed_at"], review["reviewed_at"], timestampFormat)})
	}
	if !nonempty(review["reviewed_by"]) {
		errors = append(errors, "reviewed_by 不能为空")
	}
	return finish()
}
func contains(xs []string, x string) bool {
	for _, v := range xs {
		if v == x {
			return true
		}
	}
	return false
}

func validateStateFlow(raw []byte, required bool) []string {
	const start = "<!-- ai-delivery:state-flow:start -->"
	const end = "<!-- ai-delivery:state-flow:end -->"
	if !required && !strings.Contains(string(raw), start) && !strings.Contains(string(raw), end) {
		return nil
	}
	body, err := markedBody(raw, start, end)
	if err != nil {
		return []string{err.Error()}
	}
	names := []string{"taxonomy", "mvi-loop", "lifecycle", "projection", "matrix", "sequences", "invariants", "traceability"}
	markers := []string{}
	for _, name := range names {
		markers = append(markers, "<!-- ai-delivery:state-flow:"+name+" -->")
	}
	parts, err := sections(body, markers)
	if err != nil {
		return []string{err.Error()}
	}
	errors := []string{}
	for _, name := range []string{"stale-result", "concurrency"} {
		if strings.Count(body, "<!-- ai-delivery:state-flow:"+name+" -->") != 1 {
			errors = append(errors, "state-flow 缺少策略 "+name)
		}
	}
	blocks := regexp.MustCompile("(?si)```mermaid[ \\t]*\\n(.*?)```").FindAllStringSubmatch(body, -1)
	diagrams := ""
	for _, b := range blocks {
		diagrams += b[1] + "\n"
	}
	for _, kind := range []string{"flowchart", "stateDiagram-v2"} {
		if !regexp.MustCompile(`(?mi)^\s*` + kind + `\b`).MatchString(diagrams) {
			errors = append(errors, "state-flow 缺少 Mermaid "+kind)
		}
	}
	matrix := parts[markers[4]]
	ts := regexp.MustCompile(`\bT-[0-9]{3,}\b`).FindAllString(matrix, -1)
	seen := map[string]bool{}
	if len(ts) == 0 {
		errors = append(errors, "迁移矩阵必须有 T-###")
	}
	for _, id := range ts {
		if seen[id] {
			errors = append(errors, "迁移 ID 重复: "+id)
		}
		seen[id] = true
	}
	for _, id := range ids(diagrams, "T") {
		if !seen[id] {
			errors = append(errors, "图引用未知迁移: "+id)
		}
	}
	if !regexp.MustCompile(`(?mi)^\s*sequenceDiagram\b`).MatchString(diagrams) && !strings.Contains(parts[markers[5]], "not_applicable") {
		errors = append(errors, "时序图需有 sequenceDiagram 或 not_applicable 理由")
	}
	if !strings.Contains(body, "UiEffect") {
		errors = append(errors, "state-flow 必须区分 UiEffect")
	}
	return errors
}

// ValidateDesignScenarios 以同一已冻结索引核对设计中的精确场景 ID，不把子串当作引用。
func ValidateDesignScenarios(s model.Snapshot, designPath, indexPath string) []string {
	raw, ok := s.Document(indexPath)
	if !ok {
		return nil
	} // 索引缺失由同一 ui_index 检查报告。
	index, err := protocol.Object(raw)
	if err != nil {
		return []string{err.Error()}
	}
	design, _ := s.Document(designPath)
	errors := []string{}
	for _, u := range uiList(index["units"]) {
		for _, scenario := range uiList(uiMap(u)["scenarios"]) {
			id := uiString(uiMap(scenario)["scenario_id"])
			if id == "" {
				continue
			}
			token := regexp.MustCompile(`(^|[^a-z0-9-])` + regexp.QuoteMeta(id) + `($|[^a-z0-9-])`)
			if !token.Match(design) {
				errors = append(errors, "design.md 必须引用 indexed scenario_id "+id)
			}
		}
	}
	return errors
}
