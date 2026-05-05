<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# Requirement Slice

## Metadata

- `requirement_id`:         # parent requirement identifier
- `subreq_id`:              # unique identifier for this slice
- `title`:                  # short, descriptive name
- `type`:                   # Global Rule | Shared Foundation | Shared Component | Feature Module | Cross-Feature Infrastructure
- `parent_requirement`:     # path to the parent requirement document

## Source Requirement Coverage
<!-- Each coverage item links a section of the original requirement to this slice. -->

### Coverage Item 1

- `source_ref`:             # line range in the original document, e.g. "req.md#L14-L22"
- `coverage_kind`: `direct | shared_rule | partial | unresolved`
    # direct       — section belongs exclusively to this slice
    # shared_rule  — section is a cross-cutting rule that affects 2+ slices
    # partial      — section is split; this slice owns part of it
    # unresolved   — ownership is not yet determined
- `coverage_status`: `covered | deferred | unresolved`
    # covered      — section is fully accounted for in this slice
    # deferred     — section is intentionally set aside; reason in `notes`
    # unresolved   — coverage needs further clarification
- `notes`:                  # explanation, especially for deferred/unresolved items

## Normalized Slice Statement
<!-- One sentence summarizing what this slice is about. Derived from source, not verbatim. -->

- `statement`:              # one-sentence summary
- `source_basis`:           # source_ref(s) this statement derives from
- `normalization_type`: `none | wording cleanup | merged adjacent lines | partial extraction`
- `normalization_note`:     # what was done and why

## Scope Boundary

### In Scope

- `statement`:              # what IS included
- `source_ref`:             # source evidence
- `derived_from`: `source coverage | normalized statement`

### Out Of Scope

- `statement`:              # what is explicitly excluded
- `source_ref`:
- `derived_from`: `source coverage | normalized statement`

### Inputs

- `input`:                  # external inputs this slice requires (data, APIs, upstream slices)
- `source_ref`:

### Outputs

- `output`:                 # what this slice produces
- `source_ref`:

### Non-Goals

- `non_goal`:               # explicitly NOT a goal (prevents scope creep)
- `source_ref`:

## Dependency Contract

### Depends On

- `dependency`:             # subreq_id of the dependency
- `why`:                    # reason for the dependency
- `source_ref`:

### External Constraints

- `constraint`:             # constraint imposed by external systems or interfaces
- `source_ref`:

## Acceptance Signals
<!-- Verifiable conditions that prove the slice is satisfied. -->

### Signal 1

- `signal`:                 # verifiable acceptance condition
- `source_ref`:
- `derived_from`: `source coverage | normalized statement`

## Open Questions
<!-- Questions that could not be resolved during breakdown. -->

### Question 1

- `question`:               # the open question
- `why_open`:               # why it cannot be resolved now (missing information, conflicting sources, etc.)
- `related_source_ref`:

## Ambiguities And Conflicts
<!-- Unclear or contradictory statements found in the source document. -->

### Item 1

- `issue`:                  # description of the ambiguity or conflict
- `conflict_type`: `source ambiguity | source conflict | shared-rule overlap | missing business fact`
    # source ambiguity        — source wording is vague; multiple interpretations possible
    # source conflict         — source contradicts itself
    # shared-rule overlap     — cross-cutting rule conflicts with a slice's scope
    # missing business fact   — key business fact is absent from the source
- `related_source_ref`:
- `resolution_path`:        # suggested way to resolve
