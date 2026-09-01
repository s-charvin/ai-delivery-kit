# Stage 1: Requirement Breakdown

## When to run

- Auto-decision says "split", or any sub-requirement is at `draft` with unresolved scope.

## Prepare inputs

- Read the requirement document and every explicitly supplied supporting artifact. Inspect content before assigning a semantic role; filenames, extensions, folders, and labels such as `draft` or `pending` do not prove that a source is only copy, localization, reference material, or safe to omit.
- Output directory: `.ai-delivery/requirements/<req-id>/`.

## Run `requirement-breakdown`

Feed the requirement document and supporting-source paths. It produces sub-requirements with `requirement-slice.md`, `dependency.json`, and the artifact set.

## After completion

- For each sub-requirement: if scope has complete source_ref coverage, normalized statements, and clear dependencies → set `split_ready`. If uncertain → leave `draft`.
- Set `ui_truth_mode` and `design_mode` on each subreq entry during the capability audit:
  - `ui_truth_mode`: `none` for no visible surface, `existing` for behavior/semantic changes on an existing visual surface, `runtime-baseline` for new visible UI without stable Figma truth, or `figma` when stable Figma evidence exists.
  - `design_mode`: `none` for changes with no solution-design decisions, `light` for a bounded design record, or `full` for architecture, data-flow, state-machine, cross-platform, security, or performance decisions requiring approval.
- Keep `ui_bearing` as a consistency field: it is `false` only for `ui_truth_mode=none`, and `true` for the other UI truth modes.
- Initialize `status.json`: copy the structure of `templates/status-template.json`, then fill `requirement_id`, sub-requirement entries, and statuses. Preserve all `_`-prefixed metadata keys and machine values; localize their human-readable descriptive values into the user's current conversation language.
- Record dependency graph at `.ai-delivery/requirements/<req-id>/dependency-graph.json`.

## Light audit checklist (inline — do not run the `solution-design` action)

For each `split_ready` sub-requirement, main session outputs four checks:

1. **Gaps** — missing critical business facts?
2. **Conflicts** — contradictions with `global-rules.md` or other slices?
3. **States** — do all sources agree on reachable states, event-driven transitions, ordering, branches/convergence, loading/error/empty/permission boundaries, persistence, and side effects? Visual evidence being unavailable does not defer non-visual flow rules.
4. **Permissions** — auth boundaries clear?

The audit must reject `split_ready` when a supplied source contains material behavior that is only categorized by document title instead of traced to a slice, global rule, open question, or explicit exclusion with reason. `pending` evidence is recorded as `unknown` where authority is unresolved; it is not silently ignored.

Outcomes:

- Critical gap → `blocked_missing_requirement`
- Critical conflict → `blocked_requirement_conflict`
- No critical issues → append audit findings to `notes`, proceed

## Skip path

When breakdown is skipped, create a minimal single sub-requirement package:

```
.ai-delivery/requirements/<req-id>/
├── requirement.md
├── status.json
└── sub-requirements/<subreq-id>/
    └── requirement-slice.md
```

Do not create a per-subreq `status.json`.

## Pause

Confirm the split plan (or skip decision) with the user before proceeding.
