# Contract-Gated Stage Checklists

## Outward Capability Checklist

1. Requirement and acceptance
2. Capability review
3. One canonical `design.md` contract
4. TDD implementation
5. Fresh-context review
6. Verification and delivery acceptance

## Internal Gates

1. Requirement Gate (`split_ready`)
2. UI Truth Authorization (CP-UI, only `figma` / `runtime-baseline`)
3. UI Truth Freeze (`acceptance_frozen`, only enabled UI truth)
4. Design Contract Gate (`design_ready`; CP-DESIGN only when
   `user_decision_required=true` and the current design lacks a valid
   hash-bound human review)
5. Development (`in_dev`, directly after a dependency-ready design)
6. Visual Acceptance (`visual_acceptance_passed`, only enabled UI truth)
7. Merge (`merged`)
8. In-place Archive (`archived`)

There is no spec/plan/tasks pipeline and no separate development-authorization
checkpoint. `state_flow_required` controls design depth, not human authority.

## UI Truth Notes

- Stage 2 writes a real host-stack component in the user-approved workspace and
  freezes v3 profile/state/scenario/evidence-scope records.
- All ten applicability-gated runtime dimensions must resolve.
- Static preview and motion acceptance are separate. Use deterministic GIF when
  available; otherwise record the reason and defer runtime acceptance.
- Real controls and evidence-backed resources are mandatory. Missing resources
  require an explicit empty/defer/block decision; fabricated data and silent
  fallbacks fail.
- Stage 4 reuses the same workspace and writes schema v2
  `visual-acceptance.json`.

## Review and Verification

- audit empty callbacks, reachable TODOs, navigation conflicts, propagation
  targets, and behavior-contract implementation;
- classify failures as introduced regression, pre-existing baseline,
  environment/tooling failure, or contract/test contradiction;
- verify every indexed scenario and independent per-unit motion acceptance;
- never merge while the latest review round is not clean.

## Checkpoints

- `CP-UI`: authorize controlled Stage 2 production UI work.
- `CP-DESIGN`: resolve a named material product, behavior, resource, or
  experience decision and bind human review to the current design hash.
- `CP-002`: pause only when no safe runnable item remains.
- `CP-ARCHIVE`: confirm in-place archive after all slices merge.
