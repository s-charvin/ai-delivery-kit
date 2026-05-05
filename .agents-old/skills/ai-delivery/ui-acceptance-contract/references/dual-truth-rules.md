# Dual Truth Rules

## Source Of Truth

- Requirement owns functional truth.
- Figma owns visual truth.
- `.ai-delivery/` is the only workflow artifact truth inside the business project.
- `ai-delivery-admin` is a governed support surface, not a replacement truth store.

## Conflict Handling

When Requirement and Figma disagree:

- stop normal execution
- record the mismatch in the relevant requirement folder
- move the affected sub-requirement into an appropriate blocker state
- do not invent missing functionality, screens, fields, states, or flow steps

## Allowed Inference Boundary

Only limited inference is allowed:

- micro-interaction defaults
- usability defaults that do not change business meaning
- reuse of already-established governed patterns that do not alter Requirement or Figma truth

All limited inference must be explicitly marked as `assumed_micro_interaction` or documented in `decisions.md`.
