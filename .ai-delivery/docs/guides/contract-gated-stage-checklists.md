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

- `ui-truth-mapping` produces `ui-acceptance-contract.yaml` with frozen component tree, layout, spacing, typography, and states for all screen states.
- `section-map.json` defines delivery slice ordering (`shared-shell` → `page` → `modal`).
- All screen states must be source-backed before `acceptance_frozen` can be set.
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

- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`

The orchestrator should auto-retry first-pass review or visual-acceptance failures before opening `CP-002`.
