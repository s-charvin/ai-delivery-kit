# Contract-Gated Stage Checklists

## Outward Six-Stage Checklist

1. Requirement
2. UI Truth Mapping
3. Spec Kit (spec → plan → tasks)
4. TDD
5. Review
6. Verification

## Internal Six Gates

1. Requirement Gate (`split_ready`)
2. UI Truth Mapping Gate (`acceptance_frozen` — UI slices only; non-UI skip)
3. Spec Kit Gate (`spec_ready` → `plan_ready` → `tasks_ready`)
4. Development Gate (`in_dev`)
5. Visual Acceptance Gate (`visual_acceptance_passed` — UI slices only; non-UI skip)
6. Merge Gate (`merged`)

## UI Truth Mapping Gate Notes

- `ui-truth-mapping` produces one `ui-contract.html` (schema v2) per independent unit, freezing that unit's component tree, layout, spacing, typography, and states (`<template data-ui-state>` blocks) — no companion YAML or JSON file.
- Each unit's embedded `meta.unit.type` (`page` / `modal` / `shared-component`) and `meta.unit.dependencies` define delivery slice ordering (`shared-component` → `page` → `modal`).
- All states must be source-backed before the contract's `delivery.status` can be `frozen`.
- API docs are passed directly to implementation — not part of this gate.

## Review Extension

- empty callback audit
- reachable TODO audit
- only-close-page-without-business-action audit
- navigation conflict audit
- propagation target audit
- acceptance contract implementation audit

## Verification Extension

- action closure verification
- visual acceptance verification
- MCP frame/state re-check
- side-by-side checklist

## Orchestrator Checkpoints

- `CP-DESIGN design_approval` — design approved before the `spec` → `plan` → `tasks` pipeline
- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`

The orchestrator should auto-retry first-pass review or visual-acceptance failures before opening `CP-002`.
