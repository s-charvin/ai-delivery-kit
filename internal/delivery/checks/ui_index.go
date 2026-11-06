package checks

import (
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"strings"
)

func (v *uiValidator) index(data map[string]any, mode string) {
	if e := protocol.RequireVersion(data, "schema_version", "ui_index"); e != nil {
		v.errors = append(v.errors, &protocol.FormatError{Path: v.path + "#/schema_version", Cause: e})
	}
	v.enum(data["ui_truth_mode"], "ui_truth_mode", "figma", "runtime-baseline")
	v.require(data["ui_truth_mode"] == mode, "ui_truth_mode", "与 status 不一致")
	source := v.object(data["design_source"], "design_source")
	v.source(source, "design_source", mode, false)
	v.time(source["captured_at"], "design_source.captured_at")
	if mode == "figma" {
		v.require(source["evidence_origin"] == "figma", "design_source", "必须为 Figma 来源")
		v.text(source, "design_source", "file_key", "root_node", "revision")
	}
	units := map[string]bool{}
	globalScenarios := map[string]bool{}
	dependencies := map[string][]any{}
	for i, raw := range v.rows(data["units"], "units", true) {
		p := uiLabel("units", i)
		u := v.object(raw, p)
		id := v.id(u["unit_id"], p+".unit_id", units)
		stack := uiString(u["stack"])
		v.enum(u["type"], p+".type", "page", "component", "modal", "shared-component")
		v.enum(stack, p+".stack", "flutter", "web", "android-view")
		v.motion(u["motion_decision"], p+".motion_decision")
		if mode == "figma" {
			v.text(u, p, "source_node")
		}
		deps := v.rows(u["dependencies"], p+".dependencies", false)
		seenDeps := map[string]bool{}
		for _, d := range deps {
			dep := v.id(d, p+".dependencies", seenDeps)
			v.require(dep != id, p, "不能依赖自身")
		}
		dependencies[id] = deps
		var suffixes []string
		if stack == "flutter" {
			suffixes = []string{".dart"}
		} else if stack == "android-view" {
			suffixes = []string{".kt", ".java", ".xml"}
		}
		component := v.file(u["component_path"], u["component_sha256"], p+".component_path", suffixes)
		render := map[string]bool{}
		if stack == "android-view" {
			for j, x := range v.rows(u["render_inputs"], p+".render_inputs", true) {
				r := v.object(x, uiLabel(p+".render_inputs", j))
				rp := v.file(r["path"], r["sha256"], p+".render_inputs", nil)
				v.require(!render[rp], p, "render_inputs 重复")
				render[rp] = true
			}
			v.require(render[component], p, "render_inputs 缺少 component_path")
		}
		_, gold := u["golden_test"]
		_, goldHash := u["golden_test_sha256"]
		if stack == "flutter" || stack == "android-view" || gold || goldHash {
			suffix := []string{".js", ".jsx", ".ts", ".tsx"}
			if stack == "flutter" {
				suffix = []string{".dart"}
			}
			if stack == "android-view" {
				suffix = []string{".kt", ".java"}
			}
			v.file(u["golden_test"], u["golden_test_sha256"], p+".golden_test", suffix)
		}
		profiles := map[string]bool{}
		for j, x := range v.rows(u["profiles"], p+".profiles", true) {
			q := uiLabel(p+".profiles", j)
			r := v.object(x, q)
			v.id(r["profile_id"], q, profiles)
			surface := v.object(r["surface"], q+".surface")
			v.enum(surface["kind"], q+".surface.kind", "viewport", "container")
			for _, k := range []string{"width", "height"} {
				v.positive(surface[k], q+".surface."+k)
			}
			if n, ok := surface["device_pixel_ratio"]; ok {
				v.positive(n, q+".device_pixel_ratio")
			}
			v.enum(r["orientation"], q+".orientation", "portrait", "landscape", "not-applicable")
			v.text(r, q, "theme", "locale", "input_mode")
			v.positive(r["text_scale"], q+".text_scale")
			_, ok := r["reduced_motion"].(bool)
			v.require(ok, q, "reduced_motion 必须为布尔值")
		}
		states := map[string]bool{}
		for j, x := range v.rows(u["states"], p+".states", true) {
			q := uiLabel(p+".states", j)
			r := v.object(x, q)
			v.id(r["state_id"], q, states)
			v.source(r, q, mode, mode == "figma")
		}
		scenarios := map[string]map[string]bool{}
		usedStates, usedProfiles := map[string]bool{}, map[string]bool{}
		hasMotion := false
		for j, x := range v.rows(u["scenarios"], p+".scenarios", true) {
			q := uiLabel(p+".scenarios", j)
			r := v.object(x, q)
			sid := v.id(r["scenario_id"], q, globalScenarios)
			st, pr := uiString(r["state_id"]), uiString(r["profile_id"])
			v.require(states[st], q, "未知 state_id，需重新取证")
			v.require(profiles[pr], q, "未知 profile_id，需重新取证")
			usedStates[st] = true
			usedProfiles[pr] = true
			dims := map[string]bool{}
			for _, d := range v.rows(r["dimensions"], q+".dimensions", true) {
				dim := uiString(d)
				v.enum(d, q+".dimensions", uiDimensions...)
				v.require(!dims[dim], q, "dimension 重复")
				dims[dim] = true
			}
			scenarios[sid] = dims
			hasMotion = hasMotion || dims["motion"]
			v.enum(r["review_mode"], q+".review_mode", "visual", "behavior", "both")
			v.scope(r, q, stack, render)
			v.source(r, q, mode, false)
			var hash any
			if r["review_mode"] == "visual" || r["review_mode"] == "both" {
				suffix := uiPreviews
				if stack == "flutter" || stack == "android-view" {
					suffix = []string{".png"}
				}
				v.file(r["preview_path"], r["preview_sha256"], q+".preview_path", suffix)
				hash = r["preview_sha256"]
			}
			v.confirmation(r["confirmation"], q+".confirmation", hash)
		}
		if uiMap(u["motion_decision"])["decision"] == "animated" {
			v.require(hasMotion, p, "animated 必须有 motion 场景")
		}
		for id := range states {
			v.require(usedStates[id], p, "state 未被场景覆盖: "+id)
		}
		for id := range profiles {
			v.require(usedProfiles[id], p, "profile 未被场景覆盖: "+id)
		}
		coverage := map[string]map[string]bool{}
		for j, x := range v.rows(u["coverage"], p+".coverage", false) {
			q := uiLabel(p+".coverage", j)
			r := v.object(x, q)
			dim := uiString(r["dimension"])
			v.enum(dim, q+".dimension", uiDimensions...)
			_, dup := coverage[dim]
			v.require(!dup, q, "coverage dimension 重复")
			v.enum(r["status"], q+".status", "covered", "not_applicable")
			set := map[string]bool{}
			for _, x := range v.rows(r["scenario_ids"], q+".scenario_ids", false) {
				sid := uiString(x)
				_, ok := scenarios[sid]
				v.require(ok, q, "未知 scenario_id")
				v.require(!set[sid], q, "scenario_id 重复")
				set[sid] = true
				v.require(scenarios[sid][dim], q, "场景未声明该 dimension")
			}
			coverage[dim] = set
			if r["status"] == "covered" {
				v.require(len(set) > 0, q, "covered 缺少场景")
			}
			if r["status"] == "not_applicable" {
				v.require(len(set) == 0, q, "not_applicable 禁止场景引用")
				v.text(r, q, "note")
			}
		}
		for _, dim := range uiDimensions {
			_, ok := coverage[dim]
			v.require(ok, p, "缺少 coverage dimension: "+dim)
		}
		for sid, dims := range scenarios {
			for dim := range dims {
				v.require(coverage[dim][sid], p, "场景 dimension 缺少 coverage: "+sid+"/"+dim)
			}
		}
	}
	for id, deps := range dependencies {
		for _, d := range deps {
			v.require(units[uiString(d)], id, "未知 dependency")
		}
	}
}
func (v *uiValidator) scope(r map[string]any, p, stack string, render map[string]bool) {
	scope := uiString(r["evidence_scope"])
	v.enum(scope, p+".evidence_scope", "component-only", "host-static", "host-runtime")
	d := v.object(r["scope_decision"], p+".scope_decision")
	v.text(d, p+".scope_decision", "reason")
	supported, ok := d["host_capture_supported"].(bool)
	v.require(ok, p, "host_capture_supported 必须为布尔值")
	if scope == "component-only" {
		v.require(ok && !supported, p, "component-only 必须声明不支持 host capture")
		v.text(d, p, "uncovered_risk")
		v.require(r["host_binding"] == nil, p, "component-only 禁止 host_binding")
		return
	}
	if scope != "host-static" && scope != "host-runtime" {
		return
	}
	v.require(ok && supported, p, "host scope 必须支持 host capture")
	h := v.object(r["host_binding"], p+".host_binding")
	var suffix []string
	if stack == "android-view" {
		suffix = []string{".kt", ".java", ".xml"}
	}
	resolved := v.file(h["host_component_path"], h["host_component_sha256"], p+".host_component_path", suffix)
	if stack == "android-view" {
		v.require(render[resolved], p, "render_inputs 缺少 host_component_path")
	}
	forbidden := []string{".ai-delivery", "test", "tests", "integration_test", "integration-tests", "__tests__"}
	for _, host := range []string{uiString(h["host_component_path"]), resolved} {
		parts := strings.Split(host, "/")
		if len(parts) > 0 {
			v.require(!contains(forbidden, parts[0]), p, "host 必须为生产源码")
		}
		if stack == "android-view" {
			for _, part := range parts {
				v.require(!contains(append(forbidden, "androidTest", "testFixtures"), part), p, "Android host 禁止测试源码")
			}
		}
	}
	v.text(h, p+".host_binding", "entrypoint_ref", "capture_boundary_ref")
	v.outsideGovernance(h["evidence_root"], p+".evidence_root")
	v.strings(h["required_landmarks"], p+".required_landmarks", true)
	ids := map[string]bool{}
	for j, x := range v.rows(h["spatial_constraints"], p+".spatial_constraints", true) {
		q := uiLabel(p+".spatial_constraints", j)
		c := v.object(x, q)
		id := uiString(c["constraint_id"])
		v.text(c, q, "constraint_id", "subject_ref", "source_ref")
		v.require(!ids[id], q, "constraint_id 重复")
		ids[id] = true
		v.enum(c["kind"], q+".kind", "visible", "contains", "relative-position", "edge-insets", "spacing", "size-mode")
	}
}
