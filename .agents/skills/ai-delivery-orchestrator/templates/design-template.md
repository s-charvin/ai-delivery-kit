<!-- ai-delivery-meta: {"version":3,"artifact_type":"design-contract","layout_key":"solution_design","canonical_path":"design.md","updated_at":"<ISO8601>","updated_by":"<agent>"} -->
<!-- ai-delivery-template-language
When instantiating this template, preserve the ai-delivery-meta comment and its machine keys, replacing only its timestamp and author placeholders. Write every human-readable heading, label, and prose passage in the user's current conversation language. Keep IDs, paths, commands, code symbols, and literal protocol tokens unchanged. Remove this language-instruction comment from the finished artifact.

Language boundary: localize Markdown headings, table headers/cells, explanatory prose, risk/open-question text, and Mermaid node, edge, or participant labels. Keep only machine syntax, keys, enum values, IDs, paths, commands, code/API/library/protocol names, and necessary standard technical terms in English. Mermaid syntax keywords stay unchanged; their labels do not. Unexplained English prose or headings must be fixed before review.
-->

# Design Contract: {{subreq_id}}

> This is the only persisted behavior and solution-design contract for `{subreq_id}`. It is not an execution plan or file-by-file task list. The review in `status.json` is valid only for the exact SHA-256 of this file.

## 1. Context and Scope

### Goal
(The user-visible or system outcome this slice must produce.)

### In Scope
- ...

### Out of Scope
- ...

### Constraints and Existing Authority
- Requirement source: ...
- Existing architecture/API/project rule: ...
- UI truth source, when enabled: `contracts/ui-truth-index.json`

<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## 2. Behavioral Boundary

(State the actors, inputs, outputs, exclusions, permissions, data ownership, and failure boundaries that implementation must preserve.)

<!-- ai-delivery:behavior-contract:behavior -->
## 3. Behavior Contract

| Behavior ID | Given | When | Then | Boundary / failure behavior |
|-------------|-------|------|------|-----------------------------|
| B-001 | ... | ... | ... | ... |

<!-- ai-delivery:behavior-contract:acceptance -->
## 4. Acceptance Contract

| Acceptance ID | Verifiable outcome | Evidence or command |
|---------------|--------------------|---------------------|
| AC-001 | ... | ... |

For each material behavior, summarize the source-backed expectation, forbidden
outcome, applicable boundary/failure/event-order cases and intended test layer.
Resolve unknown expectations with the user before implementing affected behavior.
Keep detailed cases in native tests; this is a coverage summary, not a task list.

<!-- ai-delivery:behavior-contract:traceability -->
## 5. Traceability

| Behavior ID | Requirement source | UI scenario | Acceptance ID |
|-------------|--------------------|-------------|---------------|
| B-001 | ... | `not_applicable` / ... | AC-001 |
<!-- ai-delivery:behavior-contract:end -->

## 6. Solution Design

### Architecture and Data Flow
(Only implementation-relevant boundaries, ownership, data flow, navigation, and integration contracts. Do not list mechanical edit steps.)

### Key Decisions
| Decision | Choice | Rationale and trade-off |
|----------|--------|-------------------------|
| ... | ... | ... |

### UI Scenario References

When UI truth is enabled, reference every indexed scenario without duplicating its runtime coverage plan.

| Unit ID | Scenario IDs | Implementation responsibility | Verification owner |
|---------|--------------|-------------------------------|--------------------|
| `not_applicable` / ... | ... | ... | ... |

## 7. State Flow

State-flow depth: `not_applicable` / `simple` / `complex`.

Use `not_applicable` for truly static behavior and record the reason. For a bounded flow, keep only the compact table below. Set `status.json.state_flow_required=true` only when the slice introduces or materially changes complex guards, concurrency, stale-result handling, recovery, persistence, or cross-surface state ownership; then replace this compact subsection with an adapted copy of `design-state-flow-example.md`.

<!-- ai-delivery:state-summary -->
| Transition ID | From | Event / intent | Guard | To | UI result / effect | Failure or recovery | Acceptance |
|---------------|------|----------------|-------|----|--------------------|---------------------|------------|
| T-001 | ... | ... | ... | ... | ... | ... | AC-001 |

<!-- ai-delivery:user-decisions -->
## 8. User Decisions

Set `status.json.user_decision_required=true` when this design version contains a material product, behavior, resource, or experience choice whose authority belongs to the user. Keep it `true` after approval for this version; the current hash-bound human `design_review` records that the decision is resolved. Set it to `false` only when this version contains no user-authority decision. Technical complexity alone is not a user decision. Use stable IDs for decisions that require human review.

| Decision ID | Question | Options and trade-offs | Resolution |
|-------------|----------|------------------------|------------|
| `not_applicable` / D-001 | ... | ... | ... |

## 9. Risks and Verification Notes

| Risk | Impact | Mitigation / verification |
|------|--------|---------------------------|
| ... | ... | ... |

Unresolved questions that change scope, behavior, state, resources, experience, or acceptance must be represented as user decisions before implementation. Execution order, completed work, pending work, blockers, and verification results belong in `progress.md`, not here.
