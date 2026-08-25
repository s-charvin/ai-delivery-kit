package initflow

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
)

type Bootstrapper interface {
	Run(config bootstrap.Config) error
}

type Input struct {
	TargetPath string
	Upgrade    bool
}

type Result struct {
	RepoRoot     string
	Upgraded     bool
	IDEGateAmend bootstrap.AmendReport
}

type Service struct {
	Bootstrapper Bootstrapper
	Discover     func(string) (repo.Info, error)
}

// Run resolves the target repository and seeds managed ai-delivery assets.
// The ai-delivery-orchestrator skill discovers and adapts to frameworks such as
// spec-kit, OpenSpec, ECC, and superpowers at runtime; the CLI binds none of them.
func (s Service) Run(_ context.Context, input Input) (Result, error) {
	if input.TargetPath == "" {
		return Result{}, fmt.Errorf("target repo path is required")
	}

	discover := s.Discover
	if discover == nil {
		discover = repo.Discover
	}

	info, err := discover(input.TargetPath)
	if err != nil {
		return Result{}, err
	}
	if len(info.ManagedConflicts) > 0 && !input.Upgrade {
		return Result{}, fmt.Errorf("managed asset already exists: %s", info.ManagedConflicts[0])
	}

	projectID := slugify(filepath.Base(info.Root))

	bootstrapper := s.Bootstrapper
	if bootstrapper == nil {
		bootstrapper = bootstrap.Engine{}
	}
	amendReport := bootstrap.AmendReport{}
	if err := bootstrapper.Run(bootstrap.Config{
		RepoRoot:           info.Root,
		ProjectID:          projectID,
		AllowManagedUpdate: input.Upgrade,
		Report:             &amendReport,
	}); err != nil {
		return Result{}, err
	}

	return Result{
		RepoRoot:     info.Root,
		Upgraded:     input.Upgrade,
		IDEGateAmend: amendReport,
	}, nil
}

func slugify(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var b strings.Builder
	lastDash := false
	for _, r := range value {
		isAlphaNum := (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9')
		if isAlphaNum {
			b.WriteRune(r)
			lastDash = false
			continue
		}
		if !lastDash && b.Len() > 0 {
			b.WriteByte('-')
			lastDash = true
		}
	}
	result := strings.Trim(b.String(), "-")
	if result == "" {
		return "project"
	}
	return result
}
