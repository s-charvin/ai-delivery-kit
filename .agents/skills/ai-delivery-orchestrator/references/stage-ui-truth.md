# Stage 2: UI Truth Mapping

## When to run

For each sub-requirement where `ui_bearing: true` and a Figma design source is available.

## Prepare inputs

- Read `requirement-slice.md` from `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.
- Gather Figma file key and target node id.
- Set output directory to the sub-requirement directory.

## Run `ui-truth-mapping`

Feed requirement-slice and design source. Produces one `ui-contract.html` (schema v2) per independent unit, each under its own `<unit-id>/` directory in the sub-requirement. There is no aggregate index file or companion YAML/JSON — each unit's `meta.unit.type` (`page` / `modal` / `shared-component`) and `meta.unit.dependencies` are the sole source for cross-unit relationships and delivery ordering.

`ui-truth-mapping` may dispatch per-unit subagents per its own rules. Orchestrator does not override leaf subagent policy.

## After completion

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

Run once per unit's `ui-contract.html`.

- Set `acceptance_frozen` only when every validator run prints `OK`.
- On failure → `blocked_verification_failure` with validator output; do not advance status.
- Update `status.json`.

Optional batch check:

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

## If no Figma link

- Non-UI sub-requirements: skip (already handled at breakdown).
- UI sub-requirements without design: `blocked_missing_design` (`blocker_scope: slice_local`).

## Next handoff

`acceptance_frozen` → `superpowers:brainstorming` (design mode). See [handoff-table.md](handoff-table.md).
