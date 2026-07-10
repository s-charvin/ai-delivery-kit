# Handoff Table

Each stage has exactly one legal next skill. Do not improvise jumps.

| Current completion state | Unique next skill | Forbidden |
|--------------------------|-------------------|-----------|
| Split decision pending | User confirms → `requirement-breakdown` or skip single-slice package | `ui-truth-mapping`, `speckit-*` |
| `split_ready` + light audit OK (UI-bearing) | `ui-truth-mapping` | `speckit-*`, implementation |
| `split_ready` + light audit OK (non-UI) | `superpowers:brainstorming` (design mode) | Skip design approval |
| `acceptance_frozen` (validator OK) | `superpowers:brainstorming` (design mode) | `speckit-*` before design approval |
| Design approved (`design_approved: true`) | `speckit-specify` → `speckit-plan` → `speckit-tasks` | Business code before `tasks_ready` |
| All executable subreqs at `tasks_ready` | CP-001 pause → user confirms | Silent entry to development |
| CP-001 confirmed | Stage 4: `using-git-worktrees` + `subagent-driven-development` | Parallel implementers on same slice files |
| Slice implementation complete | `finishing-a-development-branch` → set `merged` | Subagent merge or gate promotion |

## Status → next skill mapping (for reconcile)

| Subreq status | ui_bearing | design_approved | Next skill |
|---------------|------------|-----------------|------------|
| `draft` | any | any | `requirement-breakdown` |
| `split_ready` | true | any | `ui-truth-mapping` |
| `split_ready` | false | false | `superpowers:brainstorming` |
| `split_ready` | false | true | `speckit-specify` |
| `acceptance_frozen` | true | false | `superpowers:brainstorming` |
| `acceptance_frozen` | true | true | `speckit-specify` |
| `spec_ready` | any | true | `speckit-plan` |
| `plan_ready` | any | true | `speckit-tasks` |
| `tasks_ready` | any | true | (await CP-001 or Stage 4) |
| `in_dev` | any | true | `subagent-driven-development` |
| `visual_acceptance_passed` | true | true | `finishing-a-development-branch` |
| `merged` | any | any | none |
| `blocked_*` | any | any | resolve blocker first; continue other runnable subreqs |

## Design approval

- Set `design_approved: true` on the sub-requirement entry only after `superpowers:brainstorming` design session and explicit user approval.
- Store design summary in `notes`.
- Do not enter `speckit-*` while `design_approved` is false.
