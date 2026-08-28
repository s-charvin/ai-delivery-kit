<!-- ai-delivery:ui-contract-gate:start -->
# UI Truth Mapping

After explicit CP-UI authorization, Stage 2 implements and freezes **real host-stack components** in the user-approved workspace (Flutter first: widget + golden/behavior tests), using tests and fresh-context review. Before component code, resolve applicability-gated runtime coverage for state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance. Stage 4 reuses that workspace. Do not generate `ui-contract.html`. Do not translate HTML into Flutter.

Worktrees are optional and the current checkout is the default. Creating or reusing one requires explicit user confirmation for the current sub-requirement; CP-UI, CP-001, framework defaults, and legacy mandatory-isolation flags are not consent. The only allowed worktree path is `<project-root>/.worktrees/<req-id>-<sr-id>`. A native tool may run only if it accepts that exact path. If already running in `/private/tmp/...` or any other external worktree, stop production edits and ask whether to switch to the project checkout or the exact project-local worktree. Leave the external worktree unchanged; switching workspaces never authorizes its migration, reuse, or deletion. Those actions require separate explicit confirmation naming the exact action and target.

Review medium: deterministic official-stack previews for visual scenarios. Give the user every preview's **absolute path**; store v2 profiles, sourced states, scenarios, complete coverage, repo-relative paths, SHA-256 hashes, and preview-bound static confirmation/waiver evidence in `contracts/ui-truth-index.json`. Every unit also records a separate `motion_decision`: animated motion requires its own confirmation/waiver and later verification mode; static UI requires an explicit confirmed “static / no motion” decision. When the host can produce a deterministic GIF, show and hash it as motion evidence; otherwise confirm/waive first and verify at runtime after implementation. GIF is sufficient; do not add another motion format or encoder. A golden never substitutes for motion acceptance. Figma is 1:1 authority only for scenarios it actually evidences; runtime gaps require requirement, project, or explicit user-decision sources. Stage 4 must bind every scenario's evidence to the current index in `visual-acceptance.json`.

Visible UI must use real host-stack controls and evidence-backed resources. Do not use an unapproved placeholder, external visual slot, dummy/fixture visual, generic icon, painted input shell, or silent asset fallback. If a required resource is unavailable, stop and ask the user to choose empty rendering, defer, or block; empty rendering is allowed only after that decision is recorded.

## Artifact Language

Treat bundled template prose as an English source default, not as the output language. Write every human-readable AI Delivery artifact, review note, and necessary code comment in the user's current conversation language. Preserve machine-readable keys, enum values, IDs, paths, commands, code symbols, and literal protocol tokens exactly. Remove any `ai-delivery-template-language` instruction comment after localizing a copied template.

UI work enters through `ai-delivery-orchestrator`. TemPad MCP errors → STOP, do not guess.

Delivery routing is capability-gated by each sub-requirement's `ui_truth_mode`
(`none`, `existing`, `runtime-baseline`, or `figma`) and `design_mode`
(`none`, `light`, or `full`). Only `runtime-baseline` and `figma` enable CP-UI,
`contracts/ui-truth-index.json`, and visual acceptance. `full` solution design
uses CP-DESIGN; `light` self-approves a short `design.md`; `none` skips the
solution-design artifact. Keep `ui_bearing` consistent with `ui_truth_mode`.
Runtime checkpoints are `CP-UI`, `CP-DESIGN`, `CP-001`, `CP-002`, and
`CP-ARCHIVE`; the corresponding gated runtime mode is
`confirm_solution_design` for a pending full solution design.
<!-- ai-delivery:ui-contract-gate:end -->
