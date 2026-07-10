# Stage 3: Design + Spec Kit Pipeline

## When to run

- Design: each sub-requirement at `acceptance_frozen` (UI) or `split_ready` (non-UI) with `design_approved: false`.
- Spec Kit: each sub-requirement with `design_approved: true` and status ready for the next speckit step.

## Brainstorming design (HARD-GATE)

<HARD-GATE>
Do not invoke `speckit-specify`, `speckit-plan`, or `speckit-tasks` until brainstorming design is presented and the user explicitly approves it.
</HARD-GATE>

Feed `superpowers:brainstorming`:

- `requirement-slice.md`
- `ui-acceptance-contract.yaml` (if UI-bearing)
- API docs (if available)
- Dependency graph

Design session should produce:

- Architecture (component tree, data flow, state management)
- Route/navigation design (multi-screen)
- Component decomposition strategy
- Data model sketch
- Error/empty/loading handling plan
- Key technical decisions and trade-offs

Store summary in `notes`. On user approval, set `design_approved: true`.

If design conflicts with YAML contract or requirement → `blocked_spec_mismatch`.

**Pause:** design approval is checkpoint CP-DESIGN. Wait for explicit user approval.

## Spec Kit pipeline

When `design_approved: true`:

1. `speckit-specify` → `spec.md` — audit against YAML screen states (UI).
2. `speckit-plan` → `plan.md` — audit delivery slice ordering.
3. `speckit-tasks` → `tasks.md` — audit granularity, dependency order, file scope.

After each step:

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

Do not fork official `speckit-*` skills to restate repo-local contracts.

## Pause

After all executable subreqs reach `tasks_ready`, enter CP-001 and confirm with user before development.

## API policy

API docs pass directly to Spec Kit and implementation. No separate API mapping stage. Gaps → `integration_deferred` in notes; they do not block UI mapping or shell work.

## Non-UI sub-requirements

- Skip UI Truth Mapping (`acceptance_frozen` not required).
- `split_ready` → design brainstorming → Spec Kit.
- Skip `visual_acceptance_passed` at merge.
