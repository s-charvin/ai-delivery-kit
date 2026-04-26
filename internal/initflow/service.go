package initflow

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/prereq"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
)

type Prompt interface {
	Confirm(question string, defaultYes bool) (bool, error)
}

type Bootstrapper interface {
	Run(config bootstrap.Config) error
}

type Input struct {
	TargetPath  string
	ProjectID   string
	MainBranch  string
	Interactive bool
}

type Result struct {
	RepoRoot       string
	DocsLinks      []string
	InstalledTools []string
	Bootstrapped   bool
	RanSpecifyInit bool
}

type Service struct {
	Prompt            Prompt
	Runner            command.Runner
	Bootstrapper      Bootstrapper
	Discover          func(string) (repo.Info, error)
	HomeDir           string
	GOOS              string
	StatPath          func(string) error
	ReadCommandOutput func(context.Context, string, ...string) (string, error)
}

func (s Service) Run(ctx context.Context, input Input) (Result, error) {
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
	if len(info.ManagedConflicts) > 0 {
		return Result{}, fmt.Errorf("managed asset already exists: %s", info.ManagedConflicts[0])
	}

	projectID := input.ProjectID
	if projectID == "" {
		projectID = slugify(filepath.Base(info.Root))
	}
	mainBranch := input.MainBranch
	if mainBranch == "" {
		mainBranch = "main"
	}

	hasSpecify := s.hasCommand("specify")
	hasUV := s.hasCommand("uv")
	hasPipx := s.hasCommand("pipx")
	hasGit := s.hasCommand("git")
	hasSuperpowers := s.hasSuperpowers()

	specifyPlan := prereq.DetectSpecify(prereq.StatusInput{
		HasSpecify: hasSpecify,
		HasUV:      hasUV,
		HasPipx:    hasPipx,
	})
	superpowersPlan := prereq.DetectSuperpowers(prereq.SuperpowersInput{
		SkillLinkExists: hasSuperpowers,
		HasGit:          hasGit,
		HomeDir:         s.HomeDir,
		GOOS:            s.GOOS,
	})

	result := Result{RepoRoot: info.Root}
	specifyInstalledNow := false

	autoInstallable := len(specifyPlan.InstallCommands) > 0 || len(superpowersPlan.InstallCommands) > 0
	if autoInstallable {
		acceptInstall := false
		if input.Interactive && s.Prompt != nil {
			acceptInstall, err = s.Prompt.Confirm("Install missing prerequisites now?", true)
			if err != nil {
				return Result{}, err
			}
		}

		if acceptInstall {
			if len(specifyPlan.InstallCommands) > 0 {
				if err := s.runCommands(ctx, specifyPlan.InstallCommands, ""); err != nil {
					return Result{}, err
				}
				specifyInstalledNow = true
				result.InstalledTools = append(result.InstalledTools, specifyPlan.Name)
			}
			if len(superpowersPlan.InstallCommands) > 0 {
				if err := s.runCommands(ctx, superpowersPlan.InstallCommands, ""); err != nil {
					return Result{}, err
				}
				result.InstalledTools = append(result.InstalledTools, superpowersPlan.Name)
			}
		} else {
			result.DocsLinks = append(result.DocsLinks, specifyPlan.DocsURLs...)
			result.DocsLinks = append(result.DocsLinks, superpowersPlan.DocsURLs...)
		}
	}

	if specifyPlan.Status == prereq.StatusManualOnly {
		result.DocsLinks = append(result.DocsLinks, specifyPlan.DocsURLs...)
	}
	if superpowersPlan.Status == prereq.StatusManualOnly {
		result.DocsLinks = append(result.DocsLinks, superpowersPlan.DocsURLs...)
	}
	result.DocsLinks = uniqueStrings(result.DocsLinks)

	bootstrapper := s.Bootstrapper
	if bootstrapper == nil {
		bootstrapper = bootstrap.Engine{}
	}
	if err := bootstrapper.Run(bootstrap.Config{
		RepoRoot:   info.Root,
		ProjectID:  projectID,
		MainBranch: mainBranch,
	}); err != nil {
		return Result{}, err
	}
	result.Bootstrapped = true

	if !info.HasSpecify && (hasSpecify || specifyInstalledNow) {
		if cmd := prereq.BuildSpecifyInitCommand(false, s.specifyInitSupportsAISkills(ctx)); len(cmd) > 0 {
			if err := s.Runner.Run(ctx, command.Command{
				Name: cmd[0],
				Args: cmd[1:],
				Dir:  info.Root,
			}); err != nil {
				return Result{}, err
			}
			result.RanSpecifyInit = true
		}
	}

	return result, nil
}

func (s Service) specifyInitSupportsAISkills(ctx context.Context) bool {
	readCommandOutput := s.ReadCommandOutput
	if readCommandOutput == nil {
		readCommandOutput = func(ctx context.Context, name string, args ...string) (string, error) {
			cmd := exec.CommandContext(ctx, name, args...)
			output, err := cmd.CombinedOutput()
			return string(output), err
		}
	}

	output, err := readCommandOutput(ctx, "specify", "init", "--help")
	if err != nil && output == "" {
		return false
	}

	return strings.Contains(output, "--ai-skills")
}

func (s Service) hasCommand(name string) bool {
	if s.Runner == nil {
		return false
	}
	_, err := s.Runner.LookPath(name)
	return err == nil
}

func (s Service) hasSuperpowers() bool {
	statPath := s.StatPath
	if statPath == nil {
		statPath = func(path string) error {
			_, err := os.Stat(path)
			return err
		}
	}

	if s.HomeDir == "" {
		return false
	}
	return statPath(filepath.Join(s.HomeDir, ".agents", "skills", "superpowers")) == nil
}

func (s Service) runCommands(ctx context.Context, commands [][]string, dir string) error {
	if s.Runner == nil {
		return fmt.Errorf("command runner is required")
	}
	for _, parts := range commands {
		if len(parts) == 0 {
			continue
		}
		if err := s.Runner.Run(ctx, command.Command{
			Name: parts[0],
			Args: parts[1:],
			Dir:  dir,
		}); err != nil {
			return err
		}
	}
	return nil
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

func uniqueStrings(values []string) []string {
	if len(values) == 0 {
		return nil
	}
	seen := make(map[string]struct{}, len(values))
	var result []string
	for _, value := range values {
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	return result
}
