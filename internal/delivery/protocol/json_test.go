package protocol

import (
	"encoding/json"
	"testing"
)

func TestStrictJSONRejectsAmbiguity(t *testing.T) {
	for _, body := range []string{`{"a":1,"a":2}`, `{"x":{"a":1,"\u0061":2}}`, `{} {}`, `{"x":NaN}`, `{"x":Infinity}`, `{"x":1e999}`, `{"x":"\ud800"}`, `{"x":"\udc00"}`, "{\"x\":\"\xff\"}"} {
		if _, err := ParseJSON([]byte(body)); err == nil {
			t.Errorf("应拒绝 %q", body)
		}
	}
	value, err := Object([]byte(`{"n":9007199254740993,"null":null,"bool":true,"text":"1","float":1.0}`))
	if err != nil {
		t.Fatal(err)
	}
	if value["n"] != json.Number("9007199254740993") || value["float"] != json.Number("1.0") || value["null"] != nil || value["bool"] != true || value["text"] != "1" {
		t.Fatal(value)
	}
	if _, exists := value["absent"]; exists {
		t.Fatal("缺失字段被填充")
	}
	for _, body := range []string{`[]`, `null`, `true`, `1`, `"text"`} {
		if _, err := Object([]byte(body)); err == nil {
			t.Errorf("应拒绝对象根 %s", body)
		}
	}
}

func TestMetadataUsesOnlyCurrentTypedVersions(t *testing.T) {
	for _, tc := range []struct{ kind, body string }{
		{"binding", `{"version":3}`}, {"policy", `{"version":4,"verification_contract_version":2}`},
	} {
		object, err := Object([]byte(tc.body))
		if err != nil {
			t.Fatal(err)
		}
		if err := ValidateMetadata(tc.kind, object); err != nil {
			t.Fatal(err)
		}
		for _, value := range []any{nil, true, "3", json.Number("3.0"), json.Number("3e0"), json.Number("99")} {
			object["version"] = value
			if err := ValidateMetadata(tc.kind, object); err == nil {
				t.Errorf("接受错误版本 %s %v", tc.kind, value)
			}
		}
		delete(object, "version")
		if err := ValidateMetadata(tc.kind, object); err == nil {
			t.Error("接受缺失版本")
		}
	}
	for _, body := range []string{`{"version":4}`, `{"version":4,"verification_contract_version":2,"context":null}`, `{"version":4,"verification_contract_version":2,"context":{"sources":{}}}`, `{"version":4,"verification_contract_version":2,"extra":[{"design_approved":true}]}`, `{"version":4,"verification_contract_version":2,"participation":"no_design_client"}`} {
		object, _ := Object([]byte(body))
		if err := ValidateMetadata("policy", object); err == nil {
			t.Error(body)
		}
	}
}

func TestDefaultsAreIndependentAndCurrent(t *testing.T) {
	first := Defaults("binding")
	first["layout"].(map[string]any)["requirement_root"] = "corrupted"
	second := Defaults("binding")
	if second["layout"].(map[string]any)["requirement_root"] != "requirements/{req_id}" {
		t.Fatal("默认值可被调用方污染")
	}
	for _, kind := range []string{"binding", "policy"} {
		if err := ValidateMetadata(kind, Defaults(kind)); err != nil {
			t.Fatal(err)
		}
	}
}

func TestVersionRejectsUnknownKindAndWrongJSONTypes(t *testing.T) {
	for _, kind := range []string{"binding", "policy", "verification", "status", "ui_index", "visual_acceptance", "archive_evidence"} {
		if err := RequireVersion(map[string]any{"version": Version(kind)}, "version", kind); err != nil {
			t.Fatal(err)
		}
		for _, value := range []any{nil, true, map[string]any{}, []any{}, "future", json.Number("999")} {
			if err := RequireVersion(map[string]any{"version": value}, "version", kind); err == nil {
				t.Errorf("%s 接受错误类型/值: %v", kind, value)
			}
		}
	}
	if err := RequireVersion(map[string]any{"version": nil}, "version", "unknown"); err == nil {
		t.Fatal("未知协议类型被接受")
	}
}

func TestDefaultsConcurrentIsolation(t *testing.T) {
	for i := 0; i < 16; i++ {
		t.Run("independent", func(t *testing.T) {
			t.Parallel()
			data := Defaults("binding")
			layout := data["layout"].(map[string]any)
			layout["requirement_root"] = "changed"
			fresh := Defaults("binding")
			if fresh["layout"].(map[string]any)["requirement_root"] != "requirements/{req_id}" {
				t.Fatal("并发调用污染默认值")
			}
		})
	}
}
