# API Contract Mapping Checklist

- confirm `requirement-slice.md` is present and safe enough to map
- confirm `traceability.json`, `status.json`, and `decisions.md` were read first
- verify the API contract source exists before treating it as input
- inventory only client-facing contract evidence such as endpoints, fields, status values, pagination, and error semantics
- ignore server-internal implementation detail unless it changes the client-facing contract
- classify findings as `known_gap`, `integration_risk`, or `blocking_conflict`
- write `api-contract-mapping.md`
- update only `traceability.json.api_contract_mapping`
- preserve existing `spec_kit_refs`, `figma_nodes`, and other non-API traceability fields
- keep early frontend stages moving when API truth is absent or partial
- mark `downstream_revalidation` only when API conclusions can affect UI mapping or interaction design in a user-visible way
- stop on `blocked_api_contract_conflict`, `blocked_requirement_api_conflict`, or `blocked_verification_failure` only when current-stage output would otherwise become misleading
- do not invent endpoints, fields, or error behavior
