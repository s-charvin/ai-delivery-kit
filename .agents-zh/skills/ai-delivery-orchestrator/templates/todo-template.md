# AI 交付编排器 — 执行面板

> **非真相源。** 若与本文件冲突，以 `.ai-delivery/requirements/<req-id>/status.json` 为准，并重写本文件头部。

- requirement_id: `<req-id>`
- requirement_root: `.ai-delivery/requirements/<req-id>/`
- status_file: `.ai-delivery/requirements/<req-id>/status.json`
- source_of_truth: `.ai-delivery`
- runtime_mode: `bootstrap`
- current_checkpoint: `none`
- last_reconciled_at: `<ISO8601>`
- next_skill: `requirement-breakdown`
- next_subreq: `<subreq-id>`

## 对账命令

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

每次恢复或继续前，在信任本面板前先运行对账。

## 队列

- [ ] TD-001 | stage=requirement-breakdown | scope=subreq:<subreq-id> | guard=split_ready | agent=main | note=ready

## 检查点

- [ ] CP-DESIGN | checkpoint=design_approval | condition=各子需求 brainstorming 设计已批准 | action=暂停等待用户批准
- [ ] CP-001 | checkpoint=tasks_ready_user_confirmation | condition=所有可执行子需求已达 tasks_ready | action=开发前暂停
- [ ] CP-002 | checkpoint=hard_blocker_pause | condition=无安全可运行队列项剩余 | action=暂停并呈现阻塞

## 活跃阻塞

- none

## 重试日志

- none
