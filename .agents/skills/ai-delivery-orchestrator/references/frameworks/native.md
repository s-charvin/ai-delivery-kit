# Framework Guide: Native Tier

Use the native tier whenever an external framework is absent, unsuitable for the
current action, or unable to honor canonical artifact paths. It is a complete
fallback, not a lower-quality document pipeline.

## Artifact containment

- Persist process/governance artifacts only at paths declared by
  `.ai-delivery/meta/project-binding.json`.
- Do not create repository-root design, plan, review, checklist, or session
  files. Host-tree writes are limited to production source, project-native
  tests, official previews, and runtime assets.
- Resolve workspaces through [../workspace-policy.md](../workspace-policy.md).
- Run the artifact-boundary audit from
  [../framework-adaptation.md](../framework-adaptation.md) before advancing a
  gate.

## `solution-design`

Run inline in the main session:

1. Read the requirement slice, applicable global rules, dependency graph,
   project architecture, API evidence, and enabled UI truth evidence.
2. Instantiate `design-template.md` in the user's current conversation language.
3. Record scope, `B-###` behavior, `AC-###` acceptance, traceability, material
   solution decisions, and the applicable state-flow depth. Runtime Coverage
   remains in `ui-truth-index.json`.
4. With `user_decision_required=false`, self-review and hash-bind
   `design_review.review_mode=self`. With `true`, use CP-DESIGN and bind the
   user's approval as `review_mode=human`.
5. Set `design_ready` only after the current file hash, review metadata, and all
   contract validators pass.

Do not create `spec.md`, `plan.md`, or `tasks.md`. Derive implementation units
later from the current contract and codebase.

## `implement`

1. Resolve the approved workspace; reuse the Stage 2 workspace for enabled UI
   truth.
2. Derive the next coherent batch of execution units from `design.md`, dependencies,
   current code, tests, and optional `progress.md`.
3. Run TDD: observe a relevant failing test, implement the minimum behavior,
   refactor while green.
4. Run the [closed review loop](../stage-implementation.md#review-loop-closed-loop)
   against the coherent integrated batch and design contract until clean or the configured
   budget is exhausted.
5. Record only cross-session recovery facts in optional `progress.md`; do not
   turn it into a second plan.

## `finish`

1. Preserve final project analysis and test scope. Validate and reuse matching evidence under the Stage 4 reuse rules; run missing or invalidated checks, not the same successful suite again merely for finish.
2. Complete scope-appropriate visual and motion acceptance for enabled UI truth.
3. Write localized `verification.md` with the required stable markers.
4. Rebase without merge commits, integrate, and set `merged` only while all
   gates remain valid.

## Traceability and boundaries

Record the canonical design path/hash and the native reasoning method in
`traceability.json` under `source_index.design`. Never emit schema 2.0
`spec_refs` or spec/plan/task artifact entries.

Gate, blocker, status, and merge decisions stay with the main orchestrator. A
later framework installation may change the method for new actions, but it does
not change the canonical artifact model.

Use the Stage 4 subagent and evidence-reuse policies: installed agents do not mandate delegation or duplicate full checks. Keep one implementer by default, independent integrated-batch review, and scoped re-review after fixes.
