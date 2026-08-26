---
name: ai-delivery-orchestrator
description: 当需求文档需要经 Figma UI 契约、spec 管道与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）为纯工具，不感知管道。本技能拥有状态、门禁、阻塞与 handoff。

```
需求 → [拆分？] → 能力审计 → 方案设计（按需）→ Spec → Plan → Tasks → 实现 → 合并 → 归档
```

编排器是**框架无关**的：它输出抽象阶段动作，并适配用户已安装的任何 AI 开发框架。绝不要求用户安装任何东西。

## 产物语言

- 内置模板文本只是英文源默认值，不是最终输出语言。
- 标题、标签、说明、评审证据、方案设计/spec/plan/task 正文和必要代码注释，都使用用户当前对话语言；更新已有产物时也遵守此规则。
- 机器可读键、枚举值、ID、路径、命令、代码符号和协议字面量必须保持原样。
- Markdown 模板实例化后，删除 `ai-delivery-template-language` 指令注释；JSON 模板保持结构不变，只本地化人类可读的描述值。

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
| 2 | 按能力启用的 `ui-truth-mapping`（仅 `ui_truth_mode` 需要时） | 启用时为 `acceptance_frozen` |
| 3a | `solution-design`（canonical 产物仍为 `design.md`） | `design_mode=full` 时为 `design_approved` |
| 3b | `spec` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |
| 6 | `archive` | `archived`（全部子需求） |

阶段细节：[references/stage-breakdown.md](references/stage-breakdown.md)、[stage-ui-truth.md](references/stage-ui-truth.md)、[stage-design-and-spec.md](references/stage-design-and-spec.md)、[stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md)、[stage-implementation.md](references/stage-implementation.md)。

## 状态模型

```
draft → split_ready → [acceptance_frozen] → [design_approved] → spec_ready → plan_ready → tasks_ready → in_dev → [visual_acceptance_passed] → merged → archived
```

方括号状态按能力启用：`ui_truth_mode=none` 与 `existing` 跳过 UI truth 冻结和视觉验收；`design_mode=none` 与 `light` 不需要完整审批检查点。

真相源：`.ai-delivery/requirements/<req-id>/status.json`。逐字复制 [templates/status-template.json](templates/status-template.json) 的结构，并本地化其中人类可读的描述值；禁止凭记忆生成结构。使用用户当前对话语言实例化 [templates/todo-template.md](templates/todo-template.md)（非真相源）。

| 字段 | 用途 |
|------|------|
| `status` | 当前状态或 `blocked_*` |
| `ui_bearing` | `true` / `false` — 切片是否拥有 UI 表面；校验器要求它与 `ui_truth_mode` 一致 |
| `ui_truth_mode` | `none` / `existing` / `runtime-baseline` / `figma` — 切片所需的 UI truth 能力 |
| `design_mode` | `none` / `light` / `full` — 方案设计深度与审批策略 |
| `design_approved` | 方案设计门禁已满足：`light` 在 AI 自审后，`full` 在用户明确批准后；`none` 保持 `false` |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | 阻塞清除后的恢复目标 |

## 对账优先

每次恢复或继续前，在信任 `todo.md` 之前运行对账：

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile 输出抽象动作（`solution-design` / `spec` / `plan` / `tasks` / `implement` / `finish`，另含 kit 自有技能）— 绝不输出第三方技能名。规则：[references/reconcile-rules.md](references/reconcile-rules.md)。

## Handoff 表

每个阶段仅有一个合法下一站动作。完整表：[references/handoff-table.md](references/handoff-table.md)。

| 完成态 | 下一站 |
|--------|--------|
| `split_ready` + 审计（`ui_truth_mode=figma` 或 `runtime-baseline`） | CP-UI → `ui-truth-mapping` |
| `split_ready` + 审计（`ui_truth_mode=none` 或 `existing`） | `design_mode` 为 `light` 或 `full` 时进入 `solution-design`，否则进入 `spec` |
| `acceptance_frozen` | 按 `design_mode` 进入 `solution-design` |
| `design_approved=true` 或 `design_mode=none` | `spec` |
| 全部 `tasks_ready` + CP-001 | Stage 4 `implement` |
| 切片完成 | `finish` |

## 暂停点（6 个）

1. 拆分/跳过决策后 — 与用户确认
2. 启用 UI truth 能力写生产代码前 — CP-UI，授权受控视觉实现与切片 worktree
3. `design_mode=full` 方案设计会话后 — CP-DESIGN，进入 `spec` 前须明确批准
4. `tasks_ready` 后 — CP-001，进入剩余开发工作前确认
5. 评审循环预算耗尽 — 任务级评审循环（实现 → 评审 → 修复 → 复审）在没有干净一轮的情况下停下；报告未解决的 finding 并等待用户
6. 所有子需求 `merged` 后 — CP-ARCHIVE，标记 `archived` 前确认冻结不可变归档

## 硬边界

- 不要把工作流真相移出 `.ai-delivery`。
- 正常路径不要求用户安装或选择框架/技能；适配已安装的现状。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的子需求未 `acceptance_frozen` 不得进入 `spec`；`none` 与 `existing` 跳过该 gate。
- 只有模式启用且明确确认、记录 CP-UI 后，才能 dispatch `ui-truth-mapping`。Stage 2 会写生产代码，必须创建或复用切片 worktree，执行 TDD/golden 测试并完成新鲜上下文评审闭环。
- UI truth 切片未 `visual_acceptance_passed` 不得声称 `merged`；`none` 与 `existing` 使用普通行为/语义证据。
- 仍有安全可运行项时，不得将 slice-local 阻塞升级为需求全局。
- 门禁 / 阻塞 / 状态 / 合并决策永不交给子代理。Leaf 技能可按自身规则使用子代理（`ui-truth-mapping` per-unit、Stage 4 按所选执行档位）。
- 编排器方案设计模式不要把文档写进框架自有目录；规范方案设计写入子需求 `design.md`，`notes` 只保留短指针。
- 对 `ui_truth_mode=figma` 或 `runtime-baseline`，每个 UI unit 尚未具备真实宿主组件、十个维度的按适用性运行时 coverage、每个视觉 scenario 的官方栈预览及已向用户出示的**绝对路径**、有效 v2 `contracts/ui-truth-index.json`（路径/hash/来源/profile/scenario/coverage 与当前预览 hash 绑定确认），或 Stage 2 评审未干净之前，不得设置 `acceptance_frozen`。Stage 2 仅通过 `ui-truth-mapping` 写真实组件 — 绝不经由 `figma-design-to-code`，也禁止生成 `ui-contract.html`。
- Stage 4：`ui_truth_mode=figma` 或 `runtime-baseline` 的切片复用 Stage 2 worktree；不得创建第二个 worktree 或重画组件。`existing` 使用已有组件和普通行为/语义验证，`none` 没有 UI truth 产物。默认不要再查 TemPad / 不要跑 `figma-design-to-code`；已冻结组件 + 已确认预览才是视觉真值。遵循 fill / hug / fixed（fill = 父宽减内边距，不是快照 px）。禁止从 HTML 再画一遍 Flutter。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的 UI truth 工作未先 `acceptance_frozen` + `visual_acceptance_passed`、有效 v2 `ui-truth-index.json`，以及覆盖全部已索引 scenario 的结构化 `visual-acceptance.json` 时，不得 `merged`；`none` 与 `existing` 按普通验证收口。
- 未生成冻结的 `archive/<ISO-ts>/` 快照及带 sha256 的 `MANIFEST.json` 前，不得设为 `archived`；归档不可原地修改。
- 最新一轮评审不干净时不得声称任务完成或合并；评审循环预算耗尽时升级给用户。
- 实现阶段一次只改一个文件；worktree 用 rebase 合并（禁止 merge commit）。

## 状态转换门禁

| 目标状态 | 硬要求 |
|----------|--------|
| `acceptance_frozen` | 仅 `ui_truth_mode=figma` 或 `runtime-baseline`：CP-UI 已记录；切片 worktree 证据已记录；真实组件能编过；Stage 2 TDD/评审干净；十个运行时维度均为 `covered` 或有理由的 `not_applicable`；预览路径、v2 index 路径/hash/来源/profile/scenario/coverage 与预览绑定确认均有效 |
| `spec/plan/tasks_ready`（UI truth） | 曾有效 `acceptance_frozen`；v2 index 的路径、hash、coverage 与确认绑定仍有效 |
| `merged`（UI truth） | UI truth 模式已有 `acceptance_frozen` + `visual_acceptance_passed` + 有效 v2 index + 结构化验收；`existing` 使用普通行为/语义证据，`none` 跳过视觉验收 |
| `archived` | 冻结的 `archive/<ISO-ts>/` 快照 + 带 sha256 的 `MANIFEST.json`，且不可变（经 `--verify-archive` 校验） |

## 拆分决策

**跳过**（全部满足）：单屏、无共享状态、单人开发、无横切规则、文档约 300 词以内。

**拆分**（任一满足）：2+ 屏、共享状态、多人协作、跨特性基础设施。

说明理由后执行。细节：[references/stage-breakdown.md](references/stage-breakdown.md)。

## 轻量审计（非方案设计探索）

`split_ready` 后，主会话对每个子需求 inline 执行 4 项检查（缺口、冲突、状态、权限），再确定 `ui_truth_mode` 与 `design_mode`。严重问题 → 阻塞；否则写入 `notes`。此处不要执行 `solution-design` 动作。

## Stage 4（摘要）

`implement` 动作按所选档位执行（见 `references/frameworks/`）：有 superpowers 时子代理驱动，有 ECC 时代理驱动，原生档走内联纪律。无论哪个档位，默认纪律一致：顺序任务、内部 TDD、声称完成前先评审。禁止同一切片文件并行实现者。

链路：启用 UI truth 的切片复用 Stage 2 工作区（其他切片在此创建）→ 任务执行（TDD）→ 代码评审 → 按需在 `visual-acceptance.json` 记录 scenario 完整视觉/运行时验收 → 完成前验证 → 全量测试 → 合并。

UI truth 切片：接线已经写好的组件（API / 路由 / 状态 / 挂载）；`existing` UI 只做普通行为/语义验证；默认不要再查 TemPad / 不要跑 `figma-design-to-code`。

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
| UI truth 能力待授权 | `confirm_ui`（CP-UI） |
| tasks_ready，进入开发 | `confirm_to_dev`（CP-001） |
| 完整方案设计待批准 | `confirm_solution_design`（CP-DESIGN） |
| 阻塞已解决 | `blocker_recovery`（CP-002） |

## 运行时模式

`bootstrap` | `resume` | `confirm_ui` | `confirm_solution_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

检查点：CP-UI（启用 UI truth 的生产代码前）、CP-DESIGN（完整方案设计批准）、CP-001（剩余开发前）、CP-002（硬阻塞，仅当无可运行项）、CP-ARCHIVE（冻结前，所有子需求均已 merged）。

## 完成

所有可执行子需求 `merged` → `runtime_mode` 为 `closing`（CP-ARCHIVE）。执行最后一条归档命令前，先把 `templates/delivery-report-template.md` 实例化为使用用户当前对话语言的临时模板，删除其中的 `ai-delivery-template-language` 注释，并保留所有占位符。对每个子需求运行 `scripts/archive-subrequirement.py`，冻结 `archive/<ISO-ts>/` + `MANIFEST.json` 并将状态推进至 `archived`；最后一条命令须通过 `--delivery-report-template <path>` 传入准备好的模板。已本地化的 `delivery-report.md` 不存在时，不得声称 `completed`。当每个子需求均为 `archived` 时，需求进入 `completed`，归档区不可变 — 任何变更须新建 `<req-id>/` 目录。

## 编排形态（不变量）

以下规则防止编排退化，适用于主会话与对账 dispatch：

1. **主会话即编排者** — 单个人工会话驱动顺序管线（Pattern 4），阶段之间不得插入 router persona。
2. **Dispatch 表是数据，不是 router** — `ACTION_BY_STATUS` / 对账输出的是抽象动作名；不得引入重新推导或转述该表的 persona。
3. **Subagent 仅叶子、深度 ≤ 1** — 实现与评审可按 tier 规则委派 subagent；编排器不得嵌套编排 persona。
4. **禁止模式** — persona 调 persona 链、仅转述上一阶段的「顺序编排器」层、深层 persona 树。
5. **评审永不自动合并** — `merged` / `archived` 须有干净的 `verification.md` 证据与人工门禁；预算耗尽必须暂停等待用户。

本 kit 只负责单仓治理交付（`.ai-delivery/`、`status.json`、门禁）。多方协同不在本 skill 范围内 — 需要时另行安装 [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination)。
