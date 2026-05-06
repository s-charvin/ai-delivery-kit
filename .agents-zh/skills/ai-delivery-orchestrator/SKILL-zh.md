---
name: ai-delivery-orchestrator
description: 作为需求开发的唯一入口。提供需求文档，此技能自动判断是否拆分，然后串联 UI 真值映射到 Spec Kit 实现。所有状态、阻塞项和门禁都在此处管理。
---

# AI 交付编排器

完整的需求到实现管道的唯一入口：

```
需求文档 → [拆分？& 头脑风暴审计] → UI 真值映射 → [头脑风暴设计] + Spec Kit → Superpowers 开发 → 合并
                  ↑ 自动判断                                ↑ 子代理驱动的 TDD、评审、视觉验收
```

编排器拥有所有状态转换、阻塞处理、门禁决策以及技能之间的耦合。每个管道技能（`requirement-breakdown`、`ui-truth-mapping`）都是纯粹、独立的工具 — 接收输入、产生输出，对管道和彼此一无所知。

`superpowers:brainstorming` 在两个检查点使用：拆分后（需求审计 — 提前发现缺口）和 Spec Kit 前（方案设计 — 在规范驱动骨架之前确定方法）。实现阶段使用完整的 Superpowers 开发套件（`using-git-worktrees`、`test-driven-development`、`subagent-driven-development`、`dispatching-parallel-agents`、`requesting-code-review`、`finishing-a-development-branch`、`verification-before-completion`）。

## 管道概览

| 阶段 | 技能 | 输入 | 输出 | 门禁 |
|---|---|---|---|---|
| 1a | `requirement-breakdown` | 需求文档 | 子需求 + 依赖图 | 每个子需求的 `split_ready` |
| 1b | `superpowers:brainstorming` | 需求切片 + 拆分产物 | 需求审计（缺口、歧义、冲突） | 规范前质量门禁 |
| 2 | `ui-truth-mapping` | 需求切片 + Figma 设计源 | `ui-acceptance-contract.yaml` + `section-map.json` | `acceptance_frozen` |
| 3a | `superpowers:brainstorming` | YAML 契约 + 需求切片 + API 文档 | 方案设计（架构、数据流、组件策略） | 设计批准 |
| 3b | `speckit-specify` → `speckit-plan` → `speckit-tasks` | 方案设计 + YAML 契约 + 需求切片 + section-map | `spec.md` → `plan.md` → `tasks.md` | `spec_ready` → `plan_ready` → `tasks_ready` |
| 4 | Superpowers 开发套件 | 任务 + YAML 契约 + API 文档 | 实现的代码 | `visual_acceptance_passed` → `merged` |

## 状态模型

每个子需求独立追踪自身状态。状态按顺序推进：

```
draft → split_ready → acceptance_frozen → spec_ready → plan_ready → tasks_ready → in_dev → visual_acceptance_passed → merged
```

- `draft`：刚创建，边界不确定
- `split_ready`：完整的源覆盖、逐字摘录、明确的范围和依赖
- `acceptance_frozen`：YAML 契约已冻结，所有屏幕状态有源依据
- `spec_ready` / `plan_ready` / `tasks_ready`：Spec Kit 产物已生成并审计
- `in_dev`：实现进行中
- `visual_acceptance_passed`：截图匹配 YAML 契约（仅 UI 切片；非 UI 切片跳过）
- `merged`：代码已变基合并到开发分支

状态记录在需求级别的单个 `status.json` 中。以 `templates/status-template.json` 为起点 — 它以内联的 `_` 前缀元数据键记录了所有状态含义、阻塞作用域、检查点和运行时模式。

每个子需求条目：

| 字段 | 用途 |
|---|---|
| `status` | 当前状态（上述状态值之一，或 `blocked_*` 值） |
| `detail` | 该状态下正在发生什么的细粒度人类可读描述 |
| `blocked_from_status` | 阻塞前子需求正在瞄准的状态 |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` — 阻塞影响的范围 |
| `resume_target_status` | 阻塞清除后要恢复到的目标状态 |
| `notes` | 会话间交接的自由格式上下文 |

## 可运行队列与阻塞作用域

以下术语用于 `status.json` 阻塞分类和对账决策：

- **可运行队列项** — 在当前治理真值下仍可安全推进、无需捏造缺失事实的任何项。示例：Figma 证据采集、页面外壳实现、本地状态骨架、导航流程、模拟连线、只读展示路径。
- **`slice_local`** — 仅阻止一个切片、一个阶段或一个能力面。默认不得阻止不相关的切片。
- **`action_level_integration`** — 仅阻止一个操作的真实 API 连线或最终语义关闭。不阻止视觉映射、外壳工作、本地状态工作或导航骨架。
- **`requirement_global`** — 仅当所有可推导的队列项都不可运行时才有效。只要还有一个安全的可运行项存在，阻塞器就还不是需求全局的。

默认策略：**优先继续最安全的可运行工作**，而非"遇到第一个阻塞就暂停"。

## 运行时模式、检查点与解析

每次对账后确定活动模式：

1. **`completed`** — 所有可执行切片均已 `merged`。不分派新工作。
2. **`bootstrap`** — 无 `todo.md`，或需求包不完整无法推导队列。从第一个治理阶段开始构建。
3. **`confirm_to_dev`** — `todo.md` 存在，`current_checkpoint` 为 `CP-001`，所有可执行切片处于 `tasks_ready`，用户意图明确为"进入开发"。
4. **`blocker_recovery`** — `todo.md` 存在，`current_checkpoint` 为 `CP-002`，阻塞已清除。对账，仅当守卫可满足时清除阻塞，从被阻塞步骤恢复。
5. **`resume`** — `todo.md` 存在，无检查点阻止，至少一个队列项未解决或可运行。从最安全的可运行未解决项继续。

检查点：
- **`CP-001` tasks_ready_user_confirmation** — 所有可执行切片处于 `tasks_ready`；暂停等待用户确认后进入开发。
- **`CP-002` hard_blocker_pause** — 仅当没有安全的可运行队列项剩余时才有效。API 阻塞本身不足以触发，如果 UI 真值采集、外壳工作或安全的部分开发仍可继续。

`current_phase` 和 `current_checkpoint` 是执行面板提示，本身不是真值。如果与 `.ai-delivery` 冲突，信任 `.ai-delivery` 并重写 `todo.md` 头部。

## 对账规则

每次恢复或继续时，在信任 `todo.md` 之前：

1. 重新读取 `.ai-delivery` 状态和产物。
2. 对照治理产物重新检查每个守卫。
3. 在选择检查点之前将每个阻塞分为 `slice_local`、`action_level_integration` 或 `requirement_global`。
4. 重新检查阻塞实际阻止了什么：视觉真值、验收冻结、集成还是最终交付。
5. 如果守卫已满足，标记项完成而无需重新运行该阶段。
6. 如果输出存在但守卫未满足，重新运行或打开最窄阻塞。将被阻塞项保留在队列中；继续不依赖它的后续项。

## 用户入口映射

将用户意图映射到运行时模式 — 不要要求用户命名下一个技能：

1. 检查现有的 `.ai-delivery/requirements/*`、`todo.md`、`status.json`。
2. 产生一个建议：`继续 req-xxx` 或 `创建 req-yyy`。
3. 在任一路径前暂停等待人工确认。

路由确认后：
- "给了需求文档、Figma 已开，开始跑" → 无有效 `todo.md` 时进入 `bootstrap`，否则对账后 → `resume`。
- "继续编排这个需求" → 对账 → `resume`（除非有活动检查点）。
- "tasks_ready 了，继续开发" → 对账，要求 `CP-001` + 所有切片 `tasks_ready` → `confirm_to_dev`。
- "这个阻塞我处理好了，继续跑" → 对账，要求 `CP-002` → `blocker_recovery`。

## 硬边界

- 不得将工作流真值移出 `.ai-delivery`。
- 不得要求用户在正常路径中手动选择第一个底层技能。
- 不得让 UI 子需求在 `acceptance_frozen` 之前进入 `speckit-*`。
- 不得让 UI 切片在 `visual_acceptance_passed` 之前声称合并完成。
- 不得在仍有安全可运行项时将切片级阻塞升级为需求级。
- 不得让被阻塞的队列项吞掉后面仍可安全运行的项。
- 不得让子代理推进门禁、决定阻塞或合并更改。
- 不得在阶段 4 实现之外使用子代理。
- 实现期间不得应用大型多文件补丁；一次编辑一个文件。
- 不得使用合并提交重新整合工作树分支；变基以保持历史线性。
- 不得分叉官方 `speckit-specify`、`speckit-plan` 或 `speckit-tasks` 来重申仓库本地合约。
- 不要凭记忆生成 `status.json`。找到 `templates/status-template.json`，逐字复制到输出路径，然后填充子需求条目。保留所有 `_` 前缀元数据键、字段结构和默认值。只能修改值 — 不添加、删除或重命名键。

## 自动判断：拆分还是跳过？

在运行 `requirement-breakdown` 之前，分析需求。**跳过拆分** 当以下全部满足时：
- 单页面或单屏幕
- 页面或功能之间无共享状态
- 可由一个开发者独立构建无需协调
- 无横切规则（认证、权限、共享验证）
- 需求文档约 300 字以内，范围单一明确

**执行拆分** 当以下任一满足时：
- 跨越 2 个以上页面或屏幕
- 有共享状态（全局存储、跨页面传播）
- 需要多个开发者协调
- 包含跨功能基础设施或共享组件
- 有适用于多个功能区域的规则

明确陈述你的判断及理由，然后继续。

## 工作流

### 阶段 1：需求拆分

**何时运行：** 自动判断结果为"拆分"，或任何子需求处于 `draft` 且范围未解决。

**准备输入：**
- 阅读需求文档。
- 确定需求 ID 和输出目录：`.ai-delivery/requirements/<req-id>/`。

**运行 `requirement-breakdown`：**
向其提供需求文档路径。它产生带有 `requirement-slice.md`、`dependency.json` 和完整产物集的子需求。

**完成后：**
- 对每个子需求：如果范围完整（含逐字摘录和清晰依赖）→ 设为 `split_ready`。如果范围不确定 → 保持 `draft`。
- 初始化 `status.json`：将 `templates/status-template.json` 逐字复制到 `.ai-delivery/requirements/<req-id>/status.json`，然后填充 `requirement_id`、子需求条目及其状态。不要凭记忆重新生成结构 — 保留所有 `_` 前缀元数据键和默认字段结构。
- 将依赖图记录在 `.ai-delivery/requirements/<req-id>/dependency-graph.json` 中。

**头脑风暴审计（在 `split_ready` 后运行）：**
使用 `superpowers:brainstorming` 在进入 UI 真值映射或 Spec Kit 前审计每个需求切片。提供：
- requirement-slice.md
- 依赖图
- 任何已知的 API 契约或约束

头脑风暴会话应：
- 识别拆分可能遗漏的歧义、缺口和边界情况
- 暴露冲突或隐含的假设
- 标记缺失的错误状态、空状态、加载状态和权限边界
- 产出具体的问题列表 — 如果有任何关键问题，相应设为 `blocked_missing_requirement` 或 `blocked_requirement_conflict`
- 如果没有关键问题，将发现记录到子需求的 `notes` 字段并继续

此检查点防止有问题的需求进入 Spec Kit，在那里修复成本会很高。

**跳过路径：** 当跳过拆分时，直接创建最小化的单子需求包：
```
.ai-delivery/requirements/<req-id>/
├── requirement.md
└── sub-requirements/<subreq-id>/
    ├── requirement-slice.md
    └── status.json
```

**暂停：** 在继续之前与用户确认拆分方案（或跳过决定）。

### 阶段 2：UI 真值映射

**何时运行：** 对于每个 `contains_page_states: true` 且有 Figma 设计源可用的子需求。

**准备输入：**
- 从 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/` 读取 `requirement-slice.md`。
- 收集 Figma 文件 key 和目标节点 ID。
- 设置输出目录为子需求目录。

**运行 `ui-truth-mapping`：**
向其提供需求切片和设计源。它产生 `ui-acceptance-contract.yaml` 和 `section-map.json`。

**完成后：**
- 验证 YAML 中所有屏幕状态都有源依据。
- 当所有屏幕状态都有源证据时设为 `acceptance_frozen`。
- 更新 `status.json`。

**如果没有 Figma 链接：** 跳过此阶段。非 UI 子需求直接进入 Spec Kit。无设计的 UI 子需求进入 `blocked_missing_design`。

### 阶段 3：Spec Kit 管道

**何时运行：** 对于每个处于 `acceptance_frozen`（UI）或 `split_ready`（非 UI）的子需求。

**准备输入：**
- 收集：`ui-acceptance-contract.yaml`（UI 切片）、`requirement-slice.md`、`section-map.json`。
- 如果存在 API 文档，直接传入 — 无需中间映射。

**头脑风暴设计（在 Spec Kit 前运行）：**
使用 `superpowers:brainstorming` 设计方案方法。提供：
- requirement-slice.md
- `ui-acceptance-contract.yaml`（如有 UI）
- API 文档（如有）

头脑风暴会话应产出：
- 架构决策（组件树、数据流、状态管理）
- 路由/导航设计（如多屏幕）
- 组件分解策略
- 数据模型草图（实体、关系、加载策略）
- 错误/空/加载状态处理方案
- 关键技术决策与权衡

头脑风暴输出成为 `speckit-specify` 构建之上的设计基础 — 它提供"为什么"和"怎么做"，使 Spec Kit 能够产出精确、有据可依的规范骨架。将头脑风暴摘要存储在子需求的 `notes` 字段中以备追溯。

如果头脑风暴发现与 YAML 契约或需求存在设计级冲突，设为 `blocked_spec_mismatch` 并暂停。

**运行 Spec Kit 管道：**
1. 将头脑风暴输出 + 输入产物提供给 `speckit-specify` → 生成 `spec.md`。验证 spec 覆盖了 YAML 契约中的所有屏幕状态。
2. 将 `spec.md` + 输入产物提供给 `speckit-plan` → 生成 `plan.md`。验证计划遵守交付切片顺序。
3. 将 `plan.md` + 输入产物提供给 `speckit-tasks` → 生成 `tasks.md`。验证任务粒度合适、按依赖排序且文件级范围。

**每个 Spec Kit 步骤之后：**
- `spec.md` 生成 → 对照 YAML 契约屏幕状态审计 → 设为 `spec_ready`。
- `plan.md` 生成 → 对照交付切片顺序审计 → 设为 `plan_ready`。
- `tasks.md` 生成 → 审计任务粒度和依赖顺序 → 设为 `tasks_ready`。

**暂停：** 在 `tasks_ready` 之后，开始实现前与用户确认。

### 阶段 4：实现

**何时运行：** 对于每个处于 `tasks_ready` 的子需求。

**切片执行顺序：** 由 `section-map.json` 决定。先执行 `shared-shell` 单元，然后是 `page` 单元，最后是 `modal` 单元（各自在其触发页之后）。单元仅在所有结构化依赖都 `merged` 时才开始。

**使用 Superpowers 开发套件实现每个切片：**

1. **创建工作树** — `superpowers:using-git-worktrees`：为切片创建隔离的工作树（或验证已有的）。每个切片一个工作树确保与其他进行中的工作干净隔离。

2. **规划子代理派发** — `superpowers:dispatching-parallel-agents`：分析切片任务，识别哪些可以并行运行。仅当至少两个任务独立且依赖已满足时才派发。主会话拥有依赖分析和派发决策权。

3. **使用子代理执行** — `superpowers:subagent-driven-development`：每个并行任务在各自的子代理中运行。每个子代理内部通过 `superpowers:test-driven-development` 遵循 TDD（写失败测试 → 实现 → 验证）。最多同时两个活跃子代理。子代理绝不推进门禁、决定阻塞或合并更改。

4. **代码评审** — `superpowers:requesting-code-review`：评审子代理产生的所有更改。首次失败进入自动修复循环（带评审反馈返回子代理）后再升级给用户。评审检查：契约合规、测试覆盖、边界情况、回归。

5. **视觉验收**（仅 UI 切片）— 将实现截图与 YAML 契约的屏幕状态并排比较。首次失败进入自动修复循环。仅当截图匹配时才设为 `visual_acceptance_passed`。

6. **验证** — `superpowers:verification-before-completion`：最终集成检查 — 所有测试通过、无回归、契约保真度确认、合并就绪验证。

7. **完成分支** — `superpowers:finishing-a-development-branch`：清理、最终 diff 审查、准备合并。将工作树分支变基到开发分支（无合并提交）。

实现开始时设为 `in_dev`。
截图匹配 YAML 后设为 `visual_acceptance_passed`（仅 UI 切片；非 UI 跳过）。
变基后设为 `merged`。

**子代理规则（仅实现阶段 — 绝不用于门禁决策）：**
- 仅当当前切片内存在至少两个独立可运行任务时才使用子代理。
- 每个任务的依赖必须在派发前满足。
- 最多同时两个活跃子代理。
- 主会话拥有：依赖分析、工作树排序、阻塞分类、合并就绪判断。

### 阶段 5：完成

所有切片 `merged` → 需求完成。更新需求级状态。无需结束仪式。

## 阻塞项目录

当任何阶段发生阻塞时，记录最精确匹配的阻塞项，移至下一个可运行的子需求，仅当所有子需求都被阻塞时才暂停整个需求。

### 需求拆分阻塞项

| 阻塞项 | 触发条件 |
|---|---|
| `blocked_missing_requirement` | 源中缺少关键业务事实 |
| `blocked_requirement_conflict` | 两个已批准的来源互相矛盾 |
| `blocked_dependency` | 上游子需求尚未就绪 |

### UI 真值映射阻塞项

| 阻塞项 | 触发条件 |
|---|---|
| `blocked_missing_design` | 设计证据中缺少所需视觉载体 |
| `blocked_requirement_figma_conflict` | 需求与视觉真值不可调和地矛盾 |
| `blocked_figma_conflict` | 不同提供方的设计证据互相矛盾 |
| `blocked_missing_state_code` | 最终屏幕状态缺少结构化框架证据 |
| `blocked_missing_visual_truth` | 缺少默认状态、行组合、父外壳或关键资源 |
| `blocked_verification_failure` | 可执行节点无法从证据中验证 |

### Spec Kit 与实现阻塞项

| 阻塞项 | 触发条件 |
|---|---|
| `blocked_spec_mismatch` | 官方 spec 输出与治理真值冲突 |
| `blocked_dependency_slice` | 上游切片尚未合并 |
| `blocked_merge_conflict` | 变基/集成失败 |
| `blocked_verification_failure` | 测试、评审或视觉验收在自动修复后仍失败 |

### 阻塞恢复

当进入阻塞时，更新 `status.json` 中对应子需求的条目：
```json
{ "status": "blocked_missing_design", "detail": "Figma 文件缺少确认弹窗帧", "blocked_from_status": "acceptance_frozen", "blocker_scope": "slice_local", "resume_target_status": "acceptance_frozen", "notes": null }
```

当用户解决阻塞后，从 `resume_target_status` 恢复。

**最精确阻塞规则：** 始终选择最具体的阻塞项。优先 `blocked_missing_state_code` 而非 `blocked_missing_design`。优先 `blocked_requirement_figma_conflict` 而非 `blocked_missing_visual_truth`。绝不要将切片级阻塞升级为需求级，除非所有切片的所有可运行队列项都被阻塞。

## 暂停点

仅有两个明确的暂停：
1. **拆分决策后** — 与用户确认拆分方案（或跳过）
2. **tasks_ready 后** — 开始实现前确认

所有其他转换均为自动进行。

## API 策略

API 文档作为参考材料直接传递给实现。没有单独的 API 契约映射阶段。API 缺口记录为 `integration_deferred` — 它们不阻塞 UI 映射或页面状态实现。仅当缺少 API 真值导致无法识别视觉载体本身时才阻塞。

## 非 UI 子需求

非 UI 子需求（`contains_infra_only: true` 或 `contains_page_states: false`）：
- 跳过 UI 真值映射（无 `acceptance_frozen` 门禁）。
- 直接从 `split_ready` 进入 Spec Kit 管道。
- 跳过视觉验收门禁 — 代码评审和验证后直接合并。
