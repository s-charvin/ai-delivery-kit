---
name: ui-interaction-design
description: Use when a sub-requirement already has verified requirement and Figma mapping artifacts and needs a source-bounded interaction contract, micro-interaction assumptions, or escalation of missing interaction truth before implementation or Spec Kit planning.
---

# UI Interaction Design

Project-local workflow skill for converting governed requirement slices plus verified design mappings into an executable interaction contract inside the host repository.

## Overview

Use this skill after `ui-requirement-mapping` when a sub-requirement already has requirement truth, mapping truth, and supporting governed artifacts in place. This stage writes `interaction-design.md`, updates `decisions.md` when assumptions or escalations are needed, and preserves the upstream mapping and bridge contract instead of rewriting it from memory.

## Hard Boundary

- Do not invent business flow or page structure.
- Do not add new fields, steps, dialogs, permissions, or page transitions.
- Do not label an assumption as if it were original Requirement or Figma fact.
- Do not overwrite `figma-mapping.md` or `traceability.json` because an interaction contract prefers a different design.
- Do not delete later-stage bridge or Spec Kit references when they already exist.
- Do not hand-edit blocked states to look recovered.

If interaction truth cannot be resolved from Requirement, `figma-mapping.md`, and trusted design evidence without changing business meaning, stop and escalate instead of filling the gap by intuition.

## Use This Skill For

- Turning verified Requirement and Figma mapping evidence into an executable interaction contract
- Defining source-backed user actions, feedback, states, and transitions
- Recording bounded `assumed_micro_interaction` only inside the allowed boundary
- Escalating missing interaction truth before implementation or Spec Kit planning

## Do Not Use This Skill For

- Requirement splitting
- Figma node mapping
- Product redesign
- New business-logic invention
- Implementation code or task planning

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Interaction Design Template](../common/templates/interaction-design-template.md)
- [Allowed Assumptions](references/allowed-assumptions.md)
- [State Checklist](references/state-checklist.md)

Also read the existing `traceability.json` because it is a first-class governed artifact, not disposable sidecar context.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`

### Expected Supporting Inputs

- `traceability.json`
- `status.json`
- existing `decisions.md`

### Optional Inputs

- Figma comments
- prototype flows
- existing interaction conventions
- component behavior constraints

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or still too ambiguous, stop and hand the work back to `requirement-breakdown`.
- Prefer starting from `figma_mapped`; if the sub-requirement is still unmapped or blocked and the user did not ask for repair work, stop instead of pretending interaction design is normal.
- If `figma-mapping.md` is missing or not screenshot-backed, stop and hand the work back to `ui-requirement-mapping`.
- If `traceability.json` is missing or inconsistent with the visible mapping truth, repair or escalate that governed contract before claiming `interaction_ready`.
- If only micro-interaction detail is missing, continue and record `assumed_micro_interaction`.
- If the missing detail changes business meaning, stop and block instead of assuming.

## Output Goal

Produce an interaction contract that developers can consume directly while preserving upstream mapping truth. The output must preserve:

- a source-bounded `interaction-design.md`
- updates to `decisions.md` when assumptions, blockers, or revalidation notes appear
- explicit labels for `Source: Requirement`, `Source: Figma`, `Source: Existing Pattern`, and `Assumption: Micro Interaction`
- the existing `traceability.json` bridge context, including `spec_kit_refs` when present

## Default Output Paths

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── interaction-design.md
├── decisions.md
├── status.json
└── traceability.json
```

## Workflow

### 1. Confirm the upstream mapping contract

- Read `requirement-slice.md`, `figma-mapping.md`, `traceability.json`, `status.json`, and `decisions.md` before drafting any interaction contract.
- Confirm that the interaction work still matches the current sub-requirement scope and the verified mapping output.
- Prefer to start from `figma_mapped`; if the mapping is stale, blocked, or unverified, stop and hand the work back upstream.

### 2. Extract source-backed interaction facts

- Derive interaction facts from Requirement truth, Figma mapping truth, comments, prototype flows, and already-approved patterns.
- Label each fact as `Source: Requirement`, `Source: Figma`, `Source: Existing Pattern`, or `Assumption: Micro Interaction`.
- Keep explicit separation between source-backed behavior and bounded assumptions.

### 3. Write `interaction-design.md`

- Use `../common/templates/interaction-design-template.md`.
- Cover interaction goal, entry conditions, user actions, system feedback, success, empty, loading, error, and disabled states, permission or visibility impacts, navigation or local state changes, motion and transition notes, and open escalations.
- Keep the document executable for downstream implementation without redesigning the product.

### 4. Bound assumptions aggressively

- Record `assumed_micro_interaction` only inside the allowed boundary from `references/allowed-assumptions.md`.
- If an assumption would change business meaning, add a new branch, add a new screen step, or redefine permissions, stop and escalate instead of writing it as interaction truth.
- Distinguish clearly between missing interaction detail and missing product requirement truth.

### 5. Preserve adjacent artifacts

- Do not rewrite `figma-mapping.md` from memory.
- Do not clear or replace `traceability.json`, including existing bridge fields such as `spec_kit_refs`.
- If interaction analysis reveals a mapping or visual-truth gap, record it in `decisions.md` and hand the issue back to `ui-requirement-mapping` or block it, rather than silently fixing the mapping in prose.

### 6. Handle state and blockers conservatively

- Only advance the sub-requirement toward `interaction_ready` when the key interaction states are defined and the remaining assumptions stay inside the allowed micro-interaction boundary.
- If the requirement needs an action but design cannot carry it, block on `blocked_missing_design`.
- If Figma interaction evidence conflicts with requirement truth, block on `blocked_requirement_figma_conflict`.
- If a key business interaction cannot be resolved from current materials, block on `blocked_missing_requirement`.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not bypass recovery through manual edits.
- Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

### 7. Re-audit before handoff

- Re-open `requirement-slice.md`, `figma-mapping.md`, `interaction-design.md`, and `traceability.json`.
- Verify that every important interaction behavior is source-backed or explicitly labeled as `Assumption: Micro Interaction`.
- Verify that no assumption changed business meaning and no upstream mapping truth was overwritten.
- If later bridge context already exists in `traceability.json`, confirm it was preserved.

## State And Blocker Rules

- If the requirement needs an action but design cannot carry it, block on `blocked_missing_design`.
- If Figma interaction evidence conflicts with requirement truth, block on `blocked_requirement_figma_conflict`.
- If a key business interaction cannot be resolved from current materials, block on `blocked_missing_requirement`.
- Do not move the sub-requirement forward as interaction-complete while those blockers remain open.
- Only advance the sub-requirement toward `interaction_ready` when the contract is source-backed and assumption-bounded.

## Hard Constraints

- Do not invent business flow or page structure.
- Do not add new fields, steps, dialogs, permissions, or page transitions.
- Do not move interaction truth into `ai-delivery-admin`.
- Do not label an assumption as if it were original Figma or Requirement fact.
- Keep `assumed_micro_interaction` inside the approved boundary only.
- Do not overwrite `figma-mapping.md` or `traceability.json`.

## Output Standard

Every interaction contract should define:

- source-backed interaction facts
- user actions
- system feedback
- success, empty, loading, error, and disabled states
- permission or visibility effects when they already exist in source truth
- navigation or local state changes
- motion and transition notes
- explicit assumptions and escalations

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing another status or log store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md`, `figma-mapping.md`, and `traceability.json` were read before drafting
- [ ] The sub-requirement was safe to move from `figma_mapped` toward `interaction_ready`
- [ ] Every key interaction fact is labeled by source or by `Assumption: Micro Interaction`
- [ ] All critical states are defined: success, empty, loading, error, and disabled
- [ ] No new business branch, field, step, dialog, permission rule, or page transition was invented
- [ ] `assumed_micro_interaction` stays inside the allowed boundary
- [ ] `figma-mapping.md` and `traceability.json` were preserved rather than overwritten
- [ ] Existing bridge fields such as `spec_kit_refs` remain intact when they already existed
- [ ] Blockers preserve `blocked_from_status` and `resume_target_status`

## Pressure Scenarios

Use these as mental regression tests while writing or updating the interaction contract.

### Scenario 1: Only loading or focus behavior is missing

Expected behavior:

- continue the contract
- record `Assumption: Micro Interaction`
- do not block if business meaning is unchanged

### Scenario 2: Figma implies a confirm dialog that Requirement does not mention

Expected behavior:

- do not invent the dialog as truth
- block on `blocked_requirement_figma_conflict` if the conflict is real
- or escalate the mismatch explicitly

### Scenario 3: The interaction needs a new business decision to proceed

Expected behavior:

- block on `blocked_missing_requirement`
- record the exact unresolved business meaning
- do not patch it with a friendly default

### Scenario 4: `figma-mapping.md` exists, but the executable-node evidence is stale or weak

Expected behavior:

- stop and hand the work back to `ui-requirement-mapping`
- do not write an authoritative interaction contract on top of untrusted mapping evidence

### Scenario 5: `traceability.json` already contains bridge context such as `spec_kit_refs`

Expected behavior:

- preserve those fields
- do not replace `traceability.json`
- do not invent a second bridge artifact

### Scenario 6: An existing team pattern suggests a smoother flow than the source materials support

Expected behavior:

- record it only as `Source: Existing Pattern` or `Assumption: Micro Interaction` when allowed
- do not let convenience override Requirement or Figma truth

## Handoff

Stop after producing the interaction contract and passing the self-check.

If the user wants to continue, hand the downstream stage `interaction-design.md`, `decisions.md`, and the preserved governed sub-requirement package. Do not perform Spec Kit planning or implementation inside this skill unless the user explicitly asks for the next stage.
