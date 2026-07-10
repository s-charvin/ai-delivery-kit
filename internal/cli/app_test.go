package cli

import (
	"bytes"
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
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

func TestRunInitPrintsIDEGateRestoreHint(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{
		result: initflow.Result{
			RepoRoot: "/tmp/demo-repo",
			IDEGateAmend: bootstrap.AmendReport{
				BackupStamp: "2026-07-10T06-43-00Z",
				BackupDir:   "/tmp/demo-repo/.ai-delivery/backups/ide-gates/2026-07-10T06-43-00Z",
				Files:       []string{".claude/settings.json"},
			},
		},
	}
	app := New(&out, &out)
	app.initRunner = fake

	if exitCode := app.Run([]string{"init", "/tmp/demo-repo"}); exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}
	got := out.String()
	if !strings.Contains(got, "Amended IDE gate config(s): .claude/settings.json") {
		t.Fatalf("expected amend hint, got %q", got)
	}
	if !strings.Contains(got, "ai-delivery ide-gates restore --to 2026-07-10T06-43-00Z") {
		t.Fatalf("expected restore command hint, got %q", got)
	}
}

func TestRunIDEGatesListAndRestore(t *testing.T) {
	root := t.TempDir()
	runCmd(t, exec.Command("git", "init", root))

	settings := filepath.Join(root, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(settings), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(settings, []byte(`{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo current"}]}]}}`), 0o644); err != nil {
		t.Fatal(err)
	}

	stamp := "2026-07-01T00-00-00Z"
	backupFile := filepath.Join(root, ".ai-delivery", "backups", "ide-gates", stamp, ".claude", "settings.json")
	if err := os.MkdirAll(filepath.Dir(backupFile), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(backupFile, []byte(`{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo old"}]}]}}`), 0o644); err != nil {
		t.Fatal(err)
	}

	var listOut bytes.Buffer
	app := New(&listOut, &listOut)
	if exitCode := app.Run([]string{"ide-gates", "list", root}); exitCode != 0 {
		t.Fatalf("list exit %d: %s", exitCode, listOut.String())
	}
	if !strings.Contains(listOut.String(), stamp) {
		t.Fatalf("expected stamp in list output, got %q", listOut.String())
	}

	var restoreOut, restoreErr bytes.Buffer
	app = New(&restoreOut, &restoreErr)
	if exitCode := app.Run([]string{"ide-gates", "restore", "--to", stamp, root}); exitCode != 0 {
		t.Fatalf("restore exit %d: %s", exitCode, restoreErr.String())
	}
	body, err := os.ReadFile(settings)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "echo old") {
		t.Fatalf("expected restored content, got %s", string(body))
	}
	if !strings.Contains(restoreOut.String(), "Restored IDE gate config from "+stamp) {
		t.Fatalf("expected restore confirmation, got %q", restoreOut.String())
	}
}

func TestRunUpgradePullsExistingRepo(t *testing.T) {
	tmpDir := t.TempDir()
	repoPath := filepath.Join(tmpDir, "ai-delivery-kit")

	// Set up a minimal git repo so git pull doesn't fail.
	runCmd(t, exec.Command("git", "-C", tmpDir, "init", repoPath))
	runCmd(t, exec.Command("git", "-C", repoPath, "-c", "user.name=test", "-c", "user.email=test@test.com", "commit", "--allow-empty", "-m", "init"))

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
	input  initflow.Input
	result initflow.Result
}

func (f *fakeInitRunner) Run(_ context.Context, input initflow.Input) (initflow.Result, error) {
	f.input = input
	result := f.result
	if result.RepoRoot == "" {
		result.RepoRoot = input.TargetPath
	}
	return result, nil
}
