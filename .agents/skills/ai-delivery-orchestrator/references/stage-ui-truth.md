# Stage 2: UI Truth Mapping

## When to run

For each sub-requirement where `ui_bearing: true` and a Figma design source is available.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- Gather Figma file key and target node id.
- Set output directory to the sub-requirement directory.

## Run `ui-truth-mapping` only (Stage 2)

Stage 2 runs **`ui-truth-mapping` alone**. Do **not** run `figma-design-to-code` here — that skill is an implementation-time consumer, not a contract author. Mixing them in Stage 2 confuses authorship and skips scope/layout gates. Stage 4 does not re-run it by default — implement from the frozen HTML (see [stage-implementation.md](stage-implementation.md)).

Feed requirement-slice and design source. Produces one `ui-contract.html` (schema v2) per independent unit, each under its own `<unit-id>/` directory in the sub-requirement. There is no aggregate index file or companion YAML/JSON — each unit's `meta.unit.type` (`page` / `modal` / `shared-component` / `component`) and `meta.unit.dependencies` are the sole source for cross-unit relationships and delivery ordering.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

**Freeze bar (all required):**

1. Validator prints `OK` for every unit contract.
2. Browser open shows **hydrated default state** in `[data-ui-state-host]` (preview script present); empty host = not frozen.
3. `[data-ui-state-switcher]` can flip every declared state to a matching preview.
4. Contract root matches requirement-slice **In Scope** (minimal ancestor; not an unrelated whole-page dump).
5. Every icon/image/vectorized subtree is evidence-backed: inlined asset bytes (with asset hash), a reused project asset, or a review-panel-noted server-provided placeholder / pending item. Hand-drawn glyphs, `get_structure`-only reconstructions (structure cannot prove paint: opacity/gradient/stroke), and unresolved `data-src` shells fail the bar.
6. The user has manually confirmed each `ui-contract.html` (skip only when the user explicitly waived re-review). The hydrated HTML is the review medium — do not save preview screenshot artifacts.
7. If the contract set changed in this run (contracts added, deleted, replaced, or unit ids changed), the stale-pointer sweep (`ui-truth-mapping` §9) is done: no **active** pointer in `status.json` notes, `visual-acceptance.md`, progress/todo, or breakdown summaries targets a removed/renamed contract. One historical "superseded by …" note line is allowed.
8. Nearby Figma notes / stickies on the **parent SECTION** (not only inside `source_node`) that describe motion / transitions are in `meta.dynamics[]` **and** the review-panel **Motion and transitions** table, with verbatim `hint_text` (source language in JSON; the HTML panel paraphrases in the user's language). Multi-clause notes are **split per unit** — numbered modules on the same canvas often name sibling units, not leftover children of the first nearby card.

## After completion

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

Run once per unit's `ui-contract.html`.

- Set `acceptance_frozen` only when every validator run prints `OK` **and** the freeze bar above is satisfied (hydrated preview + scope alignment + icon asset fidelity + per-contract user confirmation + stale-pointer sweep when the contract set changed).
- On failure → `blocked_verification_failure` with validator output; do not advance status.
- Update `status.json`.

Optional batch check:

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

Besides the status gates, this check rejects **dangling `ui-contract.html` pointers** in the requirement directory (referenced contract path does not exist, and the line is not marked as a historical "deleted / superseded" note). Run it whenever the contract set changed, before setting `acceptance_frozen`.

## If no Figma link

- Non-UI sub-requirements: skip (already handled at breakdown).
- UI sub-requirements without design: `blocked_missing_design` (`blocker_scope: slice_local`).

## Next handoff

`acceptance_frozen` → `design` action. See [handoff-table.md](handoff-table.md).
