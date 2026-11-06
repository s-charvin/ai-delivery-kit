package protocol

import (
	"encoding/json"
	"os"
	"testing"
)

func TestCanonicalMatchesFrozenPython(t *testing.T) {
	body, err := os.ReadFile("../../../tests/migration-oracle/fixtures/canonical-cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Cases []struct {
			Input     string `json:"input_json"`
			Canonical string
			SHA256    string
		}
	}
	if err = json.Unmarshal(body, &fixture); err != nil {
		t.Fatal(err)
	}
	for _, tc := range fixture.Cases {
		value, err := ParseJSON([]byte(tc.Input))
		if err != nil {
			t.Fatal(err)
		}
		body, err := CanonicalJSON(value)
		if err != nil || string(body) != tc.Canonical {
			t.Errorf("canonical %s\n得到 %s\n期望 %s (%v)", tc.Input, body, tc.Canonical, err)
		}
		digest, err := CanonicalSHA256(value)
		if err != nil || digest != tc.SHA256 {
			t.Errorf("摘要不一致: %s %v", digest, err)
		}
	}
}

func TestDomainDigestsMatchFrozenOriginalFunctions(t *testing.T) {
	body, err := os.ReadFile("testdata/digests.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Cases []struct {
			Kind   string
			Input  string `json:"input_json"`
			SHA256 string
		}
	}
	if err = json.Unmarshal(body, &fixture); err != nil {
		t.Fatal(err)
	}
	for _, tc := range fixture.Cases {
		value, err := ParseJSON([]byte(tc.Input))
		if err != nil {
			t.Fatal(err)
		}
		var got string
		switch tc.Kind {
		case "input":
			got, err = InputDigest(value.([]any))
		case "review":
			got, err = ReviewDigest(value.(map[string]any))
		case "entry":
			got, err = EntryDigest(value.(map[string]any))
		}
		if err != nil || got != tc.SHA256 {
			t.Errorf("%s 摘要得到 %s，期望 %s (%v)", tc.Kind, got, tc.SHA256, err)
		}
	}
}

func TestCanonicalRetainsIntegerFloatAndNegativeZero(t *testing.T) {
	v, err := ParseJSON([]byte(`[-0,-0.0,1,1.0,1e0,1000000000000000.0,1e16,1e-4,1e-5]`))
	if err != nil {
		t.Fatal(err)
	}
	body, err := CanonicalJSON(v)
	want := `[0,-0.0,1,1.0,1.0,1000000000000000.0,1e+16,0.0001,1e-05]`
	if err != nil || string(body) != want {
		t.Fatalf("得到 %s，期望 %s (%v)", body, want, err)
	}
}
