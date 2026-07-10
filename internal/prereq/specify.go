package prereq

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const (
	SpecKitInstallDocsURL = "https://github.com/github/spec-kit/blob/main/docs/installation.md"
	SpecKitGitRef         = "git+https://github.com/github/spec-kit.git"
)

func DetectPreferredAI(aiDeliveryIDE, homeDir string, statPath func(string) error) string {
	ide := strings.ToLower(strings.TrimSpace(aiDeliveryIDE))
	if ide == "" {
		ide = strings.ToLower(strings.TrimSpace(os.Getenv("AI_DELIVERY_IDE")))
	}

	switch ide {
	case "claude", "cursor", "codex":
		return ide
	case "all", "":
		// fall through to probe
	default:
		// unknown value — probe then default
	}

	if statPath == nil {
		statPath = func(path string) error {
			_, err := os.Stat(path)
			return err
		}
	}

	if homeDir != "" {
		for _, candidate := range SupportedIDEs {
			if statPath(filepath.Join(homeDir, "."+candidate, "skills")) == nil {
				return candidate
			}
		}
	}

	return "codex"
}

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

func BuildSpecifyInitCommand(hasSpecifyDir bool, useAISkills bool, goos string, ai string) []string {
	if hasSpecifyDir {
		return nil
	}
	preferredAI := strings.TrimSpace(ai)
	if preferredAI == "" {
		preferredAI = "codex"
	}
	command := []string{
		"specify",
		"init",
		"--here",
		"--force",
		"--ai",
		preferredAI,
	}
	if useAISkills {
		command = append(command, "--ai-skills")
	}
	command = append(command, "--script", defaultSpecifyScript(goos))
	return command
}

func defaultSpecifyScript(goos string) string {
	if goos == "" {
		goos = runtime.GOOS
	}
	if goos == "windows" {
		return "ps"
	}
	return "sh"
}
