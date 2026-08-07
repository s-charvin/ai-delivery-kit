package initflow

import (
	"context"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
)

func TestRunDerivesProjectIDWhenInputDoesNotProvideIt(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	service := Service{
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/demo-repo"}, nil
		},
	}

	if _, err := service.Run(context.Background(), Input{TargetPath: "/tmp/demo-repo"}); err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if bootstrapper.config.ProjectID != "demo-repo" {
		t.Fatalf("expected derived project id, got %#v", bootstrapper.config)
	}
}

func TestRunStopsBeforeBootstrapOnPreflightConflict(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	service := Service{
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{
				Root:             "/tmp/project",
				ManagedConflicts: []string{"/tmp/project/.agents/skills/requirement-breakdown"},
			}, nil
		},
	}

	if _, err := service.Run(context.Background(), Input{TargetPath: "/tmp/project"}); err == nil {
		t.Fatal("expected preflight failure, got nil")
	}

	if bootstrapper.called {
		t.Fatal("expected bootstrap to be skipped on preflight failure")
	}
}

func TestRunUpgradeModeAllowsManagedConflicts(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	service := Service{
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{
				Root:             "/tmp/project",
				ManagedConflicts: []string{"/tmp/project/.agents/skills/requirement-breakdown"},
			}, nil
		},
	}

	if _, err := service.Run(context.Background(), Input{
		TargetPath: "/tmp/project",
		Upgrade:    true,
	}); err != nil {
		t.Fatalf("expected upgrade mode to bypass managed conflicts, got %v", err)
	}

	if !bootstrapper.called {
		t.Fatal("expected bootstrap to run in upgrade mode")
	}
	if !bootstrapper.config.AllowManagedUpdate {
		t.Fatalf("expected upgrade bootstrap config, got %#v", bootstrapper.config)
	}
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
