---
name: ui-requirement-mapping
description: Use when a sub-requirement already has `requirement-slice.md` and must be bound to verified Figma evidence, screenshot-backed node mappings, or visual blockers before interaction design or implementation.
---

# UI Requirement Mapping

Project-local workflow skill for binding a sub-requirement slice to verified Figma evidence and producing a 1:1 visual implementation contract inside the host repository.

## Purpose

Use this skill after `requirement-breakdown` when a sub-requirement already has `requirement-slice.md` and needs:

- `figma-mapping.md`
- `traceability.json`
- updated `decisions.md` when conflicts or mapping decisions appear

All outputs stay inside the matching `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/` folder.

`figma-mapping.md` may not exist yet in a newly bootstrapped package. This skill owns the first real write of that file.

## Required References

- [Dual Truth Rules](../common/references/dual-truth-rules.md)
- [Blocker Catalog](../common/references/blocker-catalog.md)
- [Logging Checklist](../common/references/logging-checklist.md)
- [Figma Mapping Template](../common/templates/figma-mapping-template.md)
- [Figma Fetch Order](references/figma-fetch-order.md)
- [Mapping Checklist](references/mapping-checklist.md)

## Inputs

- required: `subreq-id`
- required: `requirement-slice.md`
- required: a Figma file or node target
- optional: explicit node list, exported comments, token files, design version hints

## Workflow

1. Read `requirement-slice.md` from the target sub-requirement folder.
2. Follow the Figma retrieval order from `references/figma-fetch-order.md`.
3. Prefer cached evidence from `.ai-delivery/figma-cache/` before making new Figma requests.
4. Do not mark mapping complete without screenshot-backed evidence.
5. Write `figma-mapping.md` and update `traceability.json`.
6. Record shared nodes explicitly instead of silently assigning them to one sub-requirement.
7. Record companion UI explicitly when fidelity requires it.
8. Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

## State And Blocker Rules

- If the requirement defines functionality but Figma has no visual carrier, block on `blocked_missing_design`.
- If Figma shows a visual or state that the requirement explicitly excludes, block on `blocked_requirement_figma_conflict`.
- If evidence is incomplete, do not continue to downstream implementation as if mapping were final.
- Only advance the sub-requirement toward `figma_mapped` when the mapping is screenshot-backed and conflict-reviewed.

## Hard Constraints

- Read `requirement-slice.md` before touching Figma evidence.
- Do not invent pages, fields, components, or states.
- Do not treat `ai-delivery-admin` as a source of visual truth.
- Do not use a top-level section name as the final executable node target.
- Do not complete the mapping without `figma-mapping.md` and `traceability.json`.

## Output Standard

Every mapping must include:

- requirement-to-node mapping
- node-to-requirement mapping
- required UI list
- companion UI list
- shared node list
- missing design evidence list
- conflict list

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing an alternate truth store.
