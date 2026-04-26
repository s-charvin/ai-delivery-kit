package prereq

const (
	SpecKitInstallDocsURL = "https://github.com/github/spec-kit/blob/main/docs/installation.md"
	SpecKitGitRef         = "git+https://github.com/github/spec-kit.git"
)

func DetectSpecify(input StatusInput) ToolPlan {
	base := ToolPlan{
		Name:     "specify-cli",
		DocsURLs: []string{SpecKitInstallDocsURL},
	}

	if input.HasSpecify {
		base.Status = StatusPresent
		return base
	}

	if input.HasUV {
		base.Status = StatusMissing
		base.InstallCommands = [][]string{
			{"uv", "tool", "install", "specify-cli", "--from", SpecKitGitRef},
		}
		return base
	}

	if input.HasPipx {
		base.Status = StatusMissing
		base.InstallCommands = [][]string{
			{"pipx", "install", SpecKitGitRef},
		}
		return base
	}

	base.Status = StatusManualOnly
	base.Notes = []string{"Neither uv nor pipx is installed; show the official docs instead of guessing."}
	return base
}

func BuildSpecifyInitCommand(hasSpecifyDir bool, useAISkills bool) []string {
	if hasSpecifyDir {
		return nil
	}
	command := []string{
		"specify",
		"init",
		"--here",
		"--force",
		"--ai",
		"codex",
	}
	if useAISkills {
		command = append(command, "--ai-skills")
	}
	command = append(command, "--script", "sh")
	return command
}
