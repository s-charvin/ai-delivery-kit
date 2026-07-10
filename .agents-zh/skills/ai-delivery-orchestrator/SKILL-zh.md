---
name: ai-delivery-orchestrator
description: 当需求文档需要经 Figma UI 契约、Spec Kit 与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）为纯工具，不感知管道。本技能拥有状态、门禁、阻塞与 handoff。

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

阶段细节：[references/stage-breakdown.md](references/stage-breakdown.md)、[stage-ui-truth.md](references/stage-ui-truth.md)、[stage-design-and-speckit.md](references/stage-design-and-speckit.md)、[stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md)、[stage-implementation.md](references/stage-implementation.md)。

## 状态模型

```
draft → split_ready → acceptance_frozen → spec_ready → plan_ready → tasks_ready → in_dev → visual_acceptance_passed → merged
```

非 UI 子需求跳过 `acceptance_frozen` 与 `visual_acceptance_passed`。

真相源：`.ai-delivery/requirements/<req-id>/status.json`。逐字复制 [templates/status-template.json](templates/status-template.json)，禁止凭记忆生成结构。执行面板：[templates/todo-template.md](templates/todo-template.md)（非真相源）。

| 字段 | 用途 |
|------|------|
| `status` | 当前状态或 `blocked_*` |
| `ui_bearing` | `true` / `false` / `null` — 切片是否拥有 UI 表面 |
| `design_approved` | 用户已批准 brainstorming 设计 |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | 阻塞清除后的恢复目标 |

## 对账优先

每次恢复或继续前，在信任 `todo.md` 之前运行对账：

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

规则：[references/reconcile-rules.md](references/reconcile-rules.md)。

## Handoff 表

每个阶段仅有一个合法下一站。完整表：[references/handoff-table.md](references/handoff-table.md)。

| 完成态 | 下一站 |
|--------|--------|
| `split_ready` + 审计（UI） | `ui-truth-mapping` |
| `split_ready` + 审计（非 UI） | `superpowers:brainstorming` |
| `acceptance_frozen` | `superpowers:brainstorming` |
| `design_approved` | `speckit-specify` |
| 全部 `tasks_ready` + CP-001 | Stage 4 SDD |
| 切片完成 | `finishing-a-development-branch` |

## 暂停点（3 个）

1. 拆分/跳过决策后 — 与用户确认
2. brainstorming 设计后 — CP-DESIGN，进入 `speckit-*` 前须明确批准
3. `tasks_ready` 后 — CP-001，进入开发前确认

## 硬边界

- 不要把工作流真相移出 `.ai-delivery`。
- 正常路径不要求用户手动选择底层技能。
- UI 子需求未 `acceptance_frozen` 不得进入 `speckit-*`。
- UI 切片未 `visual_acceptance_passed` 不得声称 `merged`。
- 仍有安全可运行项时，不得将 slice-local 阻塞升级为需求全局。
- 门禁 / 阻塞 / 状态 / 合并决策永不交给子代理。Leaf 技能可按自身规则使用子代理（`ui-truth-mapping` per-unit、Stage 4 按 SDD）。
- 编排器设计模式不要 invoke `writing-plans`，不要在 `docs/superpowers/` 写设计文档；设计摘要存入子需求 `notes`。
- 不要 fork 官方 `speckit-*` 技能。
- 所有 UI 契约 `scripts/validate-ui-contract.py` 退出 0 之前，不得设置 `acceptance_frozen`。
- UI 工作未先 `acceptance_frozen` + `visual_acceptance_passed` 且契约仍通过时，不得 `merged`。
- 实现阶段一次只改一个文件；worktree 用 rebase 合并（禁止 merge commit）。

## 状态转换门禁

| 目标状态 | 硬要求 |
|----------|--------|
| `acceptance_frozen` | 所有契约通过 `validate-ui-contract.py` |
| `spec/plan/tasks_ready`（UI） | 曾有效 `acceptance_frozen`；契约仍通过 |
| `merged`（UI） | `acceptance_frozen` + `visual_acceptance_passed` + 契约通过 |

## 拆分决策

**跳过**（全部满足）：单屏、无共享状态、单人开发、无横切规则、文档约 300 词以内。

**拆分**（任一满足）：2+ 屏、共享状态、多人协作、跨特性基础设施。

说明理由后执行。细节：[references/stage-breakdown.md](references/stage-breakdown.md)。

## 轻量审计（非 brainstorming）

`split_ready` 后，主会话对每个子需求 inline 执行 4 项检查（缺口、冲突、状态、权限）。严重问题 → 阻塞；否则写入 `notes`。此处不要 invoke `superpowers:brainstorming`。

## Stage 4（摘要）

默认：`subagent-driven-development` — 顺序任务，每任务新子代理，内部 TDD。`dispatching-parallel-agents` 仅用于独立且不重叠文件的 test/bug 域。禁止同一切片文件并行 implementer。

链路：`using-git-worktrees` → SDD → `requesting-code-review` → 视觉验收（UI）→ `verification-before-completion` → 全量测试 → `finishing-a-development-branch`。

完整 runbook：[references/stage-implementation.md](references/stage-implementation.md)。

## 阻塞项

最窄阻塞优先；优先继续最安全的可运行工作。校验失败用 `blocked_verification_failure`。目录：[references/blocker-catalog.md](references/blocker-catalog.md)。

## API 策略

API 文档直接传给 Spec Kit 与实现。缺口写入 `notes` 的 `integration_deferred`；不阻塞 UI 映射或外壳工作。

## 用户入口

1. 检查 `.ai-delivery/requirements/*`、`status.json`，运行对账。
2. 推荐 `continue req-xxx` 或 `create req-yyy`。
3. 路由前暂停等待人工确认。

| 意图 | 模式 |
|------|------|
| 新需求 + 素材 | `bootstrap` 或 `resume` |
| 继续编排 | `resume` |
| tasks_ready，进入开发 | `confirm_to_dev`（CP-001） |
| 设计待批准 | `confirm_design`（CP-DESIGN） |
| 阻塞已解决 | `blocker_recovery`（CP-002） |

## 运行时模式

`bootstrap` | `resume` | `confirm_design` | `confirm_to_dev` | `blocker_recovery` | `completed`

检查点：CP-DESIGN（设计批准）、CP-001（开发前）、CP-002（硬阻塞，仅当无可运行项）。

## 完成

所有可执行子需求 `merged` → 需求完成。无收尾仪式。
