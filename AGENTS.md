<!-- ai-delivery:ui-contract-gate:start -->
# UI Truth Mapping

After explicit CP-UI authorization, Stage 2 implements and freezes **real host-stack components** in the slice worktree (Flutter first: widget + golden/behavior tests), using tests and fresh-context review. Before component code, resolve applicability-gated runtime coverage for state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. Stage 4 reuses that worktree. Do not generate `ui-contract.html`. Do not translate HTML into Flutter.

Review medium: deterministic official-stack previews for visual scenarios. Give the user every preview's **absolute path**; store v2 profiles, sourced states, scenarios, complete coverage, repo-relative paths, SHA-256 hashes, and preview-bound confirmation/waiver evidence in `contracts/ui-truth-index.json`. Figma is 1:1 authority only for scenarios it actually evidences; runtime gaps require requirement, project, or explicit user-decision sources. Stage 4 must bind every scenario's evidence to the current index in `visual-acceptance.json`.

## Artifact Language

Treat bundled template prose as an English source default, not as the output language. Write every human-readable AI Delivery artifact, review note, and necessary code comment in the user's current conversation language. Preserve machine-readable keys, enum values, IDs, paths, commands, code symbols, and literal protocol tokens exactly. Remove any `ai-delivery-template-language` instruction comment after localizing a copied template.

UI work enters through `ai-delivery-orchestrator`. TemPad MCP errors → STOP, do not guess.
<!-- ai-delivery:ui-contract-gate:end -->
