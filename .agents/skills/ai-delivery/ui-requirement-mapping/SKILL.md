---
name: ui-requirement-mapping
description: Use when a sub-requirement already has governed breakdown artifacts and must be bound to verified structured design evidence from Figma MCP or compatible provider MCPs before interaction design or implementation.
---

# UI Requirement Mapping

Project-local workflow skill for binding a governed sub-requirement slice to verified structured design evidence and producing a 1:1 visual implementation contract inside the host repository.

## Overview

Use this skill after `requirement-breakdown` when a sub-requirement package already exists under `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/`. This stage writes `figma-mapping.md`, updates `traceability.json` in place, and preserves the governed artifact contract created upstream instead of inventing a parallel mapping store.

The primary evidence for this stage is structured node data from Figma MCP or compatible provider MCPs such as TemPad Dev, F2C, or other trustworthy structured design providers. Screenshots or previews may be cached as optional supporting context, but they are never the completion gate and never override structured node payloads.

## Hard Boundary

- Do not invent visual truth.
- Do not add pages, fields, components, states, or business flows.
- Do not treat a node name alone as evidence.
- Do not treat screenshots, previews, or prose-only descriptions as sufficient mapping evidence.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not mark mapping complete without trustworthy structured node payloads for each claimed executable node.
- Do not flatten provider payloads into a lossy replacement schema inside the cache.
- Do not replace `traceability.json` with a sidecar note or a second bridge artifact.
- Do not delete `interaction-design.md` or other later-stage artifacts when re-running mapping.
- Do not hand-edit blocked states to look recovered.

If trustworthy structured design evidence cannot be obtained for required UI from Figma MCP or a compatible provider MCP, stop and report that this stage cannot complete safely.

## Use This Skill For

- Binding a `requirement-slice.md` to structured design evidence from Figma MCP or compatible provider MCPs
- Producing `figma-mapping.md` before interaction design or implementation
- Updating `traceability.json` with verified nodes, confidence, conflicts, verification timing, and provider-aware evidence references when the governed contract already supports them
- Surfacing visual blockers, shared nodes, and companion UI without silently broadening business scope

## Do Not Use This Skill For

- Requirement splitting or requirement truth repair
- Interaction contract design
- Final code generation
- Filling missing design evidence by guesswork
- Replacing raw provider evidence with prose-only descriptions

## Required References

- [Dual Truth Rules](references/dual-truth-rules.md)
- [Blocker Catalog](references/blocker-catalog.md)
- [Logging Checklist](references/logging-checklist.md)
- [Figma Mapping Template](templates/figma-mapping-template.md)
- [Figma Fetch Order](references/figma-fetch-order.md)
- [Mapping Checklist](references/mapping-checklist.md)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` and the raw-evidence boundary under `.ai-delivery/figma-cache/`.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- a design file, file id, node target, or equivalent design-source locator

### Expected Supporting Inputs

- `traceability.json`
- `status.json`
- existing `decisions.md`

### Optional Inputs

- explicit node list
- provider hint or preferred provider order
- exported comments
- token files
- design version hints
- optional screenshots or previews for human review only

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or still not safe for mapping, stop and hand the work back to `requirement-breakdown`.
- Prefer starting from `split_ready`; if the slice is still `draft` or blocked and the user did not ask for repair work, stop instead of pretending mapping is normal.
- If `traceability.json` is missing in a legacy folder, repair only the current governed contract and record that repair in `decisions.md`; do not invent a different JSON shape.
- If cached structured evidence is missing, stale, or does not cover the required executable node, refresh it using the Figma retrieval order.
- If trustworthy structured node evidence still cannot be obtained from a supported provider, stop and block rather than mapping from screenshots, previews, or memory.
- Optional previews may be cached or referenced when helpful, but they are never required for completion.
- If `interaction-design.md` already exists, preserve it and record any required revalidation in `decisions.md` when the mapping changes materially.

## Output Goal

Produce a mapping package that downstream interaction design or implementation can consume directly. The output must preserve:

- a structure-backed `figma-mapping.md`
- an updated `traceability.json` with `requirement_refs`, `figma_nodes`, `mapping_type`, `confidence`, `conflicts`, and `last_verified_at`, plus provider-aware evidence refs when the existing governed contract already supports them
- existing bridge fields such as `spec_kit_refs` when the repo already carries them
- explicit `required UI`, `companion UI`, `shared nodes`, `missing design evidence`, `conflicts`, and structured verification evidence
- the raw evidence boundary between `.ai-delivery/figma-cache/` and the governed sub-requirement artifacts
- a unified provider-aware cache in which each cached artifact preserves compatibility metadata plus `provider`, `artifact_type`, and `raw_payload` without flattening the provider response

## Default Output Paths

```text
.ai-delivery/figma-cache/<design-source-id>/
├── index.json
└── artifacts/
    └── <artifact-id>.json

.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── figma-mapping.md
├── traceability.json
└── decisions.md
```

Recommended cache record shape:

```json
{
  "figma_file_id": "abc123",
  "node_id": "987:654",
  "node_name": "Save Button",
  "subreq_ids": ["profile-settings-edit-form"],
  "last_updated_at": "<ISO8601>",
  "freshness": "fresh | stale | missing | corrupt",
  "provider": "figma-mcp | tempad-dev | f2c | <compatible-provider>",
  "artifact_type": "file_context | node | comments | tokens | assets | preview",
  "source_ref": {},
  "raw_payload": {}
}
```

Keep `raw_payload` in the provider's native response shape. Preserve the compatibility metadata required by existing admin readers while adding provider-aware fields. If a provider returns non-JSON preview or asset files, store the binary as a sibling artifact and reference it from the JSON wrapper instead of replacing the raw structured payload.

## Workflow

### 1. Confirm the upstream breakdown contract

- Read `requirement-slice.md`, `traceability.json`, `status.json`, and `decisions.md` before touching design evidence.
- Confirm that the sub-requirement folder and `subreq-id` match the intended scope.
- Prefer to start from `split_ready`; if upstream scope is still unstable, stop instead of papering over a breakdown issue.

### 2. Gather or refresh structured design evidence

- Follow the Figma retrieval order from `references/figma-fetch-order.md`.
- Prefer cached evidence from `.ai-delivery/figma-cache/` before making new provider requests.
- Use Figma MCP by default when it provides the needed structured context; compatible providers such as TemPad Dev or F2C may supplement or substitute when they provide trustworthy structured node payloads.
- Refresh evidence only when the user requests it, the cache is missing, the cache is stale against the requested design version, or a required node cannot be validated from the cache.
- Cache each retrieved artifact under `.ai-delivery/figma-cache/` with compatibility metadata plus `provider`, `artifact_type`, and provider-native `raw_payload`.

### 3. Select executable nodes conservatively

- Converge to real executable frames, components, or regions from structured provider payloads.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not complete mapping from node names alone, screenshots alone, or prose-only summaries.
- Record `companion UI` explicitly when fidelity requires neighboring UI to ship together.
- Record `shared nodes` explicitly when one visual carrier belongs to multiple sub-requirements.
- If two structured providers disagree on hierarchy, node identity, or executable boundaries, record the conflict and block when it cannot be resolved safely.

### 4. Write `figma-mapping.md`

- Use `templates/figma-mapping-template.md`.
- Include design target, structured evidence sources, requirement-to-node mapping, node-to-requirement mapping, required UI, companion UI, shared nodes, missing design evidence, conflicts, and traceability update notes.
- For each mapped requirement point, record the provider, node ids, raw artifact refs, and why the structured payload is sufficient.
- Keep missing design evidence factual. Missing design evidence is not permission to invent visual truth.

### 5. Update `traceability.json` in place

- Treat `traceability.json` as a first-class governed artifact, not a disposable sidecar.
- Preserve existing `requirement_refs`, existing conflict history, and existing bridge fields such as `spec_kit_refs`.
- Update only the mapping-owned facts such as `figma_nodes`, `mapping_type`, `confidence`, and `last_verified_at`.
- If the existing governed contract already carries provider refs or evidence refs, preserve and update them in place.
- If the contract does not yet carry provider-aware evidence fields, do not invent an incompatible JSON shape; keep the full provider and raw-artifact evidence trail in `figma-mapping.md` and `decisions.md`.

### 6. Handle state and blockers conservatively

- Only advance the sub-requirement toward `figma_mapped` when the mapping is backed by trustworthy structured node payloads, conflict-reviewed, and executable-node-based.
- If Figma-derived structured evidence conflicts with itself across providers or retrieval passes, block on `blocked_figma_conflict`.
- If the requirement defines functionality but the design evidence has no visual carrier, block on `blocked_missing_design`.
- If design evidence shows a visual or state that the requirement explicitly excludes, block on `blocked_requirement_figma_conflict`.
- If a required executable node cannot be validated from trustworthy structured evidence, block on `blocked_verification_failure`.
- Optional screenshots or previews never upgrade low-confidence structured evidence into `figma_mapped`.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not bypass recovery with manual edits.
- Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

### 7. Re-audit before handoff

- Re-open `requirement-slice.md`, `figma-mapping.md`, and `traceability.json`.
- Verify that every claimed mapping still has structured evidence with provider, node ids, raw artifact refs, and explicit evidence basis.
- Verify that every required UI item maps to real design evidence and every shared node or companion UI item is explicitly recorded.
- Verify that cached artifacts preserve provider-native raw payloads instead of flattened summaries while keeping compatibility metadata required by current admin readers.
- Verify that `traceability.json` still preserves bridge fields such as `spec_kit_refs` when they existed before the mapping pass.
- If material mapping truth changed and `interaction-design.md` already exists, record the revalidation need in `decisions.md`.

## State And Blocker Rules

- If the requirement defines functionality but design evidence has no visual carrier, block on `blocked_missing_design`.
- If design evidence shows a visual or state that the requirement explicitly excludes, block on `blocked_requirement_figma_conflict`.
- If Figma-derived structured evidence conflicts with itself across providers or retrieval passes, block on `blocked_figma_conflict`.
- If a required executable node cannot be validated from trustworthy structured evidence, block on `blocked_verification_failure`.
- Only advance the sub-requirement toward `figma_mapped` when the mapping is structure-backed and conflict-reviewed.

## Hard Constraints

- Read `requirement-slice.md` before touching design evidence.
- Do not invent pages, fields, components, or states.
- Do not treat `ai-delivery-admin` as a source of visual truth.
- Do not use a top-level `SECTION` as the final executable node target.
- Do not complete the mapping without `figma-mapping.md` and `traceability.json`.
- Do not complete a mapping from node names alone, screenshots alone, or screenshots that disagree with structured payloads.
- Do not flatten provider raw payloads into a lossy cache schema.
- Do not replace `traceability.json` or invent a second bridge artifact.

## Output Standard

Every mapping must include:

- provider-aware requirement-to-node mapping
- provider-aware node-to-requirement mapping
- required UI list
- companion UI list
- shared nodes list
- missing design evidence list
- conflict list
- structured verification evidence with provider, artifact refs, node ids, and evidence basis

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing an alternate truth store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md` was read before touching design evidence
- [ ] The sub-requirement was safe to map from the stricter breakdown contract, preferably `split_ready`
- [ ] Trustworthy structured node evidence exists for every claimed executable node
- [ ] No mapping was completed from node names alone, screenshots alone, or prose-only descriptions
- [ ] Provider and raw artifact refs are recorded for every mapped executable node
- [ ] No top-level `SECTION` was used as the final executable target
- [ ] `companion UI` and `shared nodes` are explicitly recorded when present
- [ ] The `figma-cache` artifacts preserve compatibility metadata plus `provider`, `artifact_type`, and provider-native `raw_payload`
- [ ] `traceability.json` preserves existing bridge fields such as `spec_kit_refs`
- [ ] `traceability.json` remains a first-class governed artifact rather than a sidecar note
- [ ] Blockers preserve `blocked_from_status` and `resume_target_status`
- [ ] No later-stage artifact such as `interaction-design.md` was deleted or silently invalidated

## Pressure Scenarios

Use these as mental regression tests while writing or updating the mapping.

### Scenario 1: The cache contains a preview or screenshot but no structured node payload for the required target

Expected behavior:

- refresh the structured evidence using the retrieval order
- do not mark the mapping complete from preview-only evidence
- block if trustworthy structured evidence still cannot be obtained

### Scenario 2: A page-level `SECTION` exists, but the real implementation target is deeper

Expected behavior:

- keep drilling down to the executable frame, component, or region
- do not use the top-level `SECTION` as the final target

### Scenario 3: One node serves more than one sub-requirement

Expected behavior:

- record it in `shared nodes`
- reflect the shared ownership in `traceability.json` when the governed contract already supports it
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

### Scenario 7: Two structured providers disagree on hierarchy or executable node identity

Expected behavior:

- record the provider-specific artifact refs and node ids
- capture the conflict instead of picking one silently
- block on `blocked_figma_conflict` if the disagreement changes mapping truth

### Scenario 8: A provider returns only visual preview data with no trustworthy structured node payload

Expected behavior:

- treat the preview as optional supporting context only
- do not mark the mapping complete
- continue searching for trustworthy structured evidence or block

## Handoff

Stop after producing the mapping package and passing the self-check.

If the user wants to continue, hand the downstream stage `requirement-slice.md`, `figma-mapping.md`, `traceability.json`, and any mapping-related notes in `decisions.md`. Do not perform interaction design or implementation inside this skill unless the user explicitly asks for the next stage.
