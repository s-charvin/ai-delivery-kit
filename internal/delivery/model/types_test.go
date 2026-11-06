package model

import (
	"errors"
	"reflect"
	"testing"
)

func TestIntentChoicesCannotChangeParsing(t *testing.T) {
	want := []string{"analyze", "design", "ui", "implement", "verify", "merge", "archive"}
	choices := IntentChoices()
	if !reflect.DeepEqual(choices, want) {
		t.Fatal(choices)
	}
	choices[0] = "bootstrap"
	if !reflect.DeepEqual(IntentChoices(), want) {
		t.Fatal("调用方改写全局意图")
	}
	for _, choice := range IntentChoices() {
		if got, err := ParseIntent(choice); err != nil || string(got) != choice {
			t.Fatal(choice, got, err)
		}
	}
	if _, err := ParseIntent("bootstrap"); !errors.Is(err, ErrUnknownIntent) {
		t.Fatal("改写 choices 改变了解析结果", err)
	}
}

func TestIntentAndRequestRejectAmbiguousIdentity(t *testing.T) {
	for _, text := range []string{"analyze", "design", "ui", "implement", "verify", "merge", "archive"} {
		if got, err := ParseIntent(text); err != nil || string(got) != text {
			t.Fatal(text, err)
		}
	}
	for _, text := range []string{"", "unknown", "Implement", " implement"} {
		if _, err := ParseIntent(text); err == nil {
			t.Fatal("接受未知意图", text)
		}
	}
	for _, req := range []ReadRequest{{}, {Action: &Action{Intent: "verify"}, Context: &ContextRequest{}}, {Action: &Action{Intent: "unknown"}}} {
		if err := req.Validate(); err == nil {
			t.Fatal("接受模糊请求", req)
		}
	}
	if err := (ReadRequest{Action: &Action{Intent: "implement", TargetStatus: "in_dev"}}).Validate(); err != nil {
		t.Fatal(err)
	}
}

func TestCopiesDoNotExposeMutableEvidence(t *testing.T) {
	req := ReadRequest{Context: &ContextRequest{DeclaredPaths: []string{"original"}}}
	copy := CloneReadRequest(req)
	copy.Context.DeclaredPaths[0] = "changed"
	if req.Context.DeclaredPaths[0] != "original" {
		t.Fatal("请求路径泄漏")
	}
	hash := "original"
	mode := uint32(0600)
	target := "link"
	files := []FileIdentity{{SHA256: &hash, Mode: &mode, LinkTarget: &target}}
	copied := CloneFileIdentities(files)
	*copied[0].SHA256 = "changed"
	*copied[0].Mode = 0777
	*copied[0].LinkTarget = "changed"
	if hash != "original" || mode != 0600 || target != "link" {
		t.Fatal("身份指针泄漏")
	}
	obs := CheckObservation{Details: []byte(`{"result":"passed"}`), Evidence: files}
	other := CloneObservation(obs)
	other.Details[0] = '!'
	*other.Evidence[0].SHA256 = "changed"
	if obs.Details[0] != '{' || hash != "original" {
		t.Fatal("观察证据泄漏")
	}
	checks := []CheckSpec{{InputPaths: []string{"input"}, Method: &CheckMethod{Argv: []string{"native"}}}}
	cloned := CloneCheckSpecs(checks)
	cloned[0].InputPaths[0] = "changed"
	cloned[0].Method.Argv[0] = "changed"
	if checks[0].InputPaths[0] != "input" || checks[0].Method.Argv[0] != "native" {
		t.Fatal("检查方法泄漏")
	}
}
