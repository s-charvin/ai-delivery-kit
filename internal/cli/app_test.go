package cli

import (
	"bytes"
	"context"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/initflow"
)

func TestRunVersionCommand(t *testing.T) {
	var out bytes.Buffer
	app := New(&out, &out)

	if exitCode := app.Run([]string{"version"}); exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if got := out.String(); !strings.Contains(got, "dev") {
		t.Fatalf("expected dev version output, got %q", got)
	}
}

func TestRunWithoutCommandPrintsUsage(t *testing.T) {
	var out bytes.Buffer
	app := New(&out, &out)

	if exitCode := app.Run(nil); exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}

	if got := out.String(); !strings.Contains(got, "Usage: ai-delivery") {
		t.Fatalf("expected usage output, got %q", got)
	}
}

func TestRunInitCommandParsesOnlyTargetPath(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake

	exitCode := app.Run([]string{"init", "/tmp/demo-repo"})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if fake.input.TargetPath != "/tmp/demo-repo" {
		t.Fatalf("expected target path to be parsed, got %#v", fake.input)
	}
}

func TestRunInitUpgradeCommandParsesUpgradeFlag(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake

	exitCode := app.Run([]string{"init", "--upgrade", "/tmp/demo-repo"})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if fake.input.TargetPath != "/tmp/demo-repo" {
		t.Fatalf("expected target path to be parsed, got %#v", fake.input)
	}
	if !fake.input.Upgrade {
		t.Fatalf("expected upgrade flag to be parsed, got %#v", fake.input)
	}
}

type fakeInitRunner struct {
	input initflow.Input
}

func (f *fakeInitRunner) Run(_ context.Context, input initflow.Input) (initflow.Result, error) {
	f.input = input
	return initflow.Result{}, nil
}
