---
name: ai-delivery-orchestrator
description: Use when a requirement document needs governed end-to-end delivery through Figma UI contracts, Spec Kit, and merge gates. Use as the single entry when `.ai-delivery` state exists or the user provides a new requirement doc.
---

# AI Delivery Orchestrator

Single entry for requirement → implementation. Leaf skills (`requirement-breakdown`, `ui-truth-mapping`) are pure tools — no pipeline awareness. This skill owns state, gates, blockers, and handoffs.

```
Requirement → [Breakdown?] → UI Truth → Design → Spec Kit → SDD Implementation → Merge
```

## Pipeline

| Stage | Skill | Gate |
|-------|-------|------|
| 1 | `requirement-breakdown` + light audit | `split_ready` |
| 2 | `ui-truth-mapping` (UI only) | `acceptance_frozen` |
| 3a | `superpowers:brainstorming` (design) | `design_approved` |
| 3b | `speckit-specify` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | Superpowers SDD suite | `visual_acceptance_passed` → `merged` |

Stage details: [references/stage-breakdown.md](references/stage-breakdown.md), [stage-ui-truth.md](references/stage-ui-truth.md), [stage-design-and-speckit.md](references/stage-design-and-speckit.md), [stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md), [stage-implementation.md](references/stage-implementation.md).

## State model

```
draft → split_ready → acceptance_frozen → spec_ready → plan_ready → tasks_ready → in_dev → visual_acceptance_passed → merged
```

Non-UI subreqs skip `acceptance_frozen` and `visual_acceptance_passed`.

Truth lives in `.ai-delivery/requirements/<req-id>/status.json`. Copy [templates/status-template.json](templates/status-template.json) verbatim — never regenerate structure from memory. Execution panel: [templates/todo-template.md](templates/todo-template.md) (not source of truth).

| Field | Purpose |
|-------|---------|
| `status` | Current state or `blocked_*` |
| `ui_bearing` | `true` / `false` / `null` — whether slice owns UI surfaces |
| `design_approved` | User approved brainstorming design |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | Resume target after blocker cleared |

## Reconcile first

On every resume or continue, run reconcile before trusting `todo.md`:

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

Rules: [references/reconcile-rules.md](references/reconcile-rules.md).

## Handoff table

Each stage has one legal next skill. Full table: [references/handoff-table.md](references/handoff-table.md).

| Done | Next |
|------|------|
| `split_ready` + audit (UI) | `ui-truth-mapping` |
| `split_ready` + audit (non-UI) | `superpowers:brainstorming` |
| `acceptance_frozen` | `superpowers:brainstorming` |
| `design_approved` | `speckit-specify` |
| All `tasks_ready` + CP-001 | Stage 4 SDD |
| Slice done | `finishing-a-development-branch` |

## Pause points (3)

1. After split/skip decision — confirm with user
2. After brainstorming design — CP-DESIGN, explicit approval before `speckit-*`
3. After `tasks_ready` — CP-001, confirm before development

## Hard boundary

- Do not move workflow truth out of `.ai-delivery`.
- Do not require the user to pick low-level skills on the normal path.
- Do not let UI subreqs enter `speckit-*` before `acceptance_frozen`.
- Do not let UI slices claim `merged` before `visual_acceptance_passed`.
- Do not promote slice-local blockers to requirement-global while any runnable item exists.
- Gate / blocker / status / merge decisions never go to subagents. Leaf skills may use subagents per their own rules (`ui-truth-mapping` per-unit, Stage 4 per SDD).
- Do not invoke `writing-plans` or write design docs under `docs/superpowers/` during orchestrator design mode; store design summary in subreq `notes`.
- Do not fork official `speckit-*` skills.
- Do not set `acceptance_frozen` until `scripts/validate-ui-contract.py` exits 0 for every UI contract.
- Do not set `merged` for UI work without prior `acceptance_frozen` + `visual_acceptance_passed` + passing contracts.
- Edit one file at a time during implementation; rebase worktrees (no merge commits).

## Status transition gates

| Target | Requirement |
|--------|-------------|
| `acceptance_frozen` | All contracts pass `validate-ui-contract.py` |
| `spec/plan/tasks_ready` (UI) | Valid prior `acceptance_frozen`; contracts still pass |
| `merged` (UI) | `acceptance_frozen` + `visual_acceptance_passed` + contracts pass |

## Split decision

**Skip** when ALL: single screen, no shared state, one developer, no cross-cutting rules, doc under ~300 words.

**Split** when ANY: 2+ screens, shared state, multi-developer coordination, cross-feature infrastructure.

State decision with reasoning, then proceed. Details: [references/stage-breakdown.md](references/stage-breakdown.md).

## Light audit (not brainstorming)

After `split_ready`, main session runs inline 4-check audit per subreq (gaps, conflicts, states, permissions). Critical issues → blockers; otherwise append to `notes`. Do not invoke `superpowers:brainstorming` here.

## Stage 4 (summary)

Default: `subagent-driven-development` — sequential tasks, fresh subagent each, TDD inside. `dispatching-parallel-agents` only for independent non-overlapping test/bug domains. Never parallel implementers on the same slice files.

Chain: `using-git-worktrees` → SDD → `requesting-code-review` → visual acceptance (UI) → `verification-before-completion` → full test → `finishing-a-development-branch`.

Full runbook: [references/stage-implementation.md](references/stage-implementation.md).

## Blockers

Narrowest blocker wins; continue safest runnable work first. On validator failure use `blocked_verification_failure`. Catalog: [references/blocker-catalog.md](references/blocker-catalog.md).

## API policy

API docs pass directly to Spec Kit and implementation. Gaps → `integration_deferred` in notes; they do not block UI mapping or shell work.

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

`bootstrap` | `resume` | `confirm_design` | `confirm_to_dev` | `blocker_recovery` | `completed`

Checkpoints: CP-DESIGN (design approval), CP-001 (pre-dev), CP-002 (hard blocker, only when no runnable items remain).

## Completion

All executable subreqs `merged` → requirement complete. No closing ceremony.
