# Reconcile Rules

Run reconcile before trusting `todo.md` on every resume or continue.

## Command

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

Bootstrap copies may use `.ai-delivery/scripts/` validators; skill-local path works in the kit repo.

## Steps (script implements; main session verifies)

1. Re-read `status.json` and scan requirement artifacts.
2. Re-check guards (contract validators for post-freeze statuses).
3. Classify every blocker by `blocker_scope`.
4. If a guard is already satisfied, do not re-run the stage.
5. If outputs exist but guard fails, re-run or open narrowest blocker.
6. Keep blocked items in queue; continue later items that do not depend on them.
7. Emit `RUNTIME_MODE`, `CHECKPOINT`, `RUNNABLE`, `BLOCKED`, `BLOCKER_SCOPES`, `NEXT_ACTION`, `NEXT_SUBREQ`. Actions are abstract (`solution-design` / `spec` / `plan` / `tasks` / `implement` / `finish` / `archive`, plus kit-owned skills); map them to the selected framework tier via [framework-adaptation.md](framework-adaptation.md).

## Runtime mode resolution

| Mode | Condition |
|------|-----------|
| `completed` | All executable subreqs are `archived` |
| `closing` | All executable subreqs are `merged` and none are `archived` → `CHECKPOINT=CP-ARCHIVE`, `NEXT_ACTION=archive` |
| `bootstrap` | Missing/incomplete `status.json` or no sub_requirements |
| `confirm_ui` | A `split_ready` slice with `ui_truth_mode=figma` or `runtime-baseline` needs Stage 2 production-code authorization and nothing else is runnable → `CHECKPOINT=CP-UI`, `NEXT_ACTION=none` |
| `confirm_solution_design` | A `design_mode=full` subreq needs solution-design approval and nothing else is runnable → `CHECKPOINT=CP-DESIGN` |
| `confirm_to_dev` | All executable subreqs at `tasks_ready` → `CHECKPOINT=CP-001` |
| `blocker_recovery` | `current_checkpoint=CP-002` or only blocked items remain |
| `resume` | At least one runnable item; no blocking checkpoint. A pending full solution-design approval still surfaces `CHECKPOINT=CP-DESIGN` as a reminder while other runnable work proceeds |

## Checkpoint validity

Checkpoints are credentials, not history. A recorded checkpoint is only valid while its guards still hold:

- `NEXT_ACTION=ui-truth-mapping` requires a current `split_ready` slice with `ui_truth_mode=figma` or `runtime-baseline` and explicit user authorization recorded as `current_checkpoint=CP-UI`. First arrival emits `confirm_ui` with `NEXT_ACTION=none`; a stale CP-UI is discarded after the guard no longer holds.
- `confirm_to_dev` requires all executable subreqs at `tasks_ready` right now. A stale `current_checkpoint=CP-001` left behind after a regression (e.g. a subreq back at `spec_ready`) does not authorize `implement`.
- `NEXT_ACTION=implement` additionally requires the user confirmation to be recorded in `status.json` (`current_checkpoint=CP-001` on top of all-`tasks_ready`). First arrival at all-`tasks_ready` emits `NEXT_ACTION=none` until the user confirms.
- Never treat a recorded checkpoint as a shortcut past a failed guard; re-derive it from current governed truth.

## Truth hierarchy

1. `.ai-delivery/requirements/<req-id>/status.json` and governed artifacts
2. `reconcile-delivery.py` output
3. `todo.md` execution panel (rewrite headers if drift)

## User entry mapping

| User intent | Action |
|-------------|--------|
| New requirement + sources | reconcile → `bootstrap` or `resume` |
| Continue orchestrating | reconcile → `resume` (unless checkpoint active) |
| UI truth capability pending authorization | reconcile → require CP-UI → `confirm_ui`; after confirmation dispatch `ui-truth-mapping` |
| tasks_ready, continue to dev | reconcile → require CP-001 + all `tasks_ready` → `confirm_to_dev` |
| Blocker resolved | reconcile → CP-002 → `blocker_recovery` |

## Runnable queue

A runnable item can advance safely under current governed truth without inventing facts. Before CP-UI, UI truth work is limited to read-only evidence and governance artifacts. Page shells, local state skeletons, navigation flow, mock wiring, and any other production edits for an enabled UI truth capability become runnable only inside the authorized slice worktree. `ui_truth_mode=existing` may proceed with ordinary behavior and semantic work without CP-UI.

API gaps alone do not trigger CP-002 if UI truth capture or safe partial development can continue.
