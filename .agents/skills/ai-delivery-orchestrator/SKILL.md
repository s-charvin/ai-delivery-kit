---
name: ai-delivery-orchestrator
description: Use when a requirement document needs governed end-to-end delivery through Figma UI contracts, a spec pipeline, and merge gates. Use as the single entry when `.ai-delivery` state exists or the user provides a new requirement doc.
---

# AI Delivery Orchestrator

Single entry for requirement → implementation. Leaf skills (`requirement-breakdown`, `ui-truth-mapping`) are pure tools — no pipeline awareness. This skill owns state, gates, blockers, and handoffs.

```
Requirement → [Breakdown?] → UI Truth → Design → Spec → Plan → Tasks → Implement → Merge → Archive
```

The orchestrator is **framework-agnostic**: it emits abstract stage actions and adapts them to whatever AI development framework the user has installed. It never requires installing anything.

## Artifact language

- Treat bundled template prose as an English source default, not as the output language.
- Write headings, labels, explanations, review evidence, design/spec/plan/task prose, and necessary code comments in the user's current conversation language. Apply the same rule when updating an existing artifact.
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
| 2 | CP-UI → controlled `ui-truth-mapping` visual implementation (UI only) | `acceptance_frozen` |
| 3a | `design` | `design_approved` |
| 3b | `spec` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |
| 6 | `archive` | `archived` (all subreqs) |

Stage details: [references/stage-breakdown.md](references/stage-breakdown.md), [stage-ui-truth.md](references/stage-ui-truth.md), [stage-design-and-spec.md](references/stage-design-and-spec.md), [stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md), [stage-implementation.md](references/stage-implementation.md).

## State model

```
draft → split_ready → acceptance_frozen → spec_ready → plan_ready → tasks_ready → in_dev → visual_acceptance_passed → merged → archived
```

Non-UI subreqs skip `acceptance_frozen` and `visual_acceptance_passed`.

Truth lives in `.ai-delivery/requirements/<req-id>/status.json`. Copy the structure of [templates/status-template.json](templates/status-template.json) verbatim and localize its human-readable descriptive values; never regenerate the structure from memory. Instantiate [templates/todo-template.md](templates/todo-template.md) in the user's current conversation language (not source of truth).

| Field | Purpose |
|-------|---------|
| `status` | Current state or `blocked_*` |
| `ui_bearing` | `true` / `false` / `null` — whether slice owns UI surfaces |
| `design_approved` | User approved the design session output |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | Resume target after blocker cleared |

## Reconcile first

On every resume or continue, run reconcile before trusting `todo.md`:

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile emits abstract actions (`design` / `spec` / `plan` / `tasks` / `implement` / `finish` / `archive`, plus kit-owned skills) — never third-party skill names. Rules: [references/reconcile-rules.md](references/reconcile-rules.md).

## Handoff table

Each stage has one legal next action. Full table: [references/handoff-table.md](references/handoff-table.md).

| Done | Next |
|------|------|
| `split_ready` + audit (UI) | CP-UI → `ui-truth-mapping` |
| `split_ready` + audit (non-UI) | `design` |
| `acceptance_frozen` | `design` |
| `design_approved` | `spec` |
| All `tasks_ready` + CP-001 | Stage 4 `implement` |
| Slice done | `finish` |

## Pause points (6)

1. After split/skip decision — confirm with user
2. Before Stage 2 production-code work — CP-UI, authorize the controlled visual implementation and slice worktree
3. After the design session — CP-DESIGN, explicit approval before `spec`
4. After `tasks_ready` — CP-001, confirm before the remaining development work
5. Review-loop budget exhausted — the task-level review loop (implement → review → fix → re-review) stopped without a clean round; report outstanding findings and wait for the user
6. After all subreqs `merged` — CP-ARCHIVE, confirm freezing the immutable archive before marking `archived`

## Hard boundary

- Do not move workflow truth out of `.ai-delivery`.
- Do not require the user to install or pick frameworks/skills on the normal path; adapt to what is already installed.
- Do not let UI subreqs enter `spec` before `acceptance_frozen`.
- Do not dispatch `ui-truth-mapping` for a `split_ready` UI slice until CP-UI is explicitly confirmed and recorded. Stage 2 writes production code, so it must create or reuse the slice worktree, use TDD/golden tests, and close a fresh-context review loop.
- Do not let UI slices claim `merged` before `visual_acceptance_passed`.
- Do not promote slice-local blockers to requirement-global while any runnable item exists.
- Gate / blocker / status / merge decisions never go to subagents. Leaf skills may use subagents per their own rules (`ui-truth-mapping` per-unit, Stage 4 per the chosen execution tier).
- Do not write design docs into framework-owned directories during orchestrator design mode; write the canonical design to subreq `design.md` and keep only a short pointer in `notes`.
- Do not set `acceptance_frozen` until each UI unit has a real host-stack component, complete applicability-gated runtime coverage, an official-stack preview for every visual scenario whose **absolute path** was shown to the user, a valid v2 `contracts/ui-truth-index.json` with matching SHA-256 hashes and confirmation bound to current preview hashes, and a clean Stage 2 review. Stage 2 authors via `ui-truth-mapping` only — never via `figma-design-to-code`, and never by generating `ui-contract.html`.
- Stage 4: reuse the Stage 2 slice worktree for UI slices; do not create a second worktree or re-draw the component. Do not re-query TemPad / run `figma-design-to-code` by default; the frozen component plus confirmed preview is the visual source of truth. Follow fill / hug / fixed (fill = parent minus insets, not snapshot px). Do not re-draw Flutter from HTML.
- Do not set `merged` for UI work without prior `acceptance_frozen` + `visual_acceptance_passed` + a valid v2 `ui-truth-index.json` + structured `visual-acceptance.json` covering every indexed scenario.
- Do not set `archived` without a frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256 (run `scripts/archive-subrequirement.py` per subreq); `archived` is immutable — never edit its archived artifacts in place.
- Do not claim a task done or merge work whose latest review round is not clean; the review loop escalates to the user when its budget is exhausted.
- Edit one file at a time during implementation; rebase worktrees (no merge commits).

## Status transition gates

| Target | Requirement |
|--------|-------------|
| `acceptance_frozen` | CP-UI recorded; slice worktree evidence recorded; real component compiles; Stage 2 TDD/review clean; all ten runtime dimensions are `covered` or reasoned `not_applicable`; visual scenario preview absolute paths shown; v2 index paths/hashes/provenance/profile/scenario coverage validate; every visual confirmation binds the current preview hash |
| `spec/plan/tasks_ready` (UI) | Valid prior `acceptance_frozen`; v2 index paths, hashes, coverage, and confirmation bindings still validate |
| `merged` (UI) | `acceptance_frozen` + `visual_acceptance_passed` + v2 index still valid + `visual-acceptance.json` binds the current index and passes/waives every scenario with evidence |
| `archived` | Frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256; immutable (verified by `--verify-archive`) |

## Split decision

**Skip** when ALL: single screen, no shared state, one developer, no cross-cutting rules, doc under ~300 words.

**Split** when ANY: 2+ screens, shared state, multi-developer coordination, cross-feature infrastructure.

State decision with reasoning, then proceed. Details: [references/stage-breakdown.md](references/stage-breakdown.md).

## Light audit (not design exploration)

After `split_ready`, main session runs inline 4-check audit per subreq (gaps, conflicts, states, permissions). Critical issues → blockers; otherwise append to `notes`. Do not run the `design` action here.

## Stage 4 (summary)

The `implement` action executes per the selected tier (see `references/frameworks/`): subagent-driven when superpowers is present, agent-driven with ECC, inline disciplined on the native tier. Default discipline regardless of tier: sequential tasks, TDD inside, code review before completion claims. Never parallel implementers on the same slice files.

Chain: reuse the Stage 2 slice workspace for UI (create one here for non-UI) → task execution (TDD) → code review → scenario-complete visual/runtime acceptance recorded in `visual-acceptance.json` (UI) → verification before completion → full test → merge.

UI slices: wire the already-written component (API / route / state / mount); do not re-query TemPad / run `figma-design-to-code` by default.

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
| split_ready UI, authorize visual implementation | `confirm_ui` (CP-UI) |
| tasks_ready, proceed to dev | `confirm_to_dev` (CP-001) |
| Design pending approval | `confirm_design` (CP-DESIGN) |
| Blocker resolved | `blocker_recovery` (CP-002) |

## Runtime modes

`bootstrap` | `resume` | `confirm_ui` | `confirm_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

Checkpoints: CP-UI (pre-Stage-2 production code), CP-DESIGN (design approval), CP-001 (remaining development), CP-002 (hard blocker, only when no runnable items remain), CP-ARCHIVE (pre-freeze, all subreqs merged).

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
