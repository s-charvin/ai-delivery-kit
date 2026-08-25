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
2. UI Stage 2 Authorization Gate (`CP-UI` — UI production work only after explicit confirmation)
3. UI Truth Mapping Gate (`acceptance_frozen` — UI slices only; non-UI skip)
4. Spec Kit Gate (`spec_ready` → `plan_ready` → `tasks_ready`)
5. Development Gate (`in_dev`)
6. Visual Acceptance Gate (`visual_acceptance_passed` — UI slices only; non-UI skip)
7. Merge Gate (`merged`)

## UI Truth Mapping Gate Notes

- After CP-UI, `ui-truth-mapping` writes a real host-stack component per independent unit in the slice worktree (Flutter: widget + golden PNG) and records v1 pointers, SHA-256 hashes, dependencies, and per-state confirmation/waiver in `contracts/ui-truth-index.json`. Do not generate `ui-contract.html`.
- Each unit's v1 `type` (`page` / `component` / `modal` / `shared-component`) and `dependencies` define delivery ordering (`shared-component` → `page` → `modal`).
- All states must be source-backed, previewed, hashed, and confirmed or explicitly waived before `acceptance_frozen`.
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
- `CP-UI ui_visual_implementation_authorization` — authorized before Stage 2 writes production UI code
- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`

The orchestrator should auto-retry first-pass review or visual-acceptance failures before opening `CP-002`.
