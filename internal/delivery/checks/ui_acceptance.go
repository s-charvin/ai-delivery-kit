package checks

import (
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"strings"
)

func (v *uiValidator) manual(m map[string]any, p string) {
	v.text(m, p, "reviewed_by")
	v.time(m["reviewed_at"], p+".reviewed_at")
}
func (v *uiValidator) waiver(m map[string]any, p string) {
	v.text(m, p, "note", "waived_by")
	v.time(m["waived_at"], p+".waived_at")
}
func (v *uiValidator) evidence(e, scenario map[string]any, p string) {
	kind := uiString(e["kind"])
	v.enum(kind, p+".kind", "preview", "test", "manual", "image-diff", "runtime-capture")
	v.text(e, p, "summary")
	switch kind {
	case "preview", "test":
		var suffix []string
		if kind == "preview" {
			suffix = uiPreviews
			v.require(uiSame(e["path"], scenario["preview_path"]) && uiSame(e["sha256"], scenario["preview_sha256"]), p, "preview 必须匹配索引场景")
		}
		v.file(e["path"], e["sha256"], p, suffix)
		v.text(e, p, "command")
	case "manual":
		v.manual(e, p)
	case "image-diff":
		for _, role := range []string{"reference", "candidate", "diff"} {
			v.file(e[role+"_path"], e[role+"_sha256"], p+"."+role, uiImages)
		}
		v.text(e, p, "metric", "command")
		threshold, tok := uiNumber(e["threshold"])
		actual, aok := uiNumber(e["actual"])
		v.require(tok && threshold >= 0, p, "threshold 必须为非负有限数")
		v.require(aok && actual >= 0 && (!tok || actual <= threshold), p, "actual 无效或超过 threshold")
	case "runtime-capture":
		v.file(e["path"], e["sha256"], p+".path", uiImages)
		resolved := v.outsideGovernance(e["path"], p+".path")
		v.file(e["test_path"], e["test_sha256"], p+".test_path", nil)
		v.file(e["assertion_report_path"], e["assertion_report_sha256"], p+".assertion_report_path", []string{".json"})
		v.outsideGovernance(e["assertion_report_path"], p+".assertion_report_path")
		v.text(e, p, "command")
		v.manual(e, p)
		v.require(uiSame(e["reviewed_capture_sha256"], e["sha256"]), p, "评审未绑定当前 capture hash")
		h := v.object(scenario["host_binding"], p+".host_binding")
		for _, k := range []string{"host_component_path", "entrypoint_ref", "capture_boundary_ref"} {
			v.require(uiSame(e[k], h[k]), p, "host_binding/区域不匹配: "+k+"，需重新取证")
		}
		root, rootErr := workspace.NormalizePath(uiString(h["evidence_root"]))
		capture, captureErr := workspace.NormalizePath(uiString(e["path"]))
		v.require(rootErr == nil && captureErr == nil && strings.HasPrefix(capture, strings.TrimSuffix(root, "/")+"/"), p, "截图不在 indexed evidence_root")
		resolvedRoot := v.outsideGovernance(root, p+".evidence_root")
		v.require(resolvedRoot != "" && strings.HasPrefix(resolved, strings.TrimSuffix(resolvedRoot, "/")+"/"), p, "截图解析后越出 indexed evidence_root")
		landmarks := v.strings(e["verified_landmarks"], p+".verified_landmarks", false)
		constraints := v.strings(e["verified_constraints"], p+".verified_constraints", false)
		for _, l := range uiList(h["required_landmarks"]) {
			v.require(landmarks[uiString(l)], p, "缺少 required landmark: "+uiString(l))
		}
		for _, c := range uiList(h["spatial_constraints"]) {
			id := uiString(uiMap(c)["constraint_id"])
			v.require(constraints[id], p, "缺少 required constraint: "+id)
		}
	}
}
func (v *uiValidator) acceptance(index, data map[string]any, indexPath string) {
	if e := protocol.RequireVersion(data, "schema_version", "visual_acceptance"); e != nil {
		v.errors = append(v.errors, &protocol.FormatError{Path: v.path + "#/schema_version", Cause: e})
	}
	v.time(data["generated_at"], "generated_at")
	v.file(indexPath, data["ui_truth_index_sha256"], "ui_truth_index_sha256", []string{".json"})
	scenarios, units := map[string]map[string]any{}, map[string]map[string]any{}
	previews := map[string]bool{}
	for _, raw := range uiList(index["units"]) {
		u := uiMap(raw)
		m := uiMap(u["motion_decision"])
		units[uiString(u["unit_id"])] = m
		if nonempty(m["preview_path"]) {
			previews[uiString(m["preview_path"])] = true
		}
		for _, raw := range uiList(u["scenarios"]) {
			s := uiMap(raw)
			scenarios[uiString(s["scenario_id"])] = s
			if nonempty(s["preview_path"]) {
				previews[uiString(s["preview_path"])] = true
			}
		}
	}
	seen := map[string]bool{}
	for i, raw := range v.rows(data["scenarios"], "scenarios", false) {
		p := uiLabel("scenarios", i)
		r := v.object(raw, p)
		id := uiString(r["scenario_id"])
		s, ok := scenarios[id]
		v.require(ok && !seen[id], p, "未知或重复 scenario_id，需重新取证")
		seen[id] = true
		if !ok {
			continue
		}
		v.enum(r["result"], p+".result", "passed", "waived")
		rows := v.rows(r["evidence"], p+".evidence", false)
		kinds := map[string]bool{}
		for j, x := range rows {
			q := uiLabel(p+".evidence", j)
			e := v.object(x, q)
			kinds[uiString(e["kind"])] = true
			v.evidence(e, s, q)
		}
		if r["result"] == "passed" {
			v.require(len(rows) > 0, p, "passed 缺少证据")
			scope := s["evidence_scope"]
			if scope == "host-static" || scope == "host-runtime" {
				v.require(kinds["runtime-capture"], p, "host scope 必须有 runtime-capture")
			}
			if scope == "component-only" {
				v.require(!kinds["runtime-capture"], p, "component-only 禁止 runtime-capture")
			}
			if s["review_mode"] == "visual" || s["review_mode"] == "both" {
				v.require(kinds["preview"] || kinds["image-diff"] || kinds["runtime-capture"], p, "缺少视觉证据")
			}
			if s["review_mode"] == "behavior" || s["review_mode"] == "both" {
				v.require(kinds["test"] || kinds["manual"], p, "缺少行为证据")
			}
		} else if r["result"] == "waived" {
			v.waiver(r, p)
		}
	}
	for id := range scenarios {
		v.require(seen[id], "scenarios", "缺少场景结果: "+id)
	}
	v.motionAcceptance(data["motion_acceptance"], units, previews)
}
