---
name: ai-delivery-orchestrator
description: Use when a requirement document needs governed end-to-end delivery through Figma UI contracts, a spec pipeline, and merge gates. Use as the single entry when `.ai-delivery` state exists or the user provides a new requirement doc.
---

# AI Delivery Orchestrator

Single entry for requirement → implementation. Leaf skills (`requirement-breakdown`, `ui-truth-mapping`) are pure tools — no pipeline awareness. This skill owns state, gates, blockers, and handoffs.

```
Requirement → [Breakdown?] → Capability review → Solution Design? → Spec → Plan → Tasks → Implement → Merge → Archive
```

The orchestrator is **framework-agnostic**: it emits abstract stage actions and adapts them to whatever AI development framework the user has installed. It never requires installing anything.

## Artifact language

- Treat bundled template prose as an English source default, not as the output language.
- Write headings, labels, explanations, review evidence, solution-design/spec/plan/task prose, and necessary code comments in the user's current conversation language. Apply the same rule when updating an existing artifact.
- Preserve machine-readable keys, enum values, IDs, paths, commands, code symbols, and literal protocol tokens exactly.
- For Markdown templates, localize all human-readable content and remove the `ai-delivery-template-language` instruction comment before writing the artifact. For JSON templates, preserve the structure and localize only human-readable descriptive values.

## Framework adaptation (run once per session)

Before executing any stage action:

1. Self-check the environment per [references/framework-adaptation.md](references/framework-adaptation.md) (installed frameworks: spec-kit / OpenSpec / superpowers / ECC; none installed → native tier).
2. Select the tier for the current action (spec-type vs execution-type actions).
3. Record the selection once in the subreq `decisions.md`.

Action → guide dispatch table and loop model: [references/framework-adaptation.md](references/framework-adaptation.md). Per-framework usage guides: `references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`.

## Pipeline

| Stage | Abstract action | Gate |
|-------|-----------------|------|
| 1 | `requirement-breakdown` + light audit | `split_ready` |
| 2 | Capability-gated `ui-truth-mapping` (only when `ui_truth_mode` requires it) | `acceptance_frozen` when enabled |
| 3a | `solution-design` (canonical artifact remains `design.md`) | `design_approved` when `design_mode=full` |
| 3b | `spec` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |
| 6 | `archive` | `archived` (all subreqs) |

Stage details: [references/stage-breakdown.md](references/stage-breakdown.md), [stage-ui-truth.md](references/stage-ui-truth.md), [stage-design-and-spec.md](references/stage-design-and-spec.md), [stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md), [stage-implementation.md](references/stage-implementation.md).

## State model

```
draft → split_ready → [acceptance_frozen] → [design_approved] → spec_ready → plan_ready → tasks_ready → in_dev → [visual_acceptance_passed] → merged → archived
```

The bracketed states are capability-gated. `ui_truth_mode=none` and `existing` skip UI truth freeze and visual acceptance; `design_mode=none` and `light` do not require a full approval checkpoint.

Truth lives in `.ai-delivery/requirements/<req-id>/status.json`. Copy the structure of [templates/status-template.json](templates/status-template.json) verbatim and localize its human-readable descriptive values; never regenerate the structure from memory. Instantiate [templates/todo-template.md](templates/todo-template.md) in the user's current conversation language (not source of truth).

| Field | Purpose |
|-------|---------|
| `status` | Current state or `blocked_*` |
| `ui_bearing` | `true` / `false` — whether the slice owns a UI surface; validators require consistency with `ui_truth_mode` |
| `ui_truth_mode` | `none` / `existing` / `runtime-baseline` / `figma` — the UI truth capability required by the slice |
| `design_mode` | `none` / `light` / `full` — the solution-design depth and approval policy |
| `design_approved` | Solution-design gate satisfied: `light` after the AI self-review, `full` after explicit user approval; `none` remains `false` |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | Resume target after blocker cleared |

## Reconcile first

On every resume or continue, run reconcile before trusting `todo.md`:

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile emits abstract actions (`solution-design` / `spec` / `plan` / `tasks` / `implement` / `finish` / `archive`, plus kit-owned skills) — never third-party skill names. Rules: [references/reconcile-rules.md](references/reconcile-rules.md).

## Handoff table

Each stage has one legal next action. Full table: [references/handoff-table.md](references/handoff-table.md).

| Done | Next |
|------|------|
| `split_ready` + audit (`ui_truth_mode=figma` or `runtime-baseline`) | CP-UI → `ui-truth-mapping` |
| `split_ready` + audit (`ui_truth_mode=none` or `existing`) | `solution-design` when `design_mode` is `light` or `full`; otherwise `spec` |
| `acceptance_frozen` | `solution-design` according to `design_mode` |
| `design_approved=true` or `design_mode=none` | `spec` |
| All `tasks_ready` + CP-001 | Stage 4 `implement` |
| Slice done | `finish` |

## Pause points (6)

1. After split/skip decision — confirm with user
2. Before enabled UI truth production-code work — CP-UI, authorize the controlled visual implementation and slice worktree
3. After a `design_mode=full` solution-design session — CP-DESIGN, explicit approval before `spec`
4. After `tasks_ready` — CP-001, confirm before the remaining development work
5. Review-loop budget exhausted — the task-level review loop (implement → review → fix → re-review) stopped without a clean round; report outstanding findings and wait for the user
6. After all subreqs `merged` — CP-ARCHIVE, confirm freezing the immutable archive before marking `archived`

## Hard boundary

- Do not move workflow truth out of `.ai-delivery`.
- External skill defaults never authorize framework-owned artifact paths. External skills provide methods and execution discipline only: pass canonical `.ai-delivery` output paths before invocation; if a persistence step cannot honor them, skip that step and write the equivalent canonical artifact directly. Never create process/governance artifacts under `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, `openspec/**`, or another host-tree framework directory and move them afterward.
- Outside `.ai-delivery/`, writes are limited to production source, project-native tests, goldens/official previews, and runtime assets. Before advancing any gate, compare the entry/exit Git status/content fingerprint and independent filesystem fingerprints for every declared external default output root, including ignored files and at least the four forbidden roots above. Path, status, type, symlink-target, or SHA-256 drift catches writes even when a path was already dirty or ignored. A new or modified process/governance artifact outside `.ai-delivery/` sets `blocked_verification_failure`.
- Do not require the user to install or pick frameworks/skills on the normal path; adapt to what is already installed.
- Do not let `ui_truth_mode=figma` or `runtime-baseline` subreqs enter `spec` before `acceptance_frozen`; `none` and `existing` bypass that gate.
- Do not dispatch `ui-truth-mapping` unless the mode enables the capability and CP-UI is explicitly confirmed and recorded. Stage 2 writes production code, so it must create or reuse the slice worktree, use TDD/golden tests, and close a fresh-context review loop.
- Do not let UI truth slices claim `merged` before `visual_acceptance_passed`; `none` and `existing` use ordinary behavior/semantic verification.
- Do not promote slice-local blockers to requirement-global while any runnable item exists.
- Gate / blocker / status / merge decisions never go to subagents. Leaf skills may use subagents per their own rules (`ui-truth-mapping` per-unit, Stage 4 per the chosen execution tier).
- Do not write solution-design docs into framework-owned directories during orchestrator solution-design mode; write the canonical artifact to subreq `design.md` and keep only a short pointer in `notes`.
- For `ui_truth_mode=figma` or `runtime-baseline`, do not set `acceptance_frozen` until each UI unit has a real host-stack component, complete applicability-gated runtime coverage, an official-stack preview for every visual scenario whose **absolute path** was shown to the user, a valid v2 `contracts/ui-truth-index.json` with matching SHA-256 hashes and confirmation bound to current preview hashes, and a clean Stage 2 review. Stage 2 authors via `ui-truth-mapping` only — never via `figma-design-to-code`, and never by generating `ui-contract.html`.
- Stage 4: for `ui_truth_mode=figma` or `runtime-baseline`, reuse the Stage 2 slice worktree; do not create a second worktree or re-draw the component. `existing` uses the existing component and ordinary behavior/semantic checks; `none` has no UI truth artifact. Do not re-query TemPad / run `figma-design-to-code` by default; the frozen component plus confirmed preview is the visual source of truth. Follow fill / hug / fixed (fill = parent minus insets, not snapshot px). Do not re-draw Flutter from HTML.
- Do not set `merged` for `ui_truth_mode=figma` or `runtime-baseline` without prior `acceptance_frozen` + `visual_acceptance_passed` + a valid v2 `ui-truth-index.json` + structured `visual-acceptance.json` covering every indexed scenario. `none` and `existing` close through ordinary verification.
- Do not set `archived` without a frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256 (run `scripts/archive-subrequirement.py` per subreq); `archived` is immutable — never edit its archived artifacts in place.
- Do not claim a task done or merge work whose latest review round is not clean; the review loop escalates to the user when its budget is exhausted.
- Edit one file at a time during implementation; rebase worktrees (no merge commits).

## Status transition gates

| Target | Requirement |
|--------|-------------|
| `acceptance_frozen` | Required only for `ui_truth_mode=figma` or `runtime-baseline`: CP-UI recorded; slice worktree evidence recorded; real component compiles; Stage 2 TDD/review clean; all ten runtime dimensions are `covered` or reasoned `not_applicable`; preview paths, v2 index hashes/provenance/profile/scenario coverage, and preview-bound confirmations validate |
| `spec/plan/tasks_ready` (UI truth) | Valid prior `acceptance_frozen`; v2 index paths, hashes, coverage, and confirmation bindings still validate |
| `merged` (UI truth) | UI truth mode has prior `acceptance_frozen` + `visual_acceptance_passed` + valid v2 index + structured `visual-acceptance.json`; `existing` uses ordinary behavior/semantic evidence, and `none` skips visual acceptance |
| `archived` | Frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256; immutable (verified by `--verify-archive`) |

## Split decision

**Skip** when ALL: single screen, no shared state, one developer, no cross-cutting rules, doc under ~300 words.

**Split** when ANY: 2+ screens, shared state, multi-developer coordination, cross-feature infrastructure.

State decision with reasoning, then proceed. Details: [references/stage-breakdown.md](references/stage-breakdown.md).

## Light audit (not solution-design exploration)

After `split_ready`, main session runs inline 4-check audit per subreq (gaps, conflicts, states, permissions), then resolves `ui_truth_mode` and `design_mode`. Critical issues → blockers; otherwise append to `notes`. Do not run the `solution-design` action during the light audit.

## Stage 4 (summary)

The `implement` action executes per the selected tier (see `references/frameworks/`): subagent-driven when superpowers is present, agent-driven with ECC, inline disciplined on the native tier. Default discipline regardless of tier: sequential tasks, TDD inside, code review before completion claims. Never parallel implementers on the same slice files.

Chain: reuse the Stage 2 slice workspace for UI truth modes that enable it (create one here for other slices) → task execution (TDD) → code review → scenario-complete visual/runtime acceptance recorded in `visual-acceptance.json` when required → verification before completion → full test → merge.

UI truth slices: wire the already-written component (API / route / state / mount); do not re-query TemPad / run `figma-design-to-code` by default. `existing` UI slices do not enter Stage 2; they use normal project behavior and semantic checks.

Full runbook: [references/stage-implementation.md](references/stage-implementation.md).

## Blockers

Narrowest blocker wins; continue safest runnable work first. On validator failure use `blocked_verification_failure`. Catalog: [references/blocker-catalog.md](references/blocker-catalog.md).

## API policy

API docs pass directly to the spec pipeline and implementation. Gaps → `integration_deferred` in notes; they do not block UI mapping or shell work.

## User entry

1. Inspect `.ai-delivery/requirements/*`, `status.json`, run reconcile.
2. Recommend `continue req-xxx` or `create req-yyy`.
3. Pause for human confirmation before routing.

| Intent | Mode |
|--------|------|
| New requirement + sources | `bootstrap` or `resume` |
| Continue orchestrating | `resume` |
| UI truth capability pending authorization | `confirm_ui` (CP-UI) |
| tasks_ready, proceed to dev | `confirm_to_dev` (CP-001) |
| Full solution-design pending approval | `confirm_solution_design` (CP-DESIGN) |
| Blocker resolved | `blocker_recovery` (CP-002) |

## Runtime modes

`bootstrap` | `resume` | `confirm_ui` | `confirm_solution_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

Checkpoints: CP-UI (pre-enabled UI truth production code), CP-DESIGN (full solution-design approval), CP-001 (remaining development), CP-002 (hard blocker, only when no runnable items remain), CP-ARCHIVE (pre-freeze, all subreqs merged).

## Completion

All executable subreqs `merged` → runtime_mode `closing` (CP-ARCHIVE). Before the final archive command, instantiate `templates/delivery-report-template.md` as a temporary template in the user's current conversation language, remove its `ai-delivery-template-language` comment, and preserve its placeholders. Run `scripts/archive-subrequirement.py` per subreq to freeze `archive/<ISO-ts>/` + `MANIFEST.json` and advance status to `archived`; pass the prepared template to the final command with `--delivery-report-template <path>`. Do not claim `completed` until the localized `delivery-report.md` exists. When every subreq is `archived`, the requirement is `completed` and the archive is immutable — any change requires a new `<req-id>/` directory.

## Orchestration shape (invariants)

These rules prevent orchestration regressions. They apply to the main session and reconcile dispatch:

1. **Main session is the orchestrator** — one human-facing session drives the sequential pipeline (Pattern 4). No router persona sits between stages.
2. **Dispatch table is data, not a router** — `ACTION_BY_STATUS` / reconcile output names abstract actions; do not introduce a persona that re-derives or re-explains the table.
3. **Subagents are leaf-only, depth ≤ 1** — implementation and review may delegate to subagents per tier rules; the orchestrator never nests orchestrator personas.
4. **Forbidden patterns** — persona-calls-persona chains, “sequential orchestrator” layers that only paraphrase the previous stage, and deep persona trees.
5. **Review never auto-merges** — `merged` / `archived` require clean review evidence (`verification.md`) and human gates; budget exhaustion always pauses for the user.

This kit owns single-repo governed delivery (`.ai-delivery/`, `status.json`, gates). Multi-party coordination is out of scope here — install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately if needed.
