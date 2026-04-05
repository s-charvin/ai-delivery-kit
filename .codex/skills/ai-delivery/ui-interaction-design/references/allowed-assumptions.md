# Allowed Assumptions

Allowed as `assumed_micro_interaction`:

- button loading presentation
- hover, active, and focus behavior
- toast versus inline error priority
- empty-list baseline feedback
- validation trigger timing
- disabled controls cannot be activated
- submit deduplication while requests are in flight
- baseline keyboard reachability

Recording rules:

- label the line as `Assumption: Micro Interaction`
- identify the supporting source gap or `Source: Existing Pattern`
- explain why the assumption stays below the business-meaning threshold
- if the assumption would change business semantics, stop and escalate instead

Not allowed:

- new business branches
- new steps, fields, modals, or confirm flows
- new permission rules
- new page transitions
- new exception semantics that are not backed by Requirement or Figma
