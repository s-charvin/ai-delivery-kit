# Figma Fetch Order

1. get structured design context for the target file or node
2. narrow scope with metadata only after the broad structure is known
3. fetch screenshot evidence for the final executable node target
4. fetch comments, assets, and tokens only after the executable node set is stable

Rules:

- prefer cached evidence from `.ai-delivery/figma-cache/`
- refresh only when the user asks, the cache is missing, the cache is stale, or a required node cannot be validated
- do not mark mapping complete without screenshot evidence
- do not map a requirement point using only a node name
- do not use a top-level `SECTION` as the final executable target
