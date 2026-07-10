package prereq

import (
	"os"
	"strings"
	"testing"
)

func TestDetectSpecifyUsesInstalledBinary(t *testing.T) {
	tool := DetectSpecify(StatusInput{
		HasSpecify: true,
		HasUV:      true,
		HasPipx:    true,
	})

	if tool.Status != StatusPresent {
		t.Fatalf("expected present, got %s", tool.Status)
	}

	if len(tool.InstallCommands) != 0 {
		t.Fatalf("expected no install commands, got %#v", tool.InstallCommands)
	}
}

func TestDetectSpecifyPrefersUVInstall(t *testing.T) {
	tool := DetectSpecify(StatusInput{
		HasSpecify: false,
		HasUV:      true,
		HasPipx:    true,
	})

	if tool.Status != StatusMissing {
		t.Fatalf("expected missing, got %s", tool.Status)
	}

	if got := tool.InstallCommands[0][0]; got != "uv" {
		t.Fatalf("expected uv install command, got %q", got)
	}
}

func TestDetectSpecifyFallsBackToPipx(t *testing.T) {
	tool := DetectSpecify(StatusInput{
		HasSpecify: false,
		HasUV:      false,
		HasPipx:    true,
	})

	if tool.Status != StatusMissing {
		t.Fatalf("expected missing, got %s", tool.Status)
	}

	if got := tool.InstallCommands[0][0]; got != "pipx" {
		t.Fatalf("expected pipx install command, got %q", got)
	}
}

func TestBuildSpecifyInitCommandSkipsExistingSpecifyTree(t *testing.T) {
	if cmd := BuildSpecifyInitCommand(true, true, "linux", "cursor"); len(cmd) != 0 {
		t.Fatalf("expected no init command when .specify already exists, got %#v", cmd)
	}
}

func TestBuildSpecifyInitCommandIncludesForce(t *testing.T) {
	cmd := BuildSpecifyInitCommand(false, false, "linux", "codex")

	for _, arg := range cmd {
		if arg == "--force" {
			return
		}
	}

	t.Fatalf("expected --force in specify init command, got %#v", cmd)
}

func TestBuildSpecifyInitCommandAddsAISkillsOnlyWhenSupported(t *testing.T) {
	withSkills := BuildSpecifyInitCommand(false, true, "linux", "codex")
	withoutSkills := BuildSpecifyInitCommand(false, false, "linux", "codex")

	foundWith := false
	for _, arg := range withSkills {
		if arg == "--ai-skills" {
			foundWith = true
			break
		}
	}
	if !foundWith {
		t.Fatalf("expected --ai-skills when supported, got %#v", withSkills)
	}

	for _, arg := range withoutSkills {
		if arg == "--ai-skills" {
			t.Fatalf("did not expect --ai-skills when unsupported, got %#v", withoutSkills)
		}
	}
}

func TestBuildSpecifyInitCommandDefaultsToShOutsideWindows(t *testing.T) {
	cmd := BuildSpecifyInitCommand(false, false, "linux", "codex")

	assertSpecifyScriptArg(t, cmd, "sh")
}

func TestBuildSpecifyInitCommandDefaultsToPsOnWindows(t *testing.T) {
	cmd := BuildSpecifyInitCommand(false, false, "windows", "codex")

	assertSpecifyScriptArg(t, cmd, "ps")
}

func assertSpecifyScriptArg(t *testing.T, cmd []string, expected string) {
	t.Helper()

	for i := 0; i < len(cmd)-1; i++ {
		if cmd[i] == "--script" {
			if cmd[i+1] != expected {
				t.Fatalf("expected --script %q, got %#v", expected, cmd)
			}
			return
		}
	}

	t.Fatalf("expected --script %q, got %#v", expected, cmd)
}

func TestDetectPreferredAIRespectsExplicitIDE(t *testing.T) {
	if got := DetectPreferredAI("cursor", "/tmp/home", nil); got != "cursor" {
		t.Fatalf("expected cursor, got %q", got)
	}
}

func TestDetectPreferredAIProbesSkillDirs(t *testing.T) {
	stat := func(path string) error {
		if strings.HasSuffix(path, ".claude/skills") {
			return nil
		}
		return os.ErrNotExist
	}
	if got := DetectPreferredAI("all", "/tmp/home", stat); got != "claude" {
		t.Fatalf("expected claude from probe order, got %q", got)
	}
}

func TestDetectPreferredAIDefaultsToCodex(t *testing.T) {
	stat := func(string) error { return os.ErrNotExist }
	if got := DetectPreferredAI("", "/tmp/home", stat); got != "codex" {
		t.Fatalf("expected codex default, got %q", got)
	}
}

func TestBuildSpecifyInitCommandUsesPreferredAI(t *testing.T) {
	cmd := BuildSpecifyInitCommand(false, false, "linux", "claude")
	if !containsArg(cmd, "--ai") {
		t.Fatalf("expected --ai flag, got %#v", cmd)
	}
	for i := 0; i < len(cmd)-1; i++ {
		if cmd[i] == "--ai" && cmd[i+1] == "claude" {
			return
		}
	}
	t.Fatalf("expected --ai claude, got %#v", cmd)
}

func containsArg(args []string, target string) bool {
	for _, arg := range args {
		if arg == target {
			return true
		}
	}
	return false
}
