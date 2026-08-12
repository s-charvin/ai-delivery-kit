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
| 2 | `ui-truth-mapping` (UI only) | `acceptance_frozen` |
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

Truth lives in `.ai-delivery/requirements/<req-id>/status.json`. Copy [templates/status-template.json](templates/status-template.json) verbatim — never regenerate structure from memory. Execution panel: [templates/todo-template.md](templates/todo-template.md) (not source of truth).

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
| `split_ready` + audit (UI) | `ui-truth-mapping` |
| `split_ready` + audit (non-UI) | `design` |
| `acceptance_frozen` | `design` |
| `design_approved` | `spec` |
| All `tasks_ready` + CP-001 | Stage 4 `implement` |
| Slice done | `finish` |

## Pause points (5)

1. After split/skip decision — confirm with user
2. After the design session — CP-DESIGN, explicit approval before `spec`
3. After `tasks_ready` — CP-001, confirm before development
4. Review-loop budget exhausted — the task-level review loop (implement → review → fix → re-review) stopped without a clean round; report outstanding findings and wait for the user
5. After all subreqs `merged` — CP-ARCHIVE, confirm freezing the immutable archive before marking `archived`

## Hard boundary

- Do not move workflow truth out of `.ai-delivery`.
- Do not require the user to install or pick frameworks/skills on the normal path; adapt to what is already installed.
- Do not let UI subreqs enter `spec` before `acceptance_frozen`.
- Do not let UI slices claim `merged` before `visual_acceptance_passed`.
- Do not promote slice-local blockers to requirement-global while any runnable item exists.
- Gate / blocker / status / merge decisions never go to subagents. Leaf skills may use subagents per their own rules (`ui-truth-mapping` per-unit, Stage 4 per the chosen execution tier).
- Do not write design docs into framework-owned directories during orchestrator design mode; store design summary in subreq `notes`.
- Do not set `acceptance_frozen` until `scripts/validate-ui-contract-html.py` exits 0 for every unit's `ui-contract.html` **and** each contract's browser-hydrated default preview + requirement-scope alignment + icon asset fidelity + explicit per-contract user confirmation (unless explicitly waived) pass (see Stage 2 freeze bar). Stage 2 authors contracts via `ui-truth-mapping` only — never via `figma-design-to-code`.
- Do not set `merged` for UI work without prior `acceptance_frozen` + `visual_acceptance_passed` + passing contracts.
- Do not set `archived` without a frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256 (run `scripts/archive-subrequirement.py` per subreq); `archived` is immutable — never edit its archived artifacts in place.
- Do not claim a task done or merge work whose latest review round is not clean; the review loop escalates to the user when its budget is exhausted.
- Edit one file at a time during implementation; rebase worktrees (no merge commits).

## Status transition gates

| Target | Requirement |
|--------|-------------|
| `acceptance_frozen` | All contracts pass `validate-ui-contract-html.py`; hydrated default + state switcher preview OK; scope matches slice In Scope; icons evidence-backed (no hand-drawn glyphs); user confirmed each contract (unless waived) |
| `spec/plan/tasks_ready` (UI) | Valid prior `acceptance_frozen`; contracts still pass |
| `merged` (UI) | `acceptance_frozen` + `visual_acceptance_passed` + contracts pass |
| `archived` | Frozen `archive/<ISO-ts>/` snapshot + `MANIFEST.json` sha256; immutable (verified by `--verify-archive`) |

## Split decision

**Skip** when ALL: single screen, no shared state, one developer, no cross-cutting rules, doc under ~300 words.

**Split** when ANY: 2+ screens, shared state, multi-developer coordination, cross-feature infrastructure.

State decision with reasoning, then proceed. Details: [references/stage-breakdown.md](references/stage-breakdown.md).

## Light audit (not design exploration)

After `split_ready`, main session runs inline 4-check audit per subreq (gaps, conflicts, states, permissions). Critical issues → blockers; otherwise append to `notes`. Do not run the `design` action here.

## Stage 4 (summary)

The `implement` action executes per the selected tier (see `references/frameworks/`): subagent-driven when superpowers is present, agent-driven with ECC, inline disciplined on the native tier. Default discipline regardless of tier: sequential tasks, TDD inside, code review before completion claims. Never parallel implementers on the same slice files.

Chain: isolated workspace → task execution (TDD) → code review → visual acceptance (UI) → verification before completion → full test → merge.

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
| tasks_ready, proceed to dev | `confirm_to_dev` (CP-001) |
| Design pending approval | `confirm_design` (CP-DESIGN) |
| Blocker resolved | `blocker_recovery` (CP-002) |

## Runtime modes

`bootstrap` | `resume` | `confirm_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

Checkpoints: CP-DESIGN (design approval), CP-001 (pre-dev), CP-002 (hard blocker, only when no runnable items remain), CP-ARCHIVE (pre-freeze, all subreqs merged).

## Completion

All executable subreqs `merged` → runtime_mode `closing` (CP-ARCHIVE). Run `scripts/archive-subrequirement.py` per subreq to freeze `archive/<ISO-ts>/` + `MANIFEST.json`, advance status to `archived`, and generate `delivery-report.md`. When every subreq is `archived`, the requirement is `completed` and the archive is immutable — any change requires a new `<req-id>/` directory.

## Orchestration shape (invariants)

These rules prevent orchestration regressions. They apply to the main session, reconcile dispatch, and any `ai-delivery-coordination/` loop runner:

1. **Main session is the orchestrator** — one human-facing session drives the sequential pipeline (Pattern 4). No router persona sits between stages.
2. **Dispatch table is data, not a router** — `ACTION_BY_STATUS` / reconcile output names abstract actions; do not introduce a persona that re-derives or re-explains the table.
3. **Subagents are leaf-only, depth ≤ 1** — implementation and review may delegate to subagents per tier rules; the orchestrator never nests orchestrator personas.
4. **Forbidden patterns** — persona-calls-persona chains, “sequential orchestrator” layers that only paraphrase the previous stage, and deep persona trees.
5. **Review never auto-merges** — a loop runner may execute `implement` steps, but `merged` / `archived` require clean review evidence (`verification.md`) and human gates; budget exhaustion always pauses for the user.
6. **Cross-repo execution is MCP-only** — claim, status, and `hub://` pointers go through the coordination MCP server; never invent a local fake hub status or import coordination Python.

When autonomous execution is needed, use the **external** coordination MCP server (`start_loop`, `claim_node`, `register_artifact_ref`, `intervene_loop`, …). The skill layer keeps spec-segment truth in `status.json`; the engine only writes back execution-segment statuses and immediately re-runs reconcile. **Never import coordination Python from the skill layer** — see [references/coordination-mcp-bridge.md](references/coordination-mcp-bridge.md) and [docs/coordination-repo.md](../../../docs/coordination-repo.md).
