# Handoff Table

Each stage has one legal next action. Actions are abstract; concrete tooling
follows [framework-adaptation.md](framework-adaptation.md). Kit-owned skills
retain their names.

| Current completion state | Unique next action | Forbidden |
|--------------------------|--------------------|-----------|
| Breakdown boundary is materially ambiguous | Resolve the named user decision, then run `requirement-breakdown` or create the single-slice package | Routine approval for an unambiguous split |
| `split_ready` + `ui_truth_mode=figma` or `runtime-baseline` | CP-UI → user authorizes controlled visual implementation | Production UI edits before CP-UI |
| CP-UI confirmed | Resolve the approved workspace, then `ui-truth-mapping` | Treat CP-UI as worktree consent |
| `split_ready` + `ui_truth_mode=none` or `existing` | `solution-design` | Require a UI gate |
| `acceptance_frozen` | `solution-design` | Bypass frozen visual/motion evidence |
| Current `design.md` has an unresolved material user decision | CP-DESIGN | Treat technical complexity as a human decision |
| Current `design.md` has a valid hash-bound review | `design_ready` → `implement` when dependencies permit | A second development-authorization gate |
| Slice implementation and verification complete | `finish` → `merged` | Merge with a stale design or unclean review |
| All subreqs `merged` | CP-ARCHIVE → `archive` in place | Duplicate canonical artifacts |

## Status to next action

| Subreq status | Capability condition | Next action |
|---------------|----------------------|-------------|
| `draft` | any | `requirement-breakdown` |
| `split_ready` | `figma` or `runtime-baseline` | await CP-UI; after authorization → `ui-truth-mapping` |
| `split_ready` | `none` or `existing` | `solution-design` |
| `acceptance_frozen` | enabled UI truth | `solution-design` |
| `design_ready` | dependencies ready | `implement` |
| `in_dev` | any | `implement` |
| `visual_acceptance_passed` | `figma` or `runtime-baseline` | `finish` |
| `merged` | any | `archive` in place after the closing checkpoint |
| `archived` | any | none |
| `blocked_*` | any | resolve blocker; continue independent runnable slices |

## Design review

- Every active schema 2.0 slice has one canonical `design.md`.
- With `user_decision_required=false`, self-review and bind
  `design_review.review_mode=self` to the exact file SHA-256.
- With `user_decision_required=true`, resolve the named decision through
  CP-DESIGN and bind `review_mode=human` to the approved file SHA-256.
- A file change invalidates the review and returns the slice to
  `solution-design`. It creates a new CP-DESIGN pause only when a material user
  decision remains.
- Store only a short pointer in `notes`; do not create `spec.md`, `plan.md`, or
  `tasks.md`.
