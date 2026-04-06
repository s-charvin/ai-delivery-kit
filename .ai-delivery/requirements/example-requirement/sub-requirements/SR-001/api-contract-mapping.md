<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-06T00:00:00.000Z","updated_by":"system"} -->

# API Contract Mapping

## Input Contract Sources

- `source_type`: `openapi`
- `source_path_or_ref`: `fixtures/contracts/example-sr-001.openapi.json`
- `validation_status`: `fixture`

## Requirement To API Mapping

- `requirement_point`: `Seed a governed package that can bridge to later stages.`
- `operation_refs`: `POST /fixtures/sr-001/bootstrap`
- `coverage`: `covered`

## API To Requirement Mapping

- `method`: `POST`
- `path`: `/fixtures/sr-001/bootstrap`
- `operation_id`: `bootstrapExampleSubRequirement`
- `mapped_requirement_points`: `Bootstrap governed API contract mapping fixture`

## Request Fields

- `operation_ref`: `POST /fixtures/sr-001/bootstrap`
- `field_path`: `body.subreq_id`
- `field_type`: `string`
- `required`: `true`

## Response Fields

- `operation_ref`: `POST /fixtures/sr-001/bootstrap`
- `field_path`: `response.traceability.api_contract_mapping.status`
- `field_type`: `string`
- `semantics`: `Fixture API mapping readiness`

## Error Semantics

- `operation_ref`: `POST /fixtures/sr-001/bootstrap`
- `status_or_code`: `409`
- `meaning`: `Fixture contract conflict`

## Missing Contracts

- none for fixture scope

## Field Gaps

- none for fixture scope

## Requirement/API Conflicts

- none for fixture scope

## Traceability Update Notes

- `status`: `mapped`
- `downstream_revalidation`: `none`
