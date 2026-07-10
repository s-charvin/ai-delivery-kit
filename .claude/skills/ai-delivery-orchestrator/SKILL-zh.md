---
name: ai-delivery-orchestrator
description: 当需求文档需要经 Figma UI 契约、Spec Kit 与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

> **权威版本：** 以同目录 [SKILL.md](SKILL.md)（英文）为准。

完整编排规则、handoff 表、阶段 runbook 与 reconcile 脚本见英文 SKILL 及 `references/` 目录。

## 三个暂停点

1. 拆分/跳过决策确认
2. 设计批准（CP-DESIGN）
3. `tasks_ready` 后进入开发（CP-001）

## 关键变更摘要

- Stage 1b 全量 brainstorming → 轻量 4 项 checklist 审计
- Spec Kit 前保留 brainstorming 设计（CP-DESIGN）
- Stage 4 默认 SDD 顺序执行；子代理边界与 leaf skill 对齐
- `status.json` 为真值；`todo.md` 为执行面板
