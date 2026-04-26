# AI Delivery Kit CLI Onboarding Design

Date: 2026-04-26
Status: ready-for-user-review

## Goal

Turn `ai-delivery-kit` into a reusable onboarding product for arbitrary business repositories.

The user-facing outcome is a canonical `ai-delivery` CLI that can:

- initialize a target repository in one command
- optionally install missing prerequisites before initialization
- avoid reinstalling tools that are already present
- work on macOS, Linux, and Windows
- stay as close as possible to native binary distribution
- publish from GitHub without extra package registries or store review flows

The source repository remains `s-charvin/ai-delivery-kit`. That repository is the canonical source for the CLI, the bootstrap scripts, and the release workflow.

## Scope

This design covers:

- the public CLI surface
- repository bootstrap behavior
- prerequisite detection and optional installation
- release packaging and GitHub Actions publishing
- one-shot bootstrap scripts for users who do not want to install the CLI first

This design does not cover:

- rewriting `ai-delivery-admin`
- changing upstream `specify-cli` or `superpowers`
- adding a GUI
- adding a package-manager distribution channel such as Homebrew, npm, or a platform store
- implementing code signing or notarization in the first release

## Recommended Direction

Use a Go-based native binary named `ai-delivery` as the canonical entry point.

Why this is the right fit:

- it satisfies the preference for a native binary
- it supports macOS, Linux, and Windows with a single implementation language
- it keeps installation friction low
- it keeps the distribution path inside GitHub Releases
- it avoids depending on an external package registry or approval process

The product should expose two entry paths:

- `install.sh` and `install.ps1` for users who want a persistent CLI
- `bootstrap.sh` and `bootstrap.ps1` for users who want a one-off init without installing first

## User Experience

### Persistent CLI path

1. The user installs `ai-delivery` from GitHub Releases using the platform-appropriate install script.
2. The install script downloads the correct binary for the host platform.
3. The install script verifies the checksum before writing to `PATH`.
4. The user runs `ai-delivery init` in any target repository.
5. The CLI checks prerequisites before making changes.
6. If prerequisites are missing, the CLI asks whether to install them now.
7. If the user accepts, the CLI installs the missing tools using their official install paths when supported.
8. If the user declines, the CLI only initializes `ai-delivery` and prints official install links for the missing tools.

### No-install bootstrap path

1. The user runs `bootstrap.sh` or `bootstrap.ps1` from GitHub.
2. The script downloads a temporary `ai-delivery` binary from GitHub Releases.
3. The script executes `ai-delivery init` against the target repository.
4. The temporary binary is not installed globally.

This path exists for users who want the shortest possible onboarding path while still using the same canonical CLI logic.

## CLI Surface

The public interface should stay small.

- `ai-delivery init [repo-path]`
  - initialize the target repository
  - perform prerequisite checks
  - prompt before installing missing dependencies
  - write only the governed `ai-delivery` and related onboarding assets
- `ai-delivery version`
  - print the binary version
  - used by install scripts and smoke tests

The init command should support two execution modes:

- interactive mode for a human-driven onboarding session
- non-interactive mode for install scripts, CI validation, and future automation

## Dependency Handling

The init flow must treat prerequisites as a separate concern from repository initialization.

### `repo-discovery`

Responsibilities:

- find the git root for the target repository
- determine whether the repository is already initialized
- detect managed files that would conflict with bootstrap output

Dependencies:

- local git metadata
- existing `.ai-delivery`, `.agents`, and `.specify` paths

### `prereq-check`

Responsibilities:

- detect whether `specify-cli` is already installed
- detect whether `superpowers` is already available in the current coding-agent environment
- classify each prerequisite as `present`, `missing`, or `manual-only`

Dependencies:

- the host shell and executable PATH
- agent-specific installation markers or official install hooks for `superpowers`

### `specify-adapter`

Responsibilities:

- use the official install method for `specify-cli` when the user accepts installation
- support the official install choices that matter to this repo, especially `uv` and `pipx`
- expose the official docs link when installation is declined or unsupported

Important behavior:

- if `specify-cli` is already present, never reinstall it
- if the user declines installation, do not run a hidden fallback install
- if the CLI cannot determine a supported install route, report the official install page and stop that part of the flow cleanly

### `superpowers-adapter`

Responsibilities:

- detect whether the current environment already has `superpowers`
- use the official install path for the detected coding-agent environment when supported
- fall back to official documentation and installation links when the environment does not expose a supported command-line install path

Important behavior:

- do not overwrite an existing installation
- do not guess at private config formats
- do not claim success when the environment only supports a manual marketplace or UI-based install path

### `bootstrap-engine`

Responsibilities:

- write the governed `ai-delivery` assets into the target repository
- remain idempotent when rerun after a partial failure
- stop before writing if a managed file conflict exists

Dependencies:

- `repo-discovery`
- `prereq-check`
- the current repository asset layout

### `reporting`

Responsibilities:

- explain what was installed, skipped, or deferred
- show the next action clearly
- print official links for anything the user declined to install
- summarize conflicts or partial failures in plain language

## Release And Distribution

GitHub is the only release channel in this design.

### Release artifacts

Each release should publish:

- native binaries for macOS, Linux, and Windows
- `install.sh`
- `install.ps1`
- `bootstrap.sh`
- `bootstrap.ps1`
- checksum manifests for all binaries

### Platform matrix

The first supported binary matrix should cover the common Go targets used by developers:

- macOS arm64
- macOS amd64
- Linux arm64
- Linux amd64
- Windows amd64

Additional targets can be added later if the release workflow remains simple and reliable.

### Trigger policy

Publishing must be automated through GitHub Actions.

- `push` to `main`
  - build and test only
  - produce pre-release validation artifacts
  - do not publish a formal GitHub Release
- `tag push`
  - publish the formal release
  - use the tag as the version source of truth
  - upload the binary matrix and checksum manifests

This keeps `main` as the integration branch and makes `tag push` the only path to a user-facing release.

### Install script behavior

`install.sh` and `install.ps1` should:

- detect the host platform and architecture
- download the matching release asset
- verify the checksum before installation
- install to a predictable user-writable location or a user-specified prefix
- fail cleanly if the downloaded asset does not match the published checksum

### Bootstrap script behavior

`bootstrap.sh` and `bootstrap.ps1` should:

- download a temporary binary from the latest stable release or an explicitly provided version
- run `ai-delivery init` against the target repository
- avoid persisting the binary globally

## Error Handling

The design should prefer no-op over partial mutation.

- If the target path is not inside a git repository, stop before writing anything.
- If a managed asset already exists, stop and report the exact path.
- If a release checksum does not match, stop and refuse to install the binary.
- If a prerequisite installation fails, keep the repository state unchanged and report the official install path.
- If the user declines prerequisite installation, continue with `ai-delivery` initialization only.
- If initialization is rerun after a partial attempt, the CLI should detect what is already present and avoid duplicating work.

## Testing

Testing should prove that the onboarding path works end to end, not just that the binary compiles.

### Build and release validation

- compile the binary for the supported platform matrix
- verify version stamping from tag names
- verify checksum generation and checksum verification
- verify that `main` builds do not publish releases
- verify that `tag push` publishes the release artifacts

### Bootstrap validation

- `install.sh` installs the correct binary for the host platform
- `install.ps1` installs the correct binary for Windows
- `bootstrap.sh` and `bootstrap.ps1` run without requiring a persistent install
- repeated bootstrap runs do not corrupt the target repository

### Init flow validation

- already-installed `specify-cli` is detected and skipped
- already-installed `superpowers` is detected and skipped
- missing prerequisites trigger the yes/no prompt
- declining installation continues with `ai-delivery` initialization only
- missing prerequisites are reported with official install links
- managed-file conflicts fail loudly

## Acceptance Criteria

This design is complete when:

- a user can install `ai-delivery` from GitHub Releases on macOS, Linux, or Windows
- a user can bootstrap a business repository with one command after installing the CLI
- a user can bootstrap a repository without installing the CLI first
- `specify-cli` and `superpowers` are checked before initialization
- missing prerequisites are installed only when the user agrees
- declining prerequisite installation still allows `ai-delivery` initialization
- `main` only builds and validates
- `tag push` is the only formal release trigger
- all published binaries are checksum-verified by the install scripts
