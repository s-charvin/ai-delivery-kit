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

func TestRunInitCommandParsesTargetAndFlags(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake

	exitCode := app.Run([]string{
		"init",
		"/tmp/demo-repo",
		"--project-id",
		"demo-project",
		"--main-branch",
		"main",
	})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if fake.input.TargetPath != "/tmp/demo-repo" {
		t.Fatalf("expected target path to be parsed, got %#v", fake.input)
	}

	if fake.input.ProjectID != "demo-project" {
		t.Fatalf("expected project id to be parsed, got %#v", fake.input)
	}

	if fake.input.MainBranch != "main" {
		t.Fatalf("expected main branch to be parsed, got %#v", fake.input)
	}
}

type fakeInitRunner struct {
	input initflow.Input
}

func (f *fakeInitRunner) Run(_ context.Context, input initflow.Input) (initflow.Result, error) {
	f.input = input
	return initflow.Result{}, nil
}
