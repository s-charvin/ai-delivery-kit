---
name: ai-delivery-orchestrator
description: 当需求文档需要经 Figma UI 契约、spec 管道与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）为纯工具，不感知管道。本技能拥有状态、门禁、阻塞与 handoff。

```
需求 → [拆分？] → UI 真值 → 设计 → Spec → Plan → Tasks → 实现 → 合并
```

编排器是**框架无关**的：它输出抽象阶段动作，并适配用户已安装的任何 AI 开发框架。绝不要求用户安装任何东西。

## 框架适配（每会话执行一次）

执行任何阶段动作之前：

1. 按 [references/framework-adaptation.md](references/framework-adaptation.md) 自查环境（已安装框架：spec-kit / OpenSpec / superpowers / ECC；都没装 → 原生档）。
2. 为当前动作选择档位（规格类动作 vs 执行纪律类动作）。
3. 在子需求 `decisions.md` 记录一次选择。

动作 → 指南分发表与 loop 模型：[references/framework-adaptation.md](references/framework-adaptation.md)。各框架使用指南：`references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`。

## 管道

| 阶段 | 抽象动作 | 门禁 |
|------|----------|------|
| 1 | `requirement-breakdown` + 轻量审计 | `split_ready` |
| 2 | `ui-truth-mapping`（仅 UI） | `acceptance_frozen` |
| 3a | `design` | `design_approved` |
| 3b | `spec` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |

阶段细节：[references/stage-breakdown.md](references/stage-breakdown.md)、[stage-ui-truth.md](references/stage-ui-truth.md)、[stage-design-and-spec.md](references/stage-design-and-spec.md)、[stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md)、[stage-implementation.md](references/stage-implementation.md)。

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
| `design_approved` | 用户已批准设计会话的产出 |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | 阻塞清除后的恢复目标 |

## 对账优先

每次恢复或继续前，在信任 `todo.md` 之前运行对账：

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile 输出抽象动作（`design` / `spec` / `plan` / `tasks` / `implement` / `finish`，另含 kit 自有技能）— 绝不输出第三方技能名。规则：[references/reconcile-rules.md](references/reconcile-rules.md)。

## Handoff 表

每个阶段仅有一个合法下一站动作。完整表：[references/handoff-table.md](references/handoff-table.md)。

| 完成态 | 下一站 |
|--------|--------|
| `split_ready` + 审计（UI） | `ui-truth-mapping` |
| `split_ready` + 审计（非 UI） | `design` |
| `acceptance_frozen` | `design` |
| `design_approved` | `spec` |
| 全部 `tasks_ready` + CP-001 | Stage 4 `implement` |
| 切片完成 | `finish` |

## 暂停点（4 个）

1. 拆分/跳过决策后 — 与用户确认
2. 设计会话后 — CP-DESIGN，进入 `spec` 前须明确批准
3. `tasks_ready` 后 — CP-001，进入开发前确认
4. 评审循环预算耗尽 — 任务级评审循环（实现 → 评审 → 修复 → 复审）在没有干净一轮的情况下停下；报告未解决的 finding 并等待用户

## 硬边界

- 不要把工作流真相移出 `.ai-delivery`。
- 正常路径不要求用户安装或选择框架/技能；适配已安装的现状。
- UI 子需求未 `acceptance_frozen` 不得进入 `spec`。
- UI 切片未 `visual_acceptance_passed` 不得声称 `merged`。
- 仍有安全可运行项时，不得将 slice-local 阻塞升级为需求全局。
- 门禁 / 阻塞 / 状态 / 合并决策永不交给子代理。Leaf 技能可按自身规则使用子代理（`ui-truth-mapping` per-unit、Stage 4 按所选执行档位）。
- 编排器设计模式不要把设计文档写进框架自有目录；设计摘要存入子需求 `notes`。
- 所有 unit 的 `ui-contract.html` 未经 `scripts/validate-ui-contract-html.py` 退出 0，且浏览器 hydrate 默认态预览与需求 scope 对齐 + icon 资产保真 + 逐份契约用户显式确认（除非明确豁免）通过之前，不得设置 `acceptance_frozen`（见 Stage 2 冻结门槛）。Stage 2 仅通过 `ui-truth-mapping` 写契约 — 绝不经由 `figma-design-to-code`。
- UI 工作未先 `acceptance_frozen` + `visual_acceptance_passed` 且契约仍通过时，不得 `merged`。
- 最新一轮评审不干净时不得声称任务完成或合并；评审循环预算耗尽时升级给用户。
- 实现阶段一次只改一个文件；worktree 用 rebase 合并（禁止 merge commit）。

## 状态转换门禁

| 目标状态 | 硬要求 |
|----------|--------|
| `acceptance_frozen` | 所有契约通过 `validate-ui-contract-html.py`；hydrate 默认态 + 状态切换预览 OK；scope 对齐切片 In Scope；icon 有证据背书（禁手绘图形）；用户逐份确认契约（除非豁免） |
| `spec/plan/tasks_ready`（UI） | 曾有效 `acceptance_frozen`；契约仍通过 |
| `merged`（UI） | `acceptance_frozen` + `visual_acceptance_passed` + 契约通过 |

## 拆分决策

**跳过**（全部满足）：单屏、无共享状态、单人开发、无横切规则、文档约 300 词以内。

**拆分**（任一满足）：2+ 屏、共享状态、多人协作、跨特性基础设施。

说明理由后执行。细节：[references/stage-breakdown.md](references/stage-breakdown.md)。

## 轻量审计（非设计探索）

`split_ready` 后，主会话对每个子需求 inline 执行 4 项检查（缺口、冲突、状态、权限）。严重问题 → 阻塞；否则写入 `notes`。此处不要执行 `design` 动作。

## Stage 4（摘要）

`implement` 动作按所选档位执行（见 `references/frameworks/`）：有 superpowers 时子代理驱动，有 ECC 时代理驱动，原生档走内联纪律。无论哪个档位，默认纪律一致：顺序任务、内部 TDD、声称完成前先评审。禁止同一切片文件并行实现者。

链路：隔离工作区 → 任务执行（TDD）→ 代码评审 → 视觉验收（UI）→ 完成前验证 → 全量测试 → 合并。

完整 runbook：[references/stage-implementation.md](references/stage-implementation.md)。

## 阻塞项

最窄阻塞优先；优先继续最安全的可运行工作。校验失败用 `blocked_verification_failure`。目录：[references/blocker-catalog.md](references/blocker-catalog.md)。

## API 策略

API 文档直接传给 spec 管道与实现。缺口写入 `notes` 的 `integration_deferred`；不阻塞 UI 映射或外壳工作。

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

`bootstrap` | `resume` | `confirm_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

检查点：CP-DESIGN（设计批准）、CP-001（开发前）、CP-002（硬阻塞，仅当无可运行项）、CP-ARCHIVE（冻结前，所有子需求均已 merged）。

## 完成

所有可执行子需求 `merged` → `runtime_mode` 为 `closing`（CP-ARCHIVE）。对每个子需求运行 `scripts/archive-subrequirement.py`，冻结 `archive/<ISO-ts>/` + `MANIFEST.json`，将状态推进至 `archived`，并生成 `delivery-report.md`。当每个子需求均为 `archived` 时，需求进入 `completed`，归档区不可变 — 任何变更须新建 `<req-id>/` 目录。

## 编排形态（不变量）

以下规则防止编排退化，适用于主会话、对账 dispatch 及任何 `ai-delivery-coordination/` 循环执行器：

1. **主会话即编排者** — 单个人工会话驱动顺序管线（Pattern 4），阶段之间不得插入 router persona。
2. **Dispatch 表是数据，不是 router** — `ACTION_BY_STATUS` / 对账输出的是抽象动作名；不得引入重新推导或转述该表的 persona。
3. **Subagent 仅叶子、深度 ≤ 1** — 实现与评审可按 tier 规则委派 subagent；编排器不得嵌套编排 persona。
4. **禁止模式** — persona 调 persona 链、仅转述上一阶段的「顺序编排器」层、深层 persona 树。
5. **评审永不自动合并** — 循环执行器可跑 `implement` 步骤，但 `merged` / `archived` 须有干净的 `verification.md` 证据与人工门禁；预算耗尽必须暂停等待用户。

需要自主执行时，使用**外部** coordination MCP 服务（`start_loop`、`intervene_loop` 等）。skill 层在 `status.json` 保留 spec 段真值；引擎只写回执行段状态并立即重新对账。**禁止从 skill 层 import coordination Python** — 见 [references/coordination-mcp-bridge.md](references/coordination-mcp-bridge.md) 与 [docs/coordination-repo.md](../../../docs/coordination-repo.md)。
