---
name: ai-delivery-orchestrator
description: 当需求文档需要经 Figma UI 契约、Spec Kit 与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

> **权威版本：** 以仓库内 `.agents/skills/ai-delivery-orchestrator/SKILL.md`（英文 canonical）为准。

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）为纯工具；本技能拥有状态、门禁、阻塞与 handoff。

```
需求 → [拆分？] → UI 真值 → 设计 → Spec Kit → SDD 实现 → 合并
```

## 管道

| 阶段 | 技能 | 门禁 |
|------|------|------|
| 1 | `requirement-breakdown` + 轻量审计 | `split_ready` |
| 2 | `ui-truth-mapping`（仅 UI） | `acceptance_frozen` |
| 3a | `superpowers:brainstorming`（设计） | `design_approved` |
| 3b | `speckit-specify` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | Superpowers SDD 套件 | `visual_acceptance_passed` → `merged` |

阶段细节见 `references/` 目录（与英文版同步）。

## 状态

真相源：`.ai-delivery/requirements/<req-id>/status.json`。从 `templates/status-template.json` 逐字复制，禁止凭记忆生成结构。

新增字段：`ui_bearing`、`design_approved`。

## 对账优先

每次恢复或继续前运行：

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

## 三个暂停点

1. 拆分/跳过决策确认
2. 设计批准（CP-DESIGN）— `speckit-*` 前必须经 brainstorming 设计并获用户批准
3. `tasks_ready` 后（CP-001）— 进入开发前确认

## 关键变更（相对旧版）

- **删除** Stage 1b 全量 brainstorming → 改为拆分后 **轻量 4 项 checklist 审计**（主会话 inline，写入 `notes`）
- **保留** Spec Kit 前一次 brainstorming 设计，升为 CP-DESIGN 暂停点
- **Stage 4** 默认 `subagent-driven-development`（顺序任务）；`dispatching-parallel-agents` 仅用于独立 test/bug 域
- **子代理**：门禁/阻塞/状态/合并永不交给子代理；`ui-truth-mapping` per-unit 子代理按 leaf 规则执行
- **`split_ready`**：要求 source_ref 覆盖 + normalized statements（非逐字摘录）
- **`todo.md`**：仅为执行面板；`status.json` 为真值

## Handoff

详见 `references/handoff-table.md`。每阶段仅一个合法下一站。

## 硬边界

- UI 子需求未 `acceptance_frozen` 不得进 `speckit-*`
- UI 未 `visual_acceptance_passed` 不得 `merged`
- `acceptance_frozen` 前所有契约须 `validate-ui-contract.py` 输出 OK
- 有安全可运行项时不得将 slice-local 阻塞升级为需求全局

## 用户入口

推荐 `continue req-xxx` 或 `create req-yyy`，人工确认后路由。详见英文 SKILL 的 User entry 表。
