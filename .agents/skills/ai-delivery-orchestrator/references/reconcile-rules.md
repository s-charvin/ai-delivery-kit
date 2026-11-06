# Reconcile Rules

Run reconcile before trusting `todo.md` on every resume or continue.

## Command

```sh
ai-delivery context --project . --req <req-id> --subreq <subreq-id> --role recovery --format json
ai-delivery check --project . --req <req-id> --subreq <subreq-id> --intent <intent> --to <target-status> --format json
```

Use the installed `ai-delivery` program. Project resources contain no executable core. Select each relevant slice explicitly; no project-local script fallback exists.

## Reconciliation contract

1. Re-read `status.json`, governed artifacts, and the dependency graph.
2. Re-check contract validators for the current status.
3. Classify every blocker by `blocker_scope`.
4. Do not re-run a stage whose current guards and evidence are valid.
5. Reopen the narrowest action when evidence is absent or stale. A missing or
   stale `design_review` hash reopens `solution-design`.
6. Keep blocked slices in the queue and continue any independent runnable slice.
7. Read the scoped JSON `allowed`, `snapshot_id`, `checks`, and `diagnostics`; derive the human-readable queue from current canonical status. The CLI does not emit `RUNTIME_MODE`, `CHECKPOINT`, `RUNNABLE`, `BLOCKED`,
   `BLOCKER_SCOPES`, `NEXT_ACTION`, and `NEXT_SUBREQ`.

Schema 2.0 actions are `solution-design`, `implement`, `finish`, and `archive`,
plus kit-owned skills. Do not emit or recreate `spec`, `plan`, or `tasks`
actions. Unsupported schemas, including terminal entries, stop dependent routing.
Report actual/required formats and both user choices in [version-upgrade.md](version-upgrade.md).
Never fabricate review evidence or execute migration/reset automatically.

## Runtime mode resolution

| Mode | Condition |
|------|-----------|
| `completed` | All executable subreqs are `archived` |
| `closing` | All executable subreqs are `merged` and none are `archived` → `CHECKPOINT=CP-ARCHIVE`, `NEXT_ACTION=archive` |
| `bootstrap` | Missing/incomplete `status.json` or no sub-requirements |
| `confirm_ui` | A `split_ready` `figma`/`runtime-baseline` slice needs Stage 2 production-code authorization and nothing else is runnable → `CHECKPOINT=CP-UI`, `NEXT_ACTION=none` |
| `confirm_solution_design` | A slice has `user_decision_required=true`, its current design lacks a valid human review, and nothing else is runnable → `CHECKPOINT=CP-DESIGN`, `NEXT_ACTION=none` |
| `blocker_recovery` | `current_checkpoint=CP-002` or only blocked items remain |
| `resume` | At least one item is runnable; a pending CP-DESIGN may remain visible while an independent slice proceeds |

There is no development-confirmation runtime mode. A dependency-ready
`design_ready` slice routes directly to `implement`.

## Checkpoint validity

Checkpoints are current credentials, not history:

- `ui-truth-mapping` requires a current `split_ready` `figma` or
  `runtime-baseline` slice plus explicit CP-UI authorization. CP-UI does not
  authorize a worktree.
- CP-DESIGN applies only to a named material user decision and the exact current
  `design.md` bytes. It authorizes implementation inside the approved scope.
- A stale checkpoint never bypasses a failed guard. Re-derive routing from
  governed truth.

## Truth hierarchy

1. `.ai-delivery/requirements/<req-id>/status.json` and governed artifacts
2. `ai-delivery check` output
3. `todo.md` execution panel, rewritten when it drifts

## User entry mapping

| User intent | Action |
|-------------|--------|
| New requirement + sources | reconcile → `bootstrap` or `resume` |
| Continue orchestrating | reconcile → next runnable action |
| UI truth capability pending authorization | CP-UI → `confirm_ui`; after confirmation dispatch `ui-truth-mapping` |
| Material design decision pending | CP-DESIGN → update and hash-bind `design.md`; then route that slice to `implement` |
| Blocker resolved | reconcile → CP-002 recovery |

## Runnable queue

A runnable item can advance without inventing facts. Dependencies and explicit
blockers constrain ordering; an unrelated slice awaiting design or user input
does not. Before CP-UI, enabled UI-truth production work is not runnable.
`ui_truth_mode=existing` uses ordinary behavior and semantic work without CP-UI.
API gaps do not trigger CP-002 when safe independent work can continue.
