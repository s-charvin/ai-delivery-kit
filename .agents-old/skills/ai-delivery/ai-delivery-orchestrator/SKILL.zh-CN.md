---
name: ai-delivery-orchestrator
description: 当需求需要通过合约门控的 ai-delivery 工作流推进时使用，包含一个需求级别的 todo.md、轻量 Spec Kit 桥梁产物以及受管控的检查点处理。
---

# AI Delivery Orchestrator (AI 交付编排器)

## 概述

使用此技能通过合约门控工作流进行编排，包含一个需求级别的 `todo.md`，并将 `.ai-delivery` 作为唯一的真实数据源。

这是仓库完成初始化后处理需求工作的默认入口。在正常路径中，它应决定是继续现有需求还是创建新需求，暂停等待人工确认，然后才分派受管控的链条。

在 `requirement-breakdown` 之后，默认姿态是 `UI优先，集成靠后`（UI-first, integration-later）：一旦可运行的可信设计证据可用，优先走视觉/设计轨道，让 API/集成轨道并行运行或稍后到达，并使用后期 API 真实数据来触发受管控的 `downstream_revalidation`，而不是过早地暂停整个需求。

此技能是现有工作流技能的受管控封装。它端到端地协调当前链条：

- `requirement-breakdown`
- `api-contract-mapping`
- `ui-requirement-mapping`
- `ui-acceptance-contract`
- `ui-interaction-design`
- `prepare-speckit-context`
- 官方 `speckit-specify`
- 官方 `speckit-plan`
- 官方 `speckit-tasks`
- 本地 Spec Kit 审核/绑定
- `using-git-worktrees`
- `test-driven-development`
- `requesting-code-review`
- `verification-before-completion`

Spec Kit 桥梁模型为：

`.ai-delivery` 事实 -> `spec-kit-input.md` -> 官方 `speckit-*` -> `spec-kit-binding.json` -> `.ai-delivery` 状态和 `traceability.json`

受管控的可观测性模型为：

`traceability.json.source_index` -> 对账/下一安全操作检查 -> 智能体会话日志 -> 审查/视觉/测试证据 -> 运行时 `slice-closures.json`

官方 `speckit-specify`、`speckit-plan` 和 `speckit-tasks` 应保持上游风格的指令。此技能承载仓库特定的规则，而不是修补那些官方技能本体。

当可用时，使用 `ai-delivery-admin-support` 在有意义的阶段转换期间进行受管控的管理支持日志记录。

所需的本地参考：

- [需求路由规则](references/requirement-routing-rules.md)
- [对账规则](references/reconcile-rules.md)
- [阶段映射](references/stage-mapping.md)
- [Spec Kit 桥梁](references/spec-kit-bridge.md)
- [Spec Kit 绑定](references/spec-kit-binding.md)
- [Spec Kit 绑定检查清单](references/spec-kit-bind-checklist.md)
- [子智能体预算策略](references/subagent-budget-policy.md)
- [暂停与重试策略](references/pause-and-retry-policy.md)

## 硬边界

- 不得将工作流真实数据移出 `.ai-delivery`。
- 不得生成独立的 `todo.json`。
- 不得要求用户在正常路径中手动选择第一个底层工作流技能。
- 不得让包含 UI 的子需求在 `acceptance_frozen` 之前进入 `speckit-*`。
- 不得让包含 UI 的子需求在 `slices_ready` 之前声称规划就绪。
- 不得让包含 UI 的切片在 `visual_acceptance_passed` 之前声称合并完成。
- 不得在仍有安全可运行队列项存在时，将仅 API 或仅切片本地的阻塞器升级为需求级别 `CP-002`。
- 不得让一个被阻塞的队列项吞掉后面仍然可安全运行的队列项。
- 不得将检查点变成第二个真实数据存储。
- 不得让子智能体推进门控、决定阻塞器或合并更改。
- 不得在第二阶段开发之外为当前活动的 `SR-*` 使用子智能体。
- 不得让委托工作逃离当前 `SR-*` 边界，或递归到 `SR-*` 以下的更深层子需求层级。
- 当依赖审查后剩余不到两个独立可运行的实现任务时，不得分派子智能体。
- 实现期间不得应用一个大型多文件补丁；应一次修补一个文件，并在文件之间重新检查上下文。
- 不得使用合并提交来重新整合委托的工作树分支；应依次将其变基回当前开发分支，使历史记录保持线性。
- 在受管控的管理支持界面可用时，不得跳过源索引、智能体会话或切片关闭记录。
- 不得为了重申仓库本地合约而分叉官方 `speckit-specify`、`speckit-plan` 或 `speckit-tasks`。
- 不得将 `spec-kit-input.md` 或 `spec-kit-binding.json` 视为新的真实数据存储；它们仅是衍生的桥梁产物。

## 核心模型

三层模型：

- `.ai-delivery/*`：事实层
- `todo.md`：执行面板
- `ai-delivery-orchestrator`：决策层

`todo.md` 是一个执行面板，而非第二个真实数据存储。它记录队列项、守卫、重试、检查点和恢复上下文，但每个完成决定必须由 `.ai-delivery` 中的受管控产物来证明。

`traceability.json.source_index` 是需求、Figma、API、Spec Kit、PR、CI、视觉、部署和监控引用的规范源索引。运行时 `agent-sessions.json` 记录谁在何处执行了工作。运行时 `slice-closures.json` 记录合并后的切片摘要、测试、审查、视觉验收、部署证据、已接受的风险和后续跟进。

桥梁产物如 `spec-kit-input.md` 和 `spec-kit-binding.json` 位于 `.ai-delivery` 下，作为可丢弃的衍生旁路文件。如果它们与受管控的源合约产生偏差，应从 `.ai-delivery` 重新生成，而不是为了补偿而编辑官方的 Spec Kit 输出。

## 可运行队列与阻塞器范围

在对账和队列决策期间，显式使用以下术语：

- `runnable queue item`（可运行队列项）
  - 任何在当前受管控的真实数据下仍然可以安全前进，而无需捏造缺失事实的项。
  - 常见示例：Tempad 或 Figma 证据采集、`ui-requirement-mapping`、页面外壳实现、本地状态或事件骨架、导航流程、仓库或适配器接缝、模拟连线、只读展示路径，或其他安全的部分前端工作。
- `slice-local blocker`（切片本地阻塞器）
  - 仅阻止一个切片、一个阶段或一个能力面的阻塞器。
  - 默认不得阻止不相关的切片或阶段。
- `action-level integration blocker`（操作级别集成阻塞器）
  - 阻止一个操作的真正 API 连线或最终语义关闭的阻塞器。
  - 它不会阻止视觉映射、外壳工作、本地状态工作、导航骨架、非危险用户路径或其他安全的局部开发活动，除非这些活动确实依赖于缺失的 API 真实数据。
- `requirement-global blocker`（需求全局阻塞器）
  - 仅在当前所有可推导的队列项都不可运行时，才允许搁置整个需求的阻塞器。
  - 只要还有一个安全的可运行项存在，阻塞器就还不是需求全局的。

默认编排策略是`优先继续最安全的可运行工作`，而非`遇到第一个阻塞器就暂停`。

## 运行时模式

- `bootstrap`（引导）
- `resume`（恢复）
- `confirm-to-dev`（确认进入开发）
- `blocker-recovery`（阻塞器恢复）
- `completed`（已完成）

## 运行时模式解析

在每次对账后解析活动模式。按此顺序联合使用 `.ai-delivery` 和 `todo.md`：

1. `completed`
   - `delivery-slices/index.json` 中命名的所有可执行切片均已 `merged`。
   - `todo.md` 保留为执行面板归档，不应分派新工作。
2. `bootstrap`
   - `todo.md` 缺失，或需求包仍不完整，无法安全推导队列。
   - 从顶层需求文档开始，从第一个受管控阶段构建队列。
3. `confirm-to-dev`
   - `todo.md` 存在，`current_checkpoint` 为 `CP-001`，所有可执行切片均已达到 `tasks_ready`，且用户意图明确表示"继续进入开发"。
   - 切换到第二阶段执行，而不是重新运行开发前规划。
4. `blocker-recovery`
   - `todo.md` 存在，`current_checkpoint` 为 `CP-002`，且用户已提供缺失的决策或外部阻塞器已被清除。
   - 再次对账，仅当守卫现在可满足时才清除阻塞器记录，然后从被阻塞的步骤恢复。
5. `resume`
   - `todo.md` 存在，没有检查点主动阻止运行，且对账后至少还有一个队列项未解决或可运行。
   - 被阻塞的项可能保留在队列中，而后面独立的工作继续进行。
   - 对账后，从最安全的可运行未解决队列项继续。

`current_phase` 和 `current_checkpoint` 是执行面板提示，它们本身不是真实数据。如果它们与 `.ai-delivery` 不一致，信任 `.ai-delivery` 并在对账期间重写 `todo.md` 头部。

## 用户入口映射

将常见的用户意图映射到运行时模式，而不是要求用户命名下一个技能。

当用户带来新材料时，首先决定是继续现有需求还是创建新需求。使用需求路由规则作为该建议的最低证据阈值。

1. 检查现有的 `.ai-delivery/requirements/*` 包、`todo.md`、`status.json` 和 `traceability.json`。
2. 仅产生一个建议：
   - `continue req-xxx`（继续 req-xxx）
   - 或 `create req-yyy`（创建 req-yyy）
3. 在采取任一路径之前暂停等待人工确认。
4. 如果用户覆盖了建议，遵循人工决策并继续受管控的工作流。
5. 仅当其前置条件已满足时，将直接的低级技能调用视为异常路径。

路由决策确认后，将用户意图映射到运行时模式：

- "给你需求文档、swagger、Figma 已开，开始跑"
  - 当没有有效的 `todo.md` 时进入 `bootstrap`，否则对账并使用 `resume` 继续。
- "继续这个 requirement 的编排"
  - 先对账，然后使用 `resume`，除非有活动的检查点。
- "tasks_ready 了，继续开发"
  - 先对账，要求 `current_checkpoint=CP-001` 且所有可执行切片处于 `tasks_ready`，然后进入 `confirm-to-dev`。
- "这个 blocker 我处理好了，继续跑"
  - 先对账，要求 `current_checkpoint=CP-002`，如果阻塞器可以安全清除，则进入 `blocker-recovery`。

当底层技能的前置条件已满足时，直接使用它们仍然是支持的，但这是用于恢复或专家使用的异常路径，而非新需求的正常入口。

## 对账规则

1. 在信任 `todo.md` 之前，重新读取 `.ai-delivery` 状态和可追溯性产物。
2. 对照受管控的产物重新检查每个待办守卫。
3. 在选择检查点之前，将每个阻塞器分类为`切片本地`、`操作级别集成阻塞器`或`需求全局阻塞器`。
4. 重新检查阻塞器实际阻止了什么：视觉真实数据、验收冻结、交互合约、完整集成或最终交付声明。
5. 如果守卫已满足，标记队列项完成，无需重新运行该阶段。
6. 如果输出存在但守卫未满足，则重新运行该阶段或打开范围最小的阻塞器。将被阻塞的项保留在队列中，继续处理不依赖它的后续可运行项。

## 阶段映射

- 需求：`requirement-breakdown`
- 视觉/设计轨道：`ui-requirement-mapping`
- API/集成轨道：`api-contract-mapping`
- UI 冻结：`ui-acceptance-contract`
- 交互与切片合成：`ui-interaction-design`
- Spec Kit 桥梁：`prepare-speckit-context`
- 官方 Spec Kit：`speckit-specify`、`speckit-plan`、`speckit-tasks`
- Spec Kit 绑定：在每个官方 Spec Kit 步骤后进行本地审核/绑定
- 开发：`using-git-worktrees`、`test-driven-development`、实现、`requesting-code-review`、视觉验收、`verification-before-completion`

## 检查点

- `CP-001 tasks_ready_user_confirmation`（任务就绪待用户确认）
- `CP-002 hard_blocker_pause`（硬阻塞器暂停）
  - 仅当当前需求没有安全的可运行队列项剩余时，才进入此检查点。
  - 如果其他 UI 真实数据采集、外壳工作、本地交互工作、验收准备工作或安全的局部开发项仍可继续，则一个或多个子需求上的 API 阻塞器本身不足以进入此检查点。

## 阶段输入与守卫

使用阶段映射和桥梁参考作为固定输入和完成守卫的辅助速查。当较旧的速查与本技能中的阻塞器范围和可运行队列规则冲突时，以本技能为准。最低要求的合约为：

- `requirement-breakdown`
  - 输入：顶层需求文档
  - 守卫：需求包已在 `.ai-delivery/requirements/<requirement-id>/` 下创建
- `api-contract-mapping`
  - 输入：`requirement-slice.md`、`traceability.json`、`status.json`、API 合约
  - 守卫：子需求达到 `api_mapped`、`missing_nonblocking`、`needs_revalidation`，或带有恢复说明的最窄显式阻塞状态
  - 规则：按`切片+阶段`判断阻塞器严重程度，而非整个需求；API 缺口主要阻止危险操作连线、不可逆行为确认、服务端驱动分支和最终交付声明
- `ui-requirement-mapping`
  - 输入：`requirement-slice.md`、Figma 设计源；存在 `api-contract-mapping.md` 时添加
  - 规则：如果目标是大型 `SECTION`，从 `get_structure` 开始；最终可执行状态仍需 `get_code`
  - 规则：当 API 状态为 `api_mapped`、`missing_nonblocking` 或 `needs_revalidation` 时允许进入；如果 API 为 `blocked_*` 但阻塞器仅与 API 相关且不妨碍视觉载体识别，则以 `visual-evidence-first` 模式继续
  - 守卫：子需求达到 `figma_mapped` 并附带受管控的就绪判定，即使后续验收或集成工作仍因 API 真实数据而延迟
- `ui-acceptance-contract`
  - 输入：`requirement-slice.md`、`figma-mapping.md`、最终状态 `get_code` 证据；仅当 API 真实数据改变了可执行屏幕状态合约时才添加 `api-contract-mapping.md`
  - 输出：`ui-acceptance-contract.yaml` 作为唯一的规范 UI 验收真实数据，根植于 `screen_states[*].component_tree`
  - 守卫：子需求达到 `acceptance_frozen`
- `ui-interaction-design`
  - 输入：`requirement-slice.md`、`figma-mapping.md`、`ui-acceptance-contract.yaml`；存在或操作语义已知时添加 `api-contract-mapping.md`
  - 输出：`interaction-design.md`、`delivery-slices/index.json`
  - 规则：允许外壳、导航、本地状态和安全的操作路径合成继续推进，同时将操作级别的 API 阻塞器明确记录为延迟连线或被阻塞的集成说明
  - 守卫：子需求达到 `slices_ready`
- `prepare-speckit-context`
  - 输入：`slice-contract.md`、`interaction-design.md`、`traceability.json`；对 UI 切片添加 `ui-acceptance-contract.yaml`，当 API 影响存在时添加 `api-contract-mapping.md`
  - 输出：`spec-kit-input.md`
  - 守卫：`spec-kit-input.md` 存在且与当前受管控的切片真实数据一致
- 官方 `speckit-specify`、`speckit-plan`、`speckit-tasks`
  - 主要输入：`spec-kit-input.md`
  - 额外输入：标准的 `.specify` 模板和上游 Spec Kit 运行时
  - 规则：官方技能指令保持上游，不得为了重述仓库本地合约而重写
  - 守卫：当前切片运行的官方 `spec.md`、`plan.md` 或 `tasks.md` 产物存在
- 本地 Spec Kit 绑定
  - 输入：`spec-kit-input.md`、生成的 `spec.md`、`plan.md` 或 `tasks.md`、`traceability.json`、`status.json`
  - 规则：在写入 `traceability.json.spec_kit_refs` 之前应用最小绑定检查清单
  - 输出：`spec-kit-binding.json`；更新 `traceability.json.spec_kit_refs`
  - 守卫：`spec_ready`、`plan_ready`、`tasks_ready`
- 开发执行
  - 输入：`slice-contract.md`、`tasks.md`、`spec-kit-binding.json`、可追溯性引用
  - 可选上下文：当宿主仓库已提供时，项目本地的 `.agents/AGENTS.md`
  - 范围：仅限当前活动的 `SR-*`；如果使用委托工作，则保持在第二阶段内针对该子需求，且不得创建更深的受管控子需求层级
  - 规则：使用文件范围的补丁编辑代码；不要发送一次性重写多个文件的补丁
  - 规则：仅当当前 `SR-*` 内至少有两个独立可运行的实现任务已满足其依赖关系时才使用子智能体；否则保持在主会话中
  - 规则：如果委托工作使用了工作树，先在这些工作树中完成编码，然后按依赖顺序逐个变基并重新整合回当前开发分支，使提交历史保持线性
  - 守卫：切片达到 `merged`；包含 UI 的切片必须在合并完成前达到 `visual_acceptance_passed`

## 队列压缩

`todo.md` 可以将一个官方 Spec Kit 步骤及其本地审核/绑定跟踪为一个执行面板操作，例如 `speckit-specify-bind`、`speckit-plan-bind` 或 `speckit-tasks-bind`。以这种方式压缩时，该操作仍受 `.ai-delivery` 守卫的约束，而非队列文本本身。

## 状态机

第一阶段是一个受管控的队列，而不是 API 优先的线性硬门控：

1. `requirement-breakdown`
2. 分解后进入两个轨道：
   - `视觉/设计轨道`
   - `API/集成轨道`
3. 一旦可运行的可信设计证据可用，对包含 UI 的子需求运行 `ui-requirement-mapping`。
4. 当面向客户端的 API 真实数据存在时运行 `api-contract-mapping`；当 API 真实数据到达较晚或发生重大变化时重新运行。
5. 对两个轨道进行对账；继续不依赖于被阻塞 API 语义的安全工作。
6. 仅当视觉真实数据完全有源可溯，且任何改变冻结屏幕状态合约的 API 真实数据已充分知晓时，才对包含 UI 的子需求运行 `ui-acceptance-contract`。
7. 仅当验收合约已冻结时，才对包含 UI 的子需求运行 `ui-interaction-design`；将未解决的危险操作语义明确保留为 `integration_deferred`、`action-blocked-not-visual-blocked` 或等效的受管控说明，而不是虚构关闭。
8. `prepare-speckit-context`
9. 官方 `speckit-specify`
10. 本地 spec 绑定
11. 官方 `speckit-plan`
12. 本地 plan 绑定
13. 官方 `speckit-tasks`
14. 本地 tasks 绑定
15. `tasks_ready_user_confirmation`

第二阶段：

1. `using-git-worktrees`
2. `test-driven-development`
3. 实现
4. `requesting-code-review`
5. 审查自动修复重试
6. 视觉验收
7. 视觉自动修复重试
8. `verification-before-completion`
9. 合并

## 开发门控

- 在 `tasks_ready_user_confirmation` 暂停，直到用户确认。
- 仅在硬阻塞器、不可恢复的门控失败或缺失人工决策时升级。
- 当较窄的阻塞器仍留下可运行的队列项时，优先继续最安全的可运行工作。
- 包含 UI 的子需求在 `acceptance_frozen` 之前不得进入 `speckit-*`。
- 包含 UI 的子需求在 `slices_ready` 之前不得声称切片执行就绪。
- 包含 UI 的切片在 `visual_acceptance_passed` 之前不得声称合并完成。
- 部分前端工作（如外壳、导航路径、本地状态、适配器接缝、模拟连线、表单验证或只读界面）可以在完整 API 关闭之前推进，前提是受管控的说明使剩余的集成工作明确。
- 不得将部分或集成延迟的工作呈现为完整实现完成、完整集成完成或合并就绪。

## 子智能体预算

- 默认使用主会话。
- 子智能体是仅限第二阶段开发的工具。不得在路由、对账、映射、验收冻结、交互设计、Spec Kit 生成或门控决策中使用。
- 委托范围一次限于一个活动的 `SR-*`。交付切片仍然是该 `SR-*` 内的实现单元，而非第二个受管控的子需求层级。
- 仅将子智能体用于独立、冻结、可审查的实现工作。
- 仅当依赖审查后当前活动的 `SR-*` 内至少有两个独立可运行的实现任务可以并行推进时，才使用子智能体。
- 如果少于两个独立可运行的实现任务存在，则保持在主会话中。
- 当达到阈值时，最多允许两个活动的子智能体。
- 主会话负责依赖分析、工作树排序、阻塞器分类和合并就绪判断。
- 绝不允许子智能体在同一 `SR-*` 下生成更深的子智能体。

## 开发排序规则

- 按照 `delivery-slices/index.json` 排序切片执行，而非根据临时提示顺序。
- 一个切片只有在每一个 `depends_on_slices` 条目均已 `merged` 后才能进入 `using-git-worktrees`。
- 仅当当前 `SR-*` 内至少有两个独立可运行的实现任务已满足其依赖关系时，才允许并行。
- 不要为依赖项仍未解决的未来切片预先创建工作树。
- 如果为委托开发使用了工作树，先完成编码工作，然后由主会话将每个已完成的工作树分支变基到当前开发分支，并按依赖顺序逐个重新整合。
- 保持生成的历史记录线性；不要为工作树重新整合使用合并提交。
- 工作树创建顺序、冲突处理和合并决策始终由主会话决定。

## 暂停与重试

- `review` 首次失败必须进入自动修复循环后才能升级。
- 视觉验收首次失败必须进入自动修复循环后才能升级。
- 仅在 `CP-001 tasks_ready_user_confirmation` 或 `CP-002 hard_blocker_pause` 处暂停。
- `CP-002 hard_blocker_pause` 仅在当前需求没有安全的可运行队列项剩余时才有效。

## ai-delivery-admin 策略

- 使用 `ai-delivery-admin-support` 作为受管控的日志记录界面，而非第二个事实存储。
- 在管理支持可用时，记录阶段开始、完成、失败、阻塞器和恢复转换。
- 对于 Spec Kit 桥梁，在下一个门控推进之前记录 `prepare-speckit-context`、官方 Spec Kit 分派、本地绑定完成以及任何绑定不匹配。
- 保持 `todo.md` 仅限于执行面板恢复上下文。
