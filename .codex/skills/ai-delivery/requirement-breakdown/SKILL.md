# Requirement Breakdown

Project-local workflow skill for turning top-level requirement material into tracked sub-requirement packages inside the host repository.

## Purpose

Use this skill when a finalized or near-final requirement source needs to be split into:

- `breakdown-summary.md`
- `global-rules.md`
- `dependency-graph.json`
- per-sub-requirement `README.md`
- per-sub-requirement `requirement-slice.md`
- per-sub-requirement `dependency.json`
- per-sub-requirement `status.json`
- per-sub-requirement `traceability.json`
- per-sub-requirement `decisions.md`

All outputs stay inside `/Users/charvin/Projects/Codex/.ai-delivery/requirements/`.

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Requirement Slice Template](../common/templates/requirement-slice-template.md)
- [Checklist](references/checklist.md)
- [Sub-Requirement README Template](references/subreq-readme-template.md)

## Inputs

- required: path to top-level requirement material
- optional: API contract, codebase context, design system notes, business-rule supplements

## Workflow

1. Read the top-level requirement material and confirm the target requirement folder under `.ai-delivery/requirements/`.
2. Reuse the shared references and templates from `../common/` instead of inventing new artifact shapes.
3. Extract shared rules into `global-rules.md`.
4. Create `breakdown-summary.md` and `dependency-graph.json`.
5. Create one folder per sub-requirement with `README.md`, `requirement-slice.md`, `dependency.json`, `status.json`, `traceability.json`, and `decisions.md`.
6. Keep all artifact truth in the business project's `.ai-delivery/requirements/` tree.
7. Use the separate admin support surface for governed logging, blocker recording, or status transitions when it is available.

## State And Blocker Rules

- Only move a sub-requirement to `split_ready` when the slice is specific enough for downstream UI mapping.
- If the requirement source conflicts with itself or another approved requirement source, block on `blocked_requirement_conflict`.
- If a critical business fact is missing, block on `blocked_missing_requirement`.
- If the boundary is still ambiguous, write the draft plus open questions and stop short of `split_ready`.

## Hard Constraints

- Work only inside `.ai-delivery/requirements/`.
- Do not invent product truth.
- Do not generate Spec Kit spec, plan, or tasks here.
- Do not bind Figma nodes here.
- Do not move workflow truth into `ai-delivery-admin`.

## Output Standard

Every sub-requirement package must preserve:

- clear scope
- explicit dependencies
- acceptance signals
- open questions
- source requirement references

If governed admin support is unavailable, document that missing dependency in local notes or `decisions.md`, but keep artifact truth in `.ai-delivery/`.
