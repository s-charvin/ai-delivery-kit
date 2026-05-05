# Stage Mapping

## Requirement

- Stage: `requirement-breakdown`
- Fixed input: top-level requirement document
- Fixed output root: `.ai-delivery/requirements/<requirement-id>/...`
- Completion guard: requirement package exists and sub-requirements have been created

## API

- Stage: `api-contract-mapping`
- Fixed inputs:
  - `requirement-slice.md`
  - `traceability.json`
  - `status.json`
  - api contract
- Completion guard: sub-requirement reaches `api_mapped` or explicit blocked state

## UI Evidence

- Stage: `ui-requirement-mapping`
- Fixed inputs:
  - `requirement-slice.md`
  - `api-contract-mapping.md`
  - Figma design source
- Fixed evidence rule:
  - if the target is a large `SECTION`, start with `get_structure`
  - final executable states must still have `get_code`
- Completion guard: sub-requirement reaches `figma_mapped`

## UI Freeze

- Stage: `ui-acceptance-contract`
- Fixed inputs:
  - `requirement-slice.md`
  - `figma-mapping.md`
  - final-state `get_code` evidence
- Fixed output:
  - `ui-acceptance-contract.yaml`
- Completion guard: sub-requirement reaches `acceptance_frozen`

## Interaction And Slice Synthesis

- Stage: `ui-interaction-design`
- Fixed inputs:
  - `requirement-slice.md`
  - `figma-mapping.md`
  - `ui-acceptance-contract.yaml`
  - `api-contract-mapping.md`
- Fixed outputs:
  - `interaction-design.md`
  - `delivery-slices/index.json`
- Completion guard: sub-requirement reaches `slices_ready`
- `ui-interaction-design` is also the current `delivery-slice synthesis` owner.

## Spec Kit Bridge

- Stage: `prepare-speckit-context`
- Fixed inputs:
  - `slice-contract.md`
  - `interaction-design.md`
  - `traceability.json`
  - `ui-acceptance-contract.yaml` for UI slices
  - `api-contract-mapping.md` when API impact exists
- Fixed output:
  - `spec-kit-input.md`
- Completion guard: `spec-kit-input.md` exists and is reconciled to current governed slice truth

## Official Spec Kit

- Stages:
  - `speckit-specify`
  - `speckit-plan`
  - `speckit-tasks`
- Primary input:
  - `spec-kit-input.md`
- Fixed rule:
  - official `speckit-*` instructions stay upstream and are not patched to restate repo-local contracts
- Completion guards:
  - generated `spec.md`
  - generated `plan.md`
  - generated `tasks.md`

## Spec Kit Bind

- Stage family:
  - bind spec
  - bind plan
  - bind tasks
- Fixed inputs:
  - `spec-kit-input.md`
  - generated `spec.md`, `plan.md`, or `tasks.md`
  - `traceability.json`
  - `status.json`
- Fixed outputs:
  - `spec-kit-binding.json`
  - updated `traceability.json.spec_kit_refs`
- Completion guards:
  - `spec_ready`
  - `plan_ready`
  - `tasks_ready`

## Development

- Fixed inputs:
  - `slice-contract.md`
  - `tasks.md`
  - `spec-kit-binding.json`
  - traceability refs
- Optional context:
  - project-local `.agents/AGENTS.md` when the host repository already provides one
- Scope boundary:
  - development delegation is allowed only for the currently active `SR-*`
  - delivery slices remain implementation units inside that `SR-*`, not a deeper governed child requirement tier
- Fixed execution rules:
  - edit code with file-scoped patches only; do not send one patch that rewrites multiple files at once
  - use subagents only in Stage 2 and only when at least two independent runnable implementation tasks inside the active `SR-*` already satisfy their dependencies
  - if fewer than two independent runnable implementation tasks exist, stay in the main session
  - if delegated work uses worktrees, complete coding first, then rebase and reintegrate finished worktree branches back to the current development branch one by one in dependency order
  - keep commit history linear during worktree reintegration; do not use merge commits
- Ordered stages:
  - `using-git-worktrees`
  - `test-driven-development`
  - implementation
  - `requesting-code-review`
  - visual acceptance
  - `verification-before-completion`
- Completion guard: slice reaches `merged`
- UI-bearing slices must reach `visual_acceptance_passed` before merge completion.
