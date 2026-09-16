# Stage 3: Design Contract

Stage 3 produces a single canonical `design.md` behavior and solution contract.
Frameworks may contribute reasoning methods, but they do not add persisted
`spec.md`, `plan.md`, or `tasks.md` artifacts. Concrete tooling follows
[framework-adaptation.md](framework-adaptation.md).

Before dispatching a framework action, apply the
[artifact containment protocol](framework-adaptation.md#artifact-containment-protocol-required):
pass the canonical `design.md` path, treat framework directories as read-only
inputs, and skip any persistence step that cannot honor that path.

## When to run

Run `solution-design` for every active schema 2.0 sub-requirement after:

- `split_ready` when `ui_truth_mode` is `none` or `existing`; or
- `acceptance_frozen` when `ui_truth_mode` is `figma` or `runtime-baseline`.

A changed or stale `design.md` hash reopens this action. A valid
dependency-ready `design_ready` slice proceeds directly to `implement`; it does
not wait for unrelated slices.

## Inputs

- `requirement-slice.md` and applicable global rules
- dependency graph and source references
- API or protocol evidence, when available
- for enabled UI truth, the frozen Stage 2 component and current v3
  `ui-truth-index.json` profile, state, scenario, scope, preview, motion, asset,
  and host-binding evidence
- existing project architecture and constraints

Load `templates/design-state-flow-example.md` only when
`state_flow_required=true`. It is a generic reference, not project truth.

## Single design contract

Instantiate `templates/design-template.md` in the user's current conversation language and remove its language instruction comment. `design.md` contains only
information that a reviewer must decide, implementation must obey, or
acceptance can verify:

- context, in-scope behavior, and explicit non-goals;
- stable `B-###` behavior contracts and `AC-###` acceptance contracts;
- traceability from requirements and UI scenarios to behavior, acceptance, and
  verification;
- architecture, ownership, data flow, API boundaries, and material trade-offs;
- applicable UI scenario references without duplicating the Runtime Coverage
  Plan;
- state behavior at the depth required below;
- unresolved material user decisions, risks, and verification strategy.

Do not add file-by-file edit order, mechanical commands, implementation
checklists, or a restatement of every source paragraph. Those are execution
details, not design-contract content.

Before review, reconcile the behavior and acceptance contract with original
requirement sources and recorded user decisions, not just existing code.
Apply [the conflict question protocol](stage-breakdown.md)
to unresolved interpretations. Derive the compact acceptance coverage summary
using [test design](stage-implementation.md);
do not approve unknown expected outcomes as technical defaults.

## State-flow depth

State behavior is always explicit, but its form follows actual complexity:

- `state_flow_required=false`: use the compact state table in the template.
  Record relevant state/event/result/UI behavior; do not create decorative
  diagrams.
- `state_flow_required=true`: include state taxonomy and ownership, the MVI/UDF
  loop, business lifecycle, UI projection, authoritative `T-###` transition
  matrix, applicable async sequences, invariants, illegal transitions,
  persistence/recovery, and traceability. Mermaid diagrams are review views;
  the transition matrix is authoritative.

An architecture label such as MVI, Redux, or Store, and ordinary
loading/success/failure phases, do not by themselves require the complex form.
Use it when the slice materially changes guards, concurrency, stale-result
handling, recovery, persistence, or cross-surface state ownership.

## Review and CP-DESIGN

`state_flow_required` controls documentation depth. It never creates a human
gate. `user_decision_required` alone controls CP-DESIGN:

- `false`: resolve all technical questions from governed evidence, self-review
  the current `design.md`, and record `design_review.review_mode=self`.
- `true`: name each material scope, behavior, resource, or experience decision
  as a stable `D-###`; summarize the alternatives and impact; show the absolute
  `design.md` path; and pause at CP-DESIGN. After the user explicitly resolves
  and approves the current version, record `design_review.review_mode=human`.

Present related `D-###` items together under the orchestrator's **User decision
interaction** protocol. Use `request_user_input` when it is available and
permitted for the current turn, runtime, and mode; otherwise use one structured
chat question. Never interpret a permission approval prompt as CP-DESIGN review.

`user_decision_required` classifies the authority required by the current
design version; it is not the pending-review state. It remains `true` for that
design version after approval. A current hash-bound human review makes the
decision non-pending and permits `design_ready`. Set the field to `false` only
when the current design version contains no decision whose authority belongs to
the user.

The human review authorizes implementation within the approved scope. Do not
ask for a second development authorization. Technical complexity, a framework
preference, or the existence of state diagrams is not a user decision.

For either review mode, bind `reviewed_design_sha256` to the exact UTF-8 bytes
of `design.md` and record `reviewed_at` plus `reviewed_by`. Then set
`status=design_ready`. Any content change invalidates the review and reopens
`solution-design`; request CP-DESIGN again when
`user_decision_required=true` and the changed file lacks a valid hash-bound
human review.

Before review, localize every human-readable heading, table label and cell,
diagram label, sentence, risk, and decision to the user's current conversation
language. Preserve only machine keys, enums, IDs, paths, commands, code/API
symbols, Mermaid syntax, and English technical terms needed for precision.

If the design conflicts with governed requirements or frozen UI truth, open the
narrowest applicable blocker. Do not weaken the evidence or choose an
unrecorded interpretation.

## Execution persistence

Do not create `spec.md`, `plan.md`, or `tasks.md`. Stage 4 derives bounded
execution units dynamically from the current design contract, dependency graph,
and codebase. When work must survive compaction or another session, use optional
`progress.md` to record completed work, pending work, blockers, review results,
and verification commands/results. It is not a second plan and never promotes a
gate.

## API and UI-mode policy

API evidence feeds `design.md` and implementation directly. Record unresolved
integration facts as risks or blockers according to impact; do not add a
separate mapping stage.

`ui_truth_mode=none` and `existing` skip UI Truth Mapping and
`visual_acceptance_passed`. `figma` and `runtime-baseline` must retain valid
`acceptance_frozen` evidence before Stage 3 and scope-appropriate visual and
motion acceptance during Stage 4.
