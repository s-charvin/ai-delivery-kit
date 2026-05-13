package prereq

import (
	"path/filepath"
	"testing"
)

func TestDetectCodexSuperpowersPresent(t *testing.T) {
	tool := DetectSuperpowers(SuperpowersInput{
		SkillLinkExists: true,
	})

	if tool.Status != StatusPresent {
		t.Fatalf("expected present, got %s", tool.Status)
	}
}

func TestDetectCodexSuperpowersMissingBuildsClonePlan(t *testing.T) {
	tool := DetectSuperpowers(SuperpowersInput{
		SkillLinkExists: false,
		HasGit:          true,
		HomeDir:         "/tmp/home",
		GOOS:            "linux",
	})

	if tool.Status != StatusMissing {
		t.Fatalf("expected missing, got %s", tool.Status)
	}

	if got := tool.InstallCommands[0][0]; got != "git" {
		t.Fatalf("expected git clone command first, got %q", got)
	}

	if got := tool.InstallCommands[len(tool.InstallCommands)-1][0]; got != "ln" {
		t.Fatalf("expected symlink command last on unix, got %q", got)
	}

	// Last symlink points to the last IDE (codex).
	wantSkillPath := filepath.Join("/tmp/home", ".codex", "skills", "superpowers")
	if got := tool.InstallCommands[len(tool.InstallCommands)-1][len(tool.InstallCommands[len(tool.InstallCommands)-1])-1]; got != wantSkillPath {
		t.Fatalf("expected symlink target path %q, got %q", wantSkillPath, got)
	}
}

func TestDetectCodexSuperpowersWindowsUsesJunction(t *testing.T) {
	tool := DetectSuperpowers(SuperpowersInput{
		SkillLinkExists: false,
		HasGit:          true,
		HomeDir:         `C:\Users\demo`,
		GOOS:            "windows",
	})

	if got := tool.InstallCommands[len(tool.InstallCommands)-1][0]; got != "cmd" {
		t.Fatalf("expected junction command on windows, got %q", got)
	}

	if len(tool.InstallCommands) < 3 {
		t.Fatalf("expected git clone, parent directory creation, and junction commands, got %#v", tool.InstallCommands)
	}

	if got := tool.InstallCommands[1][0]; got != "cmd" {
		t.Fatalf("expected parent directory creation command before junction, got %#v", tool.InstallCommands[1])
	}

	if got := tool.InstallCommands[1][2]; got != "if not exist \""+filepath.Join(`C:\Users\demo`, ".claude", "skills")+"\" mkdir \""+filepath.Join(`C:\Users\demo`, ".claude", "skills")+"\"" {
		t.Fatalf("expected windows parent-directory bootstrap command, got %#v", tool.InstallCommands[1])
	}
}
