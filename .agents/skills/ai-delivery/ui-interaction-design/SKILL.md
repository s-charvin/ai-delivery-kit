---
name: ui-interaction-design
description: Use when a sub-requirement already has verified requirement and Figma mapping artifacts and needs a source-bounded interaction contract, micro-interaction assumptions, or escalation of missing interaction truth before implementation or Spec Kit planning.
---

# UI Interaction Design

Project-local workflow skill for converting governed requirement slices plus verified design mappings into an executable interaction contract inside the host repository.

## Overview

Use this skill after `ui-acceptance-contract` when a sub-requirement already has requirement truth, mapping truth, acceptance-freeze truth, and supporting governed artifacts in place. If `api-contract-mapping.md` already exists, treat it as additional interface-contract context and preserve its traceability implications. This stage writes `interaction-design.md`, finalizes `delivery-slices/index.json`, updates `decisions.md` when assumptions or escalations are needed, and preserves the upstream mapping and bridge contract instead of rewriting it from memory.

This skill may refine bounded micro-interaction detail such as feedback patterns, loading presentation, motion timing, focus treatment, and accessibility defaults, but only when those refinements stay below the business-meaning threshold and remain explicitly labeled.

This is a project-local skill with built-in interaction-design guidance. Do not stop because an external skill is missing, and do not assume users have installed any external skill package. The needed guidance for micro-interaction, motion, loading, feedback, timing, and a11y lives here in the repository on purpose.

## Hard Boundary

- Do not invent business flow or page structure.
- Do not add new fields, steps, dialogs, permissions, or page transitions.
- Do not label an assumption as if it were original Requirement or Figma fact.
- Do not repair visual truth here; if `ui-acceptance-contract.md` is incomplete or blocked, hand the issue back upstream.
- Do not overwrite `figma-mapping.md` or `traceability.json` because an interaction contract prefers a different design.
- Do not delete later-stage bridge or Spec Kit references when they already exist.
- Do not hand-edit blocked states to look recovered.
- Do not wait for request or response field finality to finish interaction design.

If interaction truth cannot be resolved from Requirement, `figma-mapping.md`, and trusted design evidence without changing business meaning, stop and escalate instead of filling the gap by intuition.

## Use This Skill For

- Turning verified Requirement and Figma mapping evidence into an executable interaction contract
- Consuming `ui-acceptance-contract.md` to freeze action closure against immutable screen contracts
- Defining source-backed user actions, feedback, states, and transitions
- Producing `Action Chain Matrix` and `State Propagation Matrix`
- Recording bounded `assumed_micro_interaction` only inside the allowed boundary
- Improving the quality of micro-interaction detail for loading, feedback, motion, timing, focus, and a11y / accessibility without expanding product meaning
- Escalating missing interaction truth before implementation or Spec Kit planning

## Do Not Use This Skill For

- Requirement splitting
- Figma node mapping
- Product redesign
- New business-logic invention
- Implementation code or task planning

## Required References

- [Dual Truth Rules](references/dual-truth-rules.md)
- [Blocker Catalog](references/blocker-catalog.md)
- [Logging Checklist](references/logging-checklist.md)
- [Interaction Design Template](templates/interaction-design-template.md)
- [Allowed Assumptions](references/allowed-assumptions.md)
- [Interaction Quality Guidelines](references/interaction-quality-guidelines.md)
- [State Checklist](references/state-checklist.md)

Also read the existing `traceability.json` because it is a first-class governed artifact, not disposable sidecar context.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`
- `ui-acceptance-contract.md`

### Expected Supporting Inputs

- `traceability.json`
- `status.json`
- existing `decisions.md`
- `delivery-slices/index.json` when the sub-requirement is being revised rather than synthesized for the first time

### Optional Inputs

- `api-contract-mapping.md`
- Figma comments
- prototype flows
- existing interaction conventions
- component behavior constraints

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or still too ambiguous, stop and hand the work back to `requirement-breakdown`.
- Prefer starting from `acceptance_frozen`; if the sub-requirement is still unmapped, unfrozen, or blocked and the user did not ask for repair work, stop instead of pretending interaction design is normal.
- If `figma-mapping.md` is missing or not backed by trustworthy structured design evidence, stop and hand the work back to `ui-requirement-mapping`.
- If `ui-acceptance-contract.md` is missing, incomplete, or blocked, stop and hand the work back to the acceptance-freeze stage.
- If `traceability.json` is missing or inconsistent with the visible mapping truth, repair or escalate that governed contract before claiming `interaction_ready`.
- If only micro-interaction detail is missing, continue and record `assumed_micro_interaction`.
- If the missing detail changes business meaning, stop and block instead of assuming.

## Output Goal

Produce an interaction contract that developers can consume directly while preserving upstream mapping truth. The output must preserve:

- a source-bounded `interaction-design.md`
- a source-bounded `Action Chain Matrix`
- a source-bounded `State Propagation Matrix`
- a finalized `delivery-slices/index.json` for the current sub-requirement
- updates to `decisions.md` when assumptions, blockers, or revalidation notes appear
- explicit labels for `Source: Requirement`, `Source: Figma`, `Source: Existing Pattern`, and `Assumption: Micro Interaction`
- the existing `traceability.json` bridge context, including `api_contract_mapping` and `spec_kit_refs` when present

## Default Output Paths

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── interaction-design.md
├── delivery-slices/index.json
├── decisions.md
├── status.json
└── traceability.json
```

## Workflow

### 1. Confirm the upstream contract stack

- Read `requirement-slice.md`, `api-contract-mapping.md` when present, `figma-mapping.md`, `ui-acceptance-contract.md`, `traceability.json`, `status.json`, and `decisions.md` before drafting any interaction contract.
- Confirm that the interaction work still matches the current sub-requirement scope and the verified mapping output.
- Prefer to start from `acceptance_frozen`; if the mapping or acceptance freeze is stale, blocked, or unverified, stop and hand the work back upstream.

### 2. Extract source-backed interaction facts

- Derive interaction facts from Requirement truth, API contract truth, Figma mapping truth, UI acceptance truth, comments, prototype flows, and already-approved patterns.
- Label each fact as `Source: Requirement`, `Source: Figma`, `Source: Existing Pattern`, or `Assumption: Micro Interaction`.
- Keep explicit separation between source-backed behavior and bounded assumptions.
- Use `references/interaction-quality-guidelines.md` to choose the lightest safe feedback, loading, motion, timing, and accessibility defaults when the source truth leaves room for bounded refinement.

### 2a. Bounded Interaction Quality Principles

Use these principles to improve interaction quality without crossing into redesign.

### 1. Feedback First

- Prefer interaction feedback that confirms user intent clearly and immediately.
- Distinguish between inline validation, field-level error, page-level error, toast, and progress feedback instead of collapsing everything into one generic message surface.
- Prefer feedback that preserves user context over feedback that interrupts flow unless the source materials explicitly require interruption.
- Choose the lightest feedback surface that preserves clarity. Prefer inline or local feedback before global or blocking interruption when business meaning is unchanged.

### 2. Loading Should Preserve Orientation

- Prefer loading states that preserve layout and user orientation.
- When source truth does not specify exact presentation, prefer bounded defaults such as button-level loading, inline progress, or skeleton placeholders that match the existing surface instead of full-screen blocking states.
- Loading behavior should explain whether the user can continue editing, wait in place, or retry.
- Loading scope should match action scope. Prefer control, section, or container loading before page-level or app-wide blocking states.

### 3. Motion Must Be Functional

- Motion should communicate feedback, focus, continuity, or state change; it should not be decorative by default.
- If motion detail is missing, prefer subtle, short, and interruptible transitions instead of large choreographed animation.
- Use motion notes to describe purpose, not implementation library choices.
- Prefer platform-neutral descriptions such as "preserve continuity between states" or "emphasize validation error" over web-specific animation techniques.

### 4. Timing Should Be Consistent And Conservative

- Micro-feedback should feel immediate.
- Small component transitions should stay short and unobtrusive.
- Longer motion should only appear when it explains meaningful continuity.
- If exact timing is not source-backed, record timing guidance as a bounded micro-interaction assumption rather than as Figma truth.

### 5. Accessibility Is Part Of The Contract

- Preserve keyboard reachability, visible focus, state clarity, and reduced-motion behavior as first-class interaction concerns.
- Treat a11y as part of interaction truth, not as optional polish after implementation.
- If the source does not specify animation accessibility behavior, default to respecting reduced-motion preferences.
- Do not let motion or loading behavior hide important state changes from assistive or keyboard users.
- If hover contributes meaning, require a focus or touch-equivalent behavior in the contract.

### 5a. Local Interaction Quality Contract

- Use this repository-local guidance directly instead of depending on an external skill installation.
- When the source leaves room for safe refinement, prefer the lightest helpful choice for feedback, loading, timing, and a11y.
- If a stronger pattern would change product meaning, do not borrow it from intuition or from an external skill; escalate it back to Requirement or Figma truth.

### 6. Interruptibility Over Lock-In

- Prefer interactions that allow users to recover, retry, or stay oriented.
- Do not assume long-running transitions, blocking overlays, or locked states unless the source truth requires them.
- If a loading or feedback pattern would temporarily block user action, state why that block is justified.

### 7. Cross-Platform Neutrality

- Write interaction guidance so web, iOS, and Android teams can all apply it without translating from one platform's implementation jargon.
- Prefer behavior language such as focus retention, state emphasis, local progress, or gesture fallback over framework-specific APIs or code snippets.
- If a platform-specific behavior matters, state the user-facing outcome instead of prescribing a single implementation stack.

### 3. Write `interaction-design.md`

- Use `templates/interaction-design-template.md`.
- Cover interaction goal, entry conditions, user actions, feedback and response model, success, empty, loading, error, and disabled states, permission or visibility impacts, navigation or local state changes, Action Chain Matrix, State Propagation Matrix, motion and transition notes, accessibility and input modality notes, and open escalations.
- Keep the document executable for downstream implementation without redesigning the product.

### 3a. Freeze action closure and propagation

- Every meaningful CTA or gesture must appear in the Action Chain Matrix with `entry_state`, `user_action`, `hit_target_owner`, `callback_owner`, `repo_or_api`, `success_state_change`, `failure_feedback`, `upstream_downstream_refresh_targets`, and `navigation_conflict_boundary`.
- Every cross-owner or cross-surface consequence must appear in the State Propagation Matrix with `source_action`, `source_state_owner`, `target_page_or_component`, `target_state_field`, `update_mode`, and `consistency_risk`.
- Treat navigation conflict, hit-target overlap, empty callback risk, and "close page without business action" risk as contract-level concerns, not review-only surprises.

### 3b. Finalize slice synthesis

- After the matrices are frozen, synthesize or update `delivery-slices/index.json`.
- Finalize one `page-state` slice per frozen screen state, plus `shared-state` or `integration` slices for propagation and cross-route ownership.
- Do not finalize slice ownership before the action and propagation contracts are explicit.

### 3.1 Improve Micro-Interaction Detail Carefully

- When the source truth is silent, use the allowed boundary to refine button loading, inline validation timing, hover or active states, focus visibility, reduced-motion handling, toast-versus-inline error priority, and other bounded a11y details that do not change business meaning.
- Prefer explicit notes such as "Loading preserves layout", "Focus remains visible after validation failure", or "Motion communicates state change only" over vague statements like "make it smoother".
- Use the feedback surface ladder, loading pattern ladder, timing guidance, and common failure modes from `references/interaction-quality-guidelines.md` when deciding among safe defaults.
- If a stronger interaction pattern would introduce a new branch, modal, page transition, or business rule, do not add it here.

### 4. Bound assumptions aggressively

- Record `assumed_micro_interaction` only inside the allowed boundary from `references/allowed-assumptions.md`.
- If an assumption would change business meaning, add a new branch, add a new screen step, or redefine permissions, stop and escalate instead of writing it as interaction truth.
- Distinguish clearly between missing interaction detail and missing product requirement truth.
- For motion, timing, and feedback assumptions, record both the reason and the restraint; explain why the assumption improves clarity without changing the feature's meaning.

### 5. Preserve adjacent artifacts

- Do not rewrite `figma-mapping.md` from memory.
- Do not clear or replace `traceability.json`, including existing bridge fields such as `api_contract_mapping` and `spec_kit_refs`.
- If interaction analysis reveals a mapping or visual-truth gap, record it in `decisions.md` and hand the issue back to `ui-requirement-mapping` or block it, rather than silently fixing the mapping in prose.
- If interaction analysis reveals an acceptance-freeze gap, record it in `decisions.md` and hand the issue back to `ui-acceptance-contract` rather than repairing visual truth here.

### 6. Handle state and blockers conservatively

- Only advance the sub-requirement toward `interaction_ready` when the key interaction states are defined, action closure is matrix-backed, propagation is matrix-backed, `delivery-slices/index.json` is finalized, and the remaining assumptions stay inside the allowed micro-interaction boundary.
- If the requirement needs an action but design cannot carry it, block on `blocked_missing_design`.
- If Figma interaction evidence conflicts with requirement truth, block on `blocked_requirement_figma_conflict`.
- If a key business interaction cannot be resolved from current materials, block on `blocked_missing_requirement`.
- When a blocker is entered, preserve the recovery intent in `status.json` with `blocked_from_status` and `resume_target_status`; do not bypass recovery through manual edits.
- Use the separate admin support surface only for governed logging, blocker handling, status transitions, and artifact updates when available.

### 7. Re-audit before handoff

- Re-open `requirement-slice.md`, `figma-mapping.md`, `interaction-design.md`, and `traceability.json`.
- Verify that every important interaction behavior is source-backed or explicitly labeled as `Assumption: Micro Interaction`.
- Verify that no assumption changed business meaning and no upstream mapping truth was overwritten.
- If later bridge context already exists in `traceability.json`, including `api_contract_mapping`, confirm it was preserved.

## State And Blocker Rules

- If the requirement needs an action but design cannot carry it, block on `blocked_missing_design`.
- If Figma interaction evidence conflicts with requirement truth, block on `blocked_requirement_figma_conflict`.
- If a key business interaction cannot be resolved from current materials, block on `blocked_missing_requirement`.
- Do not move the sub-requirement forward as interaction-complete while those blockers remain open.
- Only advance the sub-requirement toward `interaction_ready` when the contract is source-backed, acceptance-backed, propagation-aware, and assumption-bounded.

## Hard Constraints

- Do not invent business flow or page structure.
- Do not add new fields, steps, dialogs, permissions, or page transitions.
- Do not move interaction truth into `ai-delivery-admin`.
- Do not label an assumption as if it were original Figma or Requirement fact.
- Keep `assumed_micro_interaction` inside the approved boundary only.
- Do not overwrite `figma-mapping.md` or `traceability.json`.

## Output Standard

Every interaction contract should define:

- source-backed interaction facts
- user actions
- Action Chain Matrix
- State Propagation Matrix
- system feedback
- success, empty, loading, error, and disabled states
- permission or visibility effects when they already exist in source truth
- navigation or local state changes
- motion and transition notes
- accessibility and input modality notes
- feedback priority and loading presentation when they matter to usability
- explicit assumptions and escalations

If governed admin support is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing another status or log store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md`, `figma-mapping.md`, and `traceability.json` were read before drafting
- [ ] The sub-requirement was safe to move from `acceptance_frozen` toward `interaction_ready`
- [ ] Every key interaction fact is labeled by source or by `Assumption: Micro Interaction`
- [ ] Every meaningful action appears in the `Action Chain Matrix`
- [ ] Every cross-surface consequence appears in the `State Propagation Matrix`
- [ ] All critical states are defined: success, empty, loading, error, and disabled
- [ ] Feedback surfaces and loading presentation are explicit when they matter to the user flow
- [ ] Motion and timing notes are purposeful, conservative, and do not imply decorative redesign
- [ ] Accessibility and a11y expectations such as focus visibility, keyboard reachability, and reduced-motion handling are covered when relevant
- [ ] Hover, touch, keyboard, or gesture expectations are aligned when the interaction depends on more than one modality
- [ ] No new business branch, field, step, dialog, permission rule, or page transition was invented
- [ ] `assumed_micro_interaction` stays inside the allowed boundary
- [ ] `figma-mapping.md` and `traceability.json` were preserved rather than overwritten
- [ ] `delivery-slices/index.json` was finalized after the matrices were frozen
- [ ] Existing bridge fields such as `spec_kit_refs` remain intact when they already existed
- [ ] Blockers preserve `blocked_from_status` and `resume_target_status`

## Pressure Scenarios

Use these as mental regression tests while writing or updating the interaction contract.

### Scenario 1: Only loading or focus behavior is missing

Expected behavior:

- continue the contract
- record `Assumption: Micro Interaction`
- do not block if business meaning is unchanged

### Scenario 1b: The source shows an action but does not specify how progress or completion feedback appears

Expected behavior:

- choose the lightest feedback pattern that preserves orientation
- prefer inline or local feedback before heavier interruption when source truth allows
- record the choice as `Assumption: Micro Interaction` or `Source: Existing Pattern`

### Scenario 1c: A flow appears to need loading, but the source does not specify the loading scope

Expected behavior:

- choose the narrowest loading scope that matches the action scope
- preserve layout and context whenever possible
- record whether the user can keep editing, must wait, or can retry in place

### Scenario 2: Figma implies a confirm dialog that Requirement does not mention

Expected behavior:

- do not invent the dialog as truth
- block on `blocked_requirement_figma_conflict` if the conflict is real
- or escalate the mismatch explicitly

### Scenario 3: The interaction needs a new business decision to proceed

Expected behavior:

- block on `blocked_missing_requirement`
- record the exact unresolved business meaning
- do not patch it with a friendly default

### Scenario 4: `figma-mapping.md` exists, but the executable-node evidence is stale or weak

Expected behavior:

- stop and hand the work back to `ui-requirement-mapping`
- do not write an authoritative interaction contract on top of untrusted mapping evidence

### Scenario 5: `traceability.json` already contains bridge context such as `spec_kit_refs`

Expected behavior:

- preserve those fields
- do not replace `traceability.json`
- do not invent a second bridge artifact

### Scenario 6: An existing team pattern suggests a smoother flow than the source materials support

Expected behavior:

- record it only as `Source: Existing Pattern` or `Assumption: Micro Interaction` when allowed
- do not let convenience override Requirement or Figma truth

### Scenario 7: Motion detail is missing, but a transition is needed to keep state change understandable

Expected behavior:

- record a short, functional motion note
- keep timing conservative and the transition interruptible
- respect reduced-motion expectations
- do not turn the gap into decorative animation work

### Scenario 8: A control relies on hover or gesture affordance in the design evidence

Expected behavior:

- define the equivalent focus, touch, or visible fallback behavior if the source or existing pattern supports it
- do not let hover-only or gesture-only discovery become the only path for important actions
- escalate if the missing fallback changes usability or business meaning

## Handoff

Stop after producing the interaction contract and passing the self-check.

If the user wants to continue, hand the downstream stage `interaction-design.md`, `decisions.md`, and the preserved governed sub-requirement package. Do not perform Spec Kit planning or implementation inside this skill unless the user explicitly asks for the next stage.
