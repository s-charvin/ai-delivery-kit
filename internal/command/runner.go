package command

import (
	"context"
	"os"
	"os/exec"
)

type Command struct {
	Name string
	Args []string
	Dir  string
}

type Runner interface {
	Run(ctx context.Context, cmd Command) error
	LookPath(file string) (string, error)
}

type OSRunner struct{}

func (OSRunner) Run(ctx context.Context, cmd Command) error {
	execCmd := exec.CommandContext(ctx, cmd.Name, cmd.Args...)
	execCmd.Dir = cmd.Dir
	execCmd.Stdout = os.Stdout
	execCmd.Stderr = os.Stderr
	return execCmd.Run()
}

func (OSRunner) LookPath(file string) (string, error) {
	return exec.LookPath(file)
}
