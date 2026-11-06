package cli

import (
	"bytes"
	"strings"
	"testing"
)

func TestRemovedPolicyUpgradeIsActionableAndNeverCallsRunner(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake
	for _, args := range [][]string{{"init", "--upgrade-policy", "/tmp/example"}, {"init", "--upgrade", "--upgrade-policy", "/tmp/example"}} {
		if code := app.Run(args); code == 0 {
			t.Fatal("removed migration flag accepted")
		}
		if fake.input.TargetPath != "" {
			t.Fatal("removed flag reached runner")
		}
	}
	if !strings.Contains(out.String(), "已移除") || !strings.Contains(out.String(), "--reset-data") {
		t.Fatal(out.String())
	}
}

func TestResetDataCLIIsExplicit(t *testing.T) {
	for _, tc := range []struct {
		args []string
		want string
		ok   bool
	}{
		{[]string{"init", "--reset-data", "/tmp/example"}, "", false},
		{[]string{"init", "--upgrade", "--reset-data", "/tmp/example"}, ".ai-delivery", true},
		{[]string{"init", "--upgrade", "--reset-data=tooling/delivery", "/tmp/example"}, "tooling/delivery", true},
		{[]string{"init", "--upgrade", "--reset-data=", "/tmp/example"}, "", false},
		{[]string{"init", "--upgrade", "/tmp/example"}, "", true},
		{[]string{"init", "--invalid", "/tmp/example"}, "", false},
	} {
		var out bytes.Buffer
		fake := &fakeInitRunner{}
		app := New(&out, &out)
		app.initRunner = fake
		code := app.Run(tc.args)
		if (code == 0) != tc.ok {
			t.Fatalf("%v: %d %s", tc.args, code, out.String())
		}
		if fake.input.ResetData != tc.want {
			t.Fatalf("%v: %q", tc.args, fake.input.ResetData)
		}
		if !tc.ok && fake.input.TargetPath != "" {
			t.Fatal("invalid command reached runner")
		}
	}
}
