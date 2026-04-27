# AI Delivery Orchestrator-First Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `ai-delivery-kit` so `ai-delivery init` only onboards repositories, `ai-delivery-orchestrator` becomes the default requirement entry, repo identity is auto-derived, and `README.md` is the only public onboarding document.

**Architecture:** Keep the runtime split into two layers. The Go CLI remains the repository bootstrapper and now auto-derives `project_id` and `main-branch`; the orchestrator skill becomes the default requirement dispatcher that decides whether to continue an existing requirement or create a new one, then pauses for human confirmation. The managed asset contract shrinks by removing the onboarding guide from seeded assets, while README, validators, and shell tests converge on the orchestrator-first public story.

**Tech Stack:** Go 1.22, Go stdlib, Bash, PowerShell, embedded governed assets, existing shell contract tests, GitHub Actions, GoReleaser.

---

## File Structure

- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go)
  - Remove public `--project-id` and `--main-branch` parsing from `ai-delivery init`.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go)
  - Re-pin init parsing tests around the reduced public contract.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch.go`
  - Detect the repository’s main branch from `origin/HEAD`, current branch, or a `main` fallback.
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch_test.go`
  - Unit tests for branch-detection precedence and fallback behavior.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go)
  - Derive `project_id` and `main-branch` internally before calling the bootstrap engine.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go)
  - Verify auto-derived identities and unchanged prereq/bootstrap behavior.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go)
  - Remove the onboarding guide from the embedded managed-source contract.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go)
  - Stop asserting the guide as an embedded required asset.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go)
  - Stop copying the onboarding guide into target repositories.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go)
  - Remove `.ai-delivery/docs/guides` from the seeded directory contract if nothing else uses it.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go)
  - Assert the slimmer managed asset set.
- Delete: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md)
  - Remove the duplicated public onboarding guide.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md)
  - Become the only public onboarding and workflow document.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh)
  - Remove `--project-id` and `--main-branch` from the normal path and help text.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1)
  - Mirror the reduced bootstrap contract on Windows.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh)
  - Print the reduced init example in post-install output.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1)
  - Mirror the reduced install example on Windows.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh)
  - Keep the source-repo helper, but slim it to a positional target-path wrapper.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh)
  - Assert the public bootstrap script forwards only `init <target>`.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/install-script.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/install-script.test.sh)
  - Keep release-asset installation green after help/output changes.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh)
  - Assert the internal wrapper and seeded asset set match the new contract.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh)
  - Validate README-only onboarding, missing guide assets, and orchestrator-first wording.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/validate-sources.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/validate-sources.test.sh)
  - Keep the source and bootstrapped validation surfaces aligned.
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md)
  - Teach automatic requirement routing, single-recommendation human confirmation, and “lower-level skills are exception paths.”

## External Truth And Constraints

- Preserve `.ai-delivery` as the only workflow truth store.
- Do not expose `requirement_id`, `subreq_id`, `project_id`, or `main-branch` in the normal public path.
- Keep lower-level skill direct use supported only when their prerequisites are already satisfied.
- Do not keep the onboarding guide in managed assets just to preserve compatibility.

## Task 1: Shrink `ai-delivery init` And Auto-Derive Repo Identity

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch.go`
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch_test.go`
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go)

- [ ] **Step 1: Write the failing tests for the reduced CLI contract and branch detection**

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go` to replace the flag-driven init test with:

```go
func TestRunInitCommandParsesOnlyTargetPath(t *testing.T) {
	var out bytes.Buffer
	fake := &fakeInitRunner{}
	app := New(&out, &out)
	app.initRunner = fake

	exitCode := app.Run([]string{"init", "/tmp/demo-repo"})
	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}

	if fake.input.TargetPath != "/tmp/demo-repo" {
		t.Fatalf("expected target path to be parsed, got %#v", fake.input)
	}
}
```

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch_test.go`:

```go
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
```

Add a service test in `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go`:

```go
func TestRunDerivesProjectAndMainBranchWhenInputDoesNotProvideThem(t *testing.T) {
	bootstrapper := &fakeBootstrapper{}
	runner := &fakeRunner{paths: map[string]string{
		"git": "git",
	}}
	service := Service{
		Prompt:       staticPrompt(true),
		Runner:       runner,
		Bootstrapper: bootstrapper,
		Discover: func(string) (repo.Info, error) {
			return repo.Info{Root: "/tmp/demo-repo", HasSpecify: true}, nil
		},
		DetectMainBranch: func(context.Context, string) (string, error) {
			return "release/main", nil
		},
		HomeDir: "/tmp/home",
		GOOS:    "linux",
		StatPath: func(path string) error {
			if path == "/tmp/home/.agents/skills/superpowers" {
				return nil
			}
			return errors.New("missing")
		},
	}

	_, err := service.Run(context.Background(), Input{
		TargetPath:  "/tmp/demo-repo",
		Interactive: true,
	})
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	if bootstrapper.config.ProjectID != "demo-repo" {
		t.Fatalf("expected derived project id, got %#v", bootstrapper.config)
	}
	if bootstrapper.config.MainBranch != "release/main" {
		t.Fatalf("expected derived branch, got %#v", bootstrapper.config)
	}
}
```

- [ ] **Step 2: Run the focused tests and confirm they fail for the current API**

Run:

```bash
go test ./internal/cli ./internal/repo ./internal/initflow -run 'TestRunInitCommandParsesOnlyTargetPath|TestChooseDefaultBranch|TestRunDerivesProjectAndMainBranchWhenInputDoesNotProvideThem' -v
```

Expected: FAIL because `app.go` still parses removed flags, `Input` still expects manual identity fields, and the new branch helper does not exist yet.

- [ ] **Step 3: Implement automatic identity derivation and the slimmed init command**

Create `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch.go`:

```go
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
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go` so `runInit` becomes:

```go
func (a *App) runInit(args []string) int {
	if len(args) != 1 {
		_, _ = fmt.Fprintln(a.stderr, "init requires exactly one target repository path")
		a.printUsage()
		return 1
	}

	runner := a.initRunner
	if runner == nil {
		homeDir, err := a.homeDir()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 1
		}

		runner = initflow.Service{
			Prompt:          prompt.Terminal{Reader: a.stdin, Writer: a.stdout},
			Runner:          command.OSRunner{},
			Bootstrapper:    bootstrap.Engine{},
			Discover:        repo.Discover,
			DetectMainBranch: repo.DetectDefaultBranch,
			HomeDir:         homeDir,
			GOOS:            a.goos,
		}
	}

	result, err := runner.Run(context.Background(), initflow.Input{
		TargetPath:  args[0],
		Interactive: true,
	})
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go` so the input and service surface become:

```go
type Input struct {
	TargetPath  string
	Interactive bool
}

type Service struct {
	Prompt           Prompt
	Runner           command.Runner
	Bootstrapper     Bootstrapper
	Discover         func(string) (repo.Info, error)
	DetectMainBranch func(context.Context, string) (string, error)
	HomeDir          string
	GOOS             string
```

Then derive identity before bootstrap:

```go
	projectID := slugify(filepath.Base(info.Root))
	mainBranch := "main"
	if s.DetectMainBranch != nil {
		if branch, err := s.DetectMainBranch(ctx, info.Root); err == nil && strings.TrimSpace(branch) != "" {
			mainBranch = branch
		}
	}
```

- [ ] **Step 4: Re-run the focused tests and then the full Go suite**

Run:

```bash
go test ./internal/cli ./internal/repo ./internal/initflow -v
go test ./...
```

Expected: PASS. `bootstrap.Config` now receives a derived repo slug and detected branch even when the user provides only the repo path.

- [ ] **Step 5: Commit the identity refactor**

```bash
git add /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/cli/app_test.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/repo/default_branch_test.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/initflow/service_test.go
git commit -m "refactor: auto-derive init repository identity"
```

## Task 2: Remove The Onboarding Guide From Managed Assets

**Files:**
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go](/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go)
- Delete: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh)

- [ ] **Step 1: Write the failing asset-contract tests**

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go` by removing the guide requirement and pinning the remaining assets:

```go
required := []string{
	".agents/skills/ai-delivery/requirement-breakdown/SKILL.md",
	".agents/skills/ai-delivery/api-contract-mapping/templates/api-contract-mapping-template.md",
	".agents/skills/ai-delivery/ui-requirement-mapping/templates/figma-mapping-template.md",
	".agents/skills/ai-delivery/ui-acceptance-contract/templates/ui-acceptance-contract-template.yaml",
	".agents/skills/ai-delivery/ui-interaction-design/templates/interaction-design-template.md",
	".agents/skills/ai-delivery/ai-delivery-orchestrator/references/reconcile-rules.md",
	"scripts/validate-project-ai-delivery-skills.sh",
	"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
	"tests/ai-delivery-skills/validate-sources.test.sh",
}
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go` so the required target paths no longer include the guide and do include a negative assertion:

```go
if _, err := os.Stat(filepath.Join(target, ".ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md")); !os.IsNotExist(err) {
	t.Fatalf("expected onboarding guide to be absent, got %v", err)
}
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh` to replace:

```bash
[[ -f "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
```

with:

```bash
[[ ! -e "$TARGET_REPO/.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md" ]]
```

- [ ] **Step 2: Run the focused contract tests and confirm they fail**

Run:

```bash
go test ./internal/bootstrap ./... -run 'TestEmbeddedAssetsContainGovernedSources|TestRunWritesGovernedAssetsAndSeedFiles' -v
bash tests/ai-delivery-skills/bootstrap-project.test.sh
```

Expected: FAIL because the manifest and bootstrap engine still embed and copy the guide.

- [ ] **Step 3: Remove the guide from the contract and delete the source file**

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go`:

```go
func ManagedSourcePaths() []string {
	return []string{
		".agents/skills/ai-delivery/requirement-breakdown",
		".agents/skills/ai-delivery/api-contract-mapping",
		".agents/skills/ai-delivery/ui-requirement-mapping",
		".agents/skills/ai-delivery/ui-acceptance-contract",
		".agents/skills/ai-delivery/ui-interaction-design",
		".agents/skills/ai-delivery/ai-delivery-orchestrator",
		"scripts/validate-project-ai-delivery-skills.sh",
		"tests/ai-delivery-skills/api-nonblocking-policy.test.sh",
		"tests/ai-delivery-skills/validate-sources.test.sh",
	}
}
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go` to remove:

```go
{Source: "docs/guides/ai-delivery-any-repo-onboarding.md", Target: ".ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md", Kind: "file"},
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go` so `managedDirectories()` no longer creates `.ai-delivery/docs/guides`.

Delete `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md`.

- [ ] **Step 4: Re-run the asset and bootstrap tests**

Run:

```bash
go test ./internal/bootstrap ./... -run 'TestEmbeddedAssetsContainGovernedSources|TestRunWritesGovernedAssetsAndSeedFiles|TestRunFailsOnManagedConflictWithoutMutatingRepo|TestRunFailsOnSeededManagedFileConflictWithoutMutatingRepo' -v
bash tests/ai-delivery-skills/bootstrap-project.test.sh
```

Expected: PASS. The target repo still receives governed skills, validators, tests, runtime JSON, and `.specify`, but no longer receives the duplicated onboarding guide.

- [ ] **Step 5: Commit the asset-contract cleanup**

```bash
git add /Users/charvin/Projects/spec-dev/ai-delivery-kit/managed_manifest.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/managedassets_test.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/manifest.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/internal/bootstrap/engine_test.go \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/bootstrap-project.test.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/guides/ai-delivery-any-repo-onboarding.md
git commit -m "refactor: remove onboarding guide from managed assets"
```

## Task 3: Rewrite Public Scripts And README Around `init <repo>`

**Files:**
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/install-script.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/install-script.test.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md)

- [ ] **Step 1: Write the failing script-contract test updates**

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh` so the local and downloaded command assertions become:

```bash
assert_file_contains "$LOCAL_LOG" 'init'
assert_file_contains "$LOCAL_LOG" "$TARGET_REPO"
if grep -Fq -- '--project-id' "$LOCAL_LOG"; then
  fail "did not expect manual project id flags in bootstrap invocation"
fi
if grep -Fq -- '--main-branch' "$LOCAL_LOG"; then
  fail "did not expect manual main branch flags in bootstrap invocation"
fi
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh` usage target in the source smoke test to the new positional form:

```bash
PATH="$TEMP_BIN:$PATH" zsh "$SOURCE_BOOTSTRAP_SCRIPT" "$TARGET_REPO"
```

- [ ] **Step 2: Run the public and source bootstrap tests and confirm they fail**

Run:

```bash
bash tests/ai-delivery-cli/bootstrap-script.test.sh
bash tests/ai-delivery-skills/bootstrap-project.test.sh
```

Expected: FAIL because the bootstrap scripts and source wrapper still forward `--project-id` and `--main-branch`.

- [ ] **Step 3: Implement the reduced-parameter scripts and consolidate README**

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh` so the usage and invocation become:

```bash
usage() {
  cat <<'EOF'
Usage: bootstrap-ai-delivery.sh /path/to/repo

Environment overrides:
  AI_DELIVERY_CMD               Local ai-delivery executable for tests and development
  AI_DELIVERY_REPO              GitHub owner/repo. Default: s-charvin/ai-delivery-kit
  AI_DELIVERY_VERSION           Release tag or latest. Default: latest
  AI_DELIVERY_DOWNLOAD_BASE_URL Override release asset base URL for testing or mirrors
EOF
}

run_ai_delivery() {
  local ai_delivery_cmd=$1
  local target_repo=$2

  "$ai_delivery_cmd" init "$target_repo"
}
```

Update `/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh` to a positional wrapper:

```bash
usage() {
  cat <<'EOF'
Usage: bootstrap-ai-delivery-project.sh /path/to/repo

Delegates to `go run ./cmd/ai-delivery init <target>`.
EOF
}

target_repo=${1:-}
[[ -n "$target_repo" ]] || { usage; exit 1; }
exec go run ./cmd/ai-delivery init "$target_repo"
```

Update the post-install output in both install scripts to print:

```text
Run: ai-delivery init /path/to/repo
```

Rewrite `/Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md` around this structure:

```md
# AI Delivery Kit

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo
```

## Default Requirement Entry

After onboarding, start new work through `ai-delivery-orchestrator`.
Give the AI natural-language inputs such as requirement docs, Figma links, and API contracts.
The orchestrator decides whether to continue an existing requirement or create a new one, then pauses for human confirmation.

## Exception Path

Lower-level skills may still be used directly when their preconditions are already satisfied.
```

- [ ] **Step 4: Re-run bootstrap/install tests and a Markdown sanity check**

Run:

```bash
bash tests/ai-delivery-cli/bootstrap-script.test.sh
bash tests/ai-delivery-cli/install-script.test.sh
grep -n "ai-delivery init /path/to/repo" /Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md
```

Expected: PASS. The scripts no longer expose manual repo identity flags in their normal path, and README now tells one coherent story.

- [ ] **Step 5: Commit the public-contract rewrite**

```bash
git add /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery.ps1 \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/install-ai-delivery.ps1 \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/bootstrap-ai-delivery-project.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/bootstrap-script.test.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-cli/install-script.test.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/README.md
git commit -m "docs: make orchestrator the default public entry"
```

## Task 4: Rewrite The Orchestrator Skill And Validation Rules

**Files:**
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh)
- Modify: [/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/validate-sources.test.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/validate-sources.test.sh)

- [ ] **Step 1: Tighten validator expectations before changing the skill**

Update `validate_managed_contract()` in [/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh](/Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh) to remove the onboarding guide checks and add README assertions:

```bash
require_contains "$readme_file" 'ai-delivery init /path/to/repo'
require_contains "$readme_file" 'ai-delivery-orchestrator'
require_contains "$readme_file" 'continue an existing requirement or create a new one'
require_not_contains "$readme_file" '--project-id'
require_not_contains "$readme_file" '--main-branch'
```

Update `validate_orchestrator_skill()` to require the routing behavior:

```bash
require_contains "$skill_file" 'continue an existing requirement or create a new one'
require_contains "$skill_file" 'human confirmation'
require_contains "$skill_file" 'direct use of lower-level skills remains supported'
```

- [ ] **Step 2: Run the skill validator tests and confirm they fail**

Run:

```bash
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/validate-sources.test.sh
```

Expected: FAIL because README and the orchestrator skill still describe the old public contract.

- [ ] **Step 3: Update the orchestrator skill to own routing and default entry behavior**

Revise [/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md](/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md) so the entry mapping section includes:

```md
When a user brings new material, first decide whether to continue an existing requirement or create a new one.

1. Inspect existing `.ai-delivery/requirements/*` packages, `todo.md`, `status.json`, and `traceability.json`.
2. Produce one recommendation only:
   - `continue req-xxx`
   - or `create req-yyy`
3. Pause for human confirmation before taking either path.
4. Treat direct invocation of lower-level skills as an exception path only when their preconditions are already satisfied.
```

Also update the “User Entry Mapping” and “Hard Boundary” sections so they no longer imply that the human should manually choose the first low-level skill in the normal path.

- [ ] **Step 4: Re-run the validation surface**

Run:

```bash
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/validate-sources.test.sh
go test ./...
```

Expected: PASS. The skill text, README, and managed-asset validator now agree on the orchestrator-first public contract.

- [ ] **Step 5: Commit the orchestrator-first contract updates**

```bash
git add /Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/scripts/validate-project-ai-delivery-skills.sh \
  /Users/charvin/Projects/spec-dev/ai-delivery-kit/tests/ai-delivery-skills/validate-sources.test.sh
git commit -m "refactor: make orchestrator the default requirement entry"
```

## Task 5: Full Regression And Release Rehearsal

**Files:**
- Verify only; no planned source changes in this task unless a failing regression exposes a concrete defect.

- [ ] **Step 1: Run the full automated suite**

Run:

```bash
go test ./...
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/bootstrap-project.test.sh
bash tests/ai-delivery-cli/bootstrap-script.test.sh
bash tests/ai-delivery-cli/install-script.test.sh
```

Expected: PASS. This confirms Go behavior, managed-skill validation, internal bootstrap, and public script smoke coverage all agree with the new entry model.

- [ ] **Step 2: Run the release rehearsal with local skips only where tools are absent**

Run:

```bash
AI_DELIVERY_RUN_GORELEASER=never AI_DELIVERY_RUN_PWSH=never bash scripts/rehearse-release.sh
```

Expected: PASS. If the local machine has `goreleaser` or `pwsh`, remove the corresponding `never` override and let the full rehearsal run.

- [ ] **Step 3: Check for formatting and tree cleanliness**

Run:

```bash
git diff --check
git status --short
```

Expected: `git diff --check` prints nothing. `git status --short` shows a clean tree if no regression fix was needed from Task 5.

- [ ] **Step 4: If verification exposed a real defect, patch it immediately and commit once**

Use the smallest necessary follow-up change. If a fix is required, commit it with a focused message such as:

```bash
git add <changed-files>
git commit -m "fix: address orchestrator-first regression"
```

- [ ] **Step 5: Record the final handoff note in the implementation session**

Summarize:

```text
- init now derives repo identity automatically
- onboarding guide removed from managed assets
- README is the only public onboarding doc
- ai-delivery-orchestrator is the default requirement entry
- lower-level skills remain exception paths when preconditions are already satisfied
```
