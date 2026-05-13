package cli

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/initflow"
	"github.com/s-charvin/ai-delivery-kit/internal/prompt"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

const upgradeRepoPath = "~/ai-delivery-kit"

type initRunner interface {
	Run(ctx context.Context, input initflow.Input) (initflow.Result, error)
}

type App struct {
	stdout     io.Writer
	stderr     io.Writer
	stdin      io.Reader
	homeDir    func() (string, error)
	goos       string
	initRunner initRunner
}

func New(stdout, stderr io.Writer) *App {
	return &App{
		stdout:  stdout,
		stderr:  stderr,
		stdin:   os.Stdin,
		homeDir: os.UserHomeDir,
		goos:    runtime.GOOS,
	}
}

func (a *App) Run(args []string) int {
	if len(args) == 0 {
		a.printUsage()
		return 1
	}

	switch args[0] {
	case "version":
		_, _ = fmt.Fprintln(a.stdout, version.String())
		return 0
	case "init":
		return a.runInit(args[1:])
	case "upgrade":
		return a.runUpgrade()
	default:
		a.printUsage()
		return 1
	}
}

// ---------------------------------------------------------------------------
// init
// ---------------------------------------------------------------------------

func (a *App) runInit(args []string) int {
	targetPath := ""
	upgrade := false

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--upgrade":
			upgrade = true
		default:
			if targetPath == "" {
				targetPath = args[i]
			} else {
				_, _ = fmt.Fprintf(a.stderr, "Unknown argument: %s\n", args[i])
				return 1
			}
		}
	}

	if targetPath == "" {
		var err error
		targetPath, err = os.Getwd()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}
	}

	runner := a.initRunner
	if runner == nil {
		homeDir, err := a.homeDir()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}

		runner = initflow.Service{
			Prompt:           prompt.Terminal{Reader: a.stdin, Writer: a.stdout},
			Runner:           command.OSRunner{},
			Bootstrapper:     bootstrap.Engine{},
			Discover:         repo.Discover,
			DetectMainBranch: repo.DetectDefaultBranch,
			HomeDir:          homeDir,
			GOOS:             a.goos,
		}
	}

	result, err := runner.Run(context.Background(), initflow.Input{
		TargetPath:  targetPath,
		Interactive: true,
		Upgrade:     upgrade,
	})
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}

	if result.Upgraded {
		_, _ = fmt.Fprintf(a.stdout, "Upgraded ai-delivery managed assets in %s\n", result.RepoRoot)
	} else {
		_, _ = fmt.Fprintf(a.stdout, "Initialized ai-delivery in %s\n", result.RepoRoot)
	}
	for _, link := range result.DocsLinks {
		_, _ = fmt.Fprintln(a.stdout, link)
	}
	return 0
}

// ---------------------------------------------------------------------------
// upgrade
// ---------------------------------------------------------------------------

func (a *App) runUpgrade() int {
	homeDir, err := a.homeDir()
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}

	repoPath := filepath.Join(homeDir, "ai-delivery-kit")
	if _, err := os.Stat(repoPath); os.IsNotExist(err) {
		_, _ = fmt.Fprintf(a.stderr, "ai-delivery-kit repo not found at %s\n", repoPath)
		_, _ = fmt.Fprintln(a.stderr, "Run the installer first: curl -fsSL <url> | bash")
		return 1
	}

	cmd := exec.Command("git", "-C", repoPath, "pull")
	cmd.Stdout = a.stdout
	cmd.Stderr = a.stderr
	if err := cmd.Run(); err != nil {
		_, _ = fmt.Fprintf(a.stderr, "git pull failed: %v\n", err)
		return 1
	}

	_, _ = fmt.Fprintln(a.stdout, "Skills updated — IDE symlinks point to ~/ai-delivery-kit/.agents/skills/")
	return 0
}

func (a *App) printUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  version   Print the CLI version")
	_, _ = fmt.Fprintln(a.stderr, "  init      Initialize ai-delivery in a target repository")
	_, _ = fmt.Fprintln(a.stderr, "            Use: ai-delivery init [--upgrade] [/path/to/repo]")
	_, _ = fmt.Fprintln(a.stderr, "            Defaults to current directory if no path is given.")
	_, _ = fmt.Fprintln(a.stderr, "  upgrade   Update the ai-delivery-kit repo (git pull)")
}
