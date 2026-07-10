# AI Delivery Kit

Bootstrap governed `ai-delivery` workflows into arbitrary business repositories, then advance new work through `ai-delivery-orchestrator` instead of manual stage-by-stage dispatch.

## Quick Start

Install the CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo
```

Or bootstrap without installing:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- /path/to/repo
```

The bootstrap script downloads a temporary release binary and runs the same canonical `ai-delivery init` logic.

## Upgrade

Upgrade the installed CLI by rerunning the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
```

If a repository was initialized by an older `ai-delivery init`, first upgrade the CLI, then refresh the managed project assets:

```bash
ai-delivery init --upgrade /path/to/repo
```

Or do both in one step:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash -s -- --upgrade-init /path/to/repo
```

`init --upgrade` refreshes the managed `ai-delivery` assets in the target repository while preserving requirement and runtime data.

## What `ai-delivery init` Does

`ai-delivery init` is the repository onboarding command only. It:

- discovers the git root
- derives `project_id` from the repository name
- detects the main branch and writes `.ai-delivery/runtime/main-branch.json`
- checks for `specify-cli` and `superpowers`
- prompts before installing missing prerequisites through their official paths
- runs `specify init` only when `specify-cli` is already available or was installed during onboarding
- seeds the governed `.ai-delivery` contract, project-local skills, validators, and support files

The normal public path no longer asks the user to provide `project_id` or `main-branch`.

## Default Requirement Entry

After onboarding, start new work through `ai-delivery-orchestrator`.

Typical user input should stay natural-language and source-driven, for example:

- “这是需求文档，这是 Figma，这是接口，开始推进”
- “继续这个需求”
- “这个 blocker 我处理好了，继续”

The orchestrator is responsible for deciding whether to continue an existing requirement or create a new one. It gives one recommendation, pauses for human confirmation, then drives the governed workflow chain.

## Human Review Points

Humans stay in the loop only where judgment matters:

- confirm the orchestrator recommendation to continue an existing requirement or create a new one
- confirm explicit checkpoints such as `tasks_ready_user_confirmation`
- resolve blockers when governed truth is missing or conflicting

Everything else should default to AI-driven progression through the orchestrated chain.

## Exception Path

Lower-level skills such as `requirement-breakdown` and `ui-truth-mapping` can still be used directly when their prerequisites are already satisfied. `ai-delivery-orchestrator` remains the default entry for new requirements.

That path is for surgical recovery or expert use. It is not the normal entry for new requirements.

## Prerequisites

During `ai-delivery init`, the CLI checks for `specify-cli` and `superpowers`.

- If they are already present, the CLI skips reinstallation.
- If they are missing, the CLI prompts before using the official installation path.
- If you decline installation, the CLI still initializes the governed `ai-delivery` assets and prints the official install links for manual follow-up.

## Release Policy

- `main` validates build and pre-release checks only.
- `tag push` publishes the formal GitHub Release.

## Release Rehearsal

Run the local release rehearsal before creating a release tag:

```bash
bash scripts/rehearse-release.sh
```

By default, the script runs the Go test suite, validators, bootstrap/install smoke tests, and `git diff --check`.
If `goreleaser` or `pwsh` are available locally, it includes those checks too.
