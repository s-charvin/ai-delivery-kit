<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-25T00:00:00.000Z","updated_by":"codex"} -->

# IM Contacts And Add Friends Todo

source_of_truth: .ai-delivery

## Checkpoints

- CP-001 | checkpoint=tasks_ready_user_confirmation | guard=status.json:tasks_ready
- CP-002 | checkpoint=hard_blocker_pause | guard=open_blocker_absent

## Contacts Directory Slice Bridge

- stage=prepare-speckit-context | scope=slice:contacts-friends-idle | artifact=spec-kit-input.md
- stage=speckit-plan-bind | scope=slice:contacts-friends-idle | artifact=plan.md | guard=status.json:tasks_ready
- stage=speckit-tasks-bind | scope=slice:contacts-friends-idle | artifact=tasks.md | guard=status.json:tasks_ready
