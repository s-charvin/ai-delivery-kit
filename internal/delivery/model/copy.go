package model

import (
	"errors"
	"fmt"
	"strings"
)

var ErrUnknownIntent = errors.New("未知交付意图")

var intentChoices = []string{"analyze", "design", "ui", "implement", "verify", "merge", "archive"}

// IntentChoices 返回副本，调用方不能改变核心接受的意图。
func IntentChoices() []string {
	return cloneSlice(intentChoices)
}

func ParseIntent(text string) (Intent, error) {
	for _, choice := range intentChoices {
		if text == choice {
			return Intent(text), nil
		}
	}
	return "", fmt.Errorf("%w: %q；合法意图: %s", ErrUnknownIntent, text, strings.Join(intentChoices, ", "))
}
func (r ReadRequest) Validate() error {
	if (r.Action == nil) == (r.Context == nil) {
		return fmt.Errorf("Action 与 Context 必须恰有一个非空")
	}
	if r.Action != nil {
		_, err := ParseIntent(string(r.Action.Intent))
		return err
	}
	return nil
}
func CloneReadRequest(r ReadRequest) ReadRequest {
	if r.Action != nil {
		a := *r.Action
		r.Action = &a
	}
	if r.Context != nil {
		c := *r.Context
		c.DeclaredPaths = cloneSlice(c.DeclaredPaths)
		r.Context = &c
	}
	return r
}
func cloneSlice[T any](v []T) []T {
	if v == nil {
		return nil
	}
	out := make([]T, len(v))
	copy(out, v)
	return out
}
func clonePointer[T any](v *T) *T {
	if v == nil {
		return nil
	}
	c := *v
	return &c
}
func CloneFileIdentities(files []FileIdentity) []FileIdentity {
	out := cloneSlice(files)
	for i := range out {
		out[i].SHA256 = clonePointer(out[i].SHA256)
		out[i].Mode = clonePointer(out[i].Mode)
		out[i].LinkTarget = clonePointer(out[i].LinkTarget)
	}
	return out
}
func CloneDiagnostics(items []Diagnostic) []Diagnostic {
	out := cloneSlice(items)
	for i := range out {
		out[i].SourceRefs = cloneSlice(out[i].SourceRefs)
	}
	return out
}
func CloneCheckSpecs(items []CheckSpec) []CheckSpec {
	out := cloneSlice(items)
	for i := range out {
		out[i].AcceptanceIDs = cloneSlice(out[i].AcceptanceIDs)
		out[i].SourceRefs = cloneSlice(out[i].SourceRefs)
		out[i].InputPaths = cloneSlice(out[i].InputPaths)
		if out[i].Method != nil {
			m := *out[i].Method
			m.Argv = cloneSlice(m.Argv)
			m.ReportPaths = cloneSlice(m.ReportPaths)
			m.SourceRefs = cloneSlice(m.SourceRefs)
			out[i].Method = &m
		}
	}
	return out
}
func CloneObservation(o CheckObservation) CheckObservation {
	o.Details = cloneSlice(o.Details)
	o.Evidence = CloneFileIdentities(o.Evidence)
	return o
}
