# Logging Checklist

Use this order whenever the separate admin support surface is available.

1. resolve the target project and sub-requirement scope
2. append a start log for the current API contract mapping operation
3. read current blockers, status, and `traceability.json` before mutating artifacts
4. perform the artifact write inside `.ai-delivery/`
5. record any status transition, blocker creation, blocker recovery, or downstream revalidation signal through the governed support surface
6. append a completion or failure log with enough detail to resume after interruption

If the admin support surface is not available yet:

- keep artifact truth in `.ai-delivery/`
- document the missing governed dependency in `decisions.md` or `api-contract-mapping.md`
- do not invent a second state or log store outside the approved architecture
