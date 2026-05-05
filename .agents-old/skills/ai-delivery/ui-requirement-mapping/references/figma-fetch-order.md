# Figma Fetch Order

1. identify the design source and preferred provider order
2. fetch structured file or page context for the target source
3. narrow to candidate executable nodes using structured node payloads
4. fetch supporting structured artifacts such as comments, tokens, or assets only after the executable node set is stable
5. fetch optional previews or screenshots only when the user asks for them or when they help human review

Rules:

- prefer cached evidence from `.ai-delivery/figma-cache/`
- cache each artifact with a minimal wrapper that preserves compatibility metadata plus `provider`, `artifact_type`, and the provider-native `raw_payload`
- preserve compatibility metadata required by current admin readers such as `figma_file_id`, `node_id`, `last_updated_at`, and `freshness`
- keep provider payloads in their original response shape instead of flattening them into a custom cache schema
- do not mark mapping complete without trustworthy structured node payloads for each claimed executable node
- do not map a requirement point using only a node name, screenshot, preview, or prose description
- do not use a top-level `SECTION` as the final executable target
- use previews only as optional supporting context; they never override structured evidence
