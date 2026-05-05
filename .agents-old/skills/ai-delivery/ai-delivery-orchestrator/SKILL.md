---
name: ai-delivery-orchestrator
description: Use when a requirement should be advanced through the contract-gated ai-delivery workflow with one requirement-level todo.md, thin Spec Kit bridge artifacts, and governed checkpoint handling.
---

# AI Delivery Orchestrator

## Overview

Use this skill to orchestrate the contract-gated workflow through one requirement-level `todo.md` while treating `.ai-delivery` as the only source of truth.

This is the default entry for requirement work after repository onboarding. In the normal path, it should decide whether to continue an existing requirement or create a new one, pause for human confirmation, and only then dispatch the governed chain.

After `requirement-breakdown`, the default posture is `UI-first, integration-later`: prefer the visual/design track as soon as trustworthy design evidence is runnable, let the API/integration track run in parallel or arrive later, and use late API truth to trigger governed `downstream_revalidation` instead of prematurely pausing the whole requirement.

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

- [Requirement Routing Rules](references/requirement-routing-rules.md)
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
- Do not promote an API-only or slice-local blocker to requirement-wide `CP-002` while any safe runnable queue item still exists.
- Do not let a blocked queue entry swallow later queue entries that are still safe to run.
- Do not turn checkpoints into a second truth store.
- Do not let subagents advance gates, decide blockers, or merge changes.
- Do not use subagents outside Stage 2 development for the currently active `SR-*`.
- Do not let delegated work escape the current `SR-*` boundary or recurse into a deeper child requirement tier below `SR-*`.
- Do not dispatch a subagent when fewer than two independent runnable implementation tasks remain after dependency review.
- Do not apply one large multi-file patch during implementation; patch one file at a time and re-check context between files.
- Do not reintegrate delegated worktree branches with merge commits; rebase them back onto the current development branch in sequence so history stays linear.
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

## Runnable Queue And Blocker Scope

Use these terms explicitly during reconcile and queue decisions:

- `runnable queue item`
  - Any item that can still move forward safely under the current governed truth without inventing missing facts.
  - Common examples: Tempad or Figma evidence capture, `ui-requirement-mapping`, page shell implementation, local state or event skeletons, navigation flow, repository or adapter seams, mock wiring, read-only presentation paths, or other safe partial frontend work.
- `slice-local blocker`
  - A blocker that stops one slice, one stage, or one capability surface only.
  - It must not block unrelated slices or stages by default.
- `action-level integration blocker`
  - A blocker that stops real API wiring or final semantic closure for one action.
  - It does not block visual mapping, shell work, local state work, navigation skeletons, non-dangerous user paths, or other safe partial development unless those activities truly depend on the missing API truth.
- `requirement-global blocker`
  - A blocker that is allowed to hold the whole requirement only when every currently derivable queue item is non-runnable.
  - If even one safe runnable item remains, the blocker is not requirement-global yet.

The default orchestrator strategy is `continue safest runnable work first`, not `pause on first blocker`.

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
   - `todo.md` exists, no checkpoint is actively holding the run, and at least one queue item is still unresolved or runnable after reconcile.
   - Blocked items may remain in the queue while later independent work continues.
   - Continue from the safest runnable unresolved queue item after reconcile.

`current_phase` and `current_checkpoint` are execution-panel hints, not truth by themselves. If they disagree with `.ai-delivery`, trust `.ai-delivery` and rewrite the `todo.md` header during reconcile.

## User Entry Mapping

Map common user intents to the runtime modes instead of asking the user to name the next skill.

When a user brings new material, first decide whether to continue an existing requirement or create a new one. Use the Requirement Routing Rules as the minimum evidence threshold for that recommendation.

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
3. Classify every blocker as `slice-local`, `action-level integration blocker`, or `requirement-global blocker` before choosing a checkpoint.
4. Re-check what the blocker actually blocks: visual truth, acceptance freeze, interaction contract, full integration, or final delivery claim.
5. If the guard is already satisfied, mark the queue item complete without re-running the stage.
6. If outputs exist but the guard is not satisfied, re-run the stage or open the narrowest blocker. Keep the blocked item in the queue and continue later runnable items that do not depend on it.

## Stage Mapping

- Requirement: `requirement-breakdown`
- Visual/Design Track: `ui-requirement-mapping`
- API/Integration Track: `api-contract-mapping`
- UI Freeze: `ui-acceptance-contract`
- Interaction And Slice Synthesis: `ui-interaction-design`
- Spec Kit Bridge: `prepare-speckit-context`
- Official Spec Kit: `speckit-specify`, `speckit-plan`, `speckit-tasks`
- Spec Kit Bind: local audit/bind after each official Spec Kit step
- Development: `using-git-worktrees`, `test-driven-development`, implementation, `requesting-code-review`, visual acceptance, `verification-before-completion`

## Checkpoints

- `CP-001 tasks_ready_user_confirmation`
- `CP-002 hard_blocker_pause`
  - Enter this checkpoint only when the current requirement has no safe runnable queue item left.
  - API blockers on one or more sub-requirements do not qualify by themselves if other UI truth capture, shell work, local interaction work, acceptance prep, or safe partial development items can still continue.

## Stage Inputs And Guards

Use the stage mapping and bridge references as supporting shorthand for fixed inputs and completion guards. When older shorthand conflicts with the blocker-scope and runnable-queue rules in this skill, this skill wins. The minimum required contracts are:

- `requirement-breakdown`
  - Input: top-level requirement document
  - Guard: requirement package created under `.ai-delivery/requirements/<requirement-id>/`
- `api-contract-mapping`
  - Inputs: `requirement-slice.md`, `traceability.json`, `status.json`, api contract
  - Guard: sub-requirement reaches `api_mapped`, `missing_nonblocking`, `needs_revalidation`, or the narrowest explicit blocked state with recovery notes
  - Rule: judge blocker severity by `slice + stage`, not by the whole requirement; API gaps mainly block dangerous action wiring, irreversible behavior confirmation, server-driven branches, and final delivery claims
- `ui-requirement-mapping`
  - Inputs: `requirement-slice.md`, Figma design source; add `api-contract-mapping.md` when present
  - Rule: if the target is a large `SECTION`, start with `get_structure`; final executable states must still have `get_code`
  - Rule: permit entry when API status is `api_mapped`, `missing_nonblocking`, or `needs_revalidation`; if API is `blocked_*` but the blocker is API-only and does not prevent visual-carrier recognition, continue in `visual-evidence-first` mode
  - Guard: sub-requirement reaches `figma_mapped` with a governed readiness verdict, even when later acceptance or integration work is still deferred by API truth
- `ui-acceptance-contract`
  - Inputs: `requirement-slice.md`, `figma-mapping.md`, final-state `get_code` evidence; add `api-contract-mapping.md` only when API truth changes the executable screen-state contract
  - Output: `ui-acceptance-contract.yaml` as the only canonical UI acceptance truth, rooted at `screen_states[*].component_tree`
  - Guard: sub-requirement reaches `acceptance_frozen`
- `ui-interaction-design`
  - Inputs: `requirement-slice.md`, `figma-mapping.md`, `ui-acceptance-contract.yaml`; add `api-contract-mapping.md` when present or when action semantics are already known
  - Output: `interaction-design.md`, `delivery-slices/index.json`
  - Rule: allow shell, navigation, local-state, and safe action-path synthesis to continue while action-level API blockers remain explicit as deferred wiring or blocked integration notes
  - Guard: sub-requirement reaches `slices_ready`
- `prepare-speckit-context`
  - Inputs: `slice-contract.md`, `interaction-design.md`, `traceability.json`; add `ui-acceptance-contract.yaml` for UI slices and `api-contract-mapping.md` when API impact exists
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
  - Inputs: `slice-contract.md`, `tasks.md`, `spec-kit-binding.json`, traceability refs
  - Optional context: project-local `.agents/AGENTS.md` when the host repository already provides one
  - Scope: the currently active `SR-*` only; delegated work, if used, stays inside Stage 2 for that sub-requirement and must not create a deeper governed sub-requirement tier
  - Rule: edit code with file-scoped patches; do not send one patch that rewrites multiple files at once
  - Rule: use subagents only when at least two independent runnable implementation tasks inside the current `SR-*` already satisfy their dependencies; otherwise stay in the main session
  - Rule: if delegated work uses worktrees, finish coding in those worktrees first, then rebase and reintegrate them back to the current development branch one by one in dependency order so commit history stays linear
  - Guard: slice reaches `merged`; UI-bearing slices must reach `visual_acceptance_passed` before merge completion

## Queue Compression

`todo.md` may track an official Spec Kit step plus its local audit/bind as one execution-panel action such as `speckit-specify-bind`, `speckit-plan-bind`, or `speckit-tasks-bind`. When compressed this way, the action is still governed by `.ai-delivery` guards, not by the queue text itself.

## State Machine

Stage 1 is a governed queue, not an API-first linear hard gate:

1. `requirement-breakdown`
2. Enter two tracks after breakdown:
   - `visual/design track`
   - `api/integration track`
3. Run `ui-requirement-mapping` for UI-bearing sub-requirements as soon as trustworthy design evidence is runnable.
4. Run `api-contract-mapping` whenever client-facing API truth exists; rerun it later when API truth arrives late or changes materially.
5. Reconcile both tracks; continue safe work that does not depend on blocked API semantics.
6. Run `ui-acceptance-contract` for UI-bearing sub-requirements only when visual truth is fully source-backed and any API truth that changes the frozen screen-state contract is sufficiently known.
7. Run `ui-interaction-design` for UI-bearing sub-requirements only when the acceptance contract is frozen; keep unresolved dangerous-action semantics explicit as `integration_deferred`, `action-blocked-not-visual-blocked`, or equivalent governed notes instead of inventing closure.
8. `prepare-speckit-context`
9. official `speckit-specify`
10. local spec bind
11. official `speckit-plan`
12. local plan bind
13. official `speckit-tasks`
14. local tasks bind
15. `tasks_ready_user_confirmation`

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
- Continue the safest runnable work first whenever a narrower blocker still leaves queue items runnable.
- UI-bearing sub-requirements cannot enter `speckit-*` before `acceptance_frozen`.
- UI-bearing sub-requirements cannot claim slice execution readiness before `slices_ready`.
- UI-bearing slices cannot claim merge completion before `visual_acceptance_passed`.
- Partial frontend work such as shells, navigation paths, local state, adapter seams, mock wiring, form validation, or read-only surfaces may advance before full API closure when their governed notes make the remaining integration work explicit.
- Do not present partial or integration-deferred work as full implementation completion, full integration completion, or merge readiness.

## Subagent Budget

- Default to the main session.
- Subagents are a Stage 2 development-only tool. Do not use them in routing, reconcile, mapping, acceptance freeze, interaction design, Spec Kit generation, or gate decisions.
- Scope delegation to one active `SR-*` at a time. Delivery slices remain implementation units inside that `SR-*`, not a second governed child requirement tier.
- Only use subagents for independent, frozen, reviewable implementation work.
- Only use subagents when at least two independent runnable implementation tasks inside the active `SR-*` can move forward in parallel after dependency review.
- If fewer than two independent runnable implementation tasks exist, stay in the main session.
- When the threshold is met, allow at most two active subagents.
- Main session owns dependency analysis, worktree ordering, blocker classification, and merge readiness.
- Never allow a subagent to spawn deeper subagents under the same `SR-*`.

## Development Ordering Rules

- Order slice execution from `delivery-slices/index.json`, not from ad-hoc prompt order.
- A slice can only enter `using-git-worktrees` after every `depends_on_slices` entry is already `merged`.
- Parallelism is allowed only when at least two independent runnable implementation tasks inside the current `SR-*` already satisfy their dependencies.
- Do not pre-create worktrees for future slices whose dependencies are still unresolved.
- If worktrees are used for delegated development, complete the coding work first, then have the main session rebase each finished worktree branch onto the current development branch and reintegrate them one by one in dependency order.
- Keep the resulting history linear; do not use merge commits for worktree reintegration.
- Worktree creation order, conflict handling, and merge decisions always return to the main session.

## Pause And Retry

- `review` first failure must enter an auto-fix loop before escalation.
- Visual acceptance first failure must enter an auto-fix loop before escalation.
- Pause only at `CP-001 tasks_ready_user_confirmation` or `CP-002 hard_blocker_pause`.
- `CP-002 hard_blocker_pause` is valid only when no safe runnable queue item remains for the current requirement.

## ai-delivery-admin Policy

- Use `ai-delivery-admin-support` as a governed logging surface, not a second fact store.
- Log stage start, completion, failure, blocker, and recovery transitions when admin support is available.
- For the Spec Kit bridge, log `prepare-speckit-context`, official Spec Kit dispatch, local bind completion, and any bind mismatch before the next gate advances.
- Keep `todo.md` limited to execution-panel recovery context.
