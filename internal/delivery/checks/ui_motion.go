package checks

import (
	"bytes"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"image/gif"
	"path"
	"strings"
)

func (v *uiValidator) motion(raw any, p string) {
	m := v.object(raw, p)
	decision := uiString(m["decision"])
	v.enum(decision, p+".decision", "animated", "static")
	v.enum(m["verification_mode"], p+".verification_mode", "runtime", "behavior", "manual", "not_applicable")
	has := m["preview_path"] != nil || m["preview_sha256"] != nil
	if decision == "animated" {
		v.require(m["verification_mode"] != "not_applicable", p, "animated 需要后续验证方式")
		if !has {
			v.text(m, p, "preview_unavailable_reason")
		} else {
			v.require(!nonempty(m["preview_unavailable_reason"]), p, "已有预览不能声明不可用")
		}
	}
	if decision == "static" {
		v.require(m["verification_mode"] == "not_applicable", p, "static verification_mode 必须为 not_applicable")
		v.require(!has && !nonempty(m["preview_unavailable_reason"]), p, "static 禁止动效预览或不可用理由")
		v.require(uiMap(m["confirmation"])["status"] == "confirmed", p, "static 必须明确确认，不能豁免")
	}
	var hash any
	if has {
		hash = m["preview_sha256"]
		v.file(m["preview_path"], hash, p+".preview_path", []string{".gif"})
		previewPath, _ := workspace.NormalizePath(uiString(m["preview_path"]))
		b, _ := v.s.Document(previewPath)
		g, e := gif.DecodeAll(bytes.NewReader(b))
		v.require(e == nil && g != nil && len(g.Image) > 1, p, "动效预览必须为有效多帧 GIF")
	}
	v.confirmation(m["confirmation"], p+".confirmation", hash)
	v.text(uiMap(m["confirmation"]), p+".confirmation", "note")
}
func (v *uiValidator) motionAcceptance(rows any, units map[string]map[string]any, previews map[string]bool) {
	seen := map[string]bool{}
	for i, raw := range v.rows(rows, "motion_acceptance", false) {
		p := uiLabel("motion_acceptance", i)
		r := v.object(raw, p)
		id := uiString(r["unit_id"])
		m, ok := units[id]
		v.require(ok && !seen[id], p, "未知或重复 unit_id")
		seen[id] = true
		if !ok {
			continue
		}
		decision := m["decision"]
		has := nonempty(m["preview_path"])
		v.enum(r["result"], p+".result", "passed", "waived")
		kinds := map[string]bool{}
		evidence := v.rows(r["evidence"], p+".evidence", false)
		for j, raw := range evidence {
			q := uiLabel(p+".evidence", j)
			e := v.object(raw, q)
			kind := uiString(e["kind"])
			kinds[kind] = true
			v.enum(kind, q+".kind", "motion", "test", "manual")
			v.text(e, q, "summary")
			switch kind {
			case "motion":
				v.require(has && uiSame(e["path"], m["preview_path"]) && uiSame(e["sha256"], m["preview_sha256"]), q, "motion 必须绑定当前动效预览")
				v.file(e["path"], e["sha256"], q, []string{".gif"})
				v.text(e, q, "command")
			case "test":
				v.evidence(e, nil, q)
				v.require(!v.motionTestIsPreview(uiString(e["path"]), previews), q, "静态或动效预览不能代替测试报告（含别名及同内容副本）")
			case "manual":
				v.manual(e, q)
			}
		}
		if r["result"] == "passed" {
			v.require(len(evidence) > 0, p, "passed 缺少证据")
			if decision == "animated" && has {
				v.require(kinds["motion"], p, "需要独立 motion 证据")
			} else {
				v.require(!kinds["motion"], p, "无动效预览时禁止 motion 证据")
				v.require(kinds["test"] || kinds["manual"], p, "需要 test/manual 动效或 static 确认")
			}
			if decision == "static" {
				v.require(!kinds["motion"], p, "static 禁止 motion 证据")
			}
		} else if r["result"] == "waived" {
			v.waiver(r, p)
			v.require(decision != "static", p, "static/no-motion 不能豁免")
		}
	}
	for id := range units {
		v.require(seen[id], "motion_acceptance", "缺少 unit: "+id)
	}
}

// 文件有效性已由 evidence 校验；此处只判断报告是否冒用已冻结的视觉证据。
// 使用 Reader 的实际终点及内容身份，不相信声明后缀或声明 hash。
func (v *uiValidator) motionTestIsPreview(p string, previews map[string]bool) bool {
	normalized, err := workspace.NormalizePath(p)
	if err != nil {
		return false
	}
	file, observed, err := workspace.Identity(v.s, normalized)
	if err != nil || !observed || file.Kind != "file" {
		return false
	}
	for _, candidate := range []string{normalized, file.ResolvedPath} {
		if contains(uiImages, strings.ToLower(path.Ext(candidate))) || strings.EqualFold(path.Ext(candidate), ".gif") {
			return true
		}
	}
	for preview := range previews {
		previewPath, err := workspace.NormalizePath(preview)
		if err != nil {
			continue
		}
		if normalized == previewPath {
			return true
		}
		visual, observed, err := workspace.Identity(v.s, previewPath)
		if err != nil || !observed || visual.Kind != "file" {
			continue
		}
		if file.ResolvedPath != "" && file.ResolvedPath == visual.ResolvedPath || file.SHA256 != nil && visual.SHA256 != nil && *file.SHA256 == *visual.SHA256 {
			return true
		}
	}
	return false
}
