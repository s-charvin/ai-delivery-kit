# Figma Fetch Order

1. get structured design context for the target file or node
2. if scope is too large, narrow with metadata
3. fetch screenshot evidence for the final executable node target
4. fetch comments, assets, and tokens only after the executable node set is stable

Rules:

- prefer cached evidence from `.ai-delivery/figma-cache/`
- do not mark mapping complete without screenshot evidence
- do not map a requirement point using only a node name
