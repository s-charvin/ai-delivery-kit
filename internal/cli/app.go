package cli

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

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
	case "ide-gates":
		return a.runIDEGates(args[1:])
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
	a.printIDEGateAmendHint(result.IDEGateAmend)
	for _, link := range result.DocsLinks {
		_, _ = fmt.Fprintln(a.stdout, link)
	}
	return 0
}

func (a *App) printIDEGateAmendHint(report bootstrap.AmendReport) {
	if report.Empty() {
		return
	}
	_, _ = fmt.Fprintf(a.stdout, "Amended IDE gate config(s): %s\n", strings.Join(report.Files, ", "))
	_, _ = fmt.Fprintf(a.stdout, "Backup: %s\n", report.BackupDir)
	_, _ = fmt.Fprintf(a.stdout, "Restore: ai-delivery ide-gates restore --to %s\n", report.BackupStamp)
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

// ---------------------------------------------------------------------------
// ide-gates
// ---------------------------------------------------------------------------

func (a *App) runIDEGates(args []string) int {
	if len(args) == 0 {
		a.printIDEGatesUsage()
		return 1
	}
	switch args[0] {
	case "list":
		return a.runIDEGatesList(args[1:])
	case "restore":
		return a.runIDEGatesRestore(args[1:])
	default:
		a.printIDEGatesUsage()
		return 1
	}
}

func (a *App) runIDEGatesList(args []string) int {
	repoRoot, err := a.resolveRepoRoot(args)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	stamps, err := bootstrap.ListIDEGateBackups(repoRoot)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	if len(stamps) == 0 {
		_, _ = fmt.Fprintln(a.stdout, "No IDE gate backups found.")
		return 0
	}
	for _, stamp := range stamps {
		_, _ = fmt.Fprintln(a.stdout, stamp)
	}
	return 0
}

func (a *App) runIDEGatesRestore(args []string) int {
	stamp := ""
	var positional []string
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--to":
			if i+1 >= len(args) {
				_, _ = fmt.Fprintln(a.stderr, "Missing value for --to")
				return 1
			}
			i++
			stamp = args[i]
		default:
			positional = append(positional, args[i])
		}
	}

	repoRoot, err := a.resolveRepoRoot(positional)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}

	if stamp == "" {
		stamps, listErr := bootstrap.ListIDEGateBackups(repoRoot)
		if listErr != nil {
			_, _ = fmt.Fprintln(a.stderr, listErr)
			return 1
		}
		if len(stamps) == 0 {
			_, _ = fmt.Fprintln(a.stderr, "No IDE gate backups found.")
			return 1
		}
		stamp = stamps[0]
	}

	report, err := bootstrap.RestoreIDEGateBackup(repoRoot, stamp, nil)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	_, _ = fmt.Fprintf(a.stdout, "Restored IDE gate config from %s\n", stamp)
	if !report.Empty() {
		_, _ = fmt.Fprintf(a.stdout, "Pre-restore backup: %s\n", report.BackupDir)
		_, _ = fmt.Fprintf(a.stdout, "Undo restore: ai-delivery ide-gates restore --to %s\n", report.BackupStamp)
	}
	return 0
}

func (a *App) resolveRepoRoot(args []string) (string, error) {
	target := ""
	if len(args) > 0 {
		target = args[0]
	}
	if target == "" {
		cwd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		target = cwd
	}
	info, err := repo.Discover(target)
	if err != nil {
		return "", err
	}
	return info.Root, nil
}

func (a *App) printIDEGatesUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery ide-gates <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  list                 List IDE gate backup timestamps (newest first)")
	_, _ = fmt.Fprintln(a.stderr, "  restore [--to <ts>]  Restore amendable IDE gate JSON from a backup")
	_, _ = fmt.Fprintln(a.stderr, "                       Defaults to the newest backup when --to is omitted.")
}

func (a *App) printUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  version     Print the CLI version")
	_, _ = fmt.Fprintln(a.stderr, "  init        Initialize ai-delivery in a target repository")
	_, _ = fmt.Fprintln(a.stderr, "              Use: ai-delivery init [--upgrade] [/path/to/repo]")
	_, _ = fmt.Fprintln(a.stderr, "              Defaults to current directory if no path is given.")
	_, _ = fmt.Fprintln(a.stderr, "  upgrade     Update the ai-delivery-kit repo (git pull)")
	_, _ = fmt.Fprintln(a.stderr, "  ide-gates   List/restore IDE gate config backups")
}
