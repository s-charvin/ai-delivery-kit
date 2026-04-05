---
name: requirement-breakdown
description: Use when approved or near-final top-level requirement material must be expanded into governed `.ai-delivery` requirement packages, dependency metadata, and downstream-ready sub-requirement slices before UI mapping or implementation planning.
---

# Requirement Breakdown

Project-local workflow skill for turning top-level requirement material into governed requirement and sub-requirement artifacts inside the host repository.

## Overview

Turn approved or near-final requirement truth into a breakdown package that downstream skills can consume directly. This stage expands the intake package under `.ai-delivery/requirements/<requirement-id>/`, or bootstraps the same contract if intake is missing, without redesigning the product or inventing missing business truth.

## Hard Boundary

- Do not invent product truth.
- Do not redesign the product.
- Do not write implementation code.
- Do not generate Spec Kit spec, plan, or tasks here.
- Do not bind Figma nodes or make visual-truth decisions here.
- Do not silently smooth over conflicts between approved requirement sources.
- Do not create a second truth store outside `.ai-delivery/`.
- Do not delete later-stage artifacts such as `figma-mapping.md` or `interaction-design.md` if they already exist.
- Do not promote ambiguous slices to `split_ready`.

If the request is still in discovery, the requirement source is still moving, or the top-level requirement material is not yet approved enough to split safely, stop and tell the user this stage is too early.

## Use This Skill For

- Expanding an approved or near-final requirement package after requirement intake
- Splitting top-level requirement material into independently trackable sub-requirements
- Extracting cross-cutting rules and dependency ordering before UI mapping
- Seeding governed sub-requirement artifacts such as `status.json` and `traceability.json`

## Do Not Use This Skill For

- Early product exploration
- Figma mapping or interaction design
- Writing implementation tasks or plans
- Filling in missing business logic by assumption
- Backend implementation analysis that does not change requirement truth

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Requirement Slice Template](../common/templates/requirement-slice-template.md)
- [Checklist](references/checklist.md)
- [Sub-Requirement README Template](references/subreq-readme-template.md)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` in the host repository instead of inventing a parallel contract.

## Inputs

### Required Inputs

- path to the current approved top-level requirement material

### Expected Supporting Inputs

- existing requirement package path or requirement id when already known
- approved supplements that change requirement truth

### Optional Inputs

- API contract
- codebase context
- design system notes
- business-rule supplements

### Missing Input Handling

If a source or artifact is missing:

- If the top-level requirement material is missing, stale, or still moving, stop.
- If the requirement package already exists, reuse it instead of creating a duplicate.
- If intake artifacts are missing, bootstrap the same governed package under `.ai-delivery/requirements/<requirement-id>/` and record that bootstrap in `breakdown-summary.md` or `decisions.md`.
- If optional supplements are missing but the requirement truth is still sufficient, continue and record the gap under `Open Questions`.
- If a missing input removes a critical business fact needed to split safely, block on `blocked_missing_requirement`.
- If two approved requirement sources conflict, block on `blocked_requirement_conflict`.
- If downstream materials such as Figma or API contracts are absent, do not block this stage unless the requirement truth itself depends on them.

## Output Goal

Produce a requirement package that downstream skills can consume without reinterpreting the whole requirement source. The package must preserve:

- the authoritative requirement package rooted in `requirement.md`
- requirement-level summaries in `breakdown-summary.md` and `global-rules.md`
- an acyclic `dependency-graph.json`
- one governed folder per sub-requirement with `README.md`, `requirement-slice.md`, `dependency.json`, `status.json`, `traceability.json`, and `decisions.md`
- explicit source references, dependencies, acceptance signals, open questions, and blocker evidence
- first-class `traceability.json` and `status.json` contracts rather than informal notes

Every editable Markdown or JSON artifact should follow the repo's governed metadata contract instead of ad-hoc file shapes.

## Default Output Layout

```text
.ai-delivery/requirements/<requirement-id>/
├── requirement.md
├── breakdown-summary.md
├── global-rules.md
├── dependency-graph.json
└── sub-requirements/
    └── <subreq-id>/
        ├── README.md
        ├── requirement-slice.md
        ├── dependency.json
        ├── status.json
        ├── traceability.json
        └── decisions.md
```

If the folder already contains later-stage files such as `figma-mapping.md` or `interaction-design.md`, leave them in place and update only the requirement-breakdown-owned artifacts.

## Workflow

### 1. Inventory the authoritative sources

- Read the top-level requirement material carefully and capture line numbers or source positions when possible.
- Confirm which file is the current approved requirement source and which supplements are merely supporting context.
- Resolve the target requirement id and requirement folder under `.ai-delivery/requirements/`.
- Reuse the shared references and templates from `../common/` instead of inventing new artifact shapes.

### 2. Confirm or bootstrap the requirement package

- Reuse the intake-created requirement package when it exists.
- If the package is missing, bootstrap the same contract under `.ai-delivery/requirements/<requirement-id>/` instead of inventing another directory or naming scheme.
- Ensure `requirement.md` exists as the authoritative requirement artifact inside that package before writing the downstream breakdown outputs.

### 3. Decide the sub-requirement boundaries

Split by delivery meaning, not by arbitrary technical preference. A sub-requirement should satisfy at least one of these:

- it can be independently developed
- it can be independently integrated
- it can be independently tested or accepted
- it owns one coherent dependency or capability surface

Use only these sub-requirement types:

- `Global Rule`
- `Shared Foundation`
- `Shared Component`
- `Feature Module`
- `Cross-Feature Infrastructure`

Required splitting rules:

- Shared foundations and shared components must be split out before the feature modules that consume them.
- Cross-cutting rules that apply to two or more sub-requirements belong in `global-rules.md`, not in a fake feature module.
- Do not over-split purely for implementation convenience.

### 4. Extract shared rules once

- Move rules that apply across two or more sub-requirements into `global-rules.md`.
- Reference those rules from the affected sub-requirements instead of duplicating them.
- Keep `global-rules.md` focused on cross-cutting truth, not feature-local behavior.

### 5. Write the requirement-level artifacts

- Write `breakdown-summary.md` with the input sources, requirement package path, bootstrap-or-reuse note, sub-requirement index, global blockers, and global open questions.
- Write `dependency-graph.json` so it reflects the sub-requirement DAG and stays acyclic.
- Keep all workflow artifact truth in the business project's `.ai-delivery/requirements/` tree.

### 6. Create or update each sub-requirement package

For each sub-requirement:

- Write `README.md` using `references/subreq-readme-template.md`.
- Write `requirement-slice.md` using `../common/templates/requirement-slice-template.md`.
- Write `dependency.json` with explicit `depends_on` and `blocks` declarations, even when they are empty.
- Write `status.json` with the current status plus blocked-recovery fields such as `blocked_from_status` and `resume_target_status`.
- Seed `traceability.json` as a first-class governed artifact with requirement references and the repo's current bridge fields. If the project already uses `spec_kit_refs`, keep or seed that bridge inside `traceability.json` instead of inventing a second bridge artifact.
- Write `decisions.md` with blocker evidence, bootstrap notes, governed-surface gaps, and any explicitly marked local assumptions.

### 7. Set state conservatively

- Default uncertain slices to `draft`.
- Move a sub-requirement to `split_ready` only when the slice is specific enough for downstream UI mapping and includes clear scope, dependencies, acceptance signals, open questions, and source requirement references.
- When a blocker is raised, record the narrowest blocker from the catalog and preserve the blocked-recovery intent in `status.json`.
- Use the separate admin support surface for governed logging, blocker recording, or status transitions when it is available.

### 8. Re-audit before handoff

- Re-open the original requirement material after writing the artifacts.
- Re-open `breakdown-summary.md`, `global-rules.md`, `dependency-graph.json`, and each sub-requirement folder.
- Verify that no requirement section was silently dropped, the dependency graph is still acyclic, global rules are not duplicated into feature slices, and every sub-requirement has the required files and references.
- If you find a mismatch, fix the artifacts and re-check them before stopping.

## State And Blocker Rules

- Only move a sub-requirement to `split_ready` when the slice is specific enough for downstream UI mapping.
- If the requirement source conflicts with itself or another approved requirement source, block on `blocked_requirement_conflict`.
- If a critical business fact is missing, block on `blocked_missing_requirement`.
- If the boundary is still ambiguous, write the draft plus open questions and stop short of `split_ready`.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not hand-edit around the recovery path later.

## Hard Constraints

- Work only inside `.ai-delivery/requirements/`.
- Do not invent product truth.
- Do not generate Spec Kit spec, plan, or tasks here.
- Do not bind Figma nodes here.
- Do not move workflow truth into `ai-delivery-admin`.
- Do not replace `traceability.json` with an informal note or a second bridge file.

## Output Standard

Every sub-requirement package must preserve:

- clear scope
- explicit type
- explicit dependencies
- acceptance signals
- open questions
- source requirement references

Minimum artifact expectations:

- `breakdown-summary.md`: source inputs, bootstrap-or-reuse note, sub-requirement index, global blockers, global open questions
- `global-rules.md`: only cross-cutting rules that apply across multiple sub-requirements
- `dependency-graph.json`: requirement-level DAG with no invented cycles
- `README.md`: subreq id, title, type, summary, boundary, dependencies, acceptance signals, open questions, current status
- `requirement-slice.md`: metadata, summary, in scope, out of scope, dependencies, acceptance signals, open questions, source requirement references
- `dependency.json`: explicit `depends_on` and `blocks`
- `status.json`: `status`, `blocked_from_status`, and `resume_target_status`
- `traceability.json`: requirement references, empty-or-initial mapping fields, conflicts, verification fields, and existing bridge contract fields when the repo expects them
- `decisions.md`: blockers, recovery notes, bootstrap notes, governed-surface gaps, explicit assumptions

If governed admin support is unavailable, document that missing dependency in local notes or `decisions.md`, but keep artifact truth in `.ai-delivery/`.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] The current approved top-level requirement material was used
- [ ] The correct requirement package was reused or bootstrapped without inventing a new layout
- [ ] No requirement section was silently dropped
- [ ] `global-rules.md` contains only cross-cutting rules
- [ ] Every sub-requirement has a unique id, clear type, and explicit dependency declaration
- [ ] `dependency-graph.json` is acyclic and matches the per-sub-requirement dependencies
- [ ] Every sub-requirement includes `README.md`, `requirement-slice.md`, `dependency.json`, `status.json`, `traceability.json`, and `decisions.md`
- [ ] `status.json` preserves blocked-recovery fields
- [ ] `traceability.json` is treated as a first-class governed artifact
- [ ] Ambiguous slices remain `draft` or blocked instead of being forced to `split_ready`
- [ ] No Figma mapping, interaction design, Spec Kit planning, or invented product logic leaked into this stage

## Pressure Scenarios

Use these as mental regression tests while writing or updating the breakdown.

### Scenario 1: Intake package is missing

Expected behavior:

- bootstrap `.ai-delivery/requirements/<requirement-id>/` using the same governed contract
- ensure `requirement.md` exists
- record the bootstrap note
- do not invent a second directory scheme

### Scenario 2: One rule applies across multiple feature areas

Expected behavior:

- move that rule into `global-rules.md`
- reference it from the affected sub-requirements
- do not create a fake feature module just to store the rule

### Scenario 3: Supporting materials are incomplete, but core requirement truth is sufficient

Expected behavior:

- continue the breakdown
- record the missing supplement under `Open Questions`
- do not invent facts
- do not block unless a critical business fact is missing

### Scenario 4: Two approved requirement sources conflict

Expected behavior:

- block the affected slice on `blocked_requirement_conflict`
- capture the conflicting evidence
- stop short of `split_ready`

### Scenario 5: The requirement folder already contains later-stage files

Expected behavior:

- update only requirement-breakdown-owned artifacts
- preserve `figma-mapping.md` and `interaction-design.md`
- do not erase downstream work

### Scenario 6: The proposed dependency graph becomes cyclical

Expected behavior:

- re-split or hold the affected slices in draft
- do not publish a cyclical `dependency-graph.json` as final

### Scenario 7: The repo already expects bridge data in `traceability.json`

Expected behavior:

- preserve or seed that bridge contract inside `traceability.json`
- do not invent a second bridge artifact

## Handoff

Stop after producing the requirement breakdown package and passing the self-check.

If the user wants to continue, hand the downstream stage the requirement package rooted in `requirement-slice.md`, `global-rules.md`, `dependency.json`, and `traceability.json`. Do not perform UI mapping, interaction design, or implementation planning inside this skill unless the user explicitly asks for the next stage.
