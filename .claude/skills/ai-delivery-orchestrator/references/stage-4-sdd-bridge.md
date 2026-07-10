# Stage 4: SDD Bridge

Maps orchestrator Stage 4 to the Superpowers SDD suite and `.ai-delivery` progress artifacts.

## When to run

After CP-001 user confirmation, when reconcile emits `RUNTIME_MODE=confirm_to_dev` and `NEXT_SKILL=using-git-worktrees`.

**Do not dispatch implementation subagents before CP-001 is confirmed.**

## tasks.md → SDD task brief

For each task row in `tasks.md`:

| tasks.md field | SDD mapping |
|----------------|-------------|
| Task title / ID | Subagent prompt headline |
| Scope / files | Allowed edit surface for one-file-at-a-time rule |
| Dependencies | Sequential order inside `subagent-driven-development` |
| Acceptance notes | TDD success criteria via `test-driven-development` |

One SDD cycle per task: fresh subagent → implement → dual review (`requesting-code-review`) → mark task done in ledger.

## progress.md ↔ SDD ledger

Append to `.ai-delivery/requirements/<req-id>/progress.md`:

- completed task IDs from `tasks.md`
- subagent session notes (blockers, deferred integration)
- review outcomes

`progress.md` is a compaction aid only. On resume, reconcile from `status.json` and on-disk artifacts — never promote gates from progress alone.

## Dual-stage review

1. **Per-task review** — `requesting-code-review` after each SDD task; auto-fix once before user escalation.
2. **Pre-merge review** — full slice review after all tasks; then visual acceptance (UI) and `verification-before-completion`.

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
