---
name: ai-delivery-orchestrator
description: Use as the single entry point for requirement development. Provide a requirement document and this skill auto-decides whether to split, then chains through UI truth mapping to Spec Kit implementation. All state, blockers, and gates are managed here.
---

# AI Delivery Orchestrator

Single entry point for the full requirement-to-implementation pipeline:

```
Requirement Doc → [Breakdown?] → UI Truth Mapping → Spec Kit → Implementation → Merge
                      ↑ auto-decided                        ↑ TDD + review + visual acceptance
```

The orchestrator owns all state transitions, blocker handling, gate decisions, and coupling between skills. Each pipeline skill (`requirement-breakdown`, `ui-truth-mapping`) is a pure, independent tool — it receives inputs, produces outputs, and has no knowledge of the pipeline or of each other.

## Pipeline Overview

| Stage | Skill | Input | Output | Gate |
|---|---|---|---|---|
| 1 | `requirement-breakdown` | Requirement doc | sub-requirements + dependency graph | `split_ready` per subreq |
| 2 | `ui-truth-mapping` | requirement-slice + Figma design source | `ui-acceptance-contract.yaml` + `section-map.json` | `acceptance_frozen` |
| 3 | `speckit-specify` → `speckit-plan` → `speckit-tasks` | YAML contract + requirement-slice + section-map | `spec.md` → `plan.md` → `tasks.md` | `spec_ready` → `plan_ready` → `tasks_ready` |
| 4 | TDD + implement + review + visual acceptance | tasks + YAML contract + API docs | implemented code | `visual_acceptance_passed` → `merged` |

## State Model

Every sub-requirement tracks its own state independently. States advance in order:

```
draft → split_ready → acceptance_frozen → spec_ready → plan_ready → tasks_ready → in_dev → visual_acceptance_passed → merged
```

- `draft`: just created, boundaries uncertain
- `split_ready`: complete source coverage, verbatim excerpts, clear scope and dependencies
- `acceptance_frozen`: YAML contract frozen, all screen states source-backed
- `spec_ready` / `plan_ready` / `tasks_ready`: Spec Kit artifacts generated and audited
- `in_dev`: implementation in progress
- `visual_acceptance_passed`: screenshot matches YAML contract (UI slices only; non-UI slices skip this)
- `merged`: code rebased and merged to development branch

State is recorded in a single `status.json` at the requirement level. Use `templates/status-template.json` as the starting point — it documents all status meanings, blocker scopes, checkpoints, and runtime modes inline as `_`-prefixed metadata keys.

Each sub-requirement entry:

| Field | Purpose |
|---|---|
| `status` | Current state (one of the status values above, or a `blocked_*` value) |
| `detail` | Granular human-readable description of what's happening inside this state |
| `blocked_from_status` | The status the sub-requirement was targeting before the block |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` — how wide the block reaches |
| `resume_target_status` | The status to resume toward after the blocker is cleared |
| `notes` | Free-form context for handoff between sessions |

## Runnable Queue & Blocker Scope

These terms are used in `status.json` blocker classification and reconcile decisions:

- **Runnable queue item** — Any item that can still advance safely under current governed truth without inventing missing facts. Examples: Figma evidence capture, page shell implementation, local state skeletons, navigation flow, mock wiring, read-only presentation paths.
- **`slice_local`** — Blocks only one slice, stage, or capability surface. Must not block unrelated slices.
- **`action_level_integration`** — Blocks real API wiring or final semantic closure for one action only. Does not block visual mapping, shell work, local state work, or navigation skeletons.
- **`requirement_global`** — Valid only when every derivable queue item is non-runnable. If one safe runnable item remains, the blocker is not requirement-global.

Default strategy: **continue safest runnable work first**, not "pause on first blocker."

## Runtime Modes, Checkpoints & Resolution

After every reconcile, determine the active mode:

1. **`completed`** — All executable slices are `merged`. Do not dispatch new work.
2. **`bootstrap`** — No `todo.md` exists, or requirement package too incomplete to derive a queue. Build from first governed stage.
3. **`confirm_to_dev`** — `todo.md` exists, `current_checkpoint` is `CP-001`, all executable slices at `tasks_ready`, user intent means "proceed to development."
4. **`blocker_recovery`** — `todo.md` exists, `current_checkpoint` is `CP-002`, blocker cleared. Reconcile, clear blocker only if guard now satisfiable, resume from blocked step.
5. **`resume`** — `todo.md` exists, no checkpoint holding, at least one queue item unresolved or runnable. Continue from safest runnable unresolved item.

Checkpoints:
- **`CP-001` tasks_ready_user_confirmation** — All executable slices at `tasks_ready`; pause for user confirmation before development.
- **`CP-002` hard_blocker_pause** — Only valid when no safe runnable queue item remains. API blockers alone do not qualify if UI truth capture, shell work, or safe partial development can continue.

`current_phase` and `current_checkpoint` are execution-panel hints. If they conflict with `.ai-delivery`, trust `.ai-delivery` and rewrite `todo.md` headers.

## Reconcile Rules

On every resume or continue, before trusting `todo.md`:

1. Re-read `.ai-delivery` status and artifacts.
2. Re-check every guard against governed artifacts.
3. Classify every blocker as `slice_local`, `action_level_integration`, or `requirement_global` before choosing a checkpoint.
4. Re-check what the blocker actually blocks: visual truth, acceptance freeze, integration, or final delivery.
5. If a guard is already satisfied, mark the item complete without re-running the stage.
6. If outputs exist but guard is not satisfied, re-run or open the narrowest blocker. Keep blocked items in queue; continue later items that don't depend on them.

## User Entry Mapping

Map user intent to runtime mode — don't ask the user to name the next skill:

1. Inspect existing `.ai-delivery/requirements/*`, `todo.md`, `status.json`.
2. Produce one recommendation: `continue req-xxx` or `create req-yyy`.
3. Pause for human confirmation before either path.

After routing confirmed:
- "Here's the requirement doc, Figma is open, let's go" → `bootstrap` if no valid `todo.md`, otherwise reconcile → `resume`.
- "Continue orchestrating this requirement" → reconcile → `resume` (unless a checkpoint is active).
- "tasks_ready, continue to development" → reconcile, require `CP-001` + all slices `tasks_ready` → `confirm_to_dev`.
- "I've resolved this blocker, keep going" → reconcile, require `CP-002` → `blocker_recovery`.

## Hard Boundary

- Do not move workflow truth out of `.ai-delivery`.
- Do not require the user to manually choose the first low-level skill in the normal path.
- Do not let UI-bearing sub-requirements enter `speckit-*` before `acceptance_frozen`.
- Do not let UI-bearing slices claim merge completion before `visual_acceptance_passed`.
- Do not promote a slice-local blocker to requirement-wide while any safe runnable item exists.
- Do not let a blocked queue entry swallow later entries that are still safe to run.
- Do not let subagents advance gates, decide blockers, or merge changes.
- Do not use subagents outside Stage 4 implementation.
- Do not apply one large multi-file patch during implementation; edit one file at a time.
- Do not use merge commits to reintegrate worktree branches; rebase to keep history linear.
- Do not fork official `speckit-specify`, `speckit-plan`, or `speckit-tasks` to restate repo-local contracts.

## Auto-Decision: Split Or Skip?

Before running `requirement-breakdown`, analyze the requirement. **Skip breakdown** when ALL are true:
- Single page or single screen
- No shared state across pages or features
- Can be built by one developer without coordination
- No cross-cutting rules (auth, permissions, shared validation)
- Requirement doc is under ~300 words with a single clear scope

**Run breakdown** when ANY are true:
- Spans 2+ pages or screens
- Has shared state (global store, cross-page propagation)
- Needs coordination between multiple developers
- Contains cross-feature infrastructure or shared components
- Has rules that apply across multiple feature areas

State your decision explicitly with reasoning, then proceed.

## Workflow

### Stage 1: Requirement Breakdown

**When to run:** auto-decision says "split", or any sub-requirement is at `draft` with unresolved scope.

**Prepare inputs:**
- Read the requirement document.
- Determine the requirement id and output directory: `.ai-delivery/requirements/<req-id>/`.

**Run `requirement-breakdown`:**
Feed it the requirement document path. It produces sub-requirements with `requirement-slice.md`, `dependency.json`, and the full artifact set.

**After completion:**
- For each sub-requirement: if scope is complete with verbatim excerpts and clear dependencies → set `split_ready`. If scope is uncertain → leave as `draft`.
- Initialize `status.json` at the requirement level with all sub-requirements and their determined statuses.
- Record the dependency graph in `.ai-delivery/requirements/<req-id>/dependency-graph.json`.

**Skip path:** When breakdown is skipped, create a minimal single sub-requirement package directly:
```
.ai-delivery/requirements/<req-id>/
├── requirement.md
└── sub-requirements/<subreq-id>/
    ├── requirement-slice.md
    └── status.json
```

**Pause:** Confirm the split plan (or skip decision) with the user before proceeding.

### Stage 2: UI Truth Mapping

**When to run:** for each sub-requirement where `contains_page_states: true` AND a Figma design source is available.

**Prepare inputs:**
- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- Gather the Figma file key and target node id.
- Set output directory to the sub-requirement directory.

**Run `ui-truth-mapping`:**
Feed it the requirement-slice and design source. It produces `ui-acceptance-contract.yaml` and `section-map.json`.

**After completion:**
- Verify all screen states in the YAML are source-backed.
- Set `acceptance_frozen` when all screen states have source evidence.
- Update `status.json`.

**If no Figma link:** skip this stage. Non-UI sub-requirements proceed directly to Spec Kit. UI sub-requirements without design go to `blocked_missing_design`.

### Stage 3: Spec Kit Pipeline

**When to run:** for each sub-requirement at `acceptance_frozen` (UI) or `split_ready` (non-UI).

**Prepare inputs:**
- Collect: `ui-acceptance-contract.yaml` (UI slices), `requirement-slice.md`, `section-map.json`.
- If API docs exist, pass them directly — no intermediate mapping.

**Run Spec Kit pipeline:**
1. Feed input artifacts directly to `speckit-specify` → produces `spec.md`. Verify the spec covers all screen states from the YAML contract.
2. Feed `spec.md` + input artifacts to `speckit-plan` → produces `plan.md`. Verify the plan respects delivery slice ordering.
3. Feed `plan.md` + input artifacts to `speckit-tasks` → produces `tasks.md`. Verify tasks are granular, ordered by dependency, and file-scoped.

**After each Spec Kit step:**
- `spec.md` generated → audit against YAML contract screen states → set `spec_ready`.
- `plan.md` generated → audit against delivery slice ordering → set `plan_ready`.
- `tasks.md` generated → audit task granularity and dependency order → set `tasks_ready`.

**Pause:** After `tasks_ready`, confirm with the user before starting implementation.

### Stage 4: Implementation

**When to run:** for each sub-requirement at `tasks_ready`.

**Slice execution order:** determined from `section-map.json`. Execute `shared-shell` units first, then `page` units, then `modal` units (each after its trigger page). A unit starts only when all its structural dependencies are `merged`.

**Implement each slice:**
1. **Create worktree** — `using-git-worktrees`, one worktree per slice.
2. **TDD cycle** — `test-driven-development`: write failing test first, then implement.
3. **Implementation** — edit one file at a time, re-check context between files. UI slices: implement against the YAML contract component tree, layout, spacing, typography, and states. API slices: wire real endpoints; keep deferred integration explicit.
4. **Code review** — `requesting-code-review`: first failure enters auto-fix loop before escalation.
5. **Visual acceptance** (UI slices only) — compare implementation screenshot side-by-side against YAML contract screen states. First failure enters auto-fix loop.
6. **Verification** — `verification-before-completion`: final checks before merge.
7. **Merge** — rebase worktree branch onto development branch (no merge commits).

Set `in_dev` when implementation starts.
Set `visual_acceptance_passed` after screenshot matches YAML (UI slices only; non-UI skip).
Set `merged` after rebase.

**Subagent rules (implementation only — never for gate decisions):**
- Use subagents only when at least two independent runnable tasks exist inside the current slice.
- Each task's dependencies must be satisfied before dispatch.
- At most two active subagents at a time.
- Main session owns: dependency analysis, worktree ordering, blocker classification, merge readiness.

### Stage 5: Completion

All slices `merged` → requirement complete. Update requirement-level status. No closing ceremony.

## Blocker Catalog

When a blocker occurs in any stage, record the narrowest matching blocker, move to the next runnable sub-requirement, and only pause the entire requirement when all sub-requirements are blocked.

### Requirement Breakdown Blockers

| Blocker | Trigger |
|---|---|
| `blocked_missing_requirement` | A critical business fact is missing from the source |
| `blocked_requirement_conflict` | Two approved sources contradict each other |
| `blocked_dependency` | An upstream sub-requirement is not yet ready |

### UI Truth Mapping Blockers

| Blocker | Trigger |
|---|---|
| `blocked_missing_design` | Required visual carrier is missing from design evidence |
| `blocked_requirement_figma_conflict` | Requirement and visual truth disagree irreconcilably |
| `blocked_figma_conflict` | Design evidence contradicts itself across providers |
| `blocked_missing_state_code` | A final screen state lacks structured frame evidence |
| `blocked_missing_visual_truth` | Missing default state, row composition, parent shell, or key asset |
| `blocked_verification_failure` | Executable node cannot be validated from evidence |

### Spec Kit & Implementation Blockers

| Blocker | Trigger |
|---|---|
| `blocked_spec_mismatch` | Official spec output conflicts with governed truth |
| `blocked_dependency_slice` | Upstream slice not yet merged |
| `blocked_merge_conflict` | Rebase/integration failed |
| `blocked_verification_failure` | Tests, review, or visual acceptance failed after auto-fix |

### Blocker Recovery

When a blocker is entered, update the sub-requirement's entry in `status.json`:
```json
{ "status": "blocked_missing_design", "detail": "Figma file lacks the confirmation dialog frame", "blocked_from_status": "acceptance_frozen", "blocker_scope": "slice_local", "resume_target_status": "acceptance_frozen", "notes": null }
```

When the user resolves the blocker, resume from `resume_target_status`.

**Narrowest-blocker rule:** always choose the most specific blocker. Prefer `blocked_missing_state_code` over `blocked_missing_design`. Prefer `blocked_requirement_figma_conflict` over `blocked_missing_visual_truth`. Never promote a slice-local blocker to requirement-wide unless every runnable queue item across all slices is blocked.

## Pause Points

Only two explicit pauses:
1. **After breakdown decision** — confirm the split plan (or skip) with the user
2. **After tasks_ready** — confirm before starting implementation

All other transitions are automatic.

## API Policy

API docs are passed directly to implementation as reference material. There is no separate API contract mapping stage. API gaps are recorded as `integration_deferred` — they do not block UI mapping or page-state implementation. Only block when missing API truth prevents identifying the visual carrier itself.

## Non-UI Sub-Requirements

Non-UI sub-requirements (`contains_infra_only: true` or `contains_page_states: false`):
- Skip UI Truth Mapping (no `acceptance_frozen` gate).
- Proceed directly from `split_ready` to Spec Kit Pipeline.
- Skip visual acceptance gate — merge after code review and verification.
