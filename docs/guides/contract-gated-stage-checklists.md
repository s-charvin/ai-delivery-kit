# Contract-Gated Stage Checklists

## Outward Capability Checklist

1. Requirement
2. Capability review (UI truth and solution-design modes)
3. Spec Kit (spec → plan → tasks)
4. TDD
5. Review
6. Verification

## Internal Gates

1. Requirement Gate (`split_ready`)
2. UI Truth Capability Gate (`CP-UI` — only `ui_truth_mode=figma` or `runtime-baseline`; UI production work only after explicit confirmation)
3. UI Truth Mapping Gate (`acceptance_frozen` — only enabled UI truth modes)
4. Solution Design Gate (`CP-DESIGN` — only `design_mode=full`; `light` self-reviews, `none` skips)
5. Spec Kit Gate (`spec_ready` → `plan_ready` → `tasks_ready`)
6. Development Gate (`in_dev`)
7. Visual Acceptance Gate (`visual_acceptance_passed` — only enabled UI truth modes)
8. Merge Gate (`merged`)

## UI Truth Mapping Gate Notes

- After CP-UI, `ui-truth-mapping` writes a real host-stack component per independent unit in the user-approved workspace and records a v3 profile/state/scenario/evidence-scope matrix in `contracts/ui-truth-index.json`. Each scenario is `component-only`, `host-static`, or `host-runtime`; host scopes require a real production binding, while unsupported hosts remain component-only with an explicit risk boundary. The current checkout is the default; any worktree requires separate per-slice confirmation and an exact project-local path. Do not generate `ui-contract.html` or a synthetic host. `ui_truth_mode=existing` does not enter this gate.
- Each unit must resolve all ten applicability-gated runtime dimensions: `state`, `layout`, `content`, `interaction`, `motion`, `assets`, `theme`, `accessibility`, `platform`, and `performance`. Applicable but unresolved coverage blocks `acceptance_frozen`.
- State and scenario evidence comes only from `figma`, `requirement`, `project`, or `user-decision`. Only Figma-evidenced scenarios carry a 1:1 Figma claim.
- Each unit's v2 `type` (`page` / `component` / `modal` / `shared-component`) and `dependencies` define delivery ordering (`shared-component` → `page` → `modal`).
- Every visual scenario must have a deterministic preview, SHA-256, and static visual confirmation/waiver bound to the current preview hash before `acceptance_frozen`. Every unit must also have a `motion_decision`: animated motion needs separate motion confirmation/waiver and a later runtime/behavior/manual verification mode; static UI needs an explicit confirmed “static / no motion” decision. When the host can produce deterministic motion output, use GIF only, record its path/hash, and show it to the user; when it cannot, record the reason and defer runtime verification. A golden alone never confirms motion.
- Visible UI must use real host-stack controls and evidence-backed resources. Unapproved placeholders, external visual slots, dummy/fixture visuals, fabricated data, generic icons, painted input shells, and silent fallbacks fail the gate. Missing resources require an explicit user choice to render empty, defer, or block; absent data must render the real empty/omitted state.
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
- structured `visual-acceptance.json` verification against the current index hash and every scenario id
- deterministic Figma reference/candidate/diff verification when a stable reference bitmap exists
- side-by-side checklist

## Orchestrator Checkpoints

- `CP-DESIGN solution_design_approval` — full solution design approved before the `spec` → `plan` → `tasks` pipeline
- `CP-UI ui_visual_implementation_authorization` — authorized before Stage 2 writes production UI code
- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`

The orchestrator should auto-retry first-pass review or visual-acceptance failures before opening `CP-002`.
