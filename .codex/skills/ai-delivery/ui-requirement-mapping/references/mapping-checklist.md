# UI Requirement Mapping Checklist

- read `requirement-slice.md`, `traceability.json`, and `status.json` before touching Figma evidence
- prefer starting from `split_ready`; stop and hand back to `requirement-breakdown` if the slice is still unstable
- follow the `Figma retrieval order`
- prefer cached evidence from `.ai-delivery/figma-cache/`
- require screenshot-backed executable nodes
- write `figma-mapping.md`
- update `traceability.json` in place
- preserve existing bridge fields such as `spec_kit_refs`
- record companion UI explicitly
- record shared nodes explicitly
- preserve later-stage files such as `interaction-design.md` when they already exist
- preserve `blocked_from_status` and `resume_target_status` through governed recovery, not hand edits
- stop on `blocked_missing_design`
- stop on `blocked_requirement_figma_conflict`
- stop on `blocked_figma_conflict` or `blocked_verification_failure` when evidence cannot be trusted
- do not invent visual truth
