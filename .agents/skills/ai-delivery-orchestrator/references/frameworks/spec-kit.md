# Framework Guide: spec-kit

Use this tier for `spec` / `plan` / `tasks` actions when spec-kit is installed.

## Detection signs

- `.specify/` directory exists at the repository root, or
- `specify` CLI is available on PATH.

If `.specify/` exists but the CLI is missing or broken, degrade to the native tier for the affected sub-requirement and record the reason in `decisions.md`. Never reinstall or upgrade spec-kit yourself.

## Covered actions

| Action | spec-kit usage | Output artifact |
|--------|----------------|-----------------|
| `spec` | `/speckit-specify` seeded from `requirement-slice.md` (and reviewed `ui-contract.html` for UI slices) | `spec.md` under the spec-kit feature branch area (`.specify/`) |
| `plan` | `/speckit-plan` | `plan.md` |
| `tasks` | `/speckit-tasks` | `tasks.md` |

## Usage advice

- Feed spec-kit the governed inputs, not free prose: `requirement-slice.md`, each unit's frozen `ui-contract.html` (UI-bearing), API docs if available, and the dependency graph.
- For UI-bearing slices, spec-kit's input is the reviewed `ui-contract.html`; do not author a second visual description that could drift from the contract.
- Audit each output before advancing status:
  - `spec.md` → audit against the HTML contract's states (UI) → `spec_ready`
  - `plan.md` → audit delivery slice ordering → `plan_ready`
  - `tasks.md` → audit granularity, dependency order, file scope → `tasks_ready`
- If a generated output conflicts with the frozen contract or the requirement, open `blocked_spec_mismatch`; do not silently edit the contract to match.

## Constitution handling

spec-kit projects may define a constitution. Respect it where it does not conflict with `.ai-delivery` governed truth. On conflict, `.ai-delivery` truth wins; record the conflict in `decisions.md`.

## Traceability recording

In the sub-requirement `traceability.json`:

- `spec_refs.tier`: `"spec-kit"`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`: paths of the generated `spec.md` / `plan.md` / `tasks.md`
- `source_index.spec`: one entry per artifact with `ref_type` `spec` / `plan` / `tasks`

## Boundaries

- Do not fork or restate official `speckit-*` skills inside the repo.
- Do not start `speckit-*` steps before design approval (`design_approved: true`); UI slices additionally require `acceptance_frozen`.
- spec-kit covers spec-producing actions only; `implement` / `finish` dispatch to superpowers, ECC, or the native tier per [../framework-adaptation.md](../framework-adaptation.md).
