# Handoff Table

Each stage has exactly one legal next action. Do not improvise jumps. Actions are abstract; concrete tooling follows [framework-adaptation.md](framework-adaptation.md). Kit-owned skills (`requirement-breakdown`, `ui-truth-mapping`) keep their names.

| Current completion state | Unique next action | Forbidden |
|--------------------------|--------------------|-----------|
| Split decision pending | User confirms → `requirement-breakdown` or skip single-slice package | `ui-truth-mapping`, `spec`/`plan`/`tasks` |
| `split_ready` + light audit with `ui_truth_mode=figma` or `runtime-baseline` | CP-UI pause → user authorizes controlled visual implementation | Production edits or `ui-truth-mapping` dispatch before approval |
| CP-UI confirmed | Resolve the user-approved workspace, then run `ui-truth-mapping` (TDD + golden + review) | Treat Stage 2 as implementation-free mapping, or treat CP-UI as worktree consent |
| `split_ready` + light audit with `ui_truth_mode=none` or `existing` | `solution-design` when `design_mode=light` or `full`; otherwise `spec` | Require a UI gate for an existing/no-truth slice |
| `acceptance_frozen` (validator OK) | `solution-design` according to `design_mode` | `spec` before the solution-design gate is satisfied |
| Solution design gate satisfied (`design_mode=none`, or `design_approved: true` for `light`/`full`) | `spec` → `plan` → `tasks` | Business code before `tasks_ready` |
| All executable subreqs at `tasks_ready` | CP-001 pause → user confirms | Silent entry to development |
| CP-001 confirmed | Stage 4: `implement` | Parallel implementers on same slice files |
| Slice implementation complete | `finish` → set `merged` | Subagent merge or gate promotion |
| All subreqs `merged` | CP-ARCHIVE pause → `archive` (freeze immutable snapshot) | Editing archived artifacts in place |

## Status → next action mapping (for reconcile)

| Subreq status | ui_truth_mode | design_mode / approval | Next action |
|---------------|----------------|----------------------|-------------|
| `draft` | any | any | `requirement-breakdown` |
| `split_ready` | `figma` or `runtime-baseline` | any | Await CP-UI; after confirmation → `ui-truth-mapping` |
| `split_ready` | `none` or `existing` | `none` | `spec` |
| `split_ready` (after any enabled UI truth gate) | any | `light`, `design_approved=false` | `solution-design` → automatic gate satisfaction |
| `split_ready` / `acceptance_frozen` | any | `full`, `design_approved=false` | `solution-design` → CP-DESIGN |
| `split_ready` / `acceptance_frozen` | any | `full`, `design_approved=true` | `spec` |
| `spec_ready` | any | gate satisfied | `plan` |
| `plan_ready` | any | gate satisfied | `tasks` |
| `tasks_ready` | any | gate satisfied | (await CP-001; reconcile emits `implement` after confirm) |
| `in_dev` | any | gate satisfied | `implement` |
| `visual_acceptance_passed` | `figma` or `runtime-baseline` | gate satisfied | `finish` |
| `merged` | any | any | `archive` (freeze `archive/<ISO-ts>/` + `MANIFEST.json`, set `archived`) |
| `archived` | any | any | none |
| `blocked_*` | any | any | `NEXT_ACTION=none`; resolve blocker; continue other runnable subreqs |

## Solution-design approval

- Set `design_approved: true` after the required solution-design artifact is complete: `design_mode=light` after the AI self-review, or `design_mode=full` only after an explicit user approval. Keep it `false` for `design_mode=none`.
- For `design_mode=light`, record the short solution-design artifact and satisfy the gate without CP-DESIGN. For `design_mode=none`, do not create `design.md`.
- Store only a short pointer in `notes`; the canonical artifact remains `design.md` when required.
- Do not enter `spec`/`plan`/`tasks` while a `design_mode=full` gate is pending.
