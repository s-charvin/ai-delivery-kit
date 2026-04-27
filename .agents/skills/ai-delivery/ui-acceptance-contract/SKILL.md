---
name: ui-acceptance-contract
description: Use when a UI-bearing sub-requirement already has governed requirement and Figma artifacts, plus API artifacts when they materially affect the frozen screen contract, and must freeze immutable screen-state acceptance contracts before interaction design, Spec Kit, or implementation.
---

# UI Acceptance Contract

Project-local workflow skill for freezing screen and state level UI acceptance truth into governed artifacts inside the host repository.

## Overview

Use this skill after `ui-requirement-mapping` when a UI-bearing sub-requirement already has requirement truth, trustworthy structured design evidence, and API contract truth when that API truth materially changes the executable screen-state contract. This stage writes `ui-acceptance-contract.md`, updates `traceability.json.ui_acceptance_contract` in place, and advances `status.json` to `acceptance_frozen` only when the screen-state contract is truly ready.

This skill exists to separate two concerns that were previously mixed together:

- `figma-mapping.md` proves the requirement was bound to structured design evidence
- `ui-acceptance-contract.md` freezes the immutable screen/state contract that downstream interaction design, Spec Kit, and implementation must consume without reinterpreting visual truth

## Hard Boundary

- Do not invent visual truth.
- Do not invent business flow, permission rules, navigation, or API semantics.
- Do not use a top-level `SECTION` as a frozen executable frame target.
- Do not treat `get_structure` as sufficient screen-state truth when `get_code` is still missing.
- Do not overwrite `figma-mapping.md`, `api-contract-mapping.md`, or `interaction-design.md`.
- Do not replace `traceability.json` with a sidecar note or second bridge artifact.
- Do not hand-edit blocked states to look recovered.

If a required screen state, executable frame, or 1:1 visual constraint cannot be supported by trustworthy evidence, stop and block instead of pushing uncertain truth downstream.

## Use This Skill For

- Freezing immutable screen-state acceptance truth for UI-bearing sub-requirements
- Writing `ui-acceptance-contract.md`
- Updating `traceability.json.ui_acceptance_contract`
- Moving a UI-bearing sub-requirement to `acceptance_frozen` when the contract is source-backed
- Recording 1:1 visual blockers before interaction design, Spec Kit, TDD, or implementation

## Do Not Use This Skill For

- Requirement splitting
- API contract discovery
- Figma evidence discovery
- Interaction design
- Spec Kit generation
- Implementation code or visual tuning by guesswork

## Required References

- [Dual Truth Rules](references/dual-truth-rules.md)
- [Blocker Catalog](references/blocker-catalog.md)
- [Logging Checklist](references/logging-checklist.md)
- [UI Acceptance Contract Template](templates/ui-acceptance-contract-template.md)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` instead of inventing a parallel acceptance store.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`
- trustworthy `get_code` evidence for every final executable screen state

### Expected Supporting Inputs

- `api-contract-mapping.md` when action semantics already exist
- `traceability.json`
- `status.json`
- `decisions.md`

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or not safe enough to consume, stop and hand work back to `requirement-breakdown`.
- If `figma-mapping.md` is missing or is not backed by trustworthy structured evidence, stop and hand work back to `ui-requirement-mapping`.
- If any required final screen state lacks trustworthy `get_code` evidence, block on `blocked_verification_failure`.
- If a critical 1:1 visual truth gap remains unresolved, block on `blocked_missing_design`.
- If Requirement truth and Figma truth conflict inside the executable screen contract, block on `blocked_requirement_figma_conflict`.
- If API truth is incomplete but does not change the frozen screen-state contract, keep that gap explicit for later interaction or integration work instead of blocking acceptance on API completeness alone.
- If `traceability.json` is missing in a legacy folder, repair only the governed contract and record the repair in `decisions.md`.

## Output Goal

Produce an acceptance package that downstream stages can consume directly without reinterpreting visual truth. The output must preserve:

- a source-backed `ui-acceptance-contract.md`
- an updated `traceability.json.ui_acceptance_contract` subtree
- existing non-acceptance traceability fields such as `requirement_refs`, `api_contract_mapping`, `figma_nodes`, and `spec_kit_refs`
- explicit `Verification Targets`, `Blocking Unknowns`, and frozen screen-state boundaries

## Default Output Paths

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── ui-acceptance-contract.md
├── traceability.json
├── status.json
└── decisions.md
```

## Workflow

### 1. Confirm the upstream contract

- Read `requirement-slice.md`, `api-contract-mapping.md` when present and when it affects screen-state meaning, `figma-mapping.md`, `traceability.json`, `status.json`, and `decisions.md` before drafting the acceptance contract.
- Prefer starting from `figma_mapped`.
- Confirm the sub-requirement is UI-bearing and that downstream execution still depends on 1:1 visual truth.

### 2. Inventory executable screen states

- Read the executable-state evidence already established upstream.
- Require a trustworthy executable frame node for every final screen state.
- Require trustworthy `get_code` evidence for every final screen state before freezing the contract.
- Record the frozen state ids, parent shells, required structure order, and required elements.

### 3. Freeze the screen-state contract

- Use `templates/ui-acceptance-contract-template.md`.
- Write `Screen State Inventory`, `Executable Frame Contract`, `Required Structure Order`, `Required Elements`, `Layout Constraints`, `Content Constraints`, `Asset Contract`, `Reuse Policy`, `Blocking Unknowns`, and `Verification Targets`.
- Treat every 1:1-impacting unknown as either resolved or blocked.
- Do not let visual unknowns degrade into soft notes.

### 4. Update traceability and status conservatively

- Update only `traceability.json.ui_acceptance_contract`.
- Preserve `api_contract_mapping`, `figma_nodes`, `spec_kit_refs`, and other non-acceptance fields.
- Advance `status.json` to `acceptance_frozen` only when each frozen page-state contract is source-backed and the remaining unknowns do not compromise 1:1 delivery.
- Use the separate admin support surface only for governed logging, blocker handling, and status transitions when available.

### 5. Re-audit before handoff

- Re-open `figma-mapping.md`, `ui-acceptance-contract.md`, `traceability.json`, and `status.json`.
- Verify that every frozen screen state has final executable evidence and `Verification Targets`.
- Verify that no visual truth was guessed or shifted into interaction design.

## State And Blocker Rules

- If a required final screen state has no trustworthy executable evidence, block on `blocked_verification_failure`.
- If a required visual carrier is missing, block on `blocked_missing_design`.
- If requirement, API, and visual truth conflict in a way that changes the executable screen contract, block on the narrowest matching blocker and stop short of `acceptance_frozen`.
- Do not block acceptance only because later action semantics or server side effects are still incomplete when those gaps do not alter the frozen screen-state contract.
- Only move the sub-requirement to `acceptance_frozen` when the contract is fully source-backed and safe for downstream consumption.

## Hard Constraints

- Read upstream governed artifacts before writing the acceptance contract.
- Keep workflow truth in `.ai-delivery/`.
- Do not replace `traceability.json`.
- Do not soften 1:1-impacting unknowns into non-blocking prose.
- Do not allow downstream spec, plan, tasks, or implementation to proceed before `acceptance_frozen`.

## Output Standard

Every acceptance contract must define:

- a frozen screen-state inventory
- executable frame ownership
- required structure order
- required elements
- layout and content constraints
- asset and reuse rules
- blocking unknowns
- `Verification Targets`

If the separate admin support surface is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing another truth store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md` and `figma-mapping.md` were read before drafting
- [ ] Every frozen screen state has trustworthy executable evidence
- [ ] Every critical screen state has `get_code` evidence
- [ ] `ui-acceptance-contract.md` was written
- [ ] `traceability.json.ui_acceptance_contract` was updated without overwriting other fields
- [ ] `status.json` only moved to `acceptance_frozen` when the contract became source-backed
- [ ] `Verification Targets` are explicit
- [ ] No 1:1-impacting unknown was silently left as a soft note

## Handoff

Stop after producing `ui-acceptance-contract.md`, updating `traceability.json.ui_acceptance_contract`, and moving the sub-requirement to `acceptance_frozen` or blocked.

If the user wants to continue, hand the downstream stage `requirement-slice.md`, `api-contract-mapping.md` when present, `figma-mapping.md`, `ui-acceptance-contract.md`, `traceability.json`, and `decisions.md`. Do not perform interaction design, Spec Kit generation, or implementation inside this skill unless the user explicitly asks for the next stage.
