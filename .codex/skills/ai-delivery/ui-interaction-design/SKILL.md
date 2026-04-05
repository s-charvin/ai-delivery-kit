---
name: ui-interaction-design
description: Use when a sub-requirement already has `requirement-slice.md` and `figma-mapping.md` and needs an executable interaction contract, bounded micro-interaction assumptions, or escalation of missing interaction truth.
---

# UI Interaction Design

Project-local workflow skill for converting requirement slices plus verified design mappings into an executable interaction contract inside the host repository.

## Purpose

Use this skill after `ui-requirement-mapping` when a sub-requirement already has:

- `requirement-slice.md`
- `figma-mapping.md`

This skill produces:

- `interaction-design.md`
- updates to `decisions.md` when assumptions or escalations are needed

All outputs stay inside the matching `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/` folder.

`interaction-design.md` may not exist yet in a newly bootstrapped package. This skill owns the first real write of that file.

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Interaction Design Template](../common/templates/interaction-design-template.md)
- [Allowed Assumptions](references/allowed-assumptions.md)
- [State Checklist](references/state-checklist.md)

## Inputs

- required: `subreq-id`
- required: `requirement-slice.md`
- required: `figma-mapping.md`
- optional: Figma comments, prototype flows, existing interaction conventions

## Workflow

1. Read `requirement-slice.md` and `figma-mapping.md` before drafting any interaction contract.
2. Extract source-backed interaction facts from Requirement and Figma evidence.
3. Write `interaction-design.md` using the shared template.
4. Record `assumed_micro_interaction` only inside the allowed boundary from `references/allowed-assumptions.md`.
5. Distinguish clearly between source-backed facts and limited assumptions.
6. Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

## State And Blocker Rules

- If the requirement needs an action but design cannot carry it, block on `blocked_missing_design`.
- If Figma interaction evidence conflicts with requirement truth, block on `blocked_requirement_figma_conflict`.
- If a key business interaction cannot be resolved from current materials, block on `blocked_missing_requirement`.
- Do not move the sub-requirement forward as interaction-complete while those blockers remain open.

## Hard Constraints

- Do not invent business flow or page structure.
- Do not add new fields, steps, dialogs, permissions, or page transitions.
- Do not move interaction truth into `ai-delivery-admin`.
- Do not label an assumption as if it were original Figma or Requirement fact.
- Keep `assumed_micro_interaction` inside the approved boundary only.

## Output Standard

Every interaction contract should define:

- user actions
- system feedback
- success, empty, loading, error, and disabled states
- navigation or local state changes
- motion and transition notes
- explicit assumptions and escalations

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing another status or log store.
