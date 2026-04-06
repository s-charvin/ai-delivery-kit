# API Contract Mapping Checklist

- confirm `requirement-slice.md` is present and safe enough to map
- confirm `traceability.json`, `status.json`, and `decisions.md` were read first
- verify the API contract source exists before treating it as input
- inventory only client-facing contract evidence such as endpoints, fields, status values, pagination, and error semantics
- ignore server-internal implementation detail unless it changes the client-facing contract
- write `api-contract-mapping.md`
- update only `traceability.json.api_contract_mapping`
- preserve existing `spec_kit_refs`, `figma_nodes`, and other non-API traceability fields
- mark `downstream_revalidation` when API conclusions can affect UI mapping or interaction design
- stop on `blocked_missing_api_contract`, `blocked_api_contract_conflict`, `blocked_requirement_api_conflict`, or `blocked_verification_failure`
- do not invent endpoints, fields, or error behavior
