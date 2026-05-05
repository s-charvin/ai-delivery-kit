# Dual Truth Rules

## Source Of Truth

- Requirement owns functional truth.
- API contract owns client-facing interface truth.
- Figma owns visual truth.
- `.ai-delivery/` is the only workflow artifact truth inside the business project.
- `ai-delivery-admin` is a governed support surface, not a replacement truth store.

## Conflict Handling

When Requirement and API contract disagree:

- stop normal execution
- record the mismatch in the relevant requirement folder
- move the affected sub-requirement into the narrowest appropriate blocker state
- do not invent missing fields, endpoints, error semantics, or status values

## Allowed Inference Boundary

Only limited inference is allowed:

- path or operation grouping that does not change client-visible meaning
- protocol file format normalization such as YAML to JSON reading
- reuse of already-established governed naming patterns that do not alter Requirement or API truth

All limited inference must be explicitly documented in `decisions.md` or `api-contract-mapping.md`.
