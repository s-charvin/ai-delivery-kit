---
name: ai-delivery-orchestrator
description: Use when a requirement should be advanced through the contract-gated ai-delivery workflow with one requirement-level todo.md, thin Spec Kit bridge artifacts, and governed checkpoint handling.
---

# AI Delivery Orchestrator

## Overview

Use this skill to orchestrate the contract-gated workflow through one requirement-level `todo.md` while treating `.ai-delivery` as the only source of truth.

This is the default entry for requirement work after repository onboarding. In the normal path, it should decide whether to continue an existing requirement or create a new one, pause for human confirmation, and only then dispatch the governed chain.

This skill is a governed wrapper around the existing workflow skills. It coordinates the current chain end to end:

- `requirement-breakdown`
- `api-contract-mapping`
- `ui-requirement-mapping`
- `ui-acceptance-contract`
- `ui-interaction-design`
- `prepare-speckit-context`
- official `speckit-specify`
- official `speckit-plan`
- official `speckit-tasks`
- local Spec Kit audit/bind
- `using-git-worktrees`
- `test-driven-development`
- `requesting-code-review`
- `verification-before-completion`

The Spec Kit bridge model is:

`.ai-delivery` facts -> `spec-kit-input.md` -> official `speckit-*` -> `spec-kit-binding.json` -> `.ai-delivery` status and `traceability.json`

The governed observability model is:

`traceability.json.source_index` -> reconcile/next-safe-action check -> agent session log -> review/visual/test evidence -> runtime `slice-closures.json`

Official `speckit-specify`, `speckit-plan`, and `speckit-tasks` should remain upstream-style instructions. This skill carries repo-specific rules instead of patching those official skill bodies.

When available, use `ai-delivery-admin-support` for governed admin support logging around meaningful phase transitions.

Required local references:

- [Reconcile Rules](references/reconcile-rules.md)
- [Stage Mapping](references/stage-mapping.md)
- [Spec Kit Bridge](references/spec-kit-bridge.md)
- [Spec Kit Binding](references/spec-kit-binding.md)
- [Spec Kit Bind Checklist](references/spec-kit-bind-checklist.md)
- [Subagent Budget Policy](references/subagent-budget-policy.md)
- [Pause And Retry Policy](references/pause-and-retry-policy.md)

## Hard Boundary

- Do not move workflow truth out of `.ai-delivery`.
- Do not generate a separate `todo.json`.
- Do not require the user to manually choose the first low-level workflow skill in the normal path.
- Do not let UI-bearing sub-requirements enter `speckit-*` before `acceptance_frozen`.
- Do not let UI-bearing sub-requirements claim planning readiness before `slices_ready`.
- Do not let UI-bearing slices claim merge completion before `visual_acceptance_passed`.
- Do not turn checkpoints into a second truth store.
- Do not let subagents advance gates, decide blockers, or merge changes.
- Do not skip source index, agent session, or slice closure records when a governed admin support surface is available.
- Do not fork official `speckit-specify`, `speckit-plan`, or `speckit-tasks` just to restate repo-local contracts.
- Do not treat `spec-kit-input.md` or `spec-kit-binding.json` as new truth stores; they are derived bridge artifacts only.

## Core Model

Three-layer model:

- `.ai-delivery/*`: fact layer
- `todo.md`: execution panel
- `ai-delivery-orchestrator`: decision layer

`todo.md` is an execution panel, not a second truth store. It records queue entries, guards, retries, checkpoints, and recovery context, but every completion decision must be proven by governed artifacts in `.ai-delivery`.

`traceability.json.source_index` is the canonical source index for requirement, Figma, API, Spec Kit, PR, CI, visual, deploy, and monitoring references. Runtime `agent-sessions.json` records who ran the work and where. Runtime `slice-closures.json` records the merged slice summary, tests, review, visual acceptance, deployment evidence, accepted risks, and follow-ups.

Bridge artifacts such as `spec-kit-input.md` and `spec-kit-binding.json` live under `.ai-delivery` as disposable derived sidecars. If they drift from governed source contracts, regenerate them from `.ai-delivery` instead of editing official Spec Kit outputs to compensate.

## Runtime Modes

- `bootstrap`
- `resume`
- `confirm-to-dev`
- `blocker-recovery`
- `completed`

## Runtime Mode Resolution

Resolve the active mode after every reconcile. Use `.ai-delivery` plus `todo.md` together, in this order:

1. `completed`
   - All executable slices named in `delivery-slices/index.json` are already `merged`.
   - `todo.md` stays as an execution-panel archive and should not dispatch new work.
2. `bootstrap`
   - `todo.md` is missing, or the requirement package is still incomplete enough that the queue cannot be derived safely.
   - Start from the top-level requirement document and build the queue from the first governed stage.
3. `confirm-to-dev`
   - `todo.md` exists, `current_checkpoint` is `CP-001`, all executable slices have reached `tasks_ready`, and the user intent clearly means "continue into development".
   - Switch to Stage 2 execution instead of re-running pre-dev planning.
4. `blocker-recovery`
   - `todo.md` exists, `current_checkpoint` is `CP-002`, and either the user has supplied the missing decision or the external blocker has been cleared.
   - Reconcile again, clear the blocker note only if the guard is now satisfiable, then resume from the blocked step.
5. `resume`
   - `todo.md` exists, no checkpoint is actively holding the run, and at least one queue item still has an unsatisfied guard.
   - Continue from the next unresolved queue item after reconcile.

`current_phase` and `current_checkpoint` are execution-panel hints, not truth by themselves. If they disagree with `.ai-delivery`, trust `.ai-delivery` and rewrite the `todo.md` header during reconcile.

## User Entry Mapping

Map common user intents to the runtime modes instead of asking the user to name the next skill.

When a user brings new material, first decide whether to continue an existing requirement or create a new one.

1. Inspect existing `.ai-delivery/requirements/*` packages, `todo.md`, `status.json`, and `traceability.json`.
2. Produce one recommendation only:
   - `continue req-xxx`
   - or `create req-yyy`
3. Pause for human confirmation before taking either path.
4. If the user overrides the recommendation, follow the human decision and continue the governed workflow.
5. Treat direct low-level skill invocation as an exception path only when its preconditions are already satisfied.

After the routing decision is confirmed, map the user intent to the runtime mode:

- "给你需求文档、swagger、Figma 已开，开始跑"
  - Enter `bootstrap` when no valid `todo.md` exists, otherwise reconcile and continue with `resume`.
- "继续这个 requirement 的编排"
  - Reconcile first, then use `resume` unless a checkpoint is active.
- "tasks_ready 了，继续开发"
  - Reconcile first, require `current_checkpoint=CP-001` and all executable slices at `tasks_ready`, then enter `confirm-to-dev`.
- "这个 blocker 我处理好了，继续跑"
  - Reconcile first, require `current_checkpoint=CP-002`, then enter `blocker-recovery` if the blocker can now be cleared safely.

direct use of lower-level skills remains supported when their preconditions are already satisfied, but that is an exception path for recovery or expert use, not the normal entry for new requirements.

## Reconcile Rules

1. Re-read `.ai-delivery` status and traceability artifacts before trusting `todo.md`.
2. Re-check every todo guard against the governed artifacts.
3. If the guard is already satisfied, mark the queue item complete without re-running the stage.
4. If outputs exist but the guard is not satisfied, re-run the stage or open a blocker. Do not skip it.

## Stage Mapping

- Requirement: `requirement-breakdown`
- API: `api-contract-mapping`
- UI Evidence: `ui-requirement-mapping`
- UI Freeze: `ui-acceptance-contract`
- Interaction And Slice Synthesis: `ui-interaction-design`
- Spec Kit Bridge: `prepare-speckit-context`
- Official Spec Kit: `speckit-specify`, `speckit-plan`, `speckit-tasks`
- Spec Kit Bind: local audit/bind after each official Spec Kit step
- Development: `using-git-worktrees`, `test-driven-development`, implementation, `requesting-code-review`, visual acceptance, `verification-before-completion`

## Checkpoints

- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`

## Stage Inputs And Guards

Use the stage mapping and bridge references as the authoritative sources for fixed inputs and completion guards. The minimum required contracts are:

- `requirement-breakdown`
  - Input: top-level requirement document
  - Guard: requirement package created under `.ai-delivery/requirements/<requirement-id>/`
- `api-contract-mapping`
  - Inputs: `requirement-slice.md`, `traceability.json`, `status.json`, api contract
  - Guard: sub-requirement reaches `api_mapped` or explicit blocked state
- `ui-requirement-mapping`
  - Inputs: `requirement-slice.md`, `api-contract-mapping.md`, Figma design source
  - Rule: if the target is a large `SECTION`, start with `get_structure`; final executable states must still have `get_code`
  - Guard: sub-requirement reaches `figma_mapped`
- `ui-acceptance-contract`
  - Inputs: `requirement-slice.md`, `figma-mapping.md`, final-state `get_code` evidence
  - Guard: sub-requirement reaches `acceptance_frozen`
- `ui-interaction-design`
  - Inputs: `requirement-slice.md`, `figma-mapping.md`, `ui-acceptance-contract.md`, `api-contract-mapping.md`
  - Output: `interaction-design.md`, `delivery-slices/index.json`
  - Guard: sub-requirement reaches `slices_ready`
- `prepare-speckit-context`
  - Inputs: `slice-contract.md`, `interaction-design.md`, `traceability.json`; add `ui-acceptance-contract.md` for UI slices and `api-contract-mapping.md` when API impact exists
  - Output: `spec-kit-input.md`
  - Guard: `spec-kit-input.md` exists and matches current governed slice truth
- official `speckit-specify`, `speckit-plan`, `speckit-tasks`
  - Primary input: `spec-kit-input.md`
  - Additional inputs: standard `.specify` templates and upstream Spec Kit runtime
  - Rule: official skill instructions remain upstream and must not be rewritten to restate repo-local contracts
  - Guard: official `spec.md`, `plan.md`, or `tasks.md` artifact exists for the current slice run
- local Spec Kit bind
  - Inputs: `spec-kit-input.md`, generated `spec.md`, `plan.md`, or `tasks.md`, `traceability.json`, `status.json`
  - Rule: apply the minimal bind checklist before writing `traceability.json.spec_kit_refs`
  - Output: `spec-kit-binding.json`; update `traceability.json.spec_kit_refs`
  - Guards: `spec_ready`, `plan_ready`, `tasks_ready`
- Development execution
  - Inputs: `slice-contract.md`, `tasks.md`, `spec-kit-binding.json`, traceability refs, `.agents/AGENTS.md`
  - Guard: slice reaches `merged`; UI-bearing slices must reach `visual_acceptance_passed` before merge completion

## Queue Compression

`todo.md` may track an official Spec Kit step plus its local audit/bind as one execution-panel action such as `speckit-specify-bind`, `speckit-plan-bind`, or `speckit-tasks-bind`. When compressed this way, the action is still governed by `.ai-delivery` guards, not by the queue text itself.

## State Machine

Stage 1:

1. `requirement-breakdown`
2. `api-contract-mapping`
3. `ui-requirement-mapping` for UI-bearing sub-requirements only
4. `ui-acceptance-contract` for UI-bearing sub-requirements only
5. `ui-interaction-design` for UI-bearing sub-requirements only
6. `prepare-speckit-context`
7. official `speckit-specify`
8. local spec bind
9. official `speckit-plan`
10. local plan bind
11. official `speckit-tasks`
12. local tasks bind
13. `tasks_ready_user_confirmation`

Stage 2:

1. `using-git-worktrees`
2. `test-driven-development`
3. implementation
4. `requesting-code-review`
5. review auto-fix retry
6. visual acceptance
7. visual auto-fix retry
8. `verification-before-completion`
9. merge

## Development Gates

- Pause at `tasks_ready_user_confirmation` until the user confirms.
- Escalate only on a hard blocker, a non-recoverable gate failure, or a missing human decision.
- UI-bearing sub-requirements cannot enter `speckit-*` before `acceptance_frozen`.
- UI-bearing sub-requirements cannot claim slice execution readiness before `slices_ready`.
- UI-bearing slices cannot claim merge completion before `visual_acceptance_passed`.

## Subagent Budget

- Default to the main session.
- Only use subagents for independent, frozen, reviewable work.
- Default concurrency is one active subagent.
- Temporary concurrency two is allowed only for independent slices with satisfied dependencies.
- Main session owns gate decisions, worktree ordering, blocker classification, and merge readiness.
- If official Spec Kit work is delegated, run `prepare-speckit-context` first so the delegated input is frozen and reviewable.

## Development Ordering Rules

- Order slice execution from `delivery-slices/index.json`, not from ad-hoc prompt order.
- A slice can only enter `using-git-worktrees` after every `depends_on_slices` entry is already `merged`.
- Do not pre-create worktrees for future slices whose dependencies are still unresolved.
- Worktree creation order, conflict handling, and merge decisions always return to the main session.
- Parallelism is allowed only for independent slices whose dependencies are already satisfied and still remains subject to the subagent budget rules.

## Pause And Retry

- `review` first failure must enter an auto-fix loop before escalation.
- Visual acceptance first failure must enter an auto-fix loop before escalation.
- Pause only at `CP-001 tasks_ready_user_confirmation` or `CP-002 hard_blocker_pause`.

## ai-delivery-admin Policy

- Use `ai-delivery-admin-support` as a governed logging surface, not a second fact store.
- Log stage start, completion, failure, blocker, and recovery transitions when admin support is available.
- For the Spec Kit bridge, log `prepare-speckit-context`, official Spec Kit dispatch, local bind completion, and any bind mismatch before the next gate advances.
- Keep `todo.md` limited to execution-panel recovery context.
