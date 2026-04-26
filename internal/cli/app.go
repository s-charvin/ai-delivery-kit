package cli

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"
	"runtime"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/initflow"
	"github.com/s-charvin/ai-delivery-kit/internal/prompt"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

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
	default:
		a.printUsage()
		return 1
	}
}

func (a *App) runInit(args []string) int {
	if len(args) == 0 {
		_, _ = fmt.Fprintln(a.stderr, "init requires a target repository path")
		a.printUsage()
		return 1
	}

	target := args[0]
	flagSet := flag.NewFlagSet("init", flag.ContinueOnError)
	flagSet.SetOutput(a.stderr)

	var projectID string
	var mainBranch string
	flagSet.StringVar(&projectID, "project-id", "", "Project identifier")
	flagSet.StringVar(&mainBranch, "main-branch", "main", "Main branch name")

	if err := flagSet.Parse(args[1:]); err != nil {
		return 1
	}
	if flagSet.NArg() > 0 {
		_, _ = fmt.Fprintf(a.stderr, "unexpected extra arguments: %v\n", flagSet.Args())
		return 1
	}

	runner := a.initRunner
	if runner == nil {
		homeDir, err := a.homeDir()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}

		runner = initflow.Service{
			Prompt:       prompt.Terminal{Reader: a.stdin, Writer: a.stdout},
			Runner:       command.OSRunner{},
			Bootstrapper: bootstrap.Engine{},
			Discover:     repo.Discover,
			HomeDir:      homeDir,
			GOOS:         a.goos,
		}
	}

	result, err := runner.Run(context.Background(), initflow.Input{
		TargetPath:  target,
		ProjectID:   projectID,
		MainBranch:  mainBranch,
		Interactive: true,
	})
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}

	_, _ = fmt.Fprintf(a.stdout, "Initialized ai-delivery in %s\n", result.RepoRoot)
	for _, link := range result.DocsLinks {
		_, _ = fmt.Fprintln(a.stdout, link)
	}
	return 0
}

func (a *App) printUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  version   Print the CLI version")
	_, _ = fmt.Fprintln(a.stderr, "  init      Initialize ai-delivery in a target repository")
}
