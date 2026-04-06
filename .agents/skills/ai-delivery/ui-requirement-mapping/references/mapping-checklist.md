# UI Requirement Mapping Checklist

- read `requirement-slice.md`, `traceability.json`, and `status.json` before touching design evidence
- prefer starting from `split_ready`; stop and hand back to `requirement-breakdown` if the slice is still unstable
- follow the Figma retrieval order
- prefer cached evidence from `.ai-delivery/figma-cache/`
- require trustworthy structured node evidence for every claimed executable node
- record provider, node ids, and raw artifact refs in `figma-mapping.md`
- keep cached artifacts provider-aware with compatibility metadata plus `provider`, `artifact_type`, and provider-native `raw_payload`
- write `figma-mapping.md`
- update `traceability.json` in place
- preserve existing bridge fields such as `spec_kit_refs`
- record companion UI explicitly
- record shared nodes explicitly
- preserve later-stage files such as `interaction-design.md` when they already exist
- preserve `blocked_from_status` and `resume_target_status` through governed recovery, not hand edits
- stop on `blocked_missing_design`
- stop on `blocked_requirement_figma_conflict`
- stop on `blocked_figma_conflict` or `blocked_verification_failure` when structured evidence cannot be trusted
- do not invent visual truth
