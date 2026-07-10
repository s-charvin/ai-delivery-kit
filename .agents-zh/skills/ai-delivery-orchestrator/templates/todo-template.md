# AI Delivery Orchestrator — Execution Panel

> **Not source of truth.** If this file conflicts with `.ai-delivery/requirements/<req-id>/status.json`, trust `status.json` and rewrite this file's headers.

- requirement_id: `<req-id>`
- requirement_root: `.ai-delivery/requirements/<req-id>/`
- status_file: `.ai-delivery/requirements/<req-id>/status.json`
- source_of_truth: `.ai-delivery`
- runtime_mode: `bootstrap`
- current_checkpoint: `none`
- last_reconciled_at: `<ISO8601>`
- next_skill: `requirement-breakdown`
- next_subreq: `<subreq-id>`

## Reconcile Command

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

Run reconcile before trusting this panel on every resume or continue.

## Queue

- [ ] TD-001 | stage=requirement-breakdown | scope=subreq:<subreq-id> | guard=split_ready | agent=main | note=ready

## Checkpoints

- [ ] CP-DESIGN | checkpoint=design_approval | condition=brainstorming design approved per subreq | action=pause for user approval
- [ ] CP-001 | checkpoint=tasks_ready_user_confirmation | condition=all executable subreqs at tasks_ready | action=pause before development
- [ ] CP-002 | checkpoint=hard_blocker_pause | condition=no safe runnable queue item remains | action=pause and surface blocker

## Active Blockers

- none

## Retry Log

- none
