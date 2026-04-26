package repo

import (
	"context"
	"os/exec"
	"strings"
)

func chooseDefaultBranch(originHeadRef, currentBranch string) string {
	originHeadRef = strings.TrimSpace(originHeadRef)
	if originHeadRef != "" {
		return strings.TrimPrefix(originHeadRef, "origin/")
	}

	currentBranch = strings.TrimSpace(currentBranch)
	if currentBranch != "" && currentBranch != "HEAD" {
		return currentBranch
	}

	return "main"
}

func DetectDefaultBranch(ctx context.Context, repoRoot string) (string, error) {
	originHeadOutput, _ := exec.CommandContext(ctx, "git", "-C", repoRoot, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").CombinedOutput()
	currentBranchOutput, _ := exec.CommandContext(ctx, "git", "-C", repoRoot, "branch", "--show-current").CombinedOutput()
	return chooseDefaultBranch(string(originHeadOutput), string(currentBranchOutput)), nil
}
