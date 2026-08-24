# Stage 2: UI Truth Mapping

## When to run

For each sub-requirement where `ui_bearing: true` and a Figma design source is available.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- Gather Figma file key and target node id.
- Judge the host stack from the repo (Flutter first). If unsure, stop and ask.

## Run `ui-truth-mapping` only (Stage 2)

Stage 2 runs **`ui-truth-mapping` alone**. Do **not** run `figma-design-to-code` here — that skill is not a contract author. Mixing them in Stage 2 confuses authorship. **Stage 4 does not re-run it by default** — wire the already-written component (see [stage-implementation.md](stage-implementation.md)).

Feed requirement-slice and design source. Produce a **real host-stack component** per independent unit (Flutter: widget beside neighbors + golden test) plus an official-stack preview. Record pointers only in `contracts/ui-truth-index.json` (repo-relative `component_path`, `preview_path`, Flutter `golden_test`). Do not generate `ui-contract.html`. Do not translate HTML into Flutter.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

**Freeze bar (all required):**

1. Component compiles / host preview opens.
2. Official preview file exists; chat showed its **absolute path** (Flutter: golden PNG from `flutter test --update-goldens`).
3. `contracts/ui-truth-index.json` lists repo-relative paths that exist from the **repository root**.
4. Scope matches requirement-slice **In Scope** (minimal ancestor; not an unrelated whole-page dump).
5. Every icon/image is evidence-backed. Hand-drawn glyphs fail the bar.
6. The user has manually confirmed each preview (skip only when the user explicitly waived re-review). The official preview is the review medium — do not substitute `contract-preview-*.png`.
7. If the unit set changed in this run, the stale-pointer sweep (`ui-truth-mapping` §9) is done.
8. Motion / mask / fill-hug-fixed notes required by `ui-truth-mapping` are recorded (comments or freeze chat), not as a second paint file.

## After completion

There is no HTML validator. Kit status validation checks the index and listed files:

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
