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
- Set `ui_truth_mode` on each subreq entry during the capability audit: `none` for no visible surface, `existing` for behavior/semantic changes on an existing visual surface, `runtime-baseline` for new visible UI without stable Figma truth, or `figma` when stable Figma evidence exists.
- Set `state_flow_required=true` only when the slice introduces or materially changes complex guards, concurrency, stale-result handling, retry/cancel/idempotency, persistence/recovery, or cross-component/cross-screen state ownership. MVI/UDF/Redux/Reducer/Store terminology and ordinary loading/success/failure phases do not trigger it by themselves. Static surfaces and local controls without business rules keep it `false`.
- Set `user_decision_required=true` when the current design version contains a material product, behavior, resource, or experience choice whose authority belongs to the user because governed evidence cannot resolve it. Technical complexity, framework selection, and state-flow depth do not trigger it. Name each decision in `design.md`. The field remains `true` after approval for that design version; a current hash-bound `design_review.review_mode=human` records that the decision is resolved. Set it to `false` only when the current design version contains no user-authority decision.
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

## Decision boundary

Proceed automatically when source coverage supports one unambiguous split or
skip result. Ask the user only when competing boundaries would materially change
scope, ownership, sequencing, or acceptance. Record that choice as a real user
decision; do not create a routine approval checkpoint for a mechanically clear
breakdown.
