# Changelog

## Unreleased

### Fixed

- Archive actions now converge sub-requirement status in place without creating duplicate `archive/<ISO-ts>/` directories or `MANIFEST.json` copies. Delivery reports reference canonical artifact locations, while legacy snapshots remain available for explicit compatibility checks.

## v0.4.1 — 2026-09-02

### Added

- Added an optional, framework-neutral requirement-level `retrospective.md` ledger with a compact archived problem index for progressive, scenario-matched loading. Archive registration is idempotent and does not regenerate ledger content.

### Changed

- `ui-truth-mapping` now requires failure triage before adjusting code: classify the failing layer (compositing/geometry semantics, capture/preview tooling, resource availability, or implementation) and verify the smallest candidate cause first. A visually identical frame without a contrasting source is an evidence limitation, not proof of an effect bug; manufacturing a difference with shadows, fake content, or substitute visuals is prohibited.
- Stage 4 implementation guidance adds a failure-class catalog: async restore must not overwrite live user state; debug gates must be explicit and distinguishable from empty results; runtime completion callbacks are candidate signals guarded by minimum elapsed time; visible-layer swaps need a single owner and atomic handover; one visual entity needs one layout source; distinct states must not collapse into one flag; telemetry must distinguish first entry from state change; intermediate work must stay compilable and never serve as acceptance evidence.
- Stage 4 implementation guidance requires that mid-delivery decision corrections retire superseded tests, wiring, branches, cache behavior, and documentation statements in the same change batch. Temporary protocol assumptions (endpoints, token fields, expiry, error codes, migration facts) must be marked as such and never recorded as confirmed facts.
- English source and the `.agents-zh` mirror are kept in sync for the above guidance.

## v0.4.0 — 2026-09-01

### Changed

- Upgraded `contracts/ui-truth-index.json` to breaking schema v2 with environment profiles, sourced states, concrete scenarios, preview-bound confirmations, and applicability-gated coverage for state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. Schema v1 is rejected.
- Added the required Runtime Coverage Plan before Stage 2 component code. Figma remains 1:1 authority only for evidenced pixels/transitions; runtime gaps must cite the requirement, project rules, or an explicit user decision.
- Replaced Markdown/screenshot-presence visual gates with structured `visual-acceptance.json`, bound to the current index hash and every scenario's visual/behavior evidence. Preview and evidence hash drift invalidate the gate.
- Added independent `ui_truth_mode` (`none`, `existing`, `runtime-baseline`, `figma`) and `design_mode` (`none`, `light`, `full`) axes. UI truth is capability-gated; `design_mode=full` is the only mode requiring CP-DESIGN.
- Renamed the human-facing abstract action to `solution-design` while keeping the canonical `design.md` path and machine `design_approved`/`CP-DESIGN` tokens stable.
- Design artifacts now reference indexed unit/scenario IDs; Runtime Coverage remains authoritative in `contracts/ui-truth-index.json` instead of being duplicated in `design.md`.
- Propagated unit/scenario traceability through solution-design, spec, plan, tasks, implementation, verification, bootstrap layout, English sources, and the `.agents-zh` mirror.
- `ui-truth-mapping` now resolves composed vector/image assets at the semantic component boundary instead of downloading leaves and reconstructing them in layout code.
- Editable inputs require an explicit empty / editing / completed plus IME-hidden / IME-shown matrix. Icons and decorations follow real control state, not page or layout identity.
- Text pre-measurement must use the same resolved typography, scaler, and constraints as the renderer, so geometry does not jump without a real wrap or line-count change.
- Motion GIFs must cover the complete trigger-to-settled transition or one full loop, keep only a short hold, replay automatically, and decode to the expected 25 FPS frame count and duration. Passing an old golden baseline is not evidence that the current matrix was regenerated.
- Requirement breakdown classifies supporting sources by content, not filename. Pending/to-confirm labels record `unknown`; they do not authorize omission. Non-visual state machines are not deferred because Figma is missing.
- Stage 4 and change-scenario guidance reuse the host's existing API/client/injection path. Do not invent a parallel adapter solely for one new operation or easier testing.

## v0.3.7 — 2026-08-24

### Changed

- Stage 2 freezes **real host-stack components** (Flutter first: widget + `flutter test --update-goldens` PNG). `contracts/ui-truth-index.json` stores repo-relative pointers only. Do not generate `ui-contract.html`. Do not translate HTML into Flutter.
- Stage 4 wires the already-landed component (API / route / state / mount). Visual truth is the confirmed official preview, not a second HTML redraw.
- Removed HTML contract template, HTML validator, UI git hooks, and `ui-contract-gate` rules. Layout key is `ui_truth_index`.

## v0.3.6 — 2026-08-17

### Changed

- `ui-truth-mapping`: overlapping same-bounds fills/gradients or Figma masks are **paint × mask compositing**, not a second `src-over` overlay. Run §3b; record `data-ui-composite` / `dt[data-ui-compositing]`; never copy TemPad `data-hint-*` into frozen HTML.

## v0.3.5 — 2026-08-14

### Changed

- `ui-truth-mapping`: variable content must record overflow / min / max or stop and ask. Validator requires `dt[data-ui-sizing]` plus a truth-node annotation. Implementation must consume the sizing table, not dump snapshot px as layout constants.

## v0.3.4 — 2026-08-14

### Changed

- `ai-delivery-orchestrator` Stage 4: implement from the frozen `ui-contract.html`. Do not re-query TemPad / run `figma-design-to-code` as a pre-implement ritual (only when the contract is missing geometry, visual acceptance cannot be resolved from HTML, or the user asks). Live TemPad vs contract → contract wins.
- `ui-truth-mapping`: restore YAML-era **fill detection rule**. `get_code` px is an artboard snapshot; classify `data-ui-sizing="fill|hug|fixed"` so implementers stretch with parent insets instead of hardcoding snapshot widths.

## v0.3.3 — 2026-08-13

### Changed

- `ui-truth-mapping`: when the user names an existing implementation as the motion to reuse, read it first; preview mechanics must match the reference (get_code packing must not silently invert growth/reveal).

## v0.3.2 — 2026-08-13

### Changed

- `ui-truth-mapping`: split multi-clause SECTION motion notes onto the units they name; treat uneven coverage of the same chrome as an anomaly (stop and ask); require a coverage review after every dynamics prune.

## v0.3.1 — 2026-08-13

### Changed

- `ui-truth-mapping`: treat Figma notes on the **parent SECTION / canvas siblings** (not only inside `source_node`) as first-class motion evidence; keep `meta.dynamics[]` in sync with the review-panel motion table; map loading→success notes to `prototype-transition`; write the review panel in the user's language.

## v0.3.0 — 2026-08-13

Unified artifact layout refactor.

**Applies only to new `ai-delivery init` repositories.** No automatic migration for existing layouts.

### Added

- Canonical artifact home under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR>/` (`design.md`, `verification.md`, `spec/{spec,plan,tasks}.md`, `contracts/ui-contract-index.json`, `archive/<ISO-ts>/` + `MANIFEST.json`)
- `project-binding.json` → `layout` path constants (skill `layout.py`; mirror in coordination repo `config/paths.py`)
- `scripts/validate-artifact-layout.py`, `scripts/archive-subrequirement.py`
- Spec persistence policy (`living` / `flow_forward`) and `verification.md` gate at `merged` / `archived`
- OpenSpec-style closure: `merged` → `archive` action → `archived` terminal state, CP-ARCHIVE, `delivery-report.md`
- Coordination: [`s-charvin/ai-delivery-coordination`](https://github.com/s-charvin/ai-delivery-coordination) is a **separate skill + MCP service** (not vendored in this repo); install separately when multi-party work is needed

### Changed

- **`merged` vs `archived`**: `merged` = code integrated; `archived` = immutable freeze; requirement `completed` when all executable subreqs are `archived`
- Reconcile terminal status is `archived` (not `merged`)
- `native` tier: separate `spec/plan.md` and `spec/tasks.md` (no `plan_path → tasks.md` shortcut)
- Coordination MCP (optional, separate install) uses write-through SQLite STORE — see ai-delivery-coordination repo

### Coordination

Independent repository + MCP service only. **Removed** git submodule from ai-delivery-kit. `.ai-delivery/` does not contain coordination code or config.

### Completed in this refactor

- Moved `.ai-delivery/requirements/example-requirement/` → `tests/ai-delivery-contracts/fixtures/example-requirement/`; `zero-based-flow.test.sh` copies the fixture into a temp dir before asserting.
- IDE hooks 4× → 1 canonical + bootstrap-generated 2-line wrappers (`.cursor` / `.claude` / `.codex`)
- Reconcile dependency-graph-only path + `layout.resolve_validator_script` single entry
- Coordination MCP: lightweight `hub://` artifact pointers + claim/status tools (`register_artifact_ref`, `claim_node`, `report_node_status`, …); parties self-manage storage
