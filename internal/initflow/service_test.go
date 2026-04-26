package initflow

import (
	"context"
	"errors"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
)

func TestRunSkipsAlreadyInstalledTools(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"specify": "specify",
		"uv":      "uv",
		"pipx":    "pipx",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{
				Root:       "/tmp/project",
				HasSpecify: true,
			}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(path string) error {
			if path == "/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	result, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if len(runner.calls) != 0 {
		t.Fatalf("expected no external commands, got %#v", runner.calls)
	}

	if !bootstrapper.called {
		t.Fatal("expected bootstrap to run")
	}

	if len(result.DocsLinks) != 0 {
		t.Fatalf("expected no docs links, got %#v", result.DocsLinks)
	}
}

func TestRunDeclineStillBootstrapsAIDelivery(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"uv":  "uv",
		"git": "git",
	}}
	service := Service{
		Prompt:       staticPrompt(false),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(string) error {
			return errors.New("missing")
		},
	}

	result, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if !bootstrapper.called {
		t.Fatal("expected ai-delivery bootstrap to continue")
	}

	if len(runner.calls) != 0 {
		t.Fatalf("expected no install commands after decline, got %#v", runner.calls)
	}

	if len(result.DocsLinks) == 0 {
		t.Fatal("expected docs links when installs are declined")
	}
}

func TestRunAcceptInstallExecutesInstallCommandsOnly(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"uv":      "uv",
		"specify": "specify",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --ai-skills\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(string) error {
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if len(runner.calls) != 4 {
		t.Fatalf("expected specify install, superpowers install, and specify init, got %#v", runner.calls)
	}

	last := runner.calls[len(runner.calls)-1]
	if last.Name != "specify" || len(last.Args) == 0 || last.Args[0] != "init" {
		t.Fatalf("expected automatic specify init as final command, got %#v", last)
	}
	if !containsArg(last.Args, "--force") {
		t.Fatalf("expected specify init to include --force, got %#v", last.Args)
	}
	if !containsArg(last.Args, "--ai-skills") {
		t.Fatalf("expected specify init to include --ai-skills when supported, got %#v", last.Args)
	}
	if !hasArgPair(last.Args, "--script", "sh") {
		t.Fatalf("expected linux specify init to default to --script sh, got %#v", last.Args)
	}

	if last.Dir != "/tmp/project" {
		t.Fatalf("expected specify init to run in repo root, got %#v", last)
	}

	if !bootstrapper.called {
		t.Fatal("expected bootstrap to run before specify init")
	}
}

func TestRunSkipsSpecifyInitWhenInstallIsDeclined(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"uv":  "uv",
		"git": "git",
	}}
	service := Service{
		Prompt:       staticPrompt(false),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --ai-skills\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(string) error {
			return errors.New("missing")
		},
	}

	result, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if !bootstrapper.called {
		t.Fatal("expected ai-delivery bootstrap to continue")
	}

	for _, call := range runner.calls {
		if call.Name == "specify" && len(call.Args) > 0 && call.Args[0] == "init" {
			t.Fatalf("did not expect automatic specify init after decline, got %#v", call)
		}
	}

	if len(result.DocsLinks) == 0 {
		t.Fatal("expected docs links when install is declined")
	}
}

func TestRunDecliningSuperpowersInstallDoesNotBlockExistingSpecifyInit(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"specify": "specify",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(false),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --ai-skills\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(string) error {
			return errors.New("missing")
		},
	}

	result, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if !bootstrapper.called {
		t.Fatal("expected bootstrap to run")
	}

	if len(runner.calls) != 1 {
		t.Fatalf("expected only specify init command, got %#v", runner.calls)
	}

	call := runner.calls[0]
	if call.Name != "specify" || len(call.Args) == 0 || call.Args[0] != "init" {
		t.Fatalf("expected specify init command, got %#v", call)
	}

	if len(result.DocsLinks) == 0 {
		t.Fatal("expected docs links for declined superpowers install")
	}
}

func TestRunUsesExistingSpecifyToInitializeMissingSpecifyTree(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"specify": "specify",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --ai-skills\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(path string) error {
			if path == "/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if len(runner.calls) != 1 {
		t.Fatalf("expected only specify init command, got %#v", runner.calls)
	}

	call := runner.calls[0]
	if call.Name != "specify" || len(call.Args) == 0 || call.Args[0] != "init" {
		t.Fatalf("expected specify init command, got %#v", call)
	}
	if !containsArg(call.Args, "--force") {
		t.Fatalf("expected --force when initializing existing repo, got %#v", call.Args)
	}
	if !containsArg(call.Args, "--ai-skills") {
		t.Fatalf("expected --ai-skills when supported, got %#v", call.Args)
	}
}

func TestRunFallsBackWhenSpecifyInitHelpDoesNotSupportAISkills(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"specify": "specify",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --script [sh|ps]\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/project"}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(path string) error {
			if path == "/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if len(runner.calls) != 1 {
		t.Fatalf("expected only specify init command, got %#v", runner.calls)
	}

	call := runner.calls[0]
	if containsArg(call.Args, "--ai-skills") {
		t.Fatalf("did not expect --ai-skills when unsupported, got %#v", call.Args)
	}
	if !containsArg(call.Args, "--force") {
		t.Fatalf("expected --force in fallback specify init command, got %#v", call.Args)
	}
}

func TestRunUsesPsScriptModeOnWindows(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"specify": "specify",
		"git":     "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		ReadCommandOutput: func(context.Context, string, ...string) (string, error) {
			return "Usage: specify init\n  --ai-skills\n", nil
		},
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "C:/tmp/project"}, nil
		},
		HomeDir: "C:/tmp/home",
		GOOS:    "windows",
		StatPath: func(path string) error {
			if path == "C:/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "C:/tmp/project",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if len(runner.calls) != 1 {
		t.Fatalf("expected only specify init command, got %#v", runner.calls)
	}

	call := runner.calls[0]
	if !hasArgPair(call.Args, "--script", "ps") {
		t.Fatalf("expected windows specify init to default to --script ps, got %#v", call.Args)
	}
}

func TestRunDerivesProjectAndMainBranchWhenInputDoesNotProvideThem(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"git": "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/demo-repo", HasSpecify: true}, nil
		},
		DetectMainBranch: func(context.Context, string) (string, error) {
			return "release/main", nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(path string) error {
			if path == "/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/demo-repo",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if bootstrapper.config.ProjectID != "demo-repo" {
		t.Fatalf("expected derived project id, got %#v", bootstrapper.config)
	}
	if bootstrapper.config.MainBranch != "release/main" {
		t.Fatalf("expected derived branch, got %#v", bootstrapper.config)
	}
}

func TestRunStopsBeforeInstallOrBootstrapOnPreflightConflict(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"uv":  "uv",
		"git": "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{
				Root:             "/tmp/project",
				ManagedConflicts: []string{"/tmp/project/.agents/skills/requirement-breakdown"},
			}, nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(string) error {
			return errors.New("missing")
		},
	}

	if _, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/project",
		Interactive: true,
	}); err == nil {
		t.Fatal("expected preflight failure, got nil")
	}

	if len(runner.calls) != 0 {
		t.Fatalf("expected no external commands on preflight failure, got %#v", runner.calls)
	}

	if bootstrapper.called {
		t.Fatal("expected bootstrap to be skipped on preflight failure")
	}
}

type staticPrompt bool

func (s staticPrompt) Confirm(string, bool) (bool, error) {
	return bool(s), nil
}

type fakeRunner struct {
	paths map[string]string
	calls []command.Command
}

func (f *fakeRunner) Run(_ context.Context, cmd command.Command) error {
	f.calls = append(f.calls, cmd)
	return nil
}

func (f *fakeRunner) LookPath(file string) (string, error) {
	if path, ok := f.paths[file]; ok {
		return path, nil
	}
	return "", errors.New("missing")
}

func containsArg(args []string, needle string) bool {
	for _, arg := range args {
		if arg == needle {
			return true
		}
	}
	return false
}

func hasArgPair(args []string, key string, value string) bool {
	for i := 0; i < len(args)-1; i++ {
		if args[i] == key && args[i+1] == value {
			return true
		}
	}
	return false
}

type fakeBootstrapper struct {
	called bool
	config bootstrap.Config
}

func (f *fakeBootstrapper) Run(config bootstrap.Config) error {
	f.called = true
	f.config = config
	return nil
}
