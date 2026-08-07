# Stage 3: Design + Spec Pipeline

Stage 3 runs two abstract actions: `design` (approval-gated) and `spec` → `plan` → `tasks`. Concrete tooling depends on the framework tier chosen per [framework-adaptation.md](framework-adaptation.md).

## When to run

- `design`: each sub-requirement at `acceptance_frozen` (UI) or `split_ready` (non-UI) with `design_approved: false`.
- `spec` / `plan` / `tasks`: each sub-requirement with `design_approved: true`, one step at a time per reconcile output.

## Design action (HARD-GATE)

<HARD-GATE>
Orchestrator design-mode: after the design session, do NOT write plan/spec artifacts of your own before the user approves the design.
Do NOT write design docs into framework-owned directories.
Store the summary in subreq `notes`; set `design_approved=true` only after user approval; then proceed to the `spec` action.
</HARD-GATE>

<HARD-GATE>
Do not run `spec`, `plan`, or `tasks` actions until the design is presented and the user explicitly approves it.
</HARD-GATE>

Feed the design session (native flow or the installed framework's design flow, per [framework-adaptation.md](framework-adaptation.md)):

- `requirement-slice.md`
- each unit's `ui-contract.html` (if UI-bearing)
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

If design conflicts with the HTML contract or requirement → `blocked_spec_mismatch`.

**Pause:** design approval is checkpoint CP-DESIGN. Wait for explicit user approval.

## Spec pipeline (framework-agnostic)

When `design_approved: true`, execute the actions emitted by reconcile, using the selected tier's guide under [frameworks/](frameworks/):

1. `spec` → `spec.md` — audit against the HTML contract's states (UI). For UI slices the reviewed `ui-contract.html` is the visual input, not a separate spec document.
2. `plan` → `plan.md` — audit delivery slice ordering.
3. `tasks` → `tasks.md` — audit granularity, dependency order, file scope.

After each step:

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

Regardless of tier, record artifacts in `traceability.json` `spec_refs` (see [framework-adaptation.md](framework-adaptation.md) → Traceability). Do not fork or restate framework pipeline skills to duplicate repo-local contracts.

## Pause

After all executable subreqs reach `tasks_ready`, enter CP-001 and confirm with user before development.

## API policy

API docs pass directly to the spec pipeline and implementation. No separate API mapping stage. Gaps → `integration_deferred` in notes; they do not block UI mapping or shell work.

## Non-UI sub-requirements

- Skip UI Truth Mapping (`acceptance_frozen` not required).
- `split_ready` → `design` → spec pipeline.
- Skip `visual_acceptance_passed` at merge.
