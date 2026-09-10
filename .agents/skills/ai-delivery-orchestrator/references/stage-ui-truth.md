# Stage 2: UI Truth Mapping

## When to run

For each `split_ready` sub-requirement where `ui_truth_mode=figma` or `ui_truth_mode=runtime-baseline`, and CP-UI user authorization is recorded. `ui_truth_mode=none` and `existing` do not enter this stage.

Stage 2 is a **controlled visual implementation stage** because it writes production code. It is not implementation-free mapping.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- For `figma`, gather the Figma file key and target node id. For `runtime-baseline`, gather the requirement, project, or user-decision source that defines the runtime baseline; do not invent Figma provenance.
- Judge the host stack from the repo and use a matching framework adapter when available. If unsure, stop and ask.
- Resolve the user-approved workspace under [workspace-policy.md](workspace-policy.md). Use the current checkout unless the user explicitly approved the exact project-local worktree for this sub-requirement; record the choice in `decisions.md` or `progress.md` and reuse it through Stages 3 and 4.

## Run controlled `ui-truth-mapping` only (Stage 2)

Stage 2 runs **`ui-truth-mapping` alone**. Do **not** run `figma-design-to-code` here — that skill is not a contract author. Mixing them in Stage 2 confuses authorship. **Stage 4 does not re-run it by default** — wire the already-written component (see [stage-implementation.md](stage-implementation.md)).

Feed the requirement slice and the mode-appropriate truth source. Produce a **real host-stack component** per independent unit plus an official-stack preview for every visual scenario. Before component code, complete `ui-truth-mapping`'s Runtime Coverage Plan across state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. Applicable gaps require requirement/project/user-decision evidence; unresolved gaps block freeze. Data-bound content with no real value must remain empty/omitted; fixtures are test-harness-only. Every UI unit must make an explicit motion decision: document its motion contract, or explicitly record and confirm “static / no motion”. Static preview confirmation and motion confirmation/waiver are separate gates.

Record governance metadata in the v3 `contracts/ui-truth-index.json`: truth mode and source, design revision when applicable, unit type/source/dependencies, environment profiles, sourced states, concrete scenarios, evidence scopes, host capability decisions, host bindings when supported, complete applicability coverage, repo-relative paths, SHA-256 hashes, and preview-hash-bound confirmation. This metadata is not a second paint truth. Do not generate `ui-contract.html` or translate a parallel preview into the host stack. Figma-origin scenarios preserve evidenced pixels; runtime scenarios from other sources must not be described as 1:1 to Figma.

Keep design evidence layers distinct. A hierarchy/structure response proves node
relationships and bounds; a child asset URL proves only that child asset; an
actual parent export or copied file is the only evidence for that parent's
bytes, dimensions, or hash. Before comparing or adopting an asset, record the
source layer, state, bounds/viewBox, export operation, and local file being
compared. If the tool cannot provide the intended parent export, mark the
comparison unresolved and stop at that boundary; never infer parent equality
from a child URL, a filename, a renderer result, or a mismatched-size hash.
When the design source is revised, invalidate earlier comparison claims until
the current source and target file are re-read.

Before preview generation, make a host capability decision for every scenario and freeze exactly one scope: `component-only`, `host-static`, or `host-runtime`. Check whether host composition is in visual scope, an existing runnable host entrypoint exists, it mounts the production host, required state/resources are deterministic, and it emits a reviewable bounded screenshot. Any critical failure selects `component-only` with an explicit uncovered risk. Do not assemble a synthetic page from components to manufacture host evidence. `host-static` and `host-runtime` require a production `host_binding`; `component-only` has no host binding and makes no host-visual pass claim.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

Within the user-approved workspace, use the Stage 4 implementation discipline for the visual surface: write focused tests first where applicable, run red → green → refactor, generate deterministic goldens, and send the completed unit to a fresh-context code review. Findings must be fixed and re-reviewed before freeze. Record test commands and review outcomes in `progress.md`.

**Freeze bar (all required):**

1. Component compiles / host preview opens.
2. Official preview file exists; chat showed its **absolute path** (the host's static preview, plus a deterministic GIF for animated units when the host can produce one; if GIF motion cannot be recorded, the index records why and defers runtime verification).
3. The v3 `contracts/ui-truth-index.json` validates: repo-relative paths remain inside the **repository root**, hashes match current files, ids/types/stacks/dependencies are valid, profiles and sourced states are complete, every scenario has a valid evidence scope/capability decision, host scopes bind a real production host, every visual scenario has its own preview or explicit preview waiver, and all ten coverage dimensions are resolved.
4. Scope matches requirement-slice **In Scope** (minimal ancestor; not an unrelated whole-page dump).
5. Every icon/image and interactive control is evidence-backed and real. Hand-drawn glyphs, painted input shells, external visual slots, dummy/fixture visuals, fabricated data, and silent fallbacks fail the bar. If a required resource is unavailable, the user must explicitly choose empty rendering, defer, or block; the skill must not choose for them. If a temporary placeholder appears genuinely necessary, ask separately for explicit approval naming its exact scope, and keep it out of production UI/data paths; without that approval it is forbidden.
6. Every visual scenario records static visual confirmation or an explicit waiver with a reason, and `reviewed_preview_sha256` matches its current preview hash. Applicable motion scenarios additionally record motion confirmation or an explicit motion waiver with a reason and later runtime verification mode. When a deterministic GIF exists, its path/hash is recorded in `motion_decision` and shown to the user; when GIF cannot be produced, the index records why and Stage 4 verifies motion through project-native behavior/manual evidence. The official preview is the review medium — do not substitute `contract-preview-*.png`.
7. If the unit set changed in this run, the stale-pointer sweep (`ui-truth-mapping` §9) is done.
8. Runtime coverage, motion lifecycle or explicit no-motion decision, asset/rendering, mask/compositing, accessibility, and fill-hug-fixed notes required by `ui-truth-mapping` are recorded (comments or freeze chat), not as a second paint file. A static golden never substitutes for motion acceptance.
9. Stage 2 tests pass and the latest fresh-context review is clean; the user-approved workspace evidence is recorded for Stage 4 reuse. Stage 4's structured acceptance must include one independent motion acceptance record per indexed unit.
10. The Stage 2 artifact-boundary path audit compares the entry/exit Git status/content fingerprint ledger and the independent filesystem fingerprints required by the containment protocol. The root fingerprints include ignored files and cover every declared external default output root, at least `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, and `openspec/**`; this catches writes hidden by `.gitignore` and repeated writes to paths already dirty at entry. Outside `.ai-delivery/`, only production source, project-native tests, goldens/official previews, and runtime assets may be new or modified. Any new or modified process/governance artifact outside `.ai-delivery/` sets `blocked_verification_failure`; do not freeze or advance status. Record the audit result and exact offending paths in canonical `progress.md`, without deleting pre-existing user files.

## After completion

There is no HTML validator and no active-delivery compatibility branch for earlier schemas. Kit status validation checks the v3 schema, containment, file types, hashes, dependencies, profiles, sourced states, scenarios, evidence scopes, host bindings, complete coverage, and preview-bound confirmation evidence; archived records remain readable under their legacy schema:

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
