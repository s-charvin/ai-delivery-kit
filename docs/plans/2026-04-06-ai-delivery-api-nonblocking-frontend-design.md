---
title: AI Delivery API Non-Blocking Frontend Design
date: 2026-04-06
status: approved
---

# AI Delivery API Non-Blocking Frontend Design

## Context

The current `ai-delivery` workflow inside `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery` was recently expanded with an `api-contract-mapping` stage and governed `api_contract_mapping` traceability fields.

That addition improved protocol-awareness, but it also made the skill chain too strict for the actual frontend delivery sequence:

- backend and frontend often develop in parallel
- Swagger/OpenAPI may arrive late
- interface fields, enums, or whole endpoints may be incomplete during early UI work
- requirement breakdown, UI mapping, and interaction design should still be able to progress safely

The user wants the workflow to treat API truth as implementation-adjacent context, not as an early-stage gate.

## Problem

Today the skill set overweights API completeness in earlier stages:

- missing or partial API contract material too easily becomes a blocker
- `api-contract-mapping` reads more like a validation gate than a frontend-support artifact
- downstream stages consume API context as if it were required for readiness
- the documentation emphasizes conflict and blocking more than placeholder, reservation, and late binding

This does not match the actual frontend sequencing. API details usually matter most at implementation time, often specifically at data binding or viewmodel work, not during requirement splitting, UI mapping, or interaction design.

## Goals

- Keep frontend pre-development stages moving even when API contracts are missing or incomplete.
- Reframe API handling as optional governed context for early stages and a stronger input for later implementation.
- Preserve the governed artifact contract and avoid unnecessary schema churn.
- Make blockers narrow and meaningful: only API facts that would make current-stage output wrong should block or force revalidation.
- Update skill docs, templates, checklists, and guidance so the workflow consistently reflects this rule.

## Non-Goals

- Do not remove `api-contract-mapping` from the workflow.
- Do not invent API truth when no contract exists.
- Do not redesign `traceability.json` into a new incompatible shape unless absolutely necessary.
- Do not turn API mapping into implementation planning or backend analysis.

## Options Considered

### Option 1: Relax only `api-contract-mapping`

Change the API skill so missing contracts become gaps rather than blockers, while leaving other stages mostly as-is.

Pros:

- smallest doc change
- lowest implementation cost

Cons:

- leaves inconsistent workflow semantics across stages
- downstream skills still behave as if API completeness is a readiness gate

### Option 2: Make API tolerance a cross-stage policy

Treat API protocol material as a non-blocking context layer throughout `requirement-breakdown`, `api-contract-mapping`, `ui-requirement-mapping`, and `ui-interaction-design`.

Pros:

- matches real frontend sequencing
- creates one consistent rule across the chain
- keeps API usefulness without over-gating early work

Cons:

- requires synchronized updates across multiple skills, templates, and checklists

### Option 3: Make API mapping a pure note-taking stage

Keep `api-contract-mapping` only as a record artifact with no workflow influence.

Pros:

- impossible for API incompleteness to block early work by accident

Cons:

- too weak when late API truth really does invalidate current UI or interaction conclusions
- removes a governed place to signal revalidation

## Decision

Choose Option 2.

The skill chain will adopt a unified rule:

> API incompleteness does not block early frontend stages.
> Only API facts that would make the current stage's output materially wrong can block or force revalidation.

This keeps the workflow realistic for frontend teams while preserving governed escalation paths when API truth truly changes user-visible behavior.

## Design

## 1. New Workflow Posture

The workflow remains:

- `requirement-breakdown`
- `api-contract-mapping`
- `ui-requirement-mapping`
- `ui-interaction-design`

But `api-contract-mapping` changes meaning.

It is no longer an early gate that decides whether frontend pre-dev work may proceed. Instead, it becomes:

- an interface-context capture stage
- a place to record current contract coverage
- a place to document frontend reservation points
- a place to capture implementation risks for later coding and integration

The chain is therefore:

- requirement and UI truth drive early outputs
- API truth enriches those outputs when available
- API truth only blocks when it invalidates the current output

## 2. API Issue Classification

All relevant skills should reason about API findings using the same three categories.

### `known_gap`

Examples:

- no Swagger/OpenAPI yet
- endpoint exists but fields are incomplete
- enum values are not finalized
- error semantics are not specified
- pagination or filtering semantics are still absent

Effect:

- do not block early stages
- record in `api-contract-mapping.md`
- optionally mirror the gap into `decisions.md` when downstream consumers need visibility

### `integration_risk`

Examples:

- the UI can be designed, but final data binding will require adapter logic
- request payload shape is likely to change
- response structure is only partially known
- optimistic update behavior depends on backend semantics that are still unsettled

Effect:

- do not block early stages
- explicitly call out frontend reservation points
- make clear that implementation or viewmodel work must revisit the issue later

### `blocking_conflict`

Examples:

- API truth changes the number of user-visible steps
- API truth removes or adds user-visible states that the current interaction contract depends on
- API truth changes whether a required action is synchronous, asynchronous, retryable, queued, or approval-based
- API truth invalidates a field, control, or flow that current requirement or UI outputs treat as real

Effect:

- block or force targeted revalidation
- record evidence and recovery condition
- use the narrowest blocker only in this class of cases

## 3. Traceability Semantics

Preserve the existing `traceability.json.api_contract_mapping` subtree and status family. Change the usage semantics instead of introducing a new contract unless later evidence proves that insufficient.

### Status Meaning

#### `not_provided`

- no usable client-facing contract source was provided yet
- this is normal
- this does not block `requirement-breakdown`, `ui-requirement-mapping`, or `ui-interaction-design`

#### `pending`

- a contract exists or partial contract context exists, but mapping is deferred or incomplete
- this is also normal
- this does not block earlier frontend stages

#### `mapped`

- the currently available contract evidence has been mapped for the relevant scope
- this does not imply backend finality
- it only means the governed mapping for the current known scope is complete enough

#### `needs_revalidation`

- new API truth may affect an already-produced downstream artifact
- this should be used selectively
- ordinary gaps should not trigger it
- only user-visible impact should trigger it for UI or interaction stages

#### `blocked_*`

- reserve for situations where current-stage output would be materially wrong if work continued without resolution
- do not use for ordinary absence, incompleteness, or deferred API details

## 4. Per-Skill Responsibilities

## `requirement-breakdown`

This stage should:

- ignore API incompleteness as a readiness gate
- initialize `api_contract_mapping` conservatively
- seed `api-contract-mapping.md` as a placeholder artifact
- frame missing API truth as later integration context, not requirement instability

This stage should not:

- block because no API exists yet
- downgrade a good requirement slice just because backend fields are unsettled
- imply that UI work must wait for API contract maturity

Recommended default behavior:

- no API source: initialize as `not_provided`
- partial or late API source exists but not yet mapped: initialize as `pending`

## `api-contract-mapping`

This stage should become the governed place to document:

- what contract evidence exists today
- what parts of the requirement can already bind to API operations
- which user-visible conclusions remain safe without more backend truth
- which implementation points require reservation or later revisit

This stage should be allowed to complete even when:

- there is no API contract at all
- the API contract is partial
- the API contract lacks fields or semantics needed for coding later

In those cases it should produce:

- factual placeholder mapping
- explicit `known_gap` inventory
- `integration_risk` notes
- frontend reservation points

This stage should only block when API truth would make the current frontend-facing outputs wrong.

## `ui-requirement-mapping`

This stage should treat API context as optional supporting context.

It should:

- preserve `api_contract_mapping`
- use API findings when they help explain UI bindings or later data wiring
- continue mapping when API context is missing or partial

It should not:

- require complete API mapping for `figma-mapping.md`
- treat missing backend fields as a visual blocker

It may note:

- which UI surfaces are safe to design without backend finalization
- which controls, states, or placeholders will need later binding

## `ui-interaction-design`

This stage should continue to define user-visible interaction contracts even when backend protocol truth is incomplete.

It should:

- use API context when it materially shapes visible states
- label any late-binding behavior as implementation-adjacent when appropriate
- preserve upstream API traceability context

It should not:

- wait for request or response field finality
- stop because transport details are incomplete
- allow backend incompleteness to erase user-visible interaction work

It should only revalidate or block when API facts change visible behavior, not merely implementation wiring.

## 5. Blocker Policy

API blockers should be narrowed.

### `blocked_missing_api_contract`

Do not use this as the default result of missing Swagger/OpenAPI during early frontend stages.

Instead, reserve it for cases where:

- the current requested task explicitly requires contract-backed API conclusions
- and no trustworthy client-facing contract source exists
- and proceeding would make the current output misleading

For the four stages in scope here, that should be rare.

### `blocked_api_contract_conflict`

Use only when:

- multiple API sources materially disagree
- and the disagreement changes conclusions relevant to the current stage

Do not use it for harmless or implementation-only variations.

### `blocked_requirement_api_conflict`

Use only when:

- API truth contradicts the requirement in a way that changes user-visible behavior or current-stage conclusions

Do not use it for mere absence, incompleteness, or low-level payload uncertainty.

## 6. Artifact and Template Updates

## `api-contract-mapping.md`

The template should be rewritten to better support non-blocking frontend work.

It should still preserve the core mapping structure, but add or emphasize sections such as:

- frontend development posture
- known gaps
- integration risks
- frontend reservation points
- deferred implementation questions
- revalidation trigger assessment

The current structure can be preserved where useful, but the writing guidance should shift from:

- "missing contract means stop"

to:

- "missing contract means record the gap and keep early frontend work moving unless visible behavior is invalidated"

## `decisions.md`

Guidance should clarify when to record:

- API absence as a non-blocking note
- partial field semantics as a deferred implementation concern
- late contract arrival as a revalidation note

## Checklists and Blocker Catalogs

All relevant checklists should be updated so they:

- stop treating API incompleteness as a default blocker
- explicitly preserve early-stage forward progress
- distinguish `known_gap`, `integration_risk`, and `blocking_conflict`

## 7. Revalidation Rules

Late API truth should not automatically reopen all downstream work.

Use this routing:

- no user-visible impact:
  update `api-contract-mapping.md` and `traceability.json.api_contract_mapping` only
- local implementation impact only:
  record `integration_risk`, no UI or interaction revalidation
- visible feedback or state impact:
  targeted revalidation, usually `ui-interaction-design`
- visible structure or flow impact:
  stronger revalidation and possibly blocker escalation

This keeps revalidation proportional to actual impact.

## 8. Validation Strategy

The implementation should update:

- skill docs
- templates
- checklists
- blocker catalogs
- any governed examples or fixtures that currently encode the stricter posture
- repo validation coverage where helpful

Verification should confirm:

- no skill still treats missing API material as a default blocker for early frontend stages
- placeholder and partial-contract flows are explicitly documented
- blocker rules are narrowed to current-stage distortion cases
- late API truth triggers revalidation only when user-visible conclusions change

## Expected Outcome

After this change:

- frontend teams can complete requirement breakdown, UI mapping, and interaction design without waiting for backend contract maturity
- API mapping still exists as governed documentation
- API uncertainty is surfaced honestly, but without unnecessary early-stage blocking
- blockers and revalidation are reserved for the cases that actually threaten correctness
