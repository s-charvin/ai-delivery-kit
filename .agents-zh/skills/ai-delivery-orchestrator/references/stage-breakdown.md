# Stage 1: Requirement Breakdown

## When to run

- Auto-decision says "split", or any sub-requirement is at `draft` with unresolved scope.

## Prepare inputs

- Read the requirement document.
- Output directory: `.ai-delivery/requirements/<req-id>/`.

## Run `requirement-breakdown`

Feed the requirement document path. It produces sub-requirements with `requirement-slice.md`, `dependency.json`, and the artifact set.

## After completion

- For each sub-requirement: if scope has complete source_ref coverage, normalized statements, and clear dependencies → set `split_ready`. If uncertain → leave `draft`.
- Set `ui_bearing` on each subreq entry: `true` if the slice owns page/screen states; `false` if infra-only or no UI surfaces.
- Initialize `status.json`: copy `templates/status-template.json` verbatim, then fill `requirement_id`, sub-requirement entries, and statuses. Preserve all `_`-prefixed metadata keys.
- Record dependency graph at `.ai-delivery/requirements/<req-id>/dependency-graph.json`.

## Light audit checklist (inline — do not invoke brainstorming)

For each `split_ready` sub-requirement, main session outputs four checks:

1. **Gaps** — missing critical business facts?
2. **Conflicts** — contradictions with `global-rules.md` or other slices?
3. **States** — missing error, empty, loading, or permission boundaries?
4. **Permissions** — auth boundaries clear?

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
