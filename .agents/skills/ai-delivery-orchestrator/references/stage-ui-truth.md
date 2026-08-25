# Stage 2: UI Truth Mapping

## When to run

For each `split_ready` sub-requirement where `ui_bearing: true`, a Figma design source is available, and CP-UI user authorization is recorded.

Stage 2 is a **controlled visual implementation stage** because it writes production code. It is not implementation-free mapping.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- Gather Figma file key and target node id.
- Judge the host stack from the repo (Flutter first). If unsure, stop and ask.
- Create or reuse one isolated worktree/branch for the slice. Record its branch and path in `decisions.md` or `progress.md`; this same worktree continues through Stages 3 and 4.

## Run controlled `ui-truth-mapping` only (Stage 2)

Stage 2 runs **`ui-truth-mapping` alone**. Do **not** run `figma-design-to-code` here — that skill is not a contract author. Mixing them in Stage 2 confuses authorship. **Stage 4 does not re-run it by default** — wire the already-written component (see [stage-implementation.md](stage-implementation.md)).

Feed requirement-slice and design source. Produce a **real host-stack component** per independent unit (Flutter: widget beside neighbors + golden test) plus an official-stack preview. Record governance metadata in the v1 `contracts/ui-truth-index.json`: design revision, unit type/source/dependencies, per-state preview and confirmation/waiver, repo-relative paths, and SHA-256 hashes. This metadata is not a second paint truth. Do not generate `ui-contract.html`. Do not translate HTML into Flutter.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

Within the slice worktree, use the Stage 4 implementation discipline for the visual surface: write focused tests first where applicable, run red → green → refactor, generate deterministic goldens, and send the completed unit to a fresh-context code review. Findings must be fixed and re-reviewed before freeze. Record test commands and review outcomes in `progress.md`.

**Freeze bar (all required):**

1. Component compiles / host preview opens.
2. Official preview file exists; chat showed its **absolute path** (Flutter: golden PNG from `flutter test --update-goldens`).
3. The v1 `contracts/ui-truth-index.json` validates: repo-relative paths remain inside the **repository root**, hashes match current files, ids/types/stacks/dependencies are valid, and every reviewable state has its own preview.
4. Scope matches requirement-slice **In Scope** (minimal ancestor; not an unrelated whole-page dump).
5. Every icon/image is evidence-backed. Hand-drawn glyphs fail the bar.
6. Every state records explicit user confirmation or an explicit waiver with a reason. The official preview is the review medium — do not substitute `contract-preview-*.png`.
7. If the unit set changed in this run, the stale-pointer sweep (`ui-truth-mapping` §9) is done.
8. Motion / mask / fill-hug-fixed notes required by `ui-truth-mapping` are recorded (comments or freeze chat), not as a second paint file.
9. Stage 2 tests pass and the latest fresh-context review is clean; the slice worktree evidence is recorded for Stage 4 reuse.

## After completion

There is no HTML validator. Kit status validation checks the v1 schema, containment, file types, hashes, dependencies, states, and confirmation evidence:

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

- Set `acceptance_frozen` only when the freeze bar is satisfied.
- On failure → `blocked_verification_failure`; do not advance status.
- Update `status.json`.

## If no Figma link

- Non-UI sub-requirements: skip (already handled at breakdown).
- UI sub-requirements without design: `blocked_missing_design` (`blocker_scope: slice_local`).

## Next handoff

`acceptance_frozen` → `design` action. See [handoff-table.md](handoff-table.md).
