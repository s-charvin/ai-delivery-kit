<!-- ai-delivery:ui-contract-gate:start -->
# UI Truth Mapping

After explicit CP-UI authorization, Stage 2 implements and freezes **real host-stack components** in the slice worktree (Flutter first: widget + golden PNG), using tests and fresh-context review. Stage 4 reuses that worktree. Do not generate `ui-contract.html`. Do not translate HTML into Flutter.

Review medium: official-stack preview. Give the user the **absolute path**; store v1 governance metadata, repo-relative paths, SHA-256 hashes, and per-state confirmation/waiver evidence in `contracts/ui-truth-index.json`.

## Artifact Language

Treat bundled template prose as an English source default, not as the output language. Write every human-readable AI Delivery artifact, review note, and necessary code comment in the user's current conversation language. Preserve machine-readable keys, enum values, IDs, paths, commands, code symbols, and literal protocol tokens exactly. Remove any `ai-delivery-template-language` instruction comment after localizing a copied template.

UI work enters through `ai-delivery-orchestrator`. TemPad MCP errors → STOP, do not guess.
<!-- ai-delivery:ui-contract-gate:end -->
