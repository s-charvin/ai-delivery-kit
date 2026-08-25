<!-- ai-delivery-template-language
When instantiating this template, write every human-readable heading, label, and prose passage in the user's current conversation language. Keep IDs, paths, commands, code symbols, and literal protocol tokens unchanged. Remove this comment from the finished artifact.
-->

# Design Document: {{subreq_id}}

> This file is the **canonical design record** for sub-requirement `{subreq_id}`. It replaces the design fragments previously stored in `status.json` `notes`.
> - During active development (`status < archived`), this file is a **derived artifact** that may be regenerated with the spec in living-spec mode.
> - After archival (`archived`), it is frozen as an immutable snapshot. Create a new requirement directory for subsequent changes.

## 1. Context and Goals
(Why this work is needed, including its constraints and boundaries.)

## 2. Key Decisions
- Decision A: Choose X because ...
- Decision B: ...

## 3. Solution Overview
(Technology choices, module boundaries, and interaction flows. Use prose, pseudocode, or links to diagrams.)

## 4. Runtime UI Contract (UI-bearing slices only)

### Unit and Scenario Traceability
| Unit ID | Scenario IDs | Component responsibility | Data/state owner |
|---------|--------------|--------------------------|------------------|
| ... | ... | ... | ... |

### State and Transition Model
| From | Trigger | To | Loading/error/interrupt behavior |
|------|---------|----|----------------------------------|
| ... | ... | ... | ... |

### Runtime Boundaries
| Concern | Applicable scenarios | Decision and source | Verification |
|---------|----------------------|---------------------|--------------|
| Responsive/content/localization | ... | ... | ... |
| Interaction/focus/gesture | ... | ... | ... |
| Motion/reduced motion | ... | ... | ... |
| Assets/loading/error/offline | ... | ... | ... |
| Theme/accessibility/platform | ... | ... | ... |
| Performance/resource lifecycle | ... | ... | ... |

Record visible Figma fidelity separately from runtime behavior derived from requirements, project conventions, or user decisions. Do not call a non-Figma scenario 1:1 to Figma.

## 5. Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | ... | ... |

## 6. Open Questions
- ...
