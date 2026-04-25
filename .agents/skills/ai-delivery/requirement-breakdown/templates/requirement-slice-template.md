<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# Requirement Slice

## Metadata

- `requirement_id`:
- `subreq_id`:
- `title`:
- `type`:
- `status`:
- `parent_requirement`:
- `source_coverage_status`: `complete | partial | blocked`
- `split_readiness_note`:

## Capability Profile

<!-- Mark the capability surface this sub-requirement owns so downstream stages know whether it should later freeze screen contracts, shared propagation, or integration behavior. -->

- `contains_page_states`: `true | false`
- `contains_shared_state`: `true | false`
- `contains_integration`: `true | false`
- `contains_infra_only`: `true | false`
- `boundary_note`:

## Source Requirement Coverage

<!-- Exhaustively map every top-level source fragment this slice depends on. If a fragment is shared with another slice, say so explicitly. -->

### Coverage Item 1

- `source_ref`:
- `coverage_kind`: `direct | shared_rule | partial | unresolved`
- `coverage_status`: `covered | deferred | blocked`
- `mapped_into`:
- `notes`:

## Verbatim Source Excerpts

<!-- This section is mandatory for any slice that may reach split_ready. Copy original wording before summarizing it. -->

### Excerpt 1

- `source_ref`:
- `why_preserved_verbatim`:
- `quoted_text`:

> `<copy the original requirement text here as-is>`

## Normalized Slice Statement

<!-- Normalize only after preserving the original text above. Do not introduce new business truth. -->

- `statement`:
- `source_basis`:
- `normalization_type`: `none | wording cleanup | merged adjacent lines | partial extraction`
- `normalization_note`:

## Scope Boundary

### In Scope

- `statement`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`

### Out Of Scope

- `statement`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`

### Inputs

- `input`:
- `source_ref`:

### Outputs

- `output`:
- `source_ref`:

### Non-Goals

- `non_goal`:
- `source_ref`:

## Dependency Contract

### Depends On

- `dependency`:
- `why`:
- `source_ref`:

### Blocks

- `downstream_item`:
- `why`:
- `source_ref`:

### External Constraints

- `constraint`:
- `source_ref`:

## Delivery-Slice Candidates

<!-- Record likely execution slices now, but do not freeze final page-state slicing until later contract stages. -->

### Candidate 1

- `candidate_id`:
- `candidate_type`: `page-state | shared-state | integration`
- `owned_truth`:
- `why_now`:
- `freeze_later_at`: `ui-acceptance-contract | ui-interaction-design | n/a`
- `source_basis`:

## Acceptance Signals

### Signal 1

- `signal`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`
- `verification_note`:

## Open Questions

### Question 1

- `question`:
- `why_open`:
- `blocking_status`: `non_blocking | blocks_acceptance_contract | blocks_slice_synthesis | blocked`
- `related_source_ref`:

## Ambiguities And Conflicts

### Item 1

- `issue`:
- `conflict_type`: `source ambiguity | source conflict | shared-rule overlap | missing business fact`
- `related_source_ref`:
- `resolution_path`:

## Compression Warnings

### Warning 1

- `risk`:
- `affected_source_ref`:
- `what_was_compressed`:
- `mitigation`: `copied verbatim | left unresolved | blocked`

## Source Requirement Reference Index

- `source_ref`:
- `used_in_sections`:

---

## Template Authoring Rules

1. `requirement-slice.md` is the authoritative downstream contract for the sub-requirement. It should preserve top-level requirement meaning with minimal compression.
2. Fill `Source Requirement Coverage` exhaustively. If a top-level fragment matters to this slice, it must appear here even if it is also used by another slice or global rule.
3. `Verbatim Source Excerpts` is mandatory before promoting a slice to `split_ready`. Quote the critical source text exactly as written.
4. `Normalized Slice Statement` may improve readability, but it cannot replace the excerpts or invent product truth.
5. Every scope item, dependency, acceptance signal, and open question should be traceable back to a `source_ref`.
6. `Ambiguities And Conflicts` should capture unstable or conflicting truth instead of smoothing it over.
7. `Compression Warnings` should call out places where the slice structure may compress nuance from the top-level requirement.
8. Do not copy the `Template Authoring Rules` or `Template Example` sections into generated slice artifacts.

## Template Example

```md
# Requirement Slice

## Metadata
- `requirement_id`: `account-settings`
- `subreq_id`: `profile-settings-edit-form`
- `title`: `Profile Settings Edit Form`
- `type`: `Feature Module`
- `status`: `draft`
- `parent_requirement`: `account-settings`
- `source_coverage_status`: `partial`
- `split_readiness_note`: `Need to resolve whether avatar upload failure preserves edited name input.`

## Capability Profile
- `contains_page_states`: `true`
- `contains_shared_state`: `false`
- `contains_integration`: `false`
- `contains_infra_only`: `false`
- `boundary_note`: `This slice owns a page-bearing edit surface, but not cross-page propagation truth.`

## Source Requirement Coverage
### Coverage Item 1
- `source_ref`: `requirement.md#L12-L16`
- `coverage_kind`: `direct`
- `coverage_status`: `covered`
- `mapped_into`: `Verbatim Source Excerpts > Excerpt 1; Normalized Slice Statement; Scope Boundary > In Scope; Acceptance Signals > Signal 1`
- `notes`: `Core edit-form and save-gating requirement.`

### Coverage Item 2
- `source_ref`: `requirement.md#L17-L18`
- `coverage_kind`: `partial`
- `coverage_status`: `deferred`
- `mapped_into`: `Open Questions > Question 1; Compression Warnings > Warning 1`
- `notes`: `Success and failure behavior is mentioned, but the exact mixed outcome handling is unclear.`

## Verbatim Source Excerpts
### Excerpt 1
- `source_ref`: `requirement.md#L12-L16`
- `why_preserved_verbatim`: `Save gating is easy to distort if summarized too aggressively.`
- `quoted_text`:
> Users can edit their profile name and avatar from the Profile Settings screen. Save remains disabled until there is a valid change.

### Excerpt 2
- `source_ref`: `requirement.md#L17-L18`
- `why_preserved_verbatim`: `Preserves the exact failure wording for later clarification.`
- `quoted_text`:
> If avatar upload fails, show a retryable error and keep the user in context.

## Normalized Slice Statement
- `statement`: `This slice covers editing profile name and avatar from Profile Settings, including disabled-save gating until a valid change exists.`
- `source_basis`: `Excerpt 1`
- `normalization_type`: `merged adjacent lines`
- `normalization_note`: `No new rule added; adjacent lines were combined into one slice-level statement.`

## Scope Boundary
### In Scope
- `statement`: `Profile name edit interaction.`
- `source_ref`: `requirement.md#L12-L16`
- `derived_from`: `verbatim excerpt`

- `statement`: `Avatar edit interaction.`
- `source_ref`: `requirement.md#L12-L18`
- `derived_from`: `verbatim excerpt`

### Out Of Scope
- `statement`: `Password reset and account deletion.`
- `source_ref`: `requirement.md#L20-L24`
- `derived_from`: `normalized statement`

### Inputs
- `input`: `Current profile values, edited name value, selected avatar file.`
- `source_ref`: `requirement.md#L12-L18`

### Outputs
- `output`: `Saved profile changes after successful submission.`
- `source_ref`: `requirement.md#L17-L18`

### Non-Goals
- `non_goal`: `Do not infer image crop, resize, or moderation behavior if the requirement never defines it.`
- `source_ref`: `requirement.md#L12-L18`

## Dependency Contract
### Depends On
- `dependency`: `profile-settings-shell`
- `why`: `This form is hosted inside the settings surface.`
- `source_ref`: `requirement.md#L10-L11`

### Blocks
- `downstream_item`: `profile-settings-edit-figma-mapping`
- `why`: `Downstream mapping must preserve the same field and save-state contract.`
- `source_ref`: `requirement.md#L12-L16`

### External Constraints
- `constraint`: `Do not redefine upload retry behavior without clearer product truth.`
- `source_ref`: `requirement.md#L17-L18`

## Delivery-Slice Candidates
### Candidate 1
- `candidate_id`: `profile-settings-edit-idle`
- `candidate_type`: `page-state`
- `owned_truth`: `The editable Profile Settings screen state before submission.`
- `why_now`: `The requirement already establishes a stable page-bearing state and field set.`
- `freeze_later_at`: `ui-acceptance-contract`
- `source_basis`: `Excerpt 1`

## Acceptance Signals
### Signal 1
- `signal`: `Users can edit profile name and avatar from Profile Settings.`
- `source_ref`: `requirement.md#L12-L13`
- `derived_from`: `verbatim excerpt`
- `verification_note`: `Do not collapse the two editable fields into a single generic "profile update" label.`

### Signal 2
- `signal`: `Save remains disabled until there is a valid change.`
- `source_ref`: `requirement.md#L14-L16`
- `derived_from`: `verbatim excerpt`
- `verification_note`: `Keep the gating rule source-linked because it is easy to under-specify.`

## Open Questions
### Question 1
- `question`: `When avatar upload fails, should the edited name stay locally retained and still be savable?`
- `why_open`: `The requirement defines retryable error but does not define partial success behavior.`
- `blocking_status`: `blocks_slice_synthesis`
- `related_source_ref`: `requirement.md#L17-L18`

## Ambiguities And Conflicts
### Item 1
- `issue`: `The source implies retryable failure handling but does not say whether save is atomic across name and avatar changes.`
- `conflict_type`: `source ambiguity`
- `related_source_ref`: `requirement.md#L17-L18`
- `resolution_path`: `Keep as an open question and do not promote to split_ready until the coupling rule is explicit if downstream mapping depends on it.`

## Compression Warnings
### Warning 1
- `risk`: `A single slice for name edit plus avatar edit may compress whether these edits are submitted together or independently.`
- `affected_source_ref`: `requirement.md#L12-L18`
- `what_was_compressed`: `Submit coupling and mixed-success behavior.`
- `mitigation`: `left unresolved`

## Source Requirement Reference Index
- `source_ref`: `requirement.md#L10-L11`
- `used_in_sections`: `Dependency Contract > Depends On`

- `source_ref`: `requirement.md#L12-L16`
- `used_in_sections`: `Source Requirement Coverage; Verbatim Source Excerpts; Normalized Slice Statement; Scope Boundary; Acceptance Signals`

- `source_ref`: `requirement.md#L17-L18`
- `used_in_sections`: `Source Requirement Coverage; Verbatim Source Excerpts; Outputs; Open Questions; Ambiguities And Conflicts; Compression Warnings`
```
