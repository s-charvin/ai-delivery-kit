---
name: api-contract-mapping
description: Use when a sub-requirement has governed breakdown artifacts and must be mapped to Swagger, OpenAPI, or other client-facing API contract materials before or alongside UI mapping.
---

# API Contract Mapping

Project-local workflow skill for binding a governed sub-requirement slice to verified client-facing API contract evidence and producing a standardized API mapping artifact inside the host repository.

## Overview

Use this skill after `requirement-breakdown` when a sub-requirement package already exists under `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/`. This stage writes `api-contract-mapping.md`, updates `traceability.json.api_contract_mapping` in place, and preserves the governed artifact contract created upstream instead of inventing a parallel contract store.

This skill is optional in the workflow only when trustworthy API contract materials were not provided. If Swagger, OpenAPI, or an exported client-facing interface contract is provided, this skill is the governed place to map it. If API contract materials arrive late, rerun this skill rather than stuffing late API findings into UI or interaction artifacts.

## Hard Boundary

- Do not invent client-facing API truth.
- Do not analyze server-internal implementation beyond what changes the client-facing contract.
- Do not invent endpoints, request fields, response fields, status values, pagination, or error semantics.
- Do not replace `traceability.json` with a sidecar note or a second bridge artifact.
- Do not overwrite non-API traceability fields owned by other stages.
- Do not delete later-stage artifacts such as `figma-mapping.md` or `interaction-design.md`.
- Do not hand-edit blocked states to look recovered.

If trustworthy client-facing contract evidence cannot be obtained for the requested scope, stop and report that this stage cannot complete safely.

## Use This Skill For

- Mapping `requirement-slice.md` to Swagger or OpenAPI materials
- Producing `api-contract-mapping.md`
- Updating `traceability.json.api_contract_mapping` with governed API mapping facts
- Surfacing missing client-facing contracts, field gaps, and requirement or API conflicts
- Triggering governed `downstream_revalidation` when late API truth can affect UI mapping or interaction design

## Do Not Use This Skill For

- Requirement splitting
- Figma node mapping
- Interaction design
- Server architecture analysis
- New business-logic invention
- Implementation code or task planning

## Required References

- [Dual Truth Rules](references/dual-truth-rules.md)
- [Blocker Catalog](references/blocker-catalog.md)
- [Logging Checklist](references/logging-checklist.md)
- [Checklist](references/checklist.md)
- [API Contract Mapping Template](templates/api-contract-mapping-template.md)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` in the host repository instead of inventing a parallel contract.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- one or more client-facing API contract sources such as Swagger, OpenAPI, or exported contract files

### Expected Supporting Inputs

- `traceability.json`
- `status.json`
- existing `decisions.md`

### Optional Inputs

- explicit operation list
- API version hint
- related requirement supplements
- generated SDK snippets used only for locating contract evidence

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or still too ambiguous, stop and hand the work back to `requirement-breakdown`.
- If the user asked for API mapping but no trustworthy client-facing API contract source exists, block on `blocked_missing_api_contract`.
- If `traceability.json` is missing in a legacy folder, repair only the current governed contract and record that repair in `decisions.md`; do not invent a different JSON shape.
- If multiple Swagger, OpenAPI, or exported API sources disagree on client-facing truth, block on `blocked_api_contract_conflict`.
- If Requirement truth and API contract truth disagree, block on `blocked_requirement_api_conflict`.
- If the source cannot be parsed or verified safely, block on `blocked_verification_failure`.

## Output Goal

Produce an API mapping package that downstream UI mapping, interaction design, or Spec Kit planning can consume directly. The output must preserve:

- a source-backed `api-contract-mapping.md`
- an updated `traceability.json.api_contract_mapping` subtree with status, source refs, operation refs, field gaps, requirement conflicts, verification timing, and `downstream_revalidation`
- existing non-API traceability fields such as `requirement_refs`, `figma_nodes`, `spec_kit_refs`, and bridge context
- explicit missing contracts, field gaps, and requirement or API conflicts

## Default Output Paths

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── api-contract-mapping.md
├── traceability.json
└── decisions.md
```

## Workflow

### 1. Confirm the upstream breakdown contract

- Read `requirement-slice.md`, `traceability.json`, `status.json`, and `decisions.md` before touching API materials.
- Confirm that the sub-requirement scope still matches the intended API mapping scope.
- Prefer to start from `split_ready`, but permit late reruns when API contract materials arrive after UI mapping.

### 2. Gather and validate API contract evidence

- Inventory the provided Swagger, OpenAPI, JSON, YAML, or equivalent contract sources.
- Prefer repo-native contract files over paraphrased notes.
- Use tools such as `jq` for JSON and safe line-based reads for YAML or Markdown-derived exports when helpful.
- Ignore server-internal implementation material unless it changes the client-facing contract.

### 3. Map requirement points to API operations conservatively

- Map only requirement points that are actually represented in the API contract.
- Record exact operation refs such as method, path, and operation id when they exist.
- If the API partially covers the requirement, record the gap as `Field Gaps` or `Missing Contracts` instead of guessing.
- If one API operation serves multiple requirement points, record that shared coverage explicitly.

### 4. Write `api-contract-mapping.md`

- Use `templates/api-contract-mapping-template.md`.
- Include input sources, requirement-to-API mapping, API-to-requirement mapping, request fields, response fields, error semantics, missing contracts, field gaps, requirement or API conflicts, and traceability update notes.
- Keep the document factual and contract-scoped. Do not turn backend implementation uncertainty into invented client-facing gaps.

### 5. Update `traceability.json` in place

- Treat `traceability.json` as a first-class governed artifact, not a disposable sidecar.
- Update only `api_contract_mapping.*`.
- Preserve existing top-level fields such as `requirement_refs`, `figma_nodes`, `mapping_type`, `confidence`, `conflicts`, `last_verified_at`, and `spec_kit_refs`.
- Use `downstream_revalidation` when late or changed API truth can affect `ui-requirement-mapping` or `ui-interaction-design`.

### 6. Handle state and blockers conservatively

- Use `not_provided` only when the stage was skipped because no API contract source was supplied.
- Use `pending` when sources exist but mapping work is not yet complete.
- Use `mapped` only when the API mapping is backed by trustworthy client-facing contract evidence.
- Use `needs_revalidation` when new or changed API truth can affect downstream UI or interaction artifacts.
- Use `blocked_missing_api_contract`, `blocked_api_contract_conflict`, `blocked_requirement_api_conflict`, or `blocked_verification_failure` when the next safe step cannot proceed.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not bypass recovery through manual edits.
- Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

### 7. Re-audit before handoff

- Re-open `requirement-slice.md`, `api-contract-mapping.md`, and `traceability.json`.
- Verify that every claimed operation, field, error semantic, field gap, and conflict still matches the source contract.
- Verify that `traceability.json` still preserves non-API fields such as `spec_kit_refs`.
- Verify that `downstream_revalidation` is set only when it is actually needed.

## State And Blocker Rules

- If the user asked for API mapping but no trustworthy client-facing API contract source exists, block on `blocked_missing_api_contract`.
- If multiple contract sources disagree on client-facing truth, block on `blocked_api_contract_conflict`.
- If Requirement and API truth disagree, block on `blocked_requirement_api_conflict`.
- If the source cannot be parsed or verified safely, block on `blocked_verification_failure`.
- Only mark the API contract mapping stage as `mapped` when the result is source-backed and conflict-reviewed.

## Hard Constraints

- Read `requirement-slice.md` before touching API materials.
- Work only inside `.ai-delivery/requirements/`.
- Do not move workflow truth into `ai-delivery-admin`.
- Do not replace `traceability.json` with a sidecar note or a second bridge artifact.
- Do not overwrite non-API traceability fields.

## Output Standard

Every API mapping must include:

- source-backed contract inventory
- requirement-to-API mapping
- API-to-requirement mapping
- request and response field coverage
- error semantics
- missing contracts
- field gaps
- requirement or API conflicts
- traceability update notes

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing an alternate truth store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md` was read before touching API materials
- [ ] Only trustworthy client-facing contract evidence was used
- [ ] No server-internal implementation detail was misclassified as a client-facing gap
- [ ] `api-contract-mapping.md` was written
- [ ] `traceability.json.api_contract_mapping` was updated without overwriting other traceability fields
- [ ] `downstream_revalidation` was set only when justified
- [ ] The narrowest blocker was chosen when blocked
- [ ] Existing bridge fields such as `spec_kit_refs` were preserved

## Pressure Scenarios

### Scenario 1: The user invokes this skill, but no Swagger or OpenAPI source is actually available

Expected behavior:

- stop the stage
- block on `blocked_missing_api_contract`
- do not invent endpoints from requirement prose

### Scenario 2: The requirement is clear, but the API contract is partial

Expected behavior:

- write the available operation mapping
- record `Field Gaps` or `Missing Contracts`
- do not treat partial coverage as full coverage

### Scenario 3: API contract arrives after UI mapping already happened

Expected behavior:

- update `traceability.json.api_contract_mapping`
- set `needs_revalidation` when the new API truth can affect UI or interaction artifacts
- do not overwrite Figma or interaction fields

### Scenario 4: Two contract exports disagree

Expected behavior:

- block on `blocked_api_contract_conflict`
- capture the conflicting evidence
- stop short of `mapped`

## Handoff

Stop after producing `api-contract-mapping.md`, updating `traceability.json.api_contract_mapping`, and passing the self-check.

If the user wants to continue, hand the downstream stage `requirement-slice.md`, `api-contract-mapping.md`, `traceability.json`, and any mapping-related notes in `decisions.md`. Do not perform UI mapping, interaction design, or implementation planning inside this skill unless the user explicitly asks for the next stage.
