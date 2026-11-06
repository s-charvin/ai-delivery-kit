package checks

import (
	"encoding/json"
	"fmt"
	"math"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

var uiID = regexp.MustCompile(`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`)
var uiDimensions = []string{"state", "layout", "content", "interaction", "motion", "assets", "theme", "accessibility", "platform", "performance"}
var uiImages = []string{".png", ".jpg", ".jpeg", ".webp"}
var uiPreviews = []string{".png", ".jpg", ".jpeg", ".webp", ".html"}

type uiValidator struct {
	s      model.Snapshot
	errors []error
	path   string
}

func uiSame(a, b any) bool       { x, ok := a.(string); y, yes := b.(string); return ok && yes && x == y }
func uiMap(v any) map[string]any { m, _ := v.(map[string]any); return m }
func uiString(v any) string      { s, _ := v.(string); return s }
func uiList(v any) []any         { a, _ := v.([]any); return a }
func (v *uiValidator) require(ok bool, p, msg string) {
	if !ok {
		v.errors = append(v.errors, fmt.Errorf("%s: %s", p, msg))
	}
}
func (v *uiValidator) text(m map[string]any, p string, keys ...string) {
	for _, k := range keys {
		v.require(nonempty(m[k]), p+"."+k, "必须为非空文本")
	}
}
func (v *uiValidator) enum(x any, p string, values ...string) {
	v.require(contains(values, uiString(x)), p, "未知或缺少枚举值")
}
func (v *uiValidator) rows(x any, p string, nonempty bool) []any {
	a, ok := x.([]any)
	v.require(ok && (!nonempty || len(a) > 0), p, "必须为数组且满足非空要求")
	return a
}
func (v *uiValidator) object(x any, p string) map[string]any {
	m, ok := x.(map[string]any)
	v.require(ok, p, "必须为对象")
	return m
}
func (v *uiValidator) id(x any, p string, seen map[string]bool) string {
	id := uiString(x)
	v.require(uiID.MatchString(id), p, "必须为 kebab-case")
	v.require(!seen[id], p, "ID 重复")
	seen[id] = true
	return id
}
func uiNumber(x any) (float64, bool) {
	n, ok := x.(json.Number)
	if !ok {
		return 0, false
	}
	f, e := n.Float64()
	return f, e == nil && !math.IsInf(f, 0) && !math.IsNaN(f)
}
func (v *uiValidator) positive(x any, p string) {
	n, ok := uiNumber(x)
	v.require(ok && n > 0, p, "必须为正数")
}
func (v *uiValidator) strings(x any, p string, required bool) map[string]bool {
	out := map[string]bool{}
	for _, x := range v.rows(x, p, required) {
		v.require(nonempty(x), p, "必须为非空字符串数组")
		s := uiString(x)
		out[s] = true
	}
	return out
}
func (v *uiValidator) source(m map[string]any, p, mode string, node bool) {
	v.enum(m["evidence_origin"], p+".evidence_origin", "figma", "requirement", "project", "user-decision")
	v.text(m, p, "source_ref")
	if mode == "runtime-baseline" {
		v.require(m["evidence_origin"] != "figma", p, "runtime-baseline 禁止 Figma 来源")
	}
	if node && m["evidence_origin"] == "figma" {
		v.text(m, p, "source_node")
	}
}
func (v *uiValidator) confirmation(x any, p string, hash any) {
	m := v.object(x, p)
	v.enum(m["status"], p+".status", "confirmed", "waived")
	v.text(m, p, "confirmed_by")
	v.time(m["confirmed_at"], p+".confirmed_at")
	if m["status"] == "waived" {
		v.text(m, p, "note")
	}
	if hash != nil {
		v.require(hexDigest.MatchString(uiString(m["reviewed_preview_sha256"])) && m["reviewed_preview_sha256"] == hash, p, "确认未绑定当前 preview_sha256")
	}
}
func (v *uiValidator) file(pv, h any, p string, suffixes []string) string {
	rel := uiString(pv)
	normalized, err := workspace.NormalizePath(rel)
	v.require(err == nil && rel != "", p, "必须为仓库相对文件路径")
	if err != nil || rel == "" {
		return ""
	}
	f, ok, err := workspace.Identity(v.s, normalized)
	v.require(err == nil && ok && f.Kind == "file", p, "文件未登记、缺失或不可读")
	resolved := f.ResolvedPath
	if resolved == "" {
		resolved = normalized
	}
	if suffixes != nil {
		v.require(contains(suffixes, strings.ToLower(path.Ext(resolved))), p, "文件扩展名不符合宿主要求")
	}
	if h != nil {
		v.require(hexDigest.MatchString(uiString(h)) && f.SHA256 != nil && *f.SHA256 == uiString(h), p, "文件 SHA-256 无效或已漂移")
	} else {
		v.require(false, p, "缺少 SHA-256")
	}
	return resolved
}
func (v *uiValidator) outsideGovernance(pv any, p string) string {
	rel := uiString(pv)
	n, e := workspace.NormalizePath(rel)
	v.require(e == nil && rel != "", p, "必须为仓库相对路径")
	if e != nil {
		return ""
	}
	f, ok, err := workspace.Identity(v.s, n)
	v.require(err == nil && ok, p, "路径身份未登记")
	resolved := f.ResolvedPath
	if resolved == "" {
		resolved = n
	}
	dr, _ := filepath.Rel(v.s.Workspace().ProjectRoot, v.s.Workspace().DeliveryRoot)
	for _, root := range []string{".ai-delivery", filepath.ToSlash(dr)} {
		v.require(n != root && !strings.HasPrefix(n, root+"/") && resolved != root && !strings.HasPrefix(resolved, root+"/"), p, "必须位于治理目录外")
	}
	return resolved
}

type missingContractError struct{ path string }

func (e *missingContractError) Error() string { return e.path + ": 缺少合同" }
func (v *uiValidator) time(value any, field string) {
	if !timestamp(value) {
		v.errors = append(v.errors, &protocol.FormatError{Path: v.path + "#/" + field, Cause: fmt.Errorf("实际类型=%T，实际值=%v；%s", value, value, timestampFormat)})
	}
}
func (v *uiValidator) document(p string) map[string]any {
	b, ok := v.s.Document(p)
	if !ok {
		v.errors = append(v.errors, &missingContractError{path: p})
		return nil
	}
	m, e := protocol.Object(b)
	if e != nil {
		v.errors = append(v.errors, &protocol.FormatError{Path: p, Cause: e})
	}
	return m
}
func errorStrings(issues []error) []string {
	out := make([]string, 0, len(issues))
	for _, e := range issues {
		out = append(out, e.Error())
	}
	sort.Strings(out)
	return out
}

// UIReferences 仅抽取当前 UI 协议的文件身份；外部 source_ref 不是文件路径。
// 读取由 Collect 的同一个 workspace.Reader 完成，校验器本身没有文件 IO。
func UIReferences(data map[string]any) []string {
	refs := map[string]bool{}
	add := func(m map[string]any, keys ...string) {
		for _, k := range keys {
			if p, ok := m[k].(string); ok && p != "" {
				refs[p] = true
			}
		}
	}
	for _, u := range uiList(data["units"]) {
		m := uiMap(u)
		add(m, "component_path", "golden_test")
		add(uiMap(m["motion_decision"]), "preview_path")
		for _, r := range uiList(m["render_inputs"]) {
			add(uiMap(r), "path")
		}
		for _, s := range uiList(m["scenarios"]) {
			row := uiMap(s)
			add(row, "preview_path")
			add(uiMap(row["host_binding"]), "host_component_path", "evidence_root")
		}
	}
	for _, key := range []string{"scenarios", "motion_acceptance"} {
		for _, row := range uiList(data[key]) {
			for _, e := range uiList(uiMap(row)["evidence"]) {
				add(uiMap(e), "path", "reference_path", "candidate_path", "diff_path", "test_path", "assertion_report_path", "host_component_path")
			}
		}
	}
	out := []string{}
	for p := range refs {
		out = append(out, p)
	}
	sort.Strings(out)
	return out
}
func ValidateUIIndex(s model.Snapshot, indexPath, mode string) []string {
	return errorStrings(validateUIIndex(s, indexPath, mode))
}
func validateUIIndex(s model.Snapshot, indexPath, mode string) []error {
	v := uiValidator{s: s, path: indexPath}
	if data := v.document(indexPath); data != nil {
		v.index(data, mode)
	}
	sort.SliceStable(v.errors, func(i, j int) bool { return v.errors[i].Error() < v.errors[j].Error() })
	return v.errors
}
func ValidateUIAcceptance(s model.Snapshot, indexPath, acceptancePath string) []string {
	return errorStrings(validateUIAcceptance(s, indexPath, acceptancePath))
}
func validateUIAcceptance(s model.Snapshot, indexPath, acceptancePath string) []error {
	v := uiValidator{s: s, path: acceptancePath}
	index, data := v.document(indexPath), v.document(acceptancePath)
	if index != nil && data != nil {
		v.acceptance(index, data, indexPath)
	}
	sort.SliceStable(v.errors, func(i, j int) bool { return v.errors[i].Error() < v.errors[j].Error() })
	return v.errors
}
func uiLabel(p string, i int) string { return fmt.Sprintf("%s[%d]", p, i) }
