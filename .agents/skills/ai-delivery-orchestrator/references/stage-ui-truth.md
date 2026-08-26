# Stage 2: UI Truth Mapping

## When to run

For each `split_ready` sub-requirement where `ui_truth_mode=figma` or `ui_truth_mode=runtime-baseline`, and CP-UI user authorization is recorded. `ui_truth_mode=none` and `existing` do not enter this stage.

Stage 2 is a **controlled visual implementation stage** because it writes production code. It is not implementation-free mapping.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- For `figma`, gather the Figma file key and target node id. For `runtime-baseline`, gather the requirement, project, or user-decision source that defines the runtime baseline; do not invent Figma provenance.
- Judge the host stack from the repo (Flutter first). If unsure, stop and ask.
- Create or reuse one isolated worktree/branch for the slice. Record its branch and path in `decisions.md` or `progress.md`; this same worktree continues through Stages 3 and 4.

## Run controlled `ui-truth-mapping` only (Stage 2)

Stage 2 runs **`ui-truth-mapping` alone**. Do **not** run `figma-design-to-code` here — that skill is not a contract author. Mixing them in Stage 2 confuses authorship. **Stage 4 does not re-run it by default** — wire the already-written component (see [stage-implementation.md](stage-implementation.md)).

Feed the requirement slice and the mode-appropriate truth source. Produce a **real host-stack component** per independent unit (Flutter: widget beside neighbors + golden/behavior tests) plus an official-stack preview for every visual scenario. Before component code, complete `ui-truth-mapping`'s Runtime Coverage Plan across state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. Applicable gaps require requirement/project/user-decision evidence; unresolved gaps block freeze.

Record governance metadata in the v2 `contracts/ui-truth-index.json`: truth mode and source, design revision when applicable, unit type/source/dependencies, environment profiles, sourced states, concrete scenarios, complete applicability coverage, repo-relative paths, SHA-256 hashes, and preview-hash-bound confirmation. This metadata is not a second paint truth. Do not generate `ui-contract.html`. Do not translate HTML into Flutter. Figma-origin scenarios preserve evidenced pixels; runtime scenarios from other sources must not be described as 1:1 to Figma.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

Within the slice worktree, use the Stage 4 implementation discipline for the visual surface: write focused tests first where applicable, run red → green → refactor, generate deterministic goldens, and send the completed unit to a fresh-context code review. Findings must be fixed and re-reviewed before freeze. Record test commands and review outcomes in `progress.md`.

**Freeze bar (all required):**

1. Component compiles / host preview opens.
2. Official preview file exists; chat showed its **absolute path** (Flutter: golden PNG from `flutter test --update-goldens`).
3. The v2 `contracts/ui-truth-index.json` validates: repo-relative paths remain inside the **repository root**, hashes match current files, ids/types/stacks/dependencies are valid, profiles and sourced states are complete, every visual scenario has its own preview, and all ten coverage dimensions are resolved.
4. Scope matches requirement-slice **In Scope** (minimal ancestor; not an unrelated whole-page dump).
5. Every icon/image is evidence-backed. Hand-drawn glyphs fail the bar.
6. Every visual scenario records explicit confirmation or an explicit waiver with a reason, and `reviewed_preview_sha256` matches its current preview hash. The official preview is the review medium — do not substitute `contract-preview-*.png`.
7. If the unit set changed in this run, the stale-pointer sweep (`ui-truth-mapping` §9) is done.
8. Runtime coverage, motion lifecycle, asset/rendering, mask/compositing, accessibility, and fill-hug-fixed notes required by `ui-truth-mapping` are recorded (comments or freeze chat), not as a second paint file.
9. Stage 2 tests pass and the latest fresh-context review is clean; the slice worktree evidence is recorded for Stage 4 reuse.
10. The Stage 2 artifact-boundary path audit compares the entry/exit Git status/content fingerprint ledger and the independent filesystem fingerprints required by the containment protocol. The root fingerprints include ignored files and cover every declared external default output root, at least `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, and `openspec/**`; this catches writes hidden by `.gitignore` and repeated writes to paths already dirty at entry. Outside `.ai-delivery/`, only production source, project-native tests, goldens/official previews, and runtime assets may be new or modified. Any new or modified process/governance artifact outside `.ai-delivery/` sets `blocked_verification_failure`; do not freeze or advance status. Record the audit result and exact offending paths in canonical `progress.md`, without deleting pre-existing user files.

## After completion

There is no HTML validator and no v1 compatibility branch. Kit status validation checks the v2 schema, containment, file types, hashes, dependencies, profiles, sourced states, scenarios, complete coverage, and preview-bound confirmation evidence:

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

- Set `acceptance_frozen` only when the freeze bar is satisfied.
- On failure → `blocked_verification_failure`; do not advance status.
- Update `status.json`.

## If no Figma link

- `ui_truth_mode=none` or `existing`: skip; ordinary project behavior/semantic verification applies.
- `ui_truth_mode=figma` without a valid Figma source: `blocked_missing_design` (`blocker_scope: slice_local`).
- `ui_truth_mode=runtime-baseline` without a requirement, project, or user-decision source: `blocked_missing_visual_truth` (`blocker_scope: slice_local`).

## Next handoff

`acceptance_frozen` → `solution-design` according to `design_mode`. See [handoff-table.md](handoff-table.md).
