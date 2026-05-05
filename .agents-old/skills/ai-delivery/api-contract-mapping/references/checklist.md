# API Contract Mapping Checklist

- confirm `requirement-slice.md` is present and safe enough to map
- confirm `traceability.json`, `status.json`, and `decisions.md` were read first
- verify the API contract source exists before treating it as input
- inventory only client-facing contract evidence such as endpoints, fields, status values, pagination, and error semantics
- verify relation semantics and success side effects, not just endpoint presence
- ignore server-internal implementation detail unless it changes the client-facing contract
- write `api-contract-mapping.md`
- include an Action Side Effects Matrix with request contract, success_return_semantics, error_semantics, local_state_effect, and revalidation_targets
- update only `traceability.json.api_contract_mapping`
- update `action_side_effects`, `propagation_targets`, and `client_semantic_gaps` when the contract reveals downstream state implications
- preserve existing `spec_kit_refs`, `figma_nodes`, and other non-API traceability fields
- mark `downstream_revalidation` when API conclusions can affect UI mapping or interaction design
- stop on `blocked_missing_api_contract`, `blocked_api_contract_conflict`, `blocked_requirement_api_conflict`, or `blocked_verification_failure`
- block rather than guess when endpoint, request fields, response semantics, relation semantics, error mapping, or success side effects are missing
- do not invent endpoints, fields, or error behavior
