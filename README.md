# AI Delivery Kit

Bootstrap governed `ai-delivery` workflows into arbitrary business repositories, then advance new work through `ai-delivery-orchestrator` instead of manual stage-by-stage dispatch.

中文版：[README.zh-CN.md](README.zh-CN.md)

## Quick Start

Download the platform archive from [Releases](https://github.com/s-charvin/ai-delivery-kit/releases), extract the single `ai-delivery` program, and add it to PATH. Daily kit operation needs no Go SDK, Python, Node, or zsh; declared native host tools are separate. The scripts below are optional installation conveniences; they never fetch a Git checkout or combine skills from another version.

Install the CLI:

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo
```

Or bootstrap without installing:

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/bootstrap-ai-delivery.sh | bash -s -- /path/to/repo
```

The bootstrap script downloads a temporary release binary and runs the same canonical `ai-delivery init` logic.

**Developing this repo:**

```bash
git clone https://github.com/s-charvin/ai-delivery-kit.git
```

For multi-party orchestration (optional), install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately and run `coordination-cli init` in your repo. This kit does not embed coordination logic.

## Execution defaults

One implementer completes a coherent batch with focused test feedback; an independent reviewer checks the integrated result. Unit count does not trigger subagents. Delegate only for independent ownership, bounded outputs and a net coordination benefit. Preserve final test/analysis scope and UI/motion approvals; validate matching inputs and artifact hashes before reusing evidence. Details: [implementation and verification](.agents/skills/ai-delivery-orchestrator/references/stage-implementation.md).

## Upgrade

Upgrade the installed CLI by rerunning the installer:

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash
```

If a repository was initialized by an older `ai-delivery init`, first upgrade the CLI, then refresh the managed project assets:

```bash
ai-delivery init --upgrade /path/to/repo
```

Or do both in one step:

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash -s -- --upgrade-init /path/to/repo
```

`init --upgrade` refreshes human-readable skills/templates and `meta/kit-assets.json` from the running program while preserving requirement data. No executable core is installed into the project. From an initialized host project:

```bash
ai-delivery init --upgrade .
```

The kit supports only current delivery formats. Before an ordinary `init --upgrade` writes managed assets, it checks existing binding/policy metadata. Unsupported, missing or damaged metadata stops the upgrade with its file, field, actual value, required format and recovery choices. Requirement data is checked when consumed. An asset refresh never certifies all tasks or migrates their data.

When you encounter incompatibility, choose either:

- **Migrate with your own AI or tools:** copy the prompt in [version-upgrade.md](.agents/skills/ai-delivery-orchestrator/references/version-upgrade.md), back up, and convert only the data you want to keep using. Current evidence and approvals still apply.
- **Back up and start fresh:** explicitly run `ai-delivery init --upgrade --reset-data /path/to/repo`. This is a deterministic file operation; no AI is used. For a custom old delivery root, use `--reset-data=tooling/delivery`. The new workspace uses `.ai-delivery/`; an existing standard target prevents mixing it with a custom source.

Reset backs up the raw old tree and affected managed assets to a unique `.ai-delivery-backups/<UTC>-<suffix>/` directory. It verifies bytes, types and symlink targets before moving old data or refreshing assets. Invalid old JSON can be backed up. Backup failure leaves active data and managed assets untouched. Initialization failure after backup reports the complete backup, original tree location and affected targets; inspect `manifest.json` and restore `files/` paths as needed. An `absent` entry records a path that did not originally exist. Backups are never automatically rotated or deleted. Production files and unrelated skills/configuration are preserved.

The project-root `.ai-delivery.lock` serializes cooperative archive/init/upgrade/reset operations using native platform locks. Unsupported platforms fail clearly before changing data; Windows uses the same native lock support for reset and delivery actions. Add `.ai-delivery.lock` and `.ai-delivery-backups/` to your project's ignore rules; keep backups private.

For an existing current root nested beyond one directory, supply the root itself: `ai-delivery init --upgrade /project/tooling/delivery`. The same target works for `ide-gates list` and `ide-gates restore`; automatic project-root discovery stays bounded. Reset still takes the project path plus `--reset-data=tooling/delivery`.

`--upgrade-policy` and legacy archive-snapshot validation are removed. Ordinary commands do not choose a recovery option, rewrite old records, register migration receipts or fall back to old validators.

`.ai-delivery/backups/` holds separate ephemeral IDE-gate amend snapshots (gitignored). It is distinct from full reset backups in `.ai-delivery-backups/`.

## What `ai-delivery init` Does

`ai-delivery init` is the repository onboarding command only. It:

- discovers the Git root when present, otherwise uses the explicit directory (Git is not required for a non-Git project)
- derives `project_id` from the repository name
- seeds the governed `.ai-delivery` contract, project-local human-readable skills, templates, and resource identities

It never installs third-party frameworks. The workflow is framework-agnostic: it adapts at runtime to whatever AI development frameworks are already present, and falls back to built-in native artifacts when none are installed.

The normal public path no longer asks the user to provide `project_id`.

## Default Requirement Entry

After onboarding, start new work through `ai-delivery-orchestrator`.

Typical user input should stay natural-language and source-driven, for example:

- “这是需求文档，这是 Figma，这是接口，开始推进”
- “继续这个需求”
- “这个 blocker 我处理好了，继续”

The orchestrator decides whether to continue an existing requirement or create a new one. It proceeds automatically when the choice is unambiguous and asks only when competing choices materially change governed scope or ownership.

## Human Review Points

Humans stay in the loop only where judgment matters:

- resolve a materially ambiguous requirement boundary
- authorize enabled UI truth work at CP-UI and resolve named product/behavior/resource/experience decisions at CP-DESIGN
- resolve blockers when governed truth is missing or conflicting

Everything else should default to AI-driven progression through the orchestrated chain.

## Exception Path

Lower-level skills such as `requirement-breakdown` and `ui-truth-mapping` can still be used directly when their prerequisites are already satisfied. For `ui-truth-mapping`, that includes a governed Stage 2 slice and recorded CP-UI authorization. `ai-delivery-orchestrator` remains the default entry for new requirements.

That path is for surgical recovery or expert use. It is not the normal entry for new requirements.

## Framework Adaptation

The orchestrator emits abstract actions (`solution-design` / `implement` / `finish` / `archive`) and adapts them to frameworks already installed in your environment. Nothing is installed or required. `design.md` is the single persisted behavior and solution-design contract.

Recommended frameworks (detected, never installed):

| Framework | Primary actions | Detection marker |
|-----------|-----------------|------------------|
| spec-kit | optional requirement/design reasoning | `.specify/` or `specify` CLI |
| OpenSpec | optional brownfield delta reasoning | `openspec/` or `openspec` CLI |
| superpowers | `solution-design` / `implement` / `finish` | superpowers skills in user skill dirs |
| ECC | `solution-design` / `implement` / `finish` | `/ecc:*` commands registered |

No framework installed? The native tier still runs the pipeline end to end with the same canonical `design.md`, TDD, review, and verification discipline.

Per-framework usage guidance ships with the orchestrator skill: `references/framework-adaptation.md` and `references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`.

## Capability-gated UI truth (no HTML contract hooks)

Each sub-requirement declares independent capability and authority fields in `status.json`:

- `ui_truth_mode`: `none` (no visible UI), `existing` (behavior or semantics on an existing visual surface), `runtime-baseline` (new visible UI without stable Figma truth), or `figma` (stable Figma evidence).
- `state_flow_required`: whether complex state ownership, guards, concurrency, stale-result, persistence, or recovery rules require the full state-flow contract.
- `user_decision_required`: whether the current design version contains a material product, behavior, resource, or experience choice whose authority belongs to the user. It remains `true` after approval; the hash-bound `design_review` records whether that version has valid human authorization.

Only `ui_truth_mode=figma` or `runtime-baseline` enables CP-UI, Stage 2, `acceptance_frozen`, the v3 UI truth index, and visual acceptance. `none` and `existing` proceed through the design contract and ordinary behavior or semantic verification. State-flow depth does not create CP-DESIGN; a design with `user_decision_required=true` enters CP-DESIGN only when its current bytes lack a valid hash-bound human review. `ui_bearing` is a consistency field, not a workflow gate.

After CP-UI authorization, Stage 2 implements and freezes **real host-stack components** plus official previews for visual scenarios in the user-approved workspace (Flutter: widget + golden PNG; animated units additionally use a deterministic GIF when the host can produce one), with TDD and fresh-context review. GIF is the only governed motion-preview format; when it cannot be produced, record the reason and defer runtime verification rather than adding WebP/MP4 or fabricating a file. The current checkout is the default. Creating or reusing a worktree requires separate confirmation for the current sub-requirement and must use `<project-root>/.worktrees/<req-id>-<sr-id>`; external or platform-managed temp paths are forbidden. Before component code, each unit must resolve an applicability-gated Runtime Coverage Plan for state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance, and record a separate `motion_decision` (animated motion confirmation/waiver or confirmed static/no-motion decision). Golden confirmation is static evidence only; Stage 4 must record a separate motion acceptance for every unit. Visible UI uses real controls and evidence-backed resources; absent data stays empty/omitted, unapproved placeholders or silent fallbacks are forbidden, and missing resources require an explicit user choice to render empty, defer, or block. `ai-delivery init` does **not** install UI git hooks.

Give the user each preview **absolute path**. The v3 `contracts/ui-truth-index.json` stores **repo-relative** component/test/preview paths, environment profiles, sourced states, concrete scenarios, complete coverage, evidence scopes, host capability decisions, host bindings when applicable, SHA-256 hashes, and confirmation bound to the current preview hash. Figma is 1:1 truth only for scenarios it actually evidences; runtime behavior comes from the requirement, project rules, or an explicit user decision. Stage 4 reuses the same user-approved workspace and writes `visual-acceptance.json`, binding the current index hash, every scenario's mode-appropriate evidence, and one independent motion acceptance record per indexed unit.

Project `AGENTS.md` carries a short UI-truth reminder (amend-on-upgrade). Restore older IDE JSON from `.ai-delivery/backups/ide-gates/` if needed.

Native hooks are optional. Installation does not create or require `.codex/hooks.json`, `.claude/settings.json`, `.cursor/hooks.json`, or `.codex/config.toml`. Existing files, `features.hooks` values, large integers, and third-party definitions remain byte-for-byte unchanged; users choose and maintain their own opt-in configuration. See the [reviewable Codex SessionStart/PreToolUse example](.agents/skills/ai-delivery-orchestrator/references/native-hooks.md) for explicit scope and host trust requirements. Real binary protocol tests do not certify local Codex enablement, trust, or callbacks; Claude/Cursor native transports are not implemented. The explicit CLI workflow remains complete without hooks.

Managed `AGENTS.md` updates are backed up under `.ai-delivery/backups/ide-gates/`; older IDE JSON / Codex config backups remain available for explicit byte-preserving restore. Restore with:

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

## Current artifact layout

Repos initialized after this refactor use a single canonical home under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR>/`:

- `design.md` (required canonical behavior and solution-design contract), `verification.md`, optional cross-session `progress.md`, `visual-acceptance.json` (UI truth modes only), and `contracts/ui-truth-index.json` (enabled UI truth only)
- Path constants live in `.ai-delivery/meta/project-binding.json` → `layout`
- External frameworks provide methods only; schema 2.0 does not create `spec.md`, `plan.md`, or `tasks.md`, and framework-owned derived views remain read-only

Older formats are rejected. Choose your own migration or the explicit backup/reset operation described above; normal upgrades do not convert them.

### Lifecycle semantics (`merged` → `archived`)

- `merged` = code integrated on the dev branch
- `archived` = status converged in place while canonical artifacts remain in their original locations; requirement completes when all executable subreqs are `archived`
- Optional `retrospective.md` is a requirement-level living ledger. Archive keeps it as-is and registers only problem-map rows explicitly marked as reusable, cross-requirement, confirmed, and high-value in `.ai-delivery/retrospectives/index.md` for progressive, scenario-matched loading; temporary decisions remain in the ledger but are not indexed. Before archive, AI upgrades legacy problem maps to `problem-index:v2` while preserving their detailed records.
- Run `ai-delivery archive --confirm-archive --expected-snapshot <snapshot-id>` at CP-ARCHIVE before setting `archived`; it must not create duplicate artifact copies
- New archives bind original contracts in the existing status entry's `archive_evidence`. Historical integrity does not require production files or native reports to remain at their old versions; current transitions and new-task reuse still require current evidence.
- For the final sub-requirement, instantiate `delivery-report-template.md` in the user's current conversation language, remove its language instruction comment, and pass it with `--delivery-report-template <path>`

For multi-party work, install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately and run `coordination-cli init` in the repo; this kit does not embed coordination logic.

## Maintainer toolchain and support evidence

The Go source baseline is `1.22.0`; release/CI builds use `1.26.2`. New macOS versions reject some Go 1.22 outputs with missing `LC_UUID`, so source compatibility is not a promise that old compiler outputs run on every new OS. Default `go test ./...` includes native process/lock checks, actual external installation, a complete CLI lifecycle with no interpreters, and an audit of candidate process-launch sites. Python is used only for explicitly invoked frozen developer baselines under `tests/migration-oracle/`. CI runs native tests on Linux/macOS/Windows; cross-compilation does not replace native evidence.

Historical shell developer tests, including `bootstrap-project.test.sh` and `current-protocol-reset.test.sh`, belong to the [frozen developer baseline](tests/migration-oracle/README.md) and are not validation for the current Go candidate. The current release rehearsal still runs `tests/ai-delivery-cli/bootstrap-script.test.sh` and `tests/ai-delivery-cli/install-script.test.sh`; their PowerShell counterparts remain current installer smoke tests.
