# Stage 3: Solution Design + Spec Pipeline

Stage 3 runs the `solution-design` action when `design_mode` is `light` or `full`, followed by `spec` → `plan` → `tasks`. `design_mode=none` skips the solution-design artifact and gate. Concrete tooling depends on the framework tier chosen per [framework-adaptation.md](framework-adaptation.md).

Before dispatching any framework action, apply the [artifact containment protocol](framework-adaptation.md#artifact-containment-protocol-required): pass canonical `.ai-delivery` output paths, treat framework directories as read-only inputs, and skip any persistence step that cannot honor the map.

## When to run

- `solution-design`: each sub-requirement at `acceptance_frozen` (when UI truth is enabled) or `split_ready` (otherwise) with `design_mode=light`, or with `design_mode=full` and `design_approved: false`.
- `spec` / `plan` / `tasks`: each sub-requirement whose design mode gate is satisfied, one step at a time per reconcile output.

## Solution-design action (HARD-GATE)

<HARD-GATE>
For `design_mode=full`, after the solution-design session do NOT write plan/spec artifacts of your own before the user approves the design.
Do NOT write solution-design docs into framework-owned directories.
Write the canonical solution design to `design.md` in the user's current conversation language (template: `templates/design-template.md`; remove its language instruction comment); keep `notes` to a one-line pointer only. For `design_mode=light`, set `design_approved=true` after the short record and AI self-review. For `design_mode=full`, set it only after explicit user approval. Then proceed to the `spec` action.
</HARD-GATE>

<HARD-GATE>
Do not run `spec`, `plan`, or `tasks` actions while a `design_mode=full` solution-design gate is pending. `design_mode=light` requires a short design record and self-review; `design_mode=none` requires neither.
</HARD-GATE>

Feed the solution-design session (native flow or the installed framework's design flow, per [framework-adaptation.md](framework-adaptation.md)):

- `requirement-slice.md`
- each enabled UI truth unit's Stage 2 component in the recorded user-approved workspace + valid v2 `ui-truth-index.json` profile/state/scenario/coverage and preview/hash pointers (if `ui_truth_mode=figma` or `runtime-baseline`)
- API docs (if available)
- Dependency graph

The solution-design session should produce:

- Architecture (component tree, data flow, state management)
- Route/navigation design (multi-screen)
- Component decomposition strategy
- Data model sketch
- State machine and data-to-UI transitions, including applicable loading/refreshing/empty/partial/error/offline/auth/permission/disabled behavior
- References to the indexed UI scenario IDs that own runtime coverage; do not duplicate the Runtime Coverage Plan in `design.md`
- Key technical decisions and trade-offs

Write the solution-design summary to `design.md` in the user's current conversation language (one-line pointer in `notes`). For `design_mode=full`, set `design_approved: true` only on user approval; for `design_mode=light`, set it after recording the short design and self-review result without CP-DESIGN.

If the solution design conflicts with the frozen component / confirmed preview or requirement → `blocked_spec_mismatch`.

**Pause:** only `design_mode=full` uses checkpoint CP-DESIGN. Wait for explicit user approval before proceeding.

## Spec pipeline (framework-agnostic)

When the design mode gate is satisfied, execute the actions emitted by reconcile, using the selected tier's guide under [frameworks/](frameworks/):

Before dispatch, resolve the canonical outputs through the binding layout keys `spec`, `plan`, and `tasks`; `spec/spec.md`, `spec/plan.md`, and `spec/tasks.md` are default-layout examples only. Write all human-readable content in the three resolved artifacts in the user's current conversation language. Preserve machine keys, IDs, paths, commands, code symbols, and literal protocol tokens.

1. `spec` → `spec.md` — audit against every frozen unit/scenario id. For UI truth slices the Stage 2 component + confirmed preview set is the visual input, not a separate visual spec document. Preserve the distinction between Figma-origin fidelity and approved runtime behavior.
2. `plan` → `plan.md` — audit delivery slice ordering and identify which task implements or verifies each scenario id.
3. `tasks` → `tasks.md` — audit granularity, dependency order, file scope, and complete scenario-to-test/acceptance coverage.

After each step:

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

Regardless of tier, record artifacts in `traceability.json` `spec_refs` (see [framework-adaptation.md](framework-adaptation.md) → Traceability). Each `artifacts[]` entry for `spec`, `plan`, and `tasks` MUST record its resolved repo-relative `canonical_path` and current `content_sha256` so the artifact-layout validator can detect drift. Do not fork or restate framework pipeline skills to duplicate repo-local contracts.

## Spec persistence (living → in-place archive)

While the sub-requirement is not yet `archived`, the spec is **living**:

- The artifact resolved from layout key `spec` is the single source of truth; artifacts resolved from `plan` and `tasks` are derived and may be regenerated as the spec evolves.
- Before regenerating any derived artifact, move the key decisions being overturned into `decisions.md` first (prevents rationale loss).

Once the sub-requirement reaches `archived`, the canonical spec remains in place:

- The archive action only updates `status.json`; it does not create a snapshot or duplicate canonical artifacts.
- Any requirement change starts a new `<req-id>/` directory; the completed directory remains the historical source of truth.

## Pause

After all executable subreqs reach `tasks_ready`, enter CP-001 and confirm with user before development.

## API policy

API docs pass directly to the spec pipeline and implementation. No separate API mapping stage. Gaps → `integration_deferred` in notes; they do not block read-only UI evidence, while production shell work still waits for CP-UI.

## Modes without a UI truth capability

- `ui_truth_mode=none` or `existing` skips UI Truth Mapping (`acceptance_frozen` not required).
- `split_ready` → `solution-design` only when `design_mode` is `light` or `full` → spec pipeline.
- `existing` uses ordinary project behavior/semantic verification; `none` and `existing` skip `visual_acceptance_passed` at merge.
