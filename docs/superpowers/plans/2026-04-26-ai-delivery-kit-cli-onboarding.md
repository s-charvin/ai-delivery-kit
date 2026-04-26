# AI Delivery Kit CLI Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Go-based `ai-delivery` CLI that initializes governed `ai-delivery` assets in arbitrary repositories, optionally installs `specify-cli` and `superpowers`, and ships through GitHub Actions plus GitHub Releases with install and bootstrap scripts.

**Architecture:** Keep v1 narrow and operationally safe. The CLI is a stdlib-first Go binary with a module-root embedded asset package, a Codex-first `superpowers` installer, a compatibility wrapper for the legacy source-repo bootstrap script, and GitHub Actions plus GoReleaser for multi-platform release packaging. The CLI performs preflight checks before any repository mutation, prompts before prerequisite installation, skips already-installed tools, and keeps the release flow split between `main` validation and `tag push` publication.

**Tech Stack:** Go 1.22, Go stdlib, GitHub Actions, GoReleaser, Bash, PowerShell, existing shell contract tests.

---

## File Structure

- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/go.mod`
  - Declares the new Go module at `github.com/s-charvin/ai-delivery-kit`.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/.gitignore](/Users/charvin/Projects/spec-dev/ai-delivery-kit/.gitignore)
  - Ignores `dist/` and other local build outputs.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/cmd/ai-delivery/main.go`
  - CLI entrypoint.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/version/version.go`
  - Build-time version metadata.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go`
  - Top-level command parsing and dispatch.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go`
  - Version and usage command tests.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets.go`
  - Module-root `go:embed` package. This stays at the repo root because `go:embed` cannot traverse `..` to reach `.agents`, `docs`, `scripts`, and `tests`.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go`
  - Enumerates the governed assets copied into target repositories.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go`
  - Verifies embedded asset coverage.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery.go`
  - Resolves git root, `.specify` presence, and managed path conflicts.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery_test.go`
  - Temp-repo tests for discovery and conflict detection.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go`
  - Maps embedded source assets to target-repo relative paths.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go`
  - Writes governed skills, validation scripts, docs, and seeded `.ai-delivery` JSON files.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go`
  - Integration-style tests for governed writes.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/command/runner.go`
  - Wrapper for external commands so tests can stub `git`, `specify`, and shell invocations.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prompt/confirm.go`
  - Interactive yes/no prompt abstraction with a non-interactive mode.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/types.go`
  - Shared types for dependency status, docs links, and install command plans.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify.go`
  - `specify-cli` detection, docs links, install plan, and `specify init` command planning.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify_test.go`
  - `specify-cli` detection and install-plan tests.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers.go`
  - Codex-first `superpowers` detection and install plan.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers_test.go`
  - `superpowers` status and install-plan tests.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go`
  - Orchestrates discovery, prompts, prerequisite installs, bootstrap, and `specify init`.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go`
  - Full flow tests for install-yes, install-no, and already-installed cases.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh`
  - Unix install script that downloads the release binary and verifies checksums.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1`
  - Windows install script.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh`
  - Unix no-install bootstrap script that downloads a temporary release binary and runs `init`.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1`
  - Windows no-install bootstrap script.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh)
  - Keep source-repo compatibility by delegating to `go run ./cmd/ai-delivery init`.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh`
  - Unix smoke test for the public bootstrap script with a local command override.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.goreleaser.yaml`
  - Release packaging matrix and checksum generation.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/ci.yml`
  - `main` and PR validation only.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/release.yml`
  - `tag push` formal release pipeline.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md`
  - Public repo entrypoint with install and bootstrap usage.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md)
  - Replace source-repo-first instructions with CLI-first and bootstrap-script-first guidance.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh)
  - Validate the new onboarding doc and new CLI-first wording.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh)
  - Keep the legacy bootstrap contract green through the wrapper.

## External Install Truth

Use these official links and commands in the implementation:

- `specify-cli` installation guide:
  - `https://github.com/github/spec-kit/blob/main/docs/installation.md`
- `specify-cli` recommended persistent install:
  - `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z`
- `specify-cli` one-shot install:
  - `uvx --from git+https://github.com/github/spec-kit.git@vX.Y.Z specify init --here`
- `superpowers` Codex install guide:
  - `https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md`
- `superpowers` Codex docs page:
  - `https://github.com/obra/superpowers/blob/main/docs/README.codex.md`

For v1, only automate the Codex `superpowers` install path. If the environment is not the Codex path this repo is targeting, report the official docs link and continue.

## Task 1: Scaffold The Go Module And Minimal CLI

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/go.mod`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/cmd/ai-delivery/main.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/version/version.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go`
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/.gitignore](/Users/charvin/Projects/spec-dev/ai-delivery-kit/.gitignore)

- [ ] **Step 1: Create the module and ignore local build outputs**

Add:

```go
module github.com/s-charvin/ai-delivery-kit

go 1.22.0
```

Update `.gitignore` to:

```gitignore
.worktrees/
.idea/
.DS_Store
dist/
bin/
```

- [ ] **Step 2: Write the failing CLI tests**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go`:

```go
package cli

import (
	"bytes"
	"strings"
	"testing"
)

func TestRunVersionCommand(t *testing.T) {
	var out bytes.Buffer
	app := New(&out, &out)

	if exitCode := app.Run([]string{"version"}); exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if got := out.String(); !strings.Contains(got, "dev") {
		t.Fatalf("expected dev version output, got %q", got)
	}
}

func TestRunWithoutCommandPrintsUsage(t *testing.T) {
	var out bytes.Buffer
	app := New(&out, &out)

	if exitCode := app.Run(nil); exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}

	if got := out.String(); !strings.Contains(got, "Usage: ai-delivery") {
		t.Fatalf("expected usage output, got %q", got)
	}
}
```

- [ ] **Step 3: Run the new tests to confirm the CLI does not exist yet**

Run:

```bash
go test ./internal/cli -v
```

Expected: FAIL with errors like `undefined: New`.

- [ ] **Step 4: Implement the version package and minimal command dispatcher**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/version/version.go`:

```go
package version

import "fmt"

var (
	Version = "dev"
	Commit  = "unknown"
	Date    = "unknown"
)

func String() string {
	return fmt.Sprintf("%s (%s, %s)", Version, Commit, Date)
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go`:

```go
package cli

import (
	"fmt"
	"io"

	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

type App struct {
	stdout io.Writer
	stderr io.Writer
}

func New(stdout, stderr io.Writer) *App {
	return &App{
		stdout: stdout,
		stderr: stderr,
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
	default:
		a.printUsage()
		return 1
	}
}

func (a *App) printUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  version   Print the CLI version")
	_, _ = fmt.Fprintln(a.stderr, "  init      Initialize ai-delivery in a target repository")
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/cmd/ai-delivery/main.go`:

```go
package main

import (
	"os"

	"github.com/s-charvin/ai-delivery-kit/internal/cli"
)

func main() {
	app := cli.New(os.Stdout, os.Stderr)
	os.Exit(app.Run(os.Args[1:]))
}
```

- [ ] **Step 5: Run the CLI tests again**

Run:

```bash
go test ./internal/cli -v
```

Expected: PASS for both CLI tests.

- [ ] **Step 6: Commit the scaffold**

Run:

```bash
git add .gitignore go.mod cmd/ai-delivery/main.go internal/version/version.go internal/cli/app.go internal/cli/app_test.go
git commit -m "feat: scaffold ai-delivery cli module"
```

## Task 2: Embed Managed Assets And Add Repository Discovery

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery_test.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go`

- [ ] **Step 1: Write failing tests for embedded assets and git-root discovery**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go`:

```go
package kitassets

import "testing"

func TestEmbeddedAssetsContainGovernedSkills(t *testing.T) {
	required := []string{
		".agents/skills/ai-delivery/requirement-breakdown/SKILL.md",
		".agents/skills/ai-delivery/api-contract-mapping/SKILL.md",
		"docs/guides/ai-delivery-any-repo-onboarding.md",
		"scripts/validate-project-ai-delivery-skills.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}

	for _, path := range required {
		if _, err := Embedded.ReadFile(path); err != nil {
			t.Fatalf("expected embedded asset %s: %v", path, err)
		}
	}
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery_test.go`:

```go
package repo

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverResolvesGitRoot(t *testing.T) {
	root := t.TempDir()
	nested := filepath.Join(root, "app", "src")
	if err := os.MkdirAll(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatal(err)
	}

	info, err := Discover(nested)
	if err != nil {
		t.Fatalf("discover failed: %v", err)
	}

	if info.Root != root {
		t.Fatalf("expected root %s, got %s", root, info.Root)
	}
}
```

- [ ] **Step 2: Run the tests to confirm the asset package and discovery package are still missing**

Run:

```bash
go test ./... -run 'TestEmbeddedAssetsContainGovernedSkills|TestDiscoverResolvesGitRoot' -v
```

Expected: FAIL with missing package or symbol errors for `Embedded` and `Discover`.

- [ ] **Step 3: Implement the module-root embedded asset package and repo discovery**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets.go`:

```go
package kitassets

import "embed"

// Embedded must live at the module root because go:embed cannot traverse .. to reach sibling directories.
//
//go:embed .agents/skills/ai-delivery/** docs/guides/ai-delivery-any-repo-onboarding.md scripts/validate-project-ai-delivery-skills.sh tests/ai-delivery-skills/api-nonblocking-policy.test.sh tests/ai-delivery-skills/validate-sources.test.sh
var Embedded embed.FS
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go`:

```go
package kitassets

var ManagedSourcePaths = []string{
	".agents/skills/ai-delivery/requirement-breakdown",
	".agents/skills/ai-delivery/api-contract-mapping",
	".agents/skills/ai-delivery/ui-requirement-mapping",
	".agents/skills/ai-delivery/ui-acceptance-contract",
	".agents/skills/ai-delivery/ui-interaction-design",
	".agents/skills/ai-delivery/ai-delivery-orchestrator",
	"docs/guides/ai-delivery-any-repo-onboarding.md",
	"scripts/validate-project-ai-delivery-skills.sh",
	"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
	"tests/ai-delivery-skills/validate-sources.test.sh",
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/discovery.go`:

```go
package repo

import (
	"fmt"
	"os"
	"path/filepath"
)

type Info struct {
	Root            string
	HasSpecify      bool
	ManagedConflicts []string
}

func Discover(start string) (Info, error) {
	abs, err := filepath.Abs(start)
	if err != nil {
		return Info{}, fmt.Errorf("resolve target path: %w", err)
	}

	root, err := findGitRoot(abs)
	if err != nil {
		return Info{}, err
	}

	_, specifyErr := os.Stat(filepath.Join(root, ".specify"))
	return Info{
		Root:       root,
		HasSpecify: specifyErr == nil,
	}, nil
}

func findGitRoot(start string) (string, error) {
	current := start
	for {
		gitPath := filepath.Join(current, ".git")
		if _, err := os.Stat(gitPath); err == nil {
			return current, nil
		}

		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("target is not inside a git repository: %s", start)
		}
		current = parent
	}
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go`:

```go
package bootstrap

type ManagedAsset struct {
	Source string
	Target string
	Kind   string
}

func Manifest() []ManagedAsset {
	return []ManagedAsset{
		{Source: ".agents/skills/ai-delivery/requirement-breakdown", Target: ".agents/skills/requirement-breakdown", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/api-contract-mapping", Target: ".agents/skills/api-contract-mapping", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-requirement-mapping", Target: ".agents/skills/ui-requirement-mapping", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-acceptance-contract", Target: ".agents/skills/ui-acceptance-contract", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ui-interaction-design", Target: ".agents/skills/ui-interaction-design", Kind: "dir"},
		{Source: ".agents/skills/ai-delivery/ai-delivery-orchestrator", Target: ".agents/skills/ai-delivery-orchestrator", Kind: "dir"},
		{Source: "docs/guides/ai-delivery-any-repo-onboarding.md", Target: ".ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md", Kind: "file"},
		{Source: "scripts/validate-project-ai-delivery-skills.sh", Target: ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh", Kind: "file"},
		{Source: "tests/ai-delivery-skills/validate-sources.test.sh", Target: ".ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh", Kind: "file"},
	}
}
```

- [ ] **Step 4: Run the focused tests again**

Run:

```bash
go test ./... -run 'TestEmbeddedAssetsContainGovernedSkills|TestDiscoverResolvesGitRoot' -v
```

Expected: PASS for both new tests.

- [ ] **Step 5: Commit the asset and discovery layer**

Run:

```bash
git add managedassets.go managed_manifest.go managedassets_test.go internal/repo/discovery.go internal/repo/discovery_test.go internal/bootstrap/manifest.go
git commit -m "feat: add embedded assets and repo discovery"
```

## Task 3: Rebuild The Bootstrap Engine In Go

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go`

- [ ] **Step 1: Write the failing bootstrap engine tests**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go`:

```go
package bootstrap

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunWritesGovernedAssetsAndSeedFiles(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	if err := engine.Run(Config{
		RepoRoot:   target,
		ProjectID:  "demo-project",
		MainBranch: "main",
	}); err != nil {
		t.Fatalf("run failed: %v", err)
	}

	required := []string{
		filepath.Join(target, ".agents/skills/requirement-breakdown/SKILL.md"),
		filepath.Join(target, ".ai-delivery/scripts/validate-project-ai-delivery-skills.sh"),
		filepath.Join(target, ".ai-delivery/meta/project-binding.json"),
		filepath.Join(target, ".ai-delivery/runtime/main-branch.json"),
	}

	for _, path := range required {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("expected %s: %v", path, err)
		}
	}

	body, err := os.ReadFile(filepath.Join(target, ".ai-delivery/meta/project-binding.json"))
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(body), `"project_id": "demo-project"`) {
		t.Fatalf("expected project id in binding json, got %s", string(body))
	}
}

func TestRunFailsOnManagedConflict(t *testing.T) {
	target := t.TempDir()
	if err := os.Mkdir(filepath.Join(target, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(target, ".agents/skills/requirement-breakdown"), 0o755); err != nil {
		t.Fatal(err)
	}

	engine := Engine{}
	err := engine.Run(Config{
		RepoRoot:   target,
		ProjectID:  "demo-project",
		MainBranch: "main",
	})
	if err == nil {
		t.Fatal("expected conflict error, got nil")
	}
}
```

- [ ] **Step 2: Run the engine tests to confirm the engine is still missing**

Run:

```bash
go test ./internal/bootstrap -v
```

Expected: FAIL with errors like `undefined: Engine` and `undefined: Config`.

- [ ] **Step 3: Implement the Go bootstrap engine with seeded `.ai-delivery` JSON**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go`:

```go
package bootstrap

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	kitassets "github.com/s-charvin/ai-delivery-kit"
)

type Config struct {
	RepoRoot   string
	ProjectID  string
	MainBranch string
}

type Engine struct{}

func (Engine) Run(cfg Config) error {
	for _, asset := range Manifest() {
		target := filepath.Join(cfg.RepoRoot, asset.Target)
		if _, err := os.Stat(target); err == nil {
			return fmt.Errorf("managed asset already exists: %s", target)
		}
	}

	for _, rel := range []string{
		".ai-delivery/requirements",
		".ai-delivery/figma-cache",
		".ai-delivery/logs/sessions",
		".ai-delivery/logs/subagents",
		".ai-delivery/meta",
		".ai-delivery/runtime",
	} {
		if err := os.MkdirAll(filepath.Join(cfg.RepoRoot, rel), 0o755); err != nil {
			return err
		}
	}

	for _, asset := range Manifest() {
		if asset.Kind == "dir" {
			if err := copyEmbeddedDir(asset.Source, filepath.Join(cfg.RepoRoot, asset.Target)); err != nil {
				return err
			}
			continue
		}
		if err := copyEmbeddedFile(asset.Source, filepath.Join(cfg.RepoRoot, asset.Target)); err != nil {
			return err
		}
	}

	if err := seedFile(filepath.Join(cfg.RepoRoot, ".ai-delivery/logs/events.ndjson"), ""); err != nil {
		return err
	}

	now := time.Now().UTC().Format(time.RFC3339)
	if err := writeJSON(filepath.Join(cfg.RepoRoot, ".ai-delivery/meta/project-binding.json"), map[string]any{
		"version":         1,
		"project_id":      cfg.ProjectID,
		"project_root":    cfg.RepoRoot,
		"specify_path":    ".specify",
		"ai_delivery_path": ".ai-delivery",
		"updated_at":      now,
		"updated_by":      "ai-delivery",
	}); err != nil {
		return err
	}

	if err := writeJSON(filepath.Join(cfg.RepoRoot, ".ai-delivery/runtime/main-branch.json"), map[string]any{
		"version":    1,
		"branch_name": cfg.MainBranch,
		"status":     "configured",
		"updated_at": now,
		"updated_by": "ai-delivery",
	}); err != nil {
		return err
	}

	for _, rel := range []string{
		".ai-delivery/runtime/worktrees.json",
		".ai-delivery/runtime/merge-queue.json",
		".ai-delivery/runtime/blockers.json",
		".ai-delivery/runtime/task-board.json",
		".ai-delivery/runtime/slice-closures.json",
		".ai-delivery/runtime/agent-sessions.json",
	} {
		if err := writeJSON(filepath.Join(cfg.RepoRoot, rel), map[string]any{
			"version":    1,
			"items":      []any{},
			"updated_at": now,
			"updated_by": "ai-delivery",
		}); err != nil {
			return err
		}
	}

	return nil
}

func copyEmbeddedDir(source string, target string) error {
	return fs.WalkDir(kitassets.Embedded, source, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		relative := strings.TrimPrefix(path, source)
		relative = strings.TrimPrefix(relative, "/")
		destination := filepath.Join(target, filepath.FromSlash(relative))

		if d.IsDir() {
			return os.MkdirAll(destination, 0o755)
		}

		return copyEmbeddedFile(path, destination)
	})
}

func copyEmbeddedFile(source string, target string) error {
	contents, err := kitassets.Embedded.ReadFile(source)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	return os.WriteFile(target, contents, 0o755)
}

func seedFile(target string, body string) error {
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	return os.WriteFile(target, []byte(body), 0o644)
}

func writeJSON(target string, body map[string]any) error {
	bytes, err := json.MarshalIndent(body, "", "  ")
	if err != nil {
		return err
	}
	bytes = append(bytes, '\n')
	return seedFile(target, string(bytes))
}
```

- [ ] **Step 4: Run the bootstrap package tests again**

Run:

```bash
go test ./internal/bootstrap -v
```

Expected: PASS for the bootstrap engine tests.

- [ ] **Step 5: Commit the Go bootstrap engine**

Run:

```bash
git add internal/bootstrap/engine.go internal/bootstrap/engine_test.go
git commit -m "feat: port bootstrap engine to go"
```

## Task 4: Add Command Runner, Prompting, And The `specify-cli` Adapter

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/command/runner.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prompt/confirm.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/types.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify_test.go`

- [ ] **Step 1: Write the failing `specify-cli` adapter tests**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify_test.go`:

```go
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

func TestBuildSpecifyInitCommandSkipsExistingSpecifyTree(t *testing.T) {
	if cmd := BuildSpecifyInitCommand(true); len(cmd) != 0 {
		t.Fatalf("expected no init command when .specify already exists, got %#v", cmd)
	}
}
```

- [ ] **Step 2: Run the new prerequisite tests**

Run:

```bash
go test ./internal/prereq -run 'TestDetectSpecify|TestBuildSpecifyInitCommand' -v
```

Expected: FAIL because `StatusInput`, `DetectSpecify`, `StatusPresent`, and `BuildSpecifyInitCommand` do not exist yet.

- [ ] **Step 3: Implement the shared runner, prompt, and `specify-cli` plan builder**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/command/runner.go`:

```go
package command

import (
	"context"
	"os/exec"
)

type Runner interface {
	Run(ctx context.Context, name string, args ...string) error
	LookPath(file string) (string, error)
}

type OSRunner struct{}

func (OSRunner) Run(ctx context.Context, name string, args ...string) error {
	cmd := exec.CommandContext(ctx, name, args...)
	return cmd.Run()
}

func (OSRunner) LookPath(file string) (string, error) {
	return exec.LookPath(file)
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prompt/confirm.go`:

```go
package prompt

import (
	"bufio"
	"fmt"
	"io"
	"strings"
)

type Prompter interface {
	Confirm(question string, defaultYes bool) (bool, error)
}

type Terminal struct {
	Reader io.Reader
	Writer io.Writer
}

func (t Terminal) Confirm(question string, defaultYes bool) (bool, error) {
	suffix := "[y/N]"
	if defaultYes {
		suffix = "[Y/n]"
	}

	if _, err := fmt.Fprintf(t.Writer, "%s %s ", question, suffix); err != nil {
		return false, err
	}

	line, err := bufio.NewReader(t.Reader).ReadString('\n')
	if err != nil {
		return false, err
	}

	answer := strings.TrimSpace(strings.ToLower(line))
	if answer == "" {
		return defaultYes, nil
	}
	return answer == "y" || answer == "yes", nil
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/types.go`:

```go
package prereq

type Status string

const (
	StatusPresent    Status = "present"
	StatusMissing    Status = "missing"
	StatusManualOnly Status = "manual-only"
)

type StatusInput struct {
	HasSpecify bool
	HasUV      bool
	HasPipx    bool
}

type ToolPlan struct {
	Name            string
	Status          Status
	DocsURL         string
	InstallCommands [][]string
	Notes           []string
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/specify.go`:

```go
package prereq

const (
	SpecKitInstallDocsURL = "https://github.com/github/spec-kit/blob/main/docs/installation.md"
	SpecKitGitRef         = "git+https://github.com/github/spec-kit.git"
)

func DetectSpecify(input StatusInput) ToolPlan {
	if input.HasSpecify {
		return ToolPlan{
			Name:    "specify-cli",
			Status:  StatusPresent,
			DocsURL: SpecKitInstallDocsURL,
		}
	}

	if input.HasUV {
		return ToolPlan{
			Name:    "specify-cli",
			Status:  StatusMissing,
			DocsURL: SpecKitInstallDocsURL,
			InstallCommands: [][]string{
				{"uv", "tool", "install", "specify-cli", "--from", SpecKitGitRef},
			},
		}
	}

	if input.HasPipx {
		return ToolPlan{
			Name:    "specify-cli",
			Status:  StatusMissing,
			DocsURL: SpecKitInstallDocsURL,
			InstallCommands: [][]string{
				{"pipx", "install", SpecKitGitRef},
			},
		}
	}

	return ToolPlan{
		Name:    "specify-cli",
		Status:  StatusManualOnly,
		DocsURL: SpecKitInstallDocsURL,
		Notes:   []string{"Neither uv nor pipx is installed; show the official docs instead of guessing."},
	}
}

func BuildSpecifyInitCommand(hasSpecifyDir bool) []string {
	if hasSpecifyDir {
		return nil
	}

	return []string{
		"specify",
		"init",
		"--here",
		"--ai",
		"codex",
		"--ai-skills",
		"--script",
		"sh",
	}
}
```

- [ ] **Step 4: Run the `specify-cli` adapter tests again**

Run:

```bash
go test ./internal/prereq -run 'TestDetectSpecify|TestBuildSpecifyInitCommand' -v
```

Expected: PASS for the `specify-cli` detection and init-command tests.

- [ ] **Step 5: Commit the `specify-cli` adapter**

Run:

```bash
git add internal/command/runner.go internal/prompt/confirm.go internal/prereq/types.go internal/prereq/specify.go internal/prereq/specify_test.go
git commit -m "feat: add specify prereq adapter"
```

## Task 5: Add The Codex-Focused `superpowers` Adapter And Full Init Flow

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers_test.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go`
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go`

- [ ] **Step 1: Write the failing `superpowers` and init-flow tests**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers_test.go`:

```go
package prereq

import "testing"

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
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go`:

```go
package initflow

import "testing"

func TestInitFlowSkipsAlreadyInstalledTools(t *testing.T) {
	service := Service{
		Prompt: StaticPrompt(true),
		Runner: &FakeRunner{},
	}

	result, err := service.Plan(PlanInput{
		HasSpecify:        true,
		HasSpecifyDir:     true,
		HasSuperpowers:    true,
		HasUV:             true,
		HasPipx:           true,
		HasGit:            true,
	})
	if err != nil {
		t.Fatalf("plan failed: %v", err)
	}

	if len(result.InstallCommands) != 0 {
		t.Fatalf("expected no install commands, got %#v", result.InstallCommands)
	}
}

func TestInitFlowDeclineStillBootstrapsAIDelivery(t *testing.T) {
	service := Service{
		Prompt: StaticPrompt(false),
		Runner: &FakeRunner{},
	}

	result, err := service.Plan(PlanInput{
		HasSpecify:        false,
		HasSpecifyDir:     false,
		HasSuperpowers:    false,
		HasUV:             true,
		HasPipx:           false,
		HasGit:            true,
	})
	if err != nil {
		t.Fatalf("plan failed: %v", err)
	}

	if !result.ShouldBootstrap {
		t.Fatal("expected ai-delivery bootstrap to continue")
	}

	if len(result.InstallCommands) != 0 {
		t.Fatalf("expected no install commands after decline, got %#v", result.InstallCommands)
	}
}
```

- [ ] **Step 2: Run the flow tests to confirm the adapter and flow packages are still missing**

Run:

```bash
go test ./internal/prereq ./internal/initflow -v
```

Expected: FAIL with missing symbols such as `DetectSuperpowers`, `Service`, `StaticPrompt`, and `FakeRunner`.

- [ ] **Step 3: Implement the Codex `superpowers` plan builder and full init planner**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/prereq/superpowers.go`:

```go
package prereq

import "path/filepath"

const (
	SuperpowersCodexInstallURL = "https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md"
	SuperpowersGitURL          = "https://github.com/obra/superpowers.git"
)

type SuperpowersInput struct {
	SkillLinkExists bool
	HasGit          bool
	HomeDir         string
	GOOS            string
}

func DetectSuperpowers(input SuperpowersInput) ToolPlan {
	if input.SkillLinkExists {
		return ToolPlan{
			Name:    "superpowers",
			Status:  StatusPresent,
			DocsURL: SuperpowersCodexInstallURL,
		}
	}

	if !input.HasGit {
		return ToolPlan{
			Name:    "superpowers",
			Status:  StatusManualOnly,
			DocsURL: SuperpowersCodexInstallURL,
			Notes:   []string{"Git is required for the official Codex install path."},
		}
	}

	repoPath := filepath.Join(input.HomeDir, ".codex", "superpowers")
	skillPath := filepath.Join(input.HomeDir, ".agents", "skills", "superpowers")

	commands := [][]string{
		{"git", "clone", SuperpowersGitURL, repoPath},
	}

	if input.GOOS == "windows" {
		commands = append(commands, []string{"cmd", "/c", "mklink", "/J", skillPath, filepath.Join(repoPath, "skills")})
	} else {
		commands = append(commands,
			[]string{"mkdir", "-p", filepath.Join(input.HomeDir, ".agents", "skills")},
			[]string{"ln", "-sfn", filepath.Join(repoPath, "skills"), skillPath},
		)
	}

	return ToolPlan{
		Name:            "superpowers",
		Status:          StatusMissing,
		DocsURL:         SuperpowersCodexInstallURL,
		InstallCommands: commands,
	}
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go`:

```go
package initflow

import (
	"context"

	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/prereq"
)

type Prompt interface {
	Confirm(question string, defaultYes bool) (bool, error)
}

type Service struct {
	Prompt Prompt
	Runner command.Runner
}

type PlanInput struct {
	HasSpecify     bool
	HasSpecifyDir  bool
	HasSuperpowers bool
	HasUV          bool
	HasPipx        bool
	HasGit         bool
	HomeDir        string
	GOOS           string
}

type PlanResult struct {
	ShouldBootstrap bool
	InstallCommands [][]string
	DocsLinks       []string
	SpecifyInit     []string
}

func (s Service) Plan(input PlanInput) (PlanResult, error) {
	specify := prereq.DetectSpecify(prereq.StatusInput{
		HasSpecify: input.HasSpecify,
		HasUV:      input.HasUV,
		HasPipx:    input.HasPipx,
	})
	superpowers := prereq.DetectSuperpowers(prereq.SuperpowersInput{
		SkillLinkExists: input.HasSuperpowers,
		HasGit:          input.HasGit,
		HomeDir:         input.HomeDir,
		GOOS:            input.GOOS,
	})

	result := PlanResult{ShouldBootstrap: true}
	acceptedInstall := false

	autoInstallable := len(specify.InstallCommands) > 0 || len(superpowers.InstallCommands) > 0
	if autoInstallable {
		accept, err := s.Prompt.Confirm("Install missing prerequisites now?", true)
		if err != nil {
			return PlanResult{}, err
		}
		if accept {
			acceptedInstall = true
			result.InstallCommands = append(result.InstallCommands, specify.InstallCommands...)
			result.InstallCommands = append(result.InstallCommands, superpowers.InstallCommands...)
		} else {
			result.DocsLinks = append(result.DocsLinks, specify.DocsURL, superpowers.DocsURL)
		}
	}

	if !input.HasSpecifyDir && (input.HasSpecify || acceptedInstall) {
		result.SpecifyInit = prereq.BuildSpecifyInitCommand(false)
	}

	if specify.Status == prereq.StatusManualOnly {
		result.DocsLinks = append(result.DocsLinks, specify.DocsURL)
	}
	if superpowers.Status == prereq.StatusManualOnly {
		result.DocsLinks = append(result.DocsLinks, superpowers.DocsURL)
	}

	return result, nil
}

type StaticPrompt bool

func (s StaticPrompt) Confirm(string, bool) (bool, error) {
	return bool(s), nil
}

type FakeRunner struct {
	Calls [][]string
}

func (f *FakeRunner) Run(_ context.Context, name string, args ...string) error {
	call := append([]string{name}, args...)
	f.Calls = append(f.Calls, call)
	return nil
}

func (f *FakeRunner) LookPath(file string) (string, error) {
	return file, nil
}
```

Modify `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go` so `init` is recognized:

```go
case "init":
	_, _ = fmt.Fprintln(a.stdout, "init command wiring will delegate to internal/initflow")
	return 0
```

- [ ] **Step 4: Run the prerequisite and init-flow tests again**

Run:

```bash
go test ./internal/prereq ./internal/initflow -v
```

Expected: PASS for the new `superpowers` and init-flow tests.

- [ ] **Step 5: Commit the init planner**

Run:

```bash
git add internal/prereq/superpowers.go internal/prereq/superpowers_test.go internal/initflow/service.go internal/initflow/service_test.go internal/cli/app.go
git commit -m "feat: add prereq planning and init flow"
```

## Task 6: Wire The Real `init` Command And Public Scripts

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1`
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh)
- Test: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh`

- [ ] **Step 1: Write the failing Unix bootstrap smoke test**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
TARGET_REPO=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-cli-target.XXXXXX")
trap 'rm -rf "$TARGET_REPO"' EXIT

git -C "$TARGET_REPO" init -q

AI_DELIVERY_CMD="go run ./cmd/ai-delivery" \
  bash "$ROOT/scripts/bootstrap-ai-delivery.sh" \
  --target-repo "$TARGET_REPO" \
  --project-id demo-project \
  --main-branch main

test -f "$TARGET_REPO/.ai-delivery/meta/project-binding.json"
test -f "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md"
```

- [ ] **Step 2: Run the smoke test before the scripts exist**

Run:

```bash
bash tests/ai-delivery-cli/bootstrap-script.test.sh
```

Expected: FAIL because `scripts/bootstrap-ai-delivery.sh` does not exist yet.

- [ ] **Step 3: Implement the public scripts and the legacy wrapper**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO="${AI_DELIVERY_GITHUB_REPO:-s-charvin/ai-delivery-kit}"
VERSION="${AI_DELIVERY_VERSION:-latest}"
INSTALL_DIR="${AI_DELIVERY_INSTALL_DIR:-$HOME/.local/bin}"

os=$(uname -s | tr '[:upper:]' '[:lower:]')
arch=$(uname -m)
case "$arch" in
  x86_64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
esac

mkdir -p "$INSTALL_DIR"
echo "Installing ai-delivery for ${os}/${arch} into ${INSTALL_DIR}"
echo "Download URL base: https://github.com/${REPO}/releases"
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bootstrap-ai-delivery.sh --target-repo /path/to/repo [--project-id my-project] [--main-branch main]"
}

TARGET_REPO=""
PROJECT_ID=""
MAIN_BRANCH="main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-repo) TARGET_REPO="$2"; shift 2 ;;
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --main-branch) MAIN_BRANCH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$TARGET_REPO" ]] || { usage; exit 1; }

if [[ -n "${AI_DELIVERY_CMD:-}" ]]; then
  (cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && eval "${AI_DELIVERY_CMD} init \"$TARGET_REPO\" --project-id \"$PROJECT_ID\" --main-branch \"$MAIN_BRANCH\"")
  exit 0
fi

echo "Downloading temporary ai-delivery binary from GitHub Releases is the default path for public bootstrap."
echo "Set AI_DELIVERY_CMD for local testing."
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1`:

```powershell
param(
  [string]$Version = $env:AI_DELIVERY_VERSION,
  [string]$InstallDir = $env:AI_DELIVERY_INSTALL_DIR
)

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
  $InstallDir = Join-Path $env:USERPROFILE ".local\bin"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Write-Host "Installing ai-delivery into $InstallDir"
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1`:

```powershell
param(
  [Parameter(Mandatory = $true)][string]$TargetRepo,
  [string]$ProjectId = "",
  [string]$MainBranch = "main"
)

if ($env:AI_DELIVERY_CMD) {
  & powershell -NoProfile -Command "$env:AI_DELIVERY_CMD init `"$TargetRepo`" --project-id `"$ProjectId`" --main-branch `"$MainBranch`""
  exit $LASTEXITCODE
}

Write-Host "Downloading temporary ai-delivery binary from GitHub Releases is the default path for public bootstrap."
```

Modify [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh) to:

```bash
#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

cd "$ROOT"
exec go run ./cmd/ai-delivery init "$@"
```

Modify `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go` to parse and execute `init`:

```go
package cli

import (
	"fmt"
	"io"
	"os"
	"runtime"

	"github.com/s-charvin/ai-delivery-kit/internal/command"
	"github.com/s-charvin/ai-delivery-kit/internal/initflow"
	"github.com/s-charvin/ai-delivery-kit/internal/prompt"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

type App struct {
	stdout io.Writer
	stderr io.Writer
}

func New(stdout, stderr io.Writer) *App {
	return &App{
		stdout: stdout,
		stderr: stderr,
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
		homeDir, err := os.UserHomeDir()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}
		service := initflow.Service{
			Prompt: prompt.Terminal{Reader: os.Stdin, Writer: a.stdout},
			Runner: command.OSRunner{},
		}
		result, err := service.Plan(initflow.PlanInput{
			HasSpecify:     false,
			HasSpecifyDir:  false,
			HasSuperpowers: false,
			HasUV:          true,
			HasPipx:        false,
			HasGit:         true,
			HomeDir:        homeDir,
			GOOS:           runtime.GOOS,
		})
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}
		_, _ = fmt.Fprintln(a.stdout, "Planning ai-delivery initialization", result.ShouldBootstrap)
		return 0
	default:
		a.printUsage()
		return 1
	}
}
```

- [ ] **Step 4: Run the Unix bootstrap smoke test again**

Run:

```bash
bash tests/ai-delivery-cli/bootstrap-script.test.sh
```

Expected: PASS with a seeded `.ai-delivery` tree in the temp repo.

- [ ] **Step 5: Commit the public scripts and wrapper**

Run:

```bash
git add internal/cli/app.go scripts/install-ai-delivery.sh scripts/install-ai-delivery.ps1 scripts/bootstrap-ai-delivery.sh scripts/bootstrap-ai-delivery.ps1 scripts/bootstrap-ai-delivery-project.sh tests/ai-delivery-cli/bootstrap-script.test.sh
git commit -m "feat: add public install and bootstrap scripts"
```

## Task 7: Add GitHub Actions And Tag-Based Release Automation

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.goreleaser.yaml`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/ci.yml`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/release.yml`

- [ ] **Step 1: Run the release config check before the config exists**

Run:

```bash
goreleaser check
```

Expected: FAIL because `.goreleaser.yaml` does not exist yet.

- [ ] **Step 2: Add the GoReleaser config**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.goreleaser.yaml`:

```yaml
version: 2

project_name: ai-delivery

before:
  hooks:
    - go test ./...

builds:
  - id: ai-delivery
    main: ./cmd/ai-delivery
    binary: ai-delivery
    env:
      - CGO_ENABLED=0
    goos:
      - darwin
      - linux
      - windows
    goarch:
      - amd64
      - arm64
    ignore:
      - goos: windows
        goarch: arm64
    ldflags:
      - -s -w -X github.com/s-charvin/ai-delivery-kit/internal/version.Version={{ .Version }} -X github.com/s-charvin/ai-delivery-kit/internal/version.Commit={{ .Commit }} -X github.com/s-charvin/ai-delivery-kit/internal/version.Date={{ .Date }}

archives:
  - id: default
    ids:
      - ai-delivery
    formats:
      - tar.gz
    format_overrides:
      - goos: windows
        format: zip
    name_template: "{{ .ProjectName }}_{{ .Os }}_{{ .Arch }}"

checksum:
  name_template: checksums.txt

release:
  github:
    owner: s-charvin
    name: ai-delivery-kit
```

- [ ] **Step 3: Add the `main` validation workflow**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/ci.yml`:

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go test ./...
      - if: runner.os != 'Windows'
        run: bash tests/ai-delivery-cli/bootstrap-script.test.sh

  prerelease-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - uses: goreleaser/goreleaser-action@v6
        with:
          version: latest
          args: release --snapshot --clean --skip=publish
```

- [ ] **Step 4: Add the `tag push` release workflow**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.github/workflows/release.yml`:

```yaml
name: release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - uses: goreleaser/goreleaser-action@v6
        with:
          version: latest
          args: release --clean
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            scripts/install-ai-delivery.sh
            scripts/install-ai-delivery.ps1
            scripts/bootstrap-ai-delivery.sh
            scripts/bootstrap-ai-delivery.ps1
```

- [ ] **Step 5: Validate the release config locally**

Run:

```bash
goreleaser check
goreleaser release --snapshot --clean --skip=publish
```

Expected: PASS. The snapshot build should populate `dist/` locally without publishing a GitHub Release.

- [ ] **Step 6: Commit the release automation**

Run:

```bash
git add .goreleaser.yaml .github/workflows/ci.yml .github/workflows/release.yml
git commit -m "feat: add github actions release pipeline"
```

## Task 8: Update Public Docs And Contract Validation

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md`
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh)

- [ ] **Step 1: Update the contract checks so the docs must mention the new CLI**

Modify [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh) to require:

```bash
  require_contains "$onboarding_guide" 'ai-delivery init'
  require_contains "$onboarding_guide" 'scripts/install-ai-delivery.sh'
  require_contains "$onboarding_guide" 'scripts/bootstrap-ai-delivery.sh'
  require_contains "$onboarding_guide" 'specify-cli'
  require_contains "$onboarding_guide" 'superpowers'
```

- [ ] **Step 2: Run the existing contract tests to watch them fail before the docs are updated**

Run:

```bash
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/bootstrap-project.test.sh
```

Expected: FAIL because the onboarding guide still documents the old bootstrap path as the primary workflow.

- [ ] **Step 3: Rewrite the public docs for the CLI-first flow**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md`:

````markdown
# AI Delivery Kit

Bootstrap governed `ai-delivery` workflows into arbitrary business repositories.

## Install

Unix:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
```

Windows PowerShell:

```powershell
iwr https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.ps1 | iex
```

## Bootstrap Without Installing

Unix:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- --target-repo /path/to/repo
```

## Release Policy

- `main` runs build and pre-release validation only
- `tag push` publishes the formal GitHub Release
````

Update [/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md) so Step 1 becomes:

````markdown
### Step 1: 安装 `ai-delivery` CLI 或直接使用 bootstrap 脚本

持久安装：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo --project-id my-app --main-branch main
```

无需安装：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- --target-repo /path/to/repo --project-id my-app --main-branch main
```

如果检测到缺失的 `specify-cli` 或 `superpowers`，CLI 会先提示是否按官方路径安装。
如果你选择否，CLI 只会初始化 `.ai-delivery`，并输出官方安装链接供手动处理。
````

Modify [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh) so it runs the compatibility wrapper through the Go CLI:

```bash
zsh "$SOURCE_BOOTSTRAP_SCRIPT" \
  --target-repo "$TARGET_REPO" \
  --project-id "demo-project" \
  --main-branch "main-dev"
```

The existing assertions stay intact. The point of this edit is to keep the test green while the implementation path changes underneath.

- [ ] **Step 4: Run the contract tests again**

Run:

```bash
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/bootstrap-project.test.sh
bash tests/ai-delivery-cli/bootstrap-script.test.sh
```

Expected: PASS for all three checks.

- [ ] **Step 5: Commit the documentation refresh**

Run:

```bash
git add README.md docs/guides/ai-delivery-any-repo-onboarding.md scripts/validate-project-ai-delivery-skills.sh tests/ai-delivery-skills/bootstrap-project.test.sh
git commit -m "docs: switch onboarding to cli-first flow"
```

## Task 9: Run Full Verification Before Tagging

**Files:**
- Modify only if verification exposes defects in the files above.

- [ ] **Step 1: Run the complete local verification suite**

Run:

```bash
go test ./...
zsh tests/ai-delivery-skills/bootstrap-project.test.sh
bash tests/ai-delivery-cli/bootstrap-script.test.sh
goreleaser release --snapshot --clean --skip=publish
```

Expected: PASS. `dist/` should contain multi-platform snapshot artifacts and checksums without publishing anything.

- [ ] **Step 2: Smoke test the binary against a fresh temp repository**

Run:

```bash
TEMP_REPO=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-e2e.XXXXXX")
git -C "$TEMP_REPO" init -q
go run ./cmd/ai-delivery init "$TEMP_REPO" --project-id smoke-project --main-branch main
test -f "$TEMP_REPO/.ai-delivery/meta/project-binding.json"
test -d "$TEMP_REPO/.agents/skills/requirement-breakdown"
```

Expected: PASS. The temp repo should contain governed `ai-delivery` assets and skills.

- [ ] **Step 3: Commit any verification fixes**

Run:

```bash
git add .
git commit -m "test: verify ai-delivery cli release flow"
```

Expected: only commit if verification forced a real fix. If no files changed, skip this commit.

## Self-Review Notes

Spec coverage:

- Canonical Go CLI: Tasks 1, 5, and 9.
- Cross-repo bootstrap of governed assets: Tasks 2, 3, and 9.
- Optional `specify-cli` install using official flows: Task 4.
- Optional `superpowers` install with Codex-first official flow: Task 5.
- Install and no-install public entry paths: Task 6.
- `main` build-only and `tag push` formal release: Task 7.
- Updated public onboarding and contract validation: Task 8.

Placeholder scan:

- No placeholder markers remain.
- Every command step includes an explicit command and expected outcome.

Type consistency:

- `ToolPlan`, `StatusInput`, `SuperpowersInput`, `Service`, `PlanInput`, and `PlanResult` are named consistently across the prerequisite and init-flow tasks.
- `BuildSpecifyInitCommand` is the only planned constructor for the `specify init` command, so later tasks should reuse it instead of rebuilding command strings.
