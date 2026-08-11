# Framework Guide: OpenSpec

Use this tier for `spec` / `plan` / `tasks` actions when OpenSpec is installed. OpenSpec is a lightweight delta-spec workflow, well suited to brownfield repositories.

## Detection signs

- `openspec/` directory exists at the repository root (`openspec/specs/`, `openspec/changes/`), or
- `openspec` CLI is available on PATH.

Never initialize or install OpenSpec yourself; if detection is ambiguous, ask the user once and record the answer in `decisions.md`.

## Covered actions

One OpenSpec change per sub-requirement: `openspec/changes/<subreq-id-slug>/`.

| Action | OpenSpec usage | Output artifact |
|--------|----------------|-----------------|
| `spec` | Create the change proposal: problem, motivation, proposed behavior delta | `openspec/changes/<name>/proposal.md` (+ capability spec deltas under `specs/`) |
| `plan` | Technical design for the change | `openspec/changes/<name>/design.md` |
| `tasks` | Implementation checklist | `openspec/changes/<name>/tasks.md` |

## Usage advice

- Name the change after the sub-requirement (e.g. `sr-001-friend-badge`) so the mapping stays obvious.
- Seed the proposal from `requirement-slice.md`; for UI-bearing slices the frozen `ui-contract.html` remains the visual source of truth — the proposal describes behavior, not pixels.
- Validate before advancing status: `openspec validate <name>` (when the CLI exists) plus a manual audit against the slice scope.
  - proposal accepted → `spec_ready`
  - `design.md` audited → `plan_ready`
  - `tasks.md` audited (granularity, dependency order, file scope) → `tasks_ready`
- After the slice is merged, run the archive step (`openspec archive <name>`) so the delta lands in `openspec/specs/`. Archive only after `merged`; record the archived spec paths in `traceability.json` at that point.
- The orchestrator's `archive` action additionally freezes the canonical three-piece spec set + `design.md` + `verification.md` into `.ai-delivery/requirements/<req>/sub-requirements/<SR>/archive/<ISO-ts>/` with a `MANIFEST.json` (sha256), independent of the OpenSpec-derived view. Run `openspec archive <name>` for the derived spec and the orchestrator archive for the canonical snapshot.
- If the change conflicts with the frozen contract or the requirement, open `blocked_spec_mismatch` instead of editing the delta until it "passes".

## Traceability recording

In the sub-requirement `traceability.json`:

- `spec_refs.tier`: `"openspec"`
- `spec_refs.spec_path`: `openspec/changes/<name>/proposal.md`
- `spec_refs.plan_path`: `openspec/changes/<name>/design.md`
- `spec_refs.tasks_path`: `openspec/changes/<name>/tasks.md`
- `source_index.spec`: one entry per artifact with `ref_type` `spec` / `plan` / `tasks`

## Boundaries

- One change per sub-requirement; do not merge several slices into one change.
- OpenSpec covers spec-producing actions only; `implement` / `finish` dispatch to superpowers, ECC, or the native tier per [../framework-adaptation.md](../framework-adaptation.md).
