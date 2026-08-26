# Framework Guide: spec-kit

Use this tier for `spec` / `plan` / `tasks` actions when spec-kit is installed.

## Detection signs

- `.specify/` directory exists at the repository root, or
- `specify` CLI is available on PATH.

If `.specify/` exists but the CLI is missing or broken, degrade to the native tier for the affected sub-requirement and record the reason in `decisions.md`. Never reinstall or upgrade spec-kit yourself.

## Covered actions

| Action | spec-kit usage | Output artifact |
|--------|----------------|-----------------|
| `spec` | Apply `/speckit-specify` reasoning to `requirement-slice.md` (and reviewed host component + `ui-truth-index.json` for UI slices) | path resolved from layout key `spec` (default `spec/spec.md`) |
| `plan` | Apply `/speckit-plan` reasoning | path resolved from layout key `plan` (default `spec/plan.md`) |
| `tasks` | Apply `/speckit-tasks` reasoning | path resolved from layout key `tasks` (default `spec/tasks.md`) |

## Artifact containment

- Before using a `speckit-*` skill or command, resolve the layout keys `spec`, `plan`, and `tasks` from `.ai-delivery/meta/project-binding.json` via the orchestrator layout resolver, then pass those exact repo-relative canonical paths. The default suffixes are `spec/spec.md`, `spec/plan.md`, and `spec/tasks.md`; never substitute them for a customized binding.
- `.specify/**` is detection/configuration input only. Do not create or update feature specs, plans, tasks, checklists, state, or agent metadata there.
- If a `speckit-*` command insists on persisting under `.specify/**` and cannot accept the canonical map, do not invoke that persistence step. Apply the same workflow in the current session and write its result directly to `.ai-delivery`.
- Do not generate under `.specify/**` and copy back afterward. Run the artifact-boundary audit from [../framework-adaptation.md](../framework-adaptation.md) before advancing status.

## Usage advice

- Feed spec-kit the governed inputs, not free prose: `requirement-slice.md`, each enabled UI truth unit's frozen host component + `ui-truth-index.json`, API docs if available, and the dependency graph.
- For UI truth slices, spec-kit's input is the reviewed host component + v2 `ui-truth-index.json`; reference each unit/scenario id and its evidence origin instead of authoring a second visual description that could drift from the contract.
- Audit each output before advancing status:
  - `spec.md` → audit state transitions, content policies, motion, assets, accessibility, and acceptance criteria against every frozen unit/scenario id (UI) → `spec_ready`
  - `plan.md` → audit delivery slice ordering and scenario implementation/verification ownership → `plan_ready`
  - `tasks.md` → audit granularity, dependency order, file scope, and complete scenario-to-test/acceptance coverage → `tasks_ready`
- If a generated output conflicts with the frozen contract or the requirement, open `blocked_spec_mismatch`; do not silently edit the contract to match.

## Constitution handling

spec-kit projects may define a constitution. Respect it where it does not conflict with `.ai-delivery` governed truth. On conflict, `.ai-delivery` truth wins; record the conflict in `decisions.md`.

## Traceability recording

Use only the canonical `artifacts[]` shape in the sub-requirement `traceability.json`. Add one complete object for each `kind` (`spec`, `plan`, `tasks`); do not emit legacy path fields:

```json
{
  "spec_refs": {
    "tier": "spec-kit",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": "<repo-relative path resolved from layout key spec>",
        "derived_paths": [],
        "content_sha256": "<sha256 of canonical content>",
        "sync_state": "synced"
      }
    ]
  }
}
```

Also add one `source_index.spec` entry per artifact with `ref_type` `spec` / `plan` / `tasks`.

## Boundaries

- Do not fork or restate official `speckit-*` skills inside the repo.
- Do not let spec-kit create process/governance artifacts outside `.ai-delivery/`.
- Do not start `speckit-*` steps while a `design_mode=full` approval is pending (`design_approved: false`); UI truth slices additionally require `acceptance_frozen`.
- spec-kit covers spec-producing actions only; `implement` / `finish` dispatch to superpowers, ECC, or the native tier per [../framework-adaptation.md](../framework-adaptation.md).
