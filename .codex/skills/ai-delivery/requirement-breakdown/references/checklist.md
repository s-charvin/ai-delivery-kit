# Requirement Breakdown Checklist

- confirm the top-level requirement material is the current approved source
- locate or create the correct requirement folder under `.ai-delivery/requirements/`
- extract cross-cutting rules into `global-rules.md`
- produce `breakdown-summary.md`
- produce `dependency-graph.json`
- create sub-requirement folders with `README.md`, `requirement-slice.md`, `dependency.json`, `status.json`, `traceability.json`, and `decisions.md`
- set `split_ready` only when the slice is safe for downstream UI mapping
- stop on `blocked_requirement_conflict` or `blocked_missing_requirement`
- do not invent product truth
