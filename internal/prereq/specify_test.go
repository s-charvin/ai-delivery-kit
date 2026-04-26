package prereq

import "testing"

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
	if cmd := BuildSpecifyInitCommand(true, true); len(cmd) != 0 {
		t.Fatalf("expected no init command when .specify already exists, got %#v", cmd)
	}
}

func TestBuildSpecifyInitCommandIncludesForce(t *testing.T) {
	cmd := BuildSpecifyInitCommand(false, false)

	for _, arg := range cmd {
		if arg == "--force" {
			return
		}
	}

	t.Fatalf("expected --force in specify init command, got %#v", cmd)
}

func TestBuildSpecifyInitCommandAddsAISkillsOnlyWhenSupported(t *testing.T) {
	withSkills := BuildSpecifyInitCommand(false, true)
	withoutSkills := BuildSpecifyInitCommand(false, false)

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
