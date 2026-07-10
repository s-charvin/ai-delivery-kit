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
7. Emit `RUNTIME_MODE`, `RUNNABLE`, `BLOCKED`, `NEXT_SKILL`, `NEXT_SUBREQ`.

## Runtime mode resolution

| Mode | Condition |
|------|-----------|
| `completed` | All executable subreqs are `merged` |
| `bootstrap` | Missing/incomplete `status.json` or no sub_requirements |
| `confirm_to_dev` | `current_checkpoint=CP-001` and user intent is proceed to dev |
| `blocker_recovery` | `current_checkpoint=CP-002` and blocker cleared |
| `resume` | At least one runnable or unresolved item; no blocking checkpoint |

## Truth hierarchy

1. `.ai-delivery/requirements/<req-id>/status.json` and governed artifacts
2. `reconcile-delivery.py` output
3. `todo.md` execution panel (rewrite headers if drift)

## User entry mapping

| User intent | Action |
|-------------|--------|
| New requirement + sources | reconcile → `bootstrap` or `resume` |
| Continue orchestrating | reconcile → `resume` (unless checkpoint active) |
| tasks_ready, continue to dev | reconcile → require CP-001 + all `tasks_ready` → `confirm_to_dev` |
| Blocker resolved | reconcile → CP-002 → `blocker_recovery` |

## Runnable queue

A runnable item can advance safely under current governed truth without inventing facts. Examples: Figma evidence capture, page shell, local state skeletons, navigation flow, mock wiring, read-only paths.

API gaps alone do not trigger CP-002 if UI truth capture or safe partial development can continue.
