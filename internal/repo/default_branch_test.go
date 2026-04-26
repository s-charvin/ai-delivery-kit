package repo

import "testing"

func TestChooseDefaultBranchPrefersOriginHead(t *testing.T) {
	got := chooseDefaultBranch("main\n", "feature/current")
	if got != "main" {
		t.Fatalf("expected origin head branch, got %q", got)
	}
}

func TestChooseDefaultBranchFallsBackToCurrentBranch(t *testing.T) {
	got := chooseDefaultBranch("", "release/main")
	if got != "release/main" {
		t.Fatalf("expected current branch fallback, got %q", got)
	}
}

func TestChooseDefaultBranchFallsBackToMain(t *testing.T) {
	got := chooseDefaultBranch("", "")
	if got != "main" {
		t.Fatalf("expected main fallback, got %q", got)
	}
}

func TestChooseDefaultBranchIgnoresGitFatalOutput(t *testing.T) {
	got := chooseDefaultBranch("fatal: ref refs/remotes/origin/HEAD is not a symbolic ref\n", "main-dev")
	if got != "main-dev" {
		t.Fatalf("expected fatal output to be ignored, got %q", got)
	}
}
