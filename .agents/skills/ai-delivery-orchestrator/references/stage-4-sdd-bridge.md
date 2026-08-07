# Stage 4: Implementation Bridge

Maps orchestrator Stage 4 (`implement` action) to task-level execution and `.ai-delivery` progress artifacts. Concrete execution style follows the selected tier — [frameworks/superpowers.md](frameworks/superpowers.md) (subagent-driven), [frameworks/ecc.md](frameworks/ecc.md) (agent-driven), or [frameworks/native.md](frameworks/native.md) (inline discipline).

## When to run

After CP-001 user confirmation, when reconcile emits `RUNTIME_MODE=confirm_to_dev` and `NEXT_ACTION=implement`.

**Do not dispatch implementation work before CP-001 is confirmed.**

## tasks.md → task brief

For each task row in `tasks.md`:

| tasks.md field | Execution mapping |
|----------------|-------------------|
| Task title / ID | Implementer prompt headline |
| Scope / files | Allowed edit surface for one-file-at-a-time rule |
| Dependencies | Sequential order across tasks |
| Acceptance notes | TDD success criteria |

One execution cycle per task: fresh context (subagent when the tier supports it) → implement → review → mark task done in ledger.

## progress.md ↔ ledger

Append to `.ai-delivery/requirements/<req-id>/progress.md`:

- completed task IDs from `tasks.md`
- implementer session notes (blockers, deferred integration)
- review outcomes

`progress.md` is a compaction aid only. On resume, reconcile from `status.json` and on-disk artifacts — never promote gates from progress alone.

## Dual-stage review

Both stages run through the [Review loop](stage-implementation.md#review-loop-task-level-closed-loop): implement → fresh-context review → findings become a fix brief → re-review, until clean or the `review_loop.max_rounds` budget is exhausted (then escalate to the user; never auto-merge).

1. **Per-task review** — after each task; append every round's findings and fix summary to `progress.md`.
2. **Pre-merge review** — full slice review after all tasks; then visual acceptance (UI) and the verification step.

## Visual acceptance evidence (UI)

Before setting `visual_acceptance_passed`, write one of:

- `sub-requirements/<subreq-id>/visual-acceptance.md` (checklist + notes), or
- `sub-requirements/<subreq-id>/visual-acceptance/*.png` (screenshots)

`validate-delivery-status.py` weak-checks file presence; it does not parse image content.

## Status chain

```
tasks_ready → (CP-001) → in_dev → visual_acceptance_passed (UI) → merged
```

Non-UI subreqs skip `visual_acceptance_passed`.

## Handoff after slice

See [stage-implementation.md](stage-implementation.md) for PR / babysit finishing steps.
