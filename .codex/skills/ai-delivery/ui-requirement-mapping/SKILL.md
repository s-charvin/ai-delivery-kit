---
name: ui-requirement-mapping
description: Use when a sub-requirement already has governed breakdown artifacts and must be bound to verified Figma evidence, screenshot-backed executable nodes, or visual blockers before interaction design or implementation.
---

# UI Requirement Mapping

Project-local workflow skill for binding a governed sub-requirement slice to verified Figma evidence and producing a 1:1 visual implementation contract inside the host repository.

## Overview

Use this skill after `requirement-breakdown` when a sub-requirement package already exists under `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/`. This stage writes `figma-mapping.md`, updates `traceability.json` in place, and preserves the governed artifact contract created upstream instead of inventing a parallel mapping store.

## Hard Boundary

- Do not invent visual truth.
- Do not add pages, fields, components, states, or business flows.
- Do not treat a node name alone as evidence.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not mark mapping complete without screenshot-backed evidence.
- Do not replace `traceability.json` with a sidecar note or a second bridge artifact.
- Do not delete `interaction-design.md` or other later-stage artifacts when re-running mapping.
- Do not hand-edit blocked states to look recovered.

If trustworthy Figma structure or screenshot evidence is unavailable for required UI, stop and report that this stage cannot complete safely.

## Use This Skill For

- Binding a `requirement-slice.md` to verified Figma evidence
- Producing `figma-mapping.md` before interaction design or implementation
- Updating `traceability.json` with verified nodes, confidence, conflicts, and verification timing
- Surfacing visual blockers, shared nodes, and companion UI without silently broadening business scope

## Do Not Use This Skill For

- Requirement splitting or requirement truth repair
- Interaction contract design
- Final code generation
- Filling missing design evidence by guesswork
- Replacing raw Figma evidence with prose-only descriptions

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Figma Mapping Template](../common/templates/figma-mapping-template.md)
- [Figma Fetch Order](references/figma-fetch-order.md)
- [Mapping Checklist](references/mapping-checklist.md)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` and the raw-evidence boundary under `.ai-delivery/figma-cache/`.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- a Figma file, file id, or node target

### Expected Supporting Inputs

- `traceability.json`
- `status.json`
- existing `decisions.md`

### Optional Inputs

- explicit node list
- exported comments
- token files
- design version hints

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or still not safe for mapping, stop and hand the work back to `requirement-breakdown`.
- Prefer starting from `split_ready`; if the slice is still `draft` or blocked and the user did not ask for repair work, stop instead of pretending mapping is normal.
- If `traceability.json` is missing in a legacy folder, repair only the current governed contract and record that repair in `decisions.md`; do not invent a different JSON shape.
- If cached evidence is missing, stale, or does not cover the required executable node, refresh it using the Figma retrieval order.
- If trustworthy Figma structure or screenshot evidence still cannot be obtained, stop and block rather than mapping from memory.
- If `interaction-design.md` already exists, preserve it and record any required revalidation in `decisions.md` when the mapping changes materially.

## Output Goal

Produce a mapping package that downstream interaction design or implementation can consume directly. The output must preserve:

- a screenshot-backed `figma-mapping.md`
- an updated `traceability.json` with `requirement_refs`, `figma_nodes`, `mapping_type`, `confidence`, `conflicts`, and `last_verified_at`
- existing bridge fields such as `spec_kit_refs` when the repo already carries them
- explicit `required UI`, `companion UI`, `shared nodes`, `missing design evidence`, and conflict capture
- the raw evidence boundary between `.ai-delivery/figma-cache/` and the governed sub-requirement artifacts

## Default Output Paths

```text
.ai-delivery/figma-cache/<figma-file-id>/
├── structure.json
├── nodes/<node-id>.json
├── screenshots/<node-id>.png
├── comments/<node-id>.json
└── tokens/<token-set>.json

.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── figma-mapping.md
├── traceability.json
└── decisions.md
```

## Workflow

### 1. Confirm the upstream breakdown contract

- Read `requirement-slice.md`, `traceability.json`, `status.json`, and `decisions.md` before touching Figma evidence.
- Confirm that the sub-requirement folder and `subreq-id` match the intended scope.
- Prefer to start from `split_ready`; if upstream scope is still unstable, stop instead of papering over a breakdown issue.

### 2. Gather or refresh design evidence

- Follow the Figma retrieval order from `references/figma-fetch-order.md`.
- Prefer cached evidence from `.ai-delivery/figma-cache/` before making new Figma requests.
- Refresh evidence only when the user requests it, the cache is missing, the cache is stale against the requested design version, or a required node cannot be validated from the cache.

### 3. Select executable nodes conservatively

- Converge to real executable frames, components, or regions.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not complete mapping from node names alone.
- Record `companion UI` explicitly when fidelity requires neighboring UI to ship together.
- Record `shared nodes` explicitly when one visual carrier belongs to multiple sub-requirements.

### 4. Write `figma-mapping.md`

- Use `../common/templates/figma-mapping-template.md`.
- Include requirement-to-node mapping, node-to-requirement mapping, required UI, companion UI, shared nodes, missing design evidence, conflicts, and verification evidence.
- Keep missing design evidence factual. Missing design evidence is not permission to invent visual truth.

### 5. Update `traceability.json` in place

- Treat `traceability.json` as a first-class governed artifact, not a disposable sidecar.
- Preserve existing `requirement_refs`, existing conflict history, and existing bridge fields such as `spec_kit_refs`.
- Update only the mapping-owned facts such as `figma_nodes`, `mapping_type`, `confidence`, and `last_verified_at`.
- Do not clear fields owned by adjacent stages just because the current mapping pass did not use them directly.

### 6. Handle state and blockers conservatively

- Only advance the sub-requirement toward `figma_mapped` when the mapping is screenshot-backed, conflict-reviewed, and executable-node-based.
- If Figma evidence conflicts with itself, block on `blocked_figma_conflict`.
- If the requirement defines functionality but Figma has no visual carrier, block on `blocked_missing_design`.
- If Figma shows a visual or state that the requirement explicitly excludes, block on `blocked_requirement_figma_conflict`.
- If a required executable node cannot be validated from trustworthy evidence, block on `blocked_verification_failure`.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not bypass recovery with manual edits.
- Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

### 7. Re-audit before handoff

- Re-open `requirement-slice.md`, `figma-mapping.md`, and `traceability.json`.
- Verify that every claimed mapping still has screenshot-backed evidence, every required UI item maps to real design evidence, and every shared node or companion UI item is explicitly recorded.
- Verify that `traceability.json` still preserves bridge fields such as `spec_kit_refs` when they existed before the mapping pass.
- If material mapping truth changed and `interaction-design.md` already exists, record the revalidation need in `decisions.md`.

## State And Blocker Rules

- If the requirement defines functionality but Figma has no visual carrier, block on `blocked_missing_design`.
- If Figma shows a visual or state that the requirement explicitly excludes, block on `blocked_requirement_figma_conflict`.
- If Figma evidence conflicts with itself, block on `blocked_figma_conflict`.
- If a required executable node cannot be validated from trustworthy evidence, block on `blocked_verification_failure`.
- Only advance the sub-requirement toward `figma_mapped` when the mapping is screenshot-backed and conflict-reviewed.

## Hard Constraints

- Read `requirement-slice.md` before touching Figma evidence.
- Do not invent pages, fields, components, or states.
- Do not treat `ai-delivery-admin` as a source of visual truth.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not complete the mapping without `figma-mapping.md` and `traceability.json`.
- Do not replace `traceability.json` or invent a second bridge artifact.

## Output Standard

Every mapping must include:

- requirement-to-node mapping
- node-to-requirement mapping
- required UI list
- companion UI list
- shared nodes list
- missing design evidence list
- conflict list
- executable node verification evidence

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing an alternate truth store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md` was read before touching Figma evidence
- [ ] The sub-requirement was safe to map from the stricter breakdown contract, preferably `split_ready`
- [ ] Screenshot-backed evidence exists for every claimed executable node
- [ ] No mapping was completed from node names alone
- [ ] No top-level `SECTION` was used as the final executable target
- [ ] `companion UI` and `shared nodes` are explicitly recorded when present
- [ ] `traceability.json` preserves existing bridge fields such as `spec_kit_refs`
- [ ] `traceability.json` remains a first-class governed artifact rather than a sidecar note
- [ ] Blockers preserve `blocked_from_status` and `resume_target_status`
- [ ] No later-stage artifact such as `interaction-design.md` was deleted or silently invalidated

## Pressure Scenarios

Use these as mental regression tests while writing or updating the mapping.

### Scenario 1: The cache contains structure metadata but no screenshot for the required node

Expected behavior:

- refresh the evidence using the Figma retrieval order
- do not mark the mapping complete without screenshot-backed evidence
- block if trustworthy evidence still cannot be obtained

### Scenario 2: A page-level `SECTION` exists, but the real implementation target is deeper

Expected behavior:

- keep drilling down to the executable frame, component, or region
- do not use the top-level `SECTION` as the final target

### Scenario 3: One node serves more than one sub-requirement

Expected behavior:

- record it in `shared nodes`
- reflect the shared ownership in `traceability.json`
- do not silently assign it to one sub-requirement for convenience

### Scenario 4: Fidelity requires adjacent UI outside the strict business boundary

Expected behavior:

- record it as `companion UI`
- keep the business scope unchanged
- do not silently broaden the requirement

### Scenario 5: `interaction-design.md` already exists and the mapping changes materially

Expected behavior:

- preserve `interaction-design.md`
- record the revalidation need in `decisions.md`
- do not erase downstream work

### Scenario 6: `traceability.json` already carries bridge data such as `spec_kit_refs`

Expected behavior:

- preserve those existing fields
- update only mapping-owned facts
- do not invent a second bridge artifact

## Handoff

Stop after producing the mapping package and passing the self-check.

If the user wants to continue, hand the downstream stage `requirement-slice.md`, `figma-mapping.md`, `traceability.json`, and any mapping-related notes in `decisions.md`. Do not perform interaction design or implementation inside this skill unless the user explicitly asks for the next stage.
