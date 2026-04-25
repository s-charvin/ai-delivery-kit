# Contract-Gated Stage Checklists

## Outward Seven-Stage Checklist

1. Requirement
2. API
3. UI
4. Interaction
5. TDD
6. Review
7. Verification

## Internal Eight Gates

1. Requirement Gate
2. API Contract Gate
3. UI Evidence Gate
4. UI Acceptance Freeze Gate
5. Interaction Gate
6. Execution Prep / Spec Kit Bridge Gate
7. Development And Review Gate
8. Visual Acceptance And Final Verification Gate

## Execution Prep Gate Notes

- `prepare-speckit-context` writes `spec-kit-input.md` from governed `.ai-delivery` slice artifacts.
- Official `speckit-specify`, `speckit-plan`, and `speckit-tasks` run unchanged against that reduced bundle.
- Local audit/bind writes `spec-kit-binding.json` and only then advances `spec_ready`, `plan_ready`, or `tasks_ready`.

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
