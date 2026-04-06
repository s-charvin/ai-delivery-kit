<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# Figma Mapping

## Design Target

- `design_source`:
- `design_source_id`:
- `requested_scope`:
- `provider_candidates`:
- `cache_root`:

## Structured Evidence Sources

### Evidence Item 1

- `provider`:
- `artifact_type`:
- `artifact_ref`:
- `raw_payload_ref`:
- `node_ids`:
- `freshness_or_version`:
- `why_trusted`:
- `optional_preview_ref`:

## Requirement To Node Mapping

### Mapping Item 1

- `requirement_point`:
- `provider`:
- `node_ids`:
- `artifact_refs`:
- `evidence_basis`:
- `confidence`:

## Node To Requirement Mapping

### Node Item 1

- `provider`:
- `node_id`:
- `artifact_ref`:
- `requirement_points`:
- `mapping_type`:

## Required UI

- `item`:
- `provider`:
- `node_ids`:
- `artifact_refs`:

## Companion UI

- `item`:
- `why_needed`:
- `provider`:
- `node_ids`:
- `artifact_refs`:

## Shared Nodes

- `node_or_region`:
- `provider`:
- `shared_with`:
- `artifact_refs`:

## Missing Design Evidence

- `requirement_point`:
- `missing_evidence`:
- `attempted_providers`:
- `notes`:

## Conflicts

- `conflict`:
- `providers_or_artifacts`:
- `impact`:
- `resolution_path`:

## Traceability Update Notes

- `preserved_fields`:
- `changed_fields`:
- `provider_or_evidence_refs_handling`:

---

## Template Authoring Rules

1. `figma-mapping.md` is the governed mapping contract for downstream interaction design and implementation. It must be evidence-backed, not screenshot-led.
2. Every mapped requirement point should name the `provider`, the relevant `node_ids`, and one or more raw `artifact_ref` values.
3. `raw_payload_ref` should point to the cached provider artifact, not to a paraphrased summary.
4. The cached artifact referenced by `artifact_ref` should preserve compatibility metadata required by current admin readers as well as provider-aware raw payload fields.
5. Use `why_trusted` and `evidence_basis` to explain why the structured payload is sufficient for the mapping claim.
6. `optional_preview_ref` is optional supporting context only. Never rely on it as the completion gate.
7. If providers disagree, record the disagreement under `Conflicts` instead of silently picking one interpretation.
8. Do not copy the `Template Authoring Rules` or `Template Example` sections into generated mapping artifacts.

## Template Example

```md
# Figma Mapping

## Design Target
- `design_source`: `Figma file`
- `design_source_id`: `abc123`
- `requested_scope`: `Profile Settings edit form`
- `provider_candidates`: `figma-mcp, tempad-dev`
- `cache_root`: `.ai-delivery/figma-cache/abc123/`

## Structured Evidence Sources
### Evidence Item 1
- `provider`: `figma-mcp`
- `artifact_type`: `node`
- `artifact_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `raw_payload_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `node_ids`: `987:654`
- `freshness_or_version`: `verified against current file version`
- `why_trusted`: `The payload includes node type, hierarchy, text label, disabled variant, and parent frame context.`
- `optional_preview_ref`: `.ai-delivery/figma-cache/abc123/artifacts/preview-profile-save-button.json`

## Requirement To Node Mapping
### Mapping Item 1
- `requirement_point`: `Save remains disabled until there is a valid change.`
- `provider`: `figma-mcp`
- `node_ids`: `987:654`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `evidence_basis`: `Structured node payload shows disabled save button variant under the edit form state.`
- `confidence`: `high`

## Node To Requirement Mapping
### Node Item 1
- `provider`: `figma-mcp`
- `node_id`: `987:654`
- `artifact_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `requirement_points`: `Save remains disabled until there is a valid change.`
- `mapping_type`: `direct`

## Required UI
- `item`: `Disabled save button state`
- `provider`: `figma-mcp`
- `node_ids`: `987:654`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`

## Companion UI
- `item`: `Form field dirty-state container`
- `why_needed`: `The button state is only meaningful inside the form state carrier.`
- `provider`: `figma-mcp`
- `node_ids`: `987:610`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-form.json`

## Shared Nodes
- `node_or_region`: `Profile header shell`
- `provider`: `figma-mcp`
- `shared_with`: `profile-settings-shell`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-shell.json`

## Missing Design Evidence
- `requirement_point`: `Retryable avatar upload failure`
- `missing_evidence`: `No explicit error-state node was found in current structured payloads.`
- `attempted_providers`: `figma-mcp, tempad-dev`
- `notes`: `Block or hand back if the failure state is required for mapping completeness.`

## Conflicts
- `conflict`: `TemPad Dev and Figma MCP disagree on whether the disabled save button is a separate variant node or a state inside the parent component.`
- `providers_or_artifacts`: `figma-mcp node-profile-save-button.json; tempad-dev component-save-button.json`
- `impact`: `Could change executable-node granularity.`
- `resolution_path`: `Do not finalize until the executable node boundary is resolved.`

## Traceability Update Notes
- `preserved_fields`: `requirement_refs, spec_kit_refs`
- `changed_fields`: `figma_nodes, confidence, last_verified_at`
- `provider_or_evidence_refs_handling`: `Provider-specific refs remain in figma-mapping.md because traceability.json does not yet define provider-aware evidence fields.`
```
