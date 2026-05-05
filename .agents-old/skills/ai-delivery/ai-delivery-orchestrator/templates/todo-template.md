# AI Delivery Orchestrator Todo

- requirement_id: <requirement-id>
- requirement_doc: <absolute-path>
- api_contract: <absolute-path>
- design_source: figma-mcp-active
- source_of_truth: .ai-delivery
- current_phase: bootstrap
- current_checkpoint: none
- last_reconciled_at: <ISO8601>

## Queue

- [ ] TD-001 | stage=requirement-breakdown | scope=requirement:<requirement-id> | inputs=<absolute-path> | guard=.ai-delivery/... | retries=0/1 | agent=main | note=ready
- [ ] TD-002 | stage=prepare-speckit-context | scope=slice:<slice-id> | inputs=.ai-delivery/.../slice-contract.md;.ai-delivery/.../interaction-design.md | guard=.ai-delivery/.../spec-kit-input.md created | retries=0/2 | agent=main | note=bridge package

## Checkpoints

- [ ] CP-001 | checkpoint=tasks_ready_user_confirmation | condition=all executable slices reach tasks_ready | action=pause and wait for user approval
- [ ] CP-002 | checkpoint=hard_blocker_pause | condition=hard blocker or missing human decision | action=pause and surface blocker

## Retry Log

- none

## Active Blockers

- none
