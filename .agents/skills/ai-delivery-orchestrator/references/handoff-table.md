# Handoff Table

Each stage has exactly one legal next action. Do not improvise jumps. Actions are abstract; concrete tooling follows [framework-adaptation.md](framework-adaptation.md). Kit-owned skills (`requirement-breakdown`, `ui-truth-mapping`) keep their names.

| Current completion state | Unique next action | Forbidden |
|--------------------------|--------------------|-----------|
| Split decision pending | User confirms → `requirement-breakdown` or skip single-slice package | `ui-truth-mapping`, `spec`/`plan`/`tasks` |
| `split_ready` + light audit OK (UI-bearing) | `ui-truth-mapping` | `spec`/`plan`/`tasks`, implementation |
| `split_ready` + light audit OK (non-UI) | `design` | Skip design approval |
| `acceptance_frozen` (validator OK) | `design` | `spec` before design approval |
| Design approved (`design_approved: true`) | `spec` → `plan` → `tasks` | Business code before `tasks_ready` |
| All executable subreqs at `tasks_ready` | CP-001 pause → user confirms | Silent entry to development |
| CP-001 confirmed | Stage 4: `implement` | Parallel implementers on same slice files |
| Slice implementation complete | `finish` → set `merged` | Subagent merge or gate promotion |

## Status → next action mapping (for reconcile)

| Subreq status | ui_bearing | design_approved | Next action |
|---------------|------------|-----------------|-------------|
| `draft` | any | any | `requirement-breakdown` |
| `split_ready` | true | any | `ui-truth-mapping` |
| `split_ready` | false | false | `design` |
| `split_ready` | false | true | `spec` |
| `acceptance_frozen` | true | false | `design` |
| `acceptance_frozen` | true | true | `spec` |
| `spec_ready` | any | true | `plan` |
| `plan_ready` | any | true | `tasks` |
| `tasks_ready` | any | true | (await CP-001; reconcile emits `implement` after confirm) |
| `in_dev` | any | true | `implement` |
| `visual_acceptance_passed` | true | true | `finish` |
| `merged` | any | any | none |
| `blocked_*` | any | any | `NEXT_ACTION=none`; resolve blocker; continue other runnable subreqs |

## Design approval

- Set `design_approved: true` on the sub-requirement entry only after the `design` action session and explicit user approval.
- Store design summary in `notes`.
- Do not enter `spec`/`plan`/`tasks` while `design_approved` is false.
