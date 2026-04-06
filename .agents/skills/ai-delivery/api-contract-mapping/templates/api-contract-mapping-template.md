<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# API Contract Mapping

## Input Contract Sources

### Source Item 1

- `source_type`: `swagger | openapi | json | yaml | other`
- `source_path_or_ref`:
- `version_or_revision`:
- `scope_notes`:
- `validation_status`:

## Requirement To API Mapping

### Mapping Item 1

- `requirement_point`:
- `source_ref`:
- `operation_refs`:
- `coverage`: `covered | partial | not_covered`
- `notes`:

## API To Requirement Mapping

### Operation Item 1

- `method`:
- `path`:
- `operation_id`:
- `mapped_requirement_points`:
- `notes`:

## Request Fields

### Request Item 1

- `operation_ref`:
- `field_path`:
- `field_type`:
- `required`:
- `semantics`:
- `requirement_basis`:

## Response Fields

### Response Item 1

- `operation_ref`:
- `field_path`:
- `field_type`:
- `semantics`:
- `requirement_basis`:

## Error Semantics

### Error Item 1

- `operation_ref`:
- `status_or_code`:
- `surface`:
- `meaning`:
- `requirement_basis`:

## Frontend Development Posture

- `posture`: `ui_safe_to_proceed | interaction_safe_to_proceed | implementation_risk_only | needs_revalidation | blocking_conflict`
- `summary`:
- `current_stage_impact`:

## Frontend Reservation Points

### Reservation Item 1

- `ui_or_interaction_surface`:
- `reservation_reason`:
- `expected_late_binding_point`:
- `impact_level`: `known_gap | integration_risk | blocking_conflict`

## Known Gaps

### Known Gap Item 1

- `gap`:
- `why_open`:
- `affected_requirement_points`:
- `impact_level`: `known_gap | integration_risk | blocking_conflict`

## Field Gaps

### Gap Item 1

- `location`:
- `gap_type`: `field_gap | semantic_gap`
- `needed_additions`:
- `affected_requirement_points`:

## Integration Risks

### Risk Item 1

- `risk`:
- `why_later_stage_only`:
- `likely_owner`: `implementation | integration | backend-alignment`
- `affected_requirement_points`:

## Requirement/API Conflicts

### Conflict Item 1

- `issue`:
- `requirement_ref`:
- `api_ref`:
- `impact`:
- `resolution_path`:

## Traceability Update Notes

- `status`:
- `source_refs_handling`:
- `operation_refs_handling`:
- `downstream_revalidation`:

---

## Template Authoring Rules

1. `api-contract-mapping.md` is the governed human-readable API mapping contract for one sub-requirement.
2. Only document client-facing interface truth. Do not analyze server-internal implementation.
3. `Requirement To API Mapping` and `API To Requirement Mapping` should both be explicit so gaps and overreach are visible.
4. If the API contract is missing fields or semantics, record them under `Known Gaps`, `Field Gaps`, `Frontend Reservation Points`, or `Integration Risks` instead of guessing.
5. Missing or partial contracts do not block early frontend stages by default. Only use `Requirement/API Conflicts` for cases that make current-stage output materially wrong or require revalidation.
6. `Traceability Update Notes` should explain what was written into `traceability.json.api_contract_mapping`.
7. Do not copy the `Template Authoring Rules` or `Template Example` sections into generated artifacts.

## Template Example

```md
# API Contract Mapping

## Input Contract Sources
### Source Item 1
- `source_type`: `openapi`
- `source_path_or_ref`: `contracts/profile-settings.openapi.yaml`
- `version_or_revision`: `2026-04-06`
- `scope_notes`: `Covers profile settings update endpoints.`
- `validation_status`: `parsed`

## Requirement To API Mapping
### Mapping Item 1
- `requirement_point`: `Users can rename a project from Settings.`
- `source_ref`: `requirement.md#L12-L15`
- `operation_refs`: `PATCH /projects/{projectId}`
- `coverage`: `partial`
- `notes`: `The endpoint exists but does not expose save-gating semantics directly.`

## API To Requirement Mapping
### Operation Item 1
- `method`: `PATCH`
- `path`: `/projects/{projectId}`
- `operation_id`: `updateProject`
- `mapped_requirement_points`: `Rename project from Settings`
- `notes`: `No separate endpoint is required for the rename action.`

## Request Fields
### Request Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `field_path`: `body.name`
- `field_type`: `string`
- `required`: `true`
- `semantics`: `New project name`
- `requirement_basis`: `requirement.md#L12-L15`

## Response Fields
### Response Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `field_path`: `response.name`
- `field_type`: `string`
- `semantics`: `Updated project name`
- `requirement_basis`: `requirement.md#L12-L15`

## Error Semantics
### Error Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `status_or_code`: `409`
- `surface`: `inline validation or toast`
- `meaning`: `Name conflict`
- `requirement_basis`: `Open Question`

## Frontend Development Posture
- `posture`: `implementation_risk_only`
- `summary`: `Requirement, UI mapping, and interaction work can proceed, but final validation and save handling need late implementation review.`
- `current_stage_impact`: `No early-stage blocker.`

## Frontend Reservation Points
### Reservation Item 1
- `ui_or_interaction_surface`: `Save button loading and inline validation state`
- `reservation_reason`: `Backend validation semantics are not fully specified yet.`
- `expected_late_binding_point`: `Viewmodel submit handling`
- `impact_level`: `integration_risk`

## Known Gaps
### Known Gap Item 1
- `gap`: `No dedicated validation preview endpoint`
- `why_open`: `Requirement mentions disabled-save logic, but the contract does not expose additional server validation detail.`
- `affected_requirement_points`: `Save gating`
- `impact_level`: `known_gap`

## Field Gaps
### Gap Item 1
- `location`: `PATCH /projects/{projectId} response`
- `gap_type`: `semantic_gap`
- `needed_additions`: `Clarify whether unchanged names return a no-op response or a validation error.`
- `affected_requirement_points`: `Save gating`

## Integration Risks
### Risk Item 1
- `risk`: `Submit handling may need to branch between no-op, inline validation, and retryable save failure once backend semantics settle.`
- `why_later_stage_only`: `This affects implementation wiring more than early UI or interaction shape.`
- `likely_owner`: `implementation`
- `affected_requirement_points`: `Save gating; error feedback`

## Requirement/API Conflicts
### Conflict Item 1
- `issue`: `Requirement expects retryable error semantics, but the API contract only exposes a generic 500.`
- `requirement_ref`: `requirement.md#L17-L18`
- `api_ref`: `contracts/profile-settings.openapi.yaml#/paths/...`
- `impact`: `Interaction and error-surface decisions cannot be finalized safely.`
- `resolution_path`: `Block and request clarified client-facing error semantics.`

## Traceability Update Notes
- `status`: `mapped`
- `source_refs_handling`: `Recorded in traceability.json.api_contract_mapping.source_refs`
- `operation_refs_handling`: `Recorded in traceability.json.api_contract_mapping.operation_refs`
- `downstream_revalidation`: `Only required if later API truth changes user-visible save or error behavior`
```
