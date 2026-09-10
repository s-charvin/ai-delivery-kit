# Framework Guide: OpenSpec

Use this tier for `spec` / `plan` / `tasks` actions when OpenSpec is installed. OpenSpec is a lightweight delta-spec workflow, well suited to brownfield repositories.

## Detection signs

- `openspec/` directory exists at the repository root (`openspec/specs/`, `openspec/changes/`), or
- `openspec` CLI is available on PATH.

Never initialize or install OpenSpec yourself; if detection is ambiguous, ask the user once and record the answer in `decisions.md`.

## Covered actions

| Action | OpenSpec usage | Output artifact |
|--------|----------------|-----------------|
| `spec` | Apply OpenSpec proposal/delta reasoning to the slice | path resolved from layout key `spec` (default `spec/spec.md`) |
| `plan` | Apply OpenSpec technical-design reasoning | path resolved from layout key `plan` (default `spec/plan.md`) |
| `tasks` | Apply OpenSpec checklist reasoning | path resolved from layout key `tasks` (default `spec/tasks.md`) |

## Artifact containment

- Before using an OpenSpec skill or command, resolve the layout keys `spec`, `plan`, and `tasks` from `.ai-delivery/meta/project-binding.json` via the orchestrator layout resolver, then pass those exact repo-relative canonical paths. The default suffixes are `spec/spec.md`, `spec/plan.md`, and `spec/tasks.md`; never substitute them for a customized binding.
- `openspec/**` is detection/configuration input only. Do not create a change directory, proposal, design, task list, archive, state, or agent/session metadata there.
- If an OpenSpec command requires `openspec/**` persistence and cannot accept the canonical map, do not invoke that persistence step. Apply its proposal/design/task method in the current session and write the result directly to `.ai-delivery`.
- Do not create an OpenSpec change and copy it back afterward. Run the artifact-boundary audit from [../framework-adaptation.md](../framework-adaptation.md) before advancing status.

## Usage advice

- Seed the canonical spec from `requirement-slice.md`; for UI truth slices the frozen host component + confirmed previews remain the visual source of truth. Reference every v3 unit/scenario id, its evidence scope, and its evidence origin; describe runtime behavior and acceptance without restating Runtime Coverage details.
- Validate before advancing status with a manual audit against the slice scope and the kit validators. Run `openspec validate` only if it can validate canonical files without creating or updating `openspec/**`; otherwise skip it and record the reason in `decisions.md`.
- proposal accepted after all state/content/motion/assets/accessibility expectations map to unit/scenario ids and any required state-flow design has a valid review hash → `spec_ready`
  - `design.md` audited for scenario implementation and verification ownership → `plan_ready`
  - `tasks.md` audited for granularity, dependency order, file scope, and complete scenario-to-test/acceptance coverage → `tasks_ready`
- Do not run `openspec archive`; it writes a second governance copy outside `.ai-delivery`. The orchestrator `archive` action only updates `status.json` in place; it does not copy the canonical spec set, `design.md`, or `verification.md`, and does not create `archive/` or `MANIFEST.json`.
- If the change conflicts with the frozen contract or the requirement, open `blocked_spec_mismatch` instead of editing the delta until it "passes".

## Traceability recording

Use only the canonical `artifacts[]` shape in the sub-requirement `traceability.json`. Add one complete object for each `kind` (`spec`, `plan`, `tasks`); do not emit legacy path fields:

```json
{
  "spec_refs": {
    "tier": "openspec",
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

- One canonical spec set per sub-requirement; do not merge several slices into one set.
- Do not let OpenSpec create process/governance artifacts outside `.ai-delivery/`.
- OpenSpec covers spec-producing actions only; `implement` / `finish` dispatch to superpowers, ECC, or the native tier per [../framework-adaptation.md](../framework-adaptation.md).
