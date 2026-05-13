package prereq

import "path/filepath"

const (
	SuperpowersCodexInstallURL = "https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md"
	SuperpowersCodexDocsURL    = "https://github.com/obra/superpowers/blob/main/docs/README.codex.md"
	SuperpowersGitURL          = "https://github.com/obra/superpowers.git"
)

// SupportedIDEs lists the IDE identifiers for user-level skill discovery.
var SupportedIDEs = []string{"claude", "cursor", "codex"}

// SkillDir returns the user-level skills directory for a given IDE.
func SkillDir(homeDir, ide string) string {
	return filepath.Join(homeDir, "."+ide, "skills")
}

type SuperpowersInput struct {
	SkillLinkExists bool
	HasGit          bool
	HomeDir         string
	GOOS            string
}

func DetectSuperpowers(input SuperpowersInput) ToolPlan {
	base := ToolPlan{
		Name:     "superpowers",
		DocsURLs: []string{SuperpowersCodexInstallURL, SuperpowersCodexDocsURL},
	}

	if input.SkillLinkExists {
		base.Status = StatusPresent
		return base
	}

	if !input.HasGit || input.HomeDir == "" {
		base.Status = StatusManualOnly
		base.Notes = []string{"Git and a writable home directory are required for the official Codex install path."}
		return base
	}

	repoPath := filepath.Join(input.HomeDir, ".codex", "superpowers")

	commands := [][]string{
		{"git", "clone", SuperpowersGitURL, repoPath},
	}

	// Install symlinks to all supported IDE skill directories.
	for _, ide := range SupportedIDEs {
		skillRoot := SkillDir(input.HomeDir, ide)
		skillPath := filepath.Join(skillRoot, "superpowers")

		if input.GOOS == "windows" {
			commands = append(commands,
				[]string{"cmd", "/c", "if not exist \"" + skillRoot + "\" mkdir \"" + skillRoot + "\""},
				[]string{"cmd", "/c", "mklink", "/J", skillPath, filepath.Join(repoPath, "skills")},
			)
		} else {
			commands = append(commands,
				[]string{"mkdir", "-p", skillRoot},
				[]string{"ln", "-sfn", filepath.Join(repoPath, "skills"), skillPath},
			)
		}
	}

	base.Status = StatusMissing
	base.InstallCommands = commands
	return base
}
