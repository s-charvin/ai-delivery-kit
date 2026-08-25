# AI Delivery Kit

Bootstrap governed `ai-delivery` workflows into arbitrary business repositories, then advance new work through `ai-delivery-orchestrator` instead of manual stage-by-stage dispatch.

中文版：[README.zh-CN.md](README.zh-CN.md)

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

**Developing this repo:**

```bash
git clone https://github.com/s-charvin/ai-delivery-kit.git
```

For multi-party orchestration (optional), install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately and run `coordination-cli init` in your repo. This kit does not embed coordination logic.

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

`init --upgrade` refreshes managed `.ai-delivery` script/test copies in the target repository while preserving requirement data. For this kit repo itself:

```bash
ai-delivery init --upgrade .
```

`.ai-delivery/backups/` holds ephemeral IDE-gate amend snapshots (gitignored); safe to delete anytime.

## What `ai-delivery init` Does

`ai-delivery init` is the repository onboarding command only. It:

- discovers the git root
- derives `project_id` from the repository name
- seeds the governed `.ai-delivery` contract, project-local skills, validators, and support files

It never installs third-party frameworks. The workflow is framework-agnostic: it adapts at runtime to whatever AI development frameworks are already present, and falls back to built-in native artifacts when none are installed.

The normal public path no longer asks the user to provide `project_id`.

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

Lower-level skills such as `requirement-breakdown` and `ui-truth-mapping` can still be used directly when their prerequisites are already satisfied. For `ui-truth-mapping`, that includes a governed Stage 2 slice and recorded CP-UI authorization. `ai-delivery-orchestrator` remains the default entry for new requirements.

That path is for surgical recovery or expert use. It is not the normal entry for new requirements.

## Framework Adaptation

The orchestrator emits abstract stage actions (`design` / `spec` / `plan` / `tasks` / `implement` / `finish`) and adapts them to the frameworks already installed in your environment. Nothing is installed or required.

Recommended frameworks (detected, never installed):

| Framework | Primary actions | Detection marker |
|-----------|-----------------|------------------|
| spec-kit | `spec` / `plan` / `tasks` | `.specify/` or `specify` CLI |
| OpenSpec | `spec` / `plan` / `tasks` | `openspec/` or `openspec` CLI |
| superpowers | `design` / `implement` / `finish` | superpowers skills in user skill dirs |
| ECC | `design` / `implement` / `finish` | `/ecc:*` commands registered |

No framework installed? The pipeline still runs end-to-end using built-in native artifacts (lightweight `spec.md` / `tasks.md` inside each sub-requirement plus inline discipline guidance).

Per-framework usage guidance ships with the orchestrator skill: `references/framework-adaptation.md` and `references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`.

## Visual freeze (no HTML contract hooks)

After CP-UI authorization, Stage 2 implements and freezes **real host-stack components** plus official previews for visual scenarios in the slice worktree (Flutter: widget + golden PNG), with TDD and fresh-context review. Before component code, each unit must resolve an applicability-gated Runtime Coverage Plan for state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. `ai-delivery init` does **not** install UI git hooks.

Give the user each preview **absolute path**. The v2 `contracts/ui-truth-index.json` stores **repo-relative** component/test/preview paths, environment profiles, sourced states, concrete scenarios, complete coverage, SHA-256 hashes, and confirmation bound to the current preview hash. Figma is 1:1 truth only for scenarios it actually evidences; runtime behavior comes from the requirement, project rules, or an explicit user decision. Stage 4 reuses the same slice worktree and writes `visual-acceptance.json`, binding the current index hash and every scenario's mode-appropriate evidence. Codex still needs `[features] hooks = true` in `.codex/config.toml` if you use other Codex hooks.

Project `AGENTS.md` carries a short UI-truth reminder (amend-on-upgrade). Restore older IDE JSON from `.ai-delivery/backups/ide-gates/` if needed.

```toml
[features]
hooks = true
```

If you maintain a user-level `~/.codex/config.toml`, also set `[features] hooks = true` there (or keep the project file trusted). Without this flag, `.codex/hooks.json` will not run. See [Codex hooks](https://developers.openai.com/codex/hooks).

Amended IDE JSON / `AGENTS.md` / Codex config are backed up under `.ai-delivery/backups/ide-gates/`. Restore with:

```bash
ai-delivery ide-gates list
ai-delivery ide-gates restore --to <timestamp>
```

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

## Unified artifact layout (new repos only)

Repos initialized after this refactor use a single canonical home under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR>/`:

- `design.md`, `verification.md`, `visual-acceptance.json`, `spec/{spec,plan,tasks}.md`, `contracts/ui-truth-index.json`, `archive/<ISO-ts>/` + `MANIFEST.json`
- Path constants live in `.ai-delivery/meta/project-binding.json` → `layout`
- Framework dirs (`.specify/`, `openspec/changes/`) are derived views synced back to canonical artifacts

**No automatic migration** for older repos — only new `ai-delivery init` seeds the layout.

### Lifecycle semantics (`merged` → `archived`)

- `merged` = code integrated on the dev branch
- `archived` = immutable freeze (`archive/` + `MANIFEST.json`); requirement completes when all executable subreqs are `archived`
- Run `scripts/archive-subrequirement.py` at CP-ARCHIVE before setting `archived`
- For the final sub-requirement, instantiate `delivery-report-template.md` in the user's current conversation language, remove its language instruction comment, and pass it with `--delivery-report-template <path>`

For multi-party work, install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately and run `coordination-cli init` in the repo; this kit does not embed coordination logic.
