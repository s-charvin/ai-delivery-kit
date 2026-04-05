# Requirement Breakdown Checklist

- confirm the top-level requirement material is the current approved source
- reuse the existing requirement package when possible; otherwise bootstrap the same governed contract under `.ai-delivery/requirements/`
- ensure `requirement.md` exists before writing downstream breakdown artifacts
- extract cross-cutting rules into `global-rules.md`
- produce `breakdown-summary.md`
- produce an acyclic `dependency-graph.json`
- create or update sub-requirement folders with `README.md`, `requirement-slice.md`, `dependency.json`, `status.json`, `traceability.json`, and `decisions.md`
- keep `status.json` blocked-recovery fields such as `blocked_from_status` and `resume_target_status`
- keep `traceability.json` as a first-class governed artifact, including existing bridge fields when the repo expects them
- set `split_ready` only when the slice is safe for downstream UI mapping
- stop on `blocked_requirement_conflict` or `blocked_missing_requirement`
- preserve later-stage files such as `figma-mapping.md` and `interaction-design.md` when they already exist
- do not invent product truth
