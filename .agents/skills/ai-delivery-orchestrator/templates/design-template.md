<!-- ai-delivery-meta: {"version":1,"artifact_type":"solution-design","layout_key":"solution_design","canonical_path":"design.md","updated_at":"<ISO8601>","updated_by":"<agent>"} -->
<!-- ai-delivery-template-language
When instantiating this template, preserve the ai-delivery-meta comment and its machine keys, replacing only its timestamp and author placeholders. Write every human-readable heading, label, and prose passage in the user's current conversation language. Keep IDs, paths, commands, code symbols, and literal protocol tokens unchanged. Remove this language-instruction comment from the finished artifact.
-->

# Solution Design: {{subreq_id}}

> This file is the **canonical solution-design record** for sub-requirement `{subreq_id}`. It replaces the design fragments previously stored in `status.json` `notes`.
> - During active development (`status < archived`), this file is a **derived artifact** that may be regenerated with the spec in living-spec mode.
> - After archival (`archived`), the canonical artifacts remain in place as the historical source of truth. Create a new requirement directory for subsequent changes.

## 1. Context and Goals
(Why this work is needed, including its constraints and boundaries.)

## 2. Key Decisions
- Decision A: Choose X because ...
- Decision B: ...

## 3. Solution Overview
(Technology choices, module boundaries, and interaction flows. Use prose, pseudocode, or links to diagrams.)

## 4. UI Scenario References (UI truth modes only)

The runtime coverage source of truth is `contracts/ui-truth-index.json`. This document references indexed scenarios; it does not duplicate their Runtime Coverage Plan.

### Unit and Scenario Traceability
| Unit ID | Scenario IDs | Responsibility | Verification owner |
|---------|--------------|----------------|--------------------|
| ... | ... | ... | ... |

### State and Transition Model
| From | Trigger | To | Loading/error/interrupt behavior |
|------|---------|----|----------------------------------|
| ... | ... | ... | ... |

For each referenced scenario, state the implementation responsibility and the verification command or test owner. Runtime dimensions (state, layout, content, interaction, motion, assets, theme, accessibility, platform, and performance) remain in the UI truth index. Record visible Figma fidelity separately from runtime behavior derived from requirements, project conventions, or user decisions. Do not call a non-Figma scenario 1:1 to Figma.

## 5. Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | ... | ... |

## 6. Open Questions
- ...
