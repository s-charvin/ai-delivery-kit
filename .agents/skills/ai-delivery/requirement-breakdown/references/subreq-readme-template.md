<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# `<subreq_id>` `<title>`

## Metadata

- `subreq_id`:
- `title`:
- `type`: `Global Rule | Shared Foundation | Shared Component | Feature Module | Cross-Feature Infrastructure`
- `status`: `draft | split_ready | blocked_*`
- `parent_requirement`:
- `requirement_package`:

## Navigation Summary

- `one_line_purpose`:
- `primary_surface_or_actor`:
- `recommended_read_order`: `README.md -> requirement-slice.md -> api-contract-mapping.md -> dependency.json -> traceability.json -> decisions.md`

## Top-Level Requirement Coverage

<!-- Map the exact top-level source fragments this sub-requirement covers. Do not collapse multiple source fragments into one vague bullet. -->

### Coverage Item 1

- `source_ref`:
- `coverage_status`: `covered | partial | deferred | blocked`
- `why_in_this_subreq`:
- `copied_or_linked_in`:

## Key Verbatim Requirement Excerpts

<!-- Copy the original requirement text as-is. Quote first, summarize second. -->

### Excerpt 1

- `source_ref`:
- `usage_in_this_subreq`:
- `quoted_text`:

> `<copy the original requirement text here as-is>`

## Sub-Requirement Statement

<!-- This section may normalize wording, but every statement must name its source basis. -->

- `statement`:
- `source_basis`:
- `normalization_note`:

## Boundary

### In Scope

- `statement`:
- `source_ref`:

### Out Of Scope

- `statement`:
- `source_ref`:

### Inputs

- `input`:
- `source_ref`:

### Outputs

- `output`:
- `source_ref`:

### Non-Goals

- `non_goal`:
- `source_ref`:

## Dependencies

### Depends On

- `dependency`:
- `why`:
- `source_ref`:

### Blocks

- `downstream_item`:
- `why`:
- `source_ref`:

## Acceptance Signals With Source Linkage

<!-- Every acceptance signal must point back to a concrete source fragment or quoted excerpt. -->

### Signal 1

- `signal`:
- `source_ref`:
- `derived_from`: `quoted excerpt | normalized statement`
- `notes`:

## Open Questions

### Question 1

- `question`:
- `why_open`:
- `blocking_status`: `non_blocking | blocks_split_ready | blocked`
- `related_source_ref`:

## Compression Warnings

<!-- Record any place where normalization may have compressed nuance, merged conditions, or lost source detail. -->

### Warning 1

- `risk`:
- `affected_source_ref`:
- `mitigation`: `copied verbatim | kept open | blocked`
- `follow_up_owner`:

## Current Status

- `status`:
- `status_reason`:
- `next_safe_handoff`:

## Implementation-Adjacent Notes

- `api_posture`: `not_provided | pending | mapped | needs_revalidation`
- `frontend_impact`: `none | known_gap | integration_risk | blocking_conflict`
- `notes`:

---

## Template Authoring Rules

1. `README.md` is the human-readable navigation document. Keep it concise, but never source-free.
2. Copy or quote key source text before you normalize it in `Sub-Requirement Statement`.
3. `Top-Level Requirement Coverage` should show which original paragraphs or bullets were pulled into this sub-requirement. If a source fragment is shared with another sub-requirement, say so instead of silently rewording it.
4. `Key Verbatim Requirement Excerpts` should preserve the original wording that downstream readers would otherwise lose through summarization.
5. Every `In Scope`, `Out Of Scope`, dependency, and acceptance item should name a `source_ref`.
6. Use `Compression Warnings` whenever the top-level source was dense, cross-cutting, or had conditions that could be lost when simplified.
7. If API material is missing or partial, record it as implementation-adjacent context under `Implementation-Adjacent Notes` instead of treating it as requirement instability.
8. Do not copy the `Template Authoring Rules` or `Template Example` sections into generated sub-requirement artifacts.

## Template Example

```md
# `profile-settings-edit-form` `Profile Settings Edit Form`

## Metadata
- `subreq_id`: `profile-settings-edit-form`
- `title`: `Profile Settings Edit Form`
- `type`: `Feature Module`
- `status`: `draft`
- `parent_requirement`: `account-settings`
- `requirement_package`: `.ai-delivery/requirements/account-settings/`

## Navigation Summary
- `one_line_purpose`: `Covers editing profile name and avatar from the Profile Settings screen.`
- `primary_surface_or_actor`: `Signed-in user on Profile Settings`
- `recommended_read_order`: `README.md -> requirement-slice.md -> api-contract-mapping.md -> dependency.json -> traceability.json -> decisions.md`

## Top-Level Requirement Coverage
### Coverage Item 1
- `source_ref`: `requirement.md#L12-L16`
- `coverage_status`: `covered`
- `why_in_this_subreq`: `These lines define the editable fields and save gating for the settings form.`
- `copied_or_linked_in`: `Key Verbatim Requirement Excerpts > Excerpt 1; Sub-Requirement Statement; Acceptance Signals With Source Linkage > Signal 1`

## Key Verbatim Requirement Excerpts
### Excerpt 1
- `source_ref`: `requirement.md#L12-L16`
- `usage_in_this_subreq`: `Preserves the exact save-gating behavior before normalization.`
- `quoted_text`:
> Users can edit their profile name and avatar from the Profile Settings screen. Save remains disabled until there is a valid change.

## Sub-Requirement Statement
- `statement`: `This slice covers the Profile Settings edit form, including profile name and avatar editing plus disabled-save gating until a valid change exists.`
- `source_basis`: `Excerpt 1`
- `normalization_note`: `No business rule added; wording only groups the two sentences into one slice-level statement.`

## Boundary
### In Scope
- `statement`: `Editing profile name and avatar from Profile Settings.`
- `source_ref`: `requirement.md#L12-L13`

### Out Of Scope
- `statement`: `Password changes and account deletion flows.`
- `source_ref`: `requirement.md#L20-L24`

### Inputs
- `input`: `Current profile name, selected avatar image, edited profile name.`
- `source_ref`: `requirement.md#L12-L18`

### Outputs
- `output`: `Updated profile values after a successful save.`
- `source_ref`: `requirement.md#L17-L18`

### Non-Goals
- `non_goal`: `Do not define image cropping behavior if the top-level requirement never mentions it.`
- `source_ref`: `requirement.md#L12-L18`

## Dependencies
### Depends On
- `dependency`: `profile-settings-shell`
- `why`: `The edit form lives inside the existing settings shell.`
- `source_ref`: `requirement.md#L10-L11`

### Blocks
- `downstream_item`: `profile-settings-figma-mapping`
- `why`: `UI mapping should bind to the same field and save-state contract.`
- `source_ref`: `requirement.md#L12-L16`

## Acceptance Signals With Source Linkage
### Signal 1
- `signal`: `Save remains disabled when there is no valid change.`
- `source_ref`: `requirement.md#L14-L16`
- `derived_from`: `quoted excerpt`
- `notes`: `This should remain verbatim because save gating is easy to over-summarize.`

## Open Questions
### Question 1
- `question`: `Does avatar upload failure preserve the edited profile name in the form?`
- `why_open`: `The top-level requirement defines edit capability but does not define mixed success and failure behavior.`
- `blocking_status`: `non_blocking`
- `related_source_ref`: `requirement.md#L12-L18`

## Compression Warnings
### Warning 1
- `risk`: `Grouping name edit and avatar edit into one slice may hide whether they save independently or together.`
- `affected_source_ref`: `requirement.md#L12-L18`
- `mitigation`: `kept open`
- `follow_up_owner`: `requirement-breakdown`

## Current Status
- `status`: `draft`
- `status_reason`: `Core scope is clear, but save-coupling behavior is still open.`
- `next_safe_handoff`: `Resolve the mixed-success question before promoting to split_ready.`

## Implementation-Adjacent Notes
- `api_posture`: `not_provided`
- `frontend_impact`: `integration_risk`
- `notes`: `Frontend requirement, UI mapping, and interaction work can proceed. Final save wiring may need adjustment when backend contract arrives.`
```
