package cli

import (
	"bytes"
	"context"
	"os"
	"os/exec"
	"path/filepath"
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

func TestRunInitDefaultsToCWD(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake

	exitCode := app.Run([]string{"init"})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	cwd, _ := os.Getwd()
	if fake.input.TargetPath != cwd {
		t.Fatalf("expected CWD %q, got %q", cwd, fake.input.TargetPath)
	}
}

func TestRunUpgradeFailsWhenRepoNotCloned(t *testing.T) {
	var out, errOut bytes.Buffer
	app := New(&out, &errOut)
	app.homeDir = func() (string, error) { return "/tmp/phony-missing-repo", nil }

	exitCode := app.Run([]string{"upgrade"})
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when repo missing, got %d", exitCode)
	}
	if !strings.Contains(errOut.String(), "not found") {
		t.Fatalf("expected 'not found' error, got %q", errOut.String())
	}
}

func TestRunUpgradePullsExistingRepo(t *testing.T) {
	tmpDir := t.TempDir()
	repoPath := filepath.Join(tmpDir, "ai-delivery-kit")

	// Set up a minimal git repo so git pull doesn't fail.
	runCmd(t, exec.Command("git", "-C", tmpDir, "init", repoPath))
	runCmd(t, exec.Command("git", "-C", repoPath, "commit", "--allow-empty", "-m", "init"))

	// Point master/main to itself so pull has a remote.
	runCmd(t, exec.Command("git", "-C", repoPath, "remote", "add", "origin", repoPath))
	runCmd(t, exec.Command("git", "-C", repoPath, "branch", "-M", "main"))
	runCmd(t, exec.Command("git", "-C", repoPath, "fetch", "origin"))
	runCmd(t, exec.Command("git", "-C", repoPath, "branch", "--set-upstream-to=origin/main", "main"))

	var out, errOut bytes.Buffer
	app := New(&out, &errOut)
	app.homeDir = func() (string, error) { return tmpDir, nil }

	exitCode := app.Run([]string{"upgrade"})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d: %s", exitCode, errOut.String())
	}
}

func runCmd(t *testing.T, cmd *exec.Cmd) {
	t.Helper()
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git command failed: %v\n%s", err, out)
	}
}

type fakeInitRunner struct {
	input initflow.Input
}

func (f *fakeInitRunner) Run(_ context.Context, input initflow.Input) (initflow.Result, error) {
	f.input = input
	return initflow.Result{}, nil
}
