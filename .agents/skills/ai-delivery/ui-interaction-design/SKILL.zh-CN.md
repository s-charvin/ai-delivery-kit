---
name: ui-interaction-design
description: 当子需求已具备已验证的需求和 Figma 映射工件，需要在实现或 Spec Kit 规划之前获得基于源的交互契约、微交互假设或缺失交互真相的升级时使用。
---

# UI 交互设计

项目本地工作流技能，用于将有治理的需求切片加上已验证的设计映射，转换为主仓库内可执行的交互契约。

## 概述

在 `ui-acceptance-contract` 之后使用此技能，此时子需求已具备需求真相、映射真相、验收冻结真相以及支持性的治理工件。如果 `api-contract-mapping.md` 已存在，则将其视为额外的接口契约上下文，并保留其可追溯性含义。此阶段编写 `interaction-design.md`，最终确定 `delivery-slices/index.json`，在需要假设或升级时更新 `decisions.md`，并保留上游映射和桥接契约，而非凭记忆重写。

此技能可以细化有边界的微交互细节，例如反馈模式、加载呈现、动效时序、焦点处理和可访问性默认值，但前提是这些细化不超出业务含义阈值，并保持明确标注。

当 API 真相在操作集成层部分缺失、延迟或受阻时，此阶段仍可推进，前提是已接受的屏幕契约稳定，且缺失的 API 真相被记录为延迟接线、操作级集成阻塞或下游重新验证，而非凭空编造。

这是一个内置交互设计指导的项目本地技能。不要因为缺少外部技能而停止，也不要假设用户已安装任何外部技能包。微交互、动效、加载、反馈、时序和可访问性所需的指导特意放在此仓库中。

## 硬边界

- 不要发明业务流程或页面结构。
- 不要添加新字段、步骤、对话框、权限或页面转场。
- 不要将假设标注为原始需求或 Figma 事实。
- 不要在此处修复视觉真相；如果 `ui-acceptance-contract.yaml` 不完整或受阻，将问题交回上游。
- 不要因为交互契约偏好不同的设计而覆盖 `figma-mapping.md` 或 `traceability.json`。
- 当后期阶段的桥接或 Spec Kit 引用已存在时，不要删除它们。
- 不要手动编辑受阻状态使其看起来已恢复。
- 不要等待请求或响应字段的最终确定性才完成交互设计。
- 当所需 API 语义仍未解决时，不要声称完整的集成真相或危险操作闭环。
- 如果无法从需求、`figma-mapping.md` 和可信的设计证据中解决交互真相而不改变业务含义，则停止并升级，而非凭直觉填补空白。

## 使用此技能的场景

- 将已验证的需求和 Figma 映射证据转化为可执行的交互契约
- 消费 `ui-acceptance-contract.yaml` 以冻结操作闭环以对抗不可变的屏幕契约
- 定义基于源的用户操作、反馈、状态和转场
- 生成"操作链矩阵"和"状态传播矩阵"
- 仅在允许的边界内记录有边界的 `assumed_micro_interaction`
- 在不扩展产品含义的前提下，改进加载、反馈、动效、时序、焦点和可访问性等微交互细节的质量
- 在实现或 Spec Kit 规划之前升级缺失的交互真相

## 不使用此技能的场景

- 需求拆分
- Figma 节点映射
- 产品重新设计
- 新的业务逻辑发明
- 实现代码或任务规划

## 必需参考

- [双重真相规则](references/dual-truth-rules.md)
- [阻塞目录](references/blocker-catalog.md)
- [日志检查清单](references/logging-checklist.md)
- [交互设计模板](templates/interaction-design-template.md)
- [允许的假设](references/allowed-assumptions.md)
- [交互质量指南](references/interaction-quality-guidelines.md)
- [状态检查清单](references/state-checklist.md)

同时阅读现有的 `traceability.json`，因为它是第一类有治理的工件，而非可丢弃的辅助上下文。

## 输入

### 必需输入

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`
- `ui-acceptance-contract.yaml`

### 预期的支持输入

- `traceability.json`
- `status.json`
- 现有的 `decisions.md`
- 当子需求正在修订而非首次合成时的 `delivery-slices/index.json`

### 可选输入

- `api-contract-mapping.md`
- Figma 评论
- 原型流程
- 现有交互约定
- 组件行为约束

### 缺失输入处理

如果源或工件缺失：

- 如果 `requirement-slice.md` 缺失或仍然过于模糊，则停止并将工作交回 `requirement-breakdown`。
- 优先从 `acceptance_frozen` 开始；如果子需求仍未映射、未冻结或受阻，且用户未要求修复工作，则停止而非假装交互设计正常进行。
- 如果 `figma-mapping.md` 缺失或没有可信的结构化设计证据支持，则停止并将工作交回 `ui-requirement-mapping`。
- 如果 `ui-acceptance-contract.yaml` 缺失、不完整或受阻，则停止并将工作交回验收冻结阶段。
- 如果 `traceability.json` 缺失或与可见的映射真相不一致，则在声称 `interaction_ready` 之前修复或升级该有治理的契约。
- 如果 `api-contract-mapping.md` 缺失、部分或过时，则在相关行为有源支持的情况下，继续处理框架、导航、本地状态、加载、反馈和安全路径的交互契约；将未解决的操作语义明确记录为延迟集成说明，而非编造它们。
- 如果仅缺失微交互细节，则继续处理并记录 `assumed_micro_interaction`。
- 如果缺失的细节会改变业务含义，则停止并阻塞，而非假设。

## 输出目标

生成开发者可直接消费的交互契约，同时保留上游映射真相。输出必须保留：

- 基于源的 `interaction-design.md`
- 基于源的"操作链矩阵"
- 基于源的"状态传播矩阵"
- 当前子需求的最终 `delivery-slices/index.json`
- 当出现假设、阻塞或重新验证说明时对 `decisions.md` 的更新
- 明确标注 `Source: Requirement`、`Source: Figma`、`Source: Existing Pattern` 和 `Assumption: Micro Interaction`
- 现有的 `traceability.json` 桥接上下文，包括存在的 `api_contract_mapping` 和 `spec_kit_refs`

## 默认输出路径

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── interaction-design.md
├── delivery-slices/index.json
├── decisions.md
├── status.json
└── traceability.json
```

## 工作流

### 1. 确认上游契约栈

- 在起草任何交互契约之前，阅读 `requirement-slice.md`、`api-contract-mapping.md`（如果存在）、`figma-mapping.md`、`ui-acceptance-contract.yaml`、`traceability.json`、`status.json` 和 `decisions.md`。
- 将 `ui-acceptance-contract.yaml` 视为规范的 UI 验收真相。直接使用 `screen_states[*].component_tree` 获取层级、组件类型、布局、盒模型、排版、图标/图片/状态规则和实现映射；不要凭记忆或从单独的 Markdown 笔记中重建这些细节。
- 确认交互工作仍与当前子需求范围和已验证的映射输出一致。
- 优先从 `acceptance_frozen` 开始；如果映射或验收冻结已过时、受阻或未验证，则停止并将工作交回上游。

### 2. 提取基于源的交互事实

- 从需求真相、API 契约真相、Figma 映射真相、UI 验收真相、评论、原型流程和已批准的模式中推导交互事实。
- 将每个事实标注为 `Source: Requirement`、`Source: Figma`、`Source: Existing Pattern` 或 `Assumption: Micro Interaction`。
- 保持基于源的行为和有边界假设之间的明确分离。
- 使用 `references/interaction-quality-guidelines.md` 在源真相为有限细化留有余地时，选择最轻量的安全反馈、加载、动效、时序和可访问性默认值。
- 如果 API 真相不完整，则保持操作语义开放和明确；不要将缺失的请求、响应、副作用或错误真相转化为编造的交互分支。

### 2a. 有边界的交互质量原则

使用这些原则在不越界至重新设计的前提下改进交互质量。

### 1. 反馈优先

- 优先选择能清晰、即时确认用户意图的交互反馈。
- 区分内联验证、字段级错误、页面级错误、提示消息和进度反馈，而非将所有内容归结为一种通用消息表面。
- 除非源材料明确要求中断，否则优先选择保留用户上下文的反馈而非中断流程的反馈。
- 选择能保持清晰度的最轻量反馈表面。在业务含义不变的前提下，优先选择内联或局部反馈，而非全局或阻塞性中断。

### 2. 加载应保持方向感

- 优先选择能保留布局和用户方向感的加载状态。
- 当源真相未指定精确呈现方式时，优先选择有边界的默认值，例如按钮级加载、内联进度或与现有表面匹配的骨架占位符，而非全屏阻塞状态。
- 加载行为应说明用户是否可继续编辑、原地等待或重试。
- 加载范围应与操作范围匹配。在页面级或应用级阻塞状态之前，优先选择控件、区块或容器级加载。

### 3. 动效应是功能性的

- 动效应传达反馈、焦点、连续性或状态变化；默认不应是装饰性的。
- 如果动效细节缺失，优先选择细微、简短且可中断的转场，而非大型编排动画。
- 使用动效说明描述目的，而非实现库的选择。
- 优先选择平台中立的描述，例如"保持状态间的连续性"或"强调验证错误"，而非特定于 Web 的动画技术。

### 4. 时序应一致且保守

- 微反馈应感觉即时。
- 小组件转场应保持简短且不引人注目。
- 较长的动效仅应在解释有意义的连续性时出现。
- 如果精确时序不是基于源的，则将时序指导记录为有边界的微交互假设，而非 Figma 真相。

### 5. 可访问性是契约的一部分

- 将键盘可达性、可见焦点、状态清晰度和减少动效行为作为第一类交互关注点保留。
- 将可访问性视为交互真相的一部分，而非实现后的可选润色。
- 如果源未指定动画可访问性行为，则默认尊重减少动效偏好。
- 不要让动效或加载行为向辅助技术或键盘用户隐藏重要的状态变化。
- 如果悬停具有意义，则需在契约中要求焦点或触摸等效行为。

### 5a. 本地交互质量契约

- 直接使用此仓库中的本地指导，而非依赖外部技能安装。
- 当源为安全细化留有余地时，为反馈、加载、时序和可访问性选择最轻量且有用的选择。
- 如果更强的模式会改变产品含义，不要从直觉或外部技能借用；将其升级回需求或 Figma 真相。

### 6. 可中断性优于锁定

- 优先选择允许用户恢复、重试或保持方向感的交互。
- 除非源真相要求，否则不要假设长时间运行的转场、阻塞覆盖层或锁定状态。
- 如果加载或反馈模式会暂时阻塞用户操作，说明该阻塞的合理性。

### 7. 跨平台中立性

- 编写交互指导时，应让 Web、iOS 和 Android 团队都能应用，而无需从一个平台的实现行话进行翻译。
- 优先选择行为语言，例如焦点保持、状态强调、本地进度或手势回退，而非特定于框架的 API 或代码片段。
- 如果某个平台特定的行为很重要，说明面向用户的结果，而非规定单一的实现技术栈。

### 3. 编写 `interaction-design.md`

- 使用 `templates/interaction-design-template.md`。
- 涵盖交互目标、进入条件、用户操作、反馈与响应模型、成功、空、加载、错误和禁用状态、权限或可见性影响、导航或本地状态变化、操作链矩阵、状态传播矩阵、动效和转场说明、可访问性和输入模态说明，以及未解决的升级事项。
- 保持文档可供下游实现直接使用，无需重新设计产品。

### 3a. 冻结操作闭环和传播

- 每个有意义的 CTA 或手势必须出现在操作链矩阵中，包含 `entry_state`、`user_action`、`hit_target_owner`、`callback_owner`、`repo_or_api`、`success_state_change`、`failure_feedback`、`upstream_downstream_refresh_targets` 和 `navigation_conflict_boundary`。
- 每个跨所有者或跨表面的后果必须出现在状态传播矩阵中，包含 `source_action`、`source_state_owner`、`target_page_or_component`、`target_state_field`、`update_mode` 和 `consistency_risk`。
- 将导航冲突、命中目标重叠、空回调风险和"关闭页面而不执行业务操作"风险视为契约级关注点，而非仅审查时的意外。

### 3b. 最终确定切片合成

- 矩阵冻结后，合成或更新 `delivery-slices/index.json`。
- 为每个冻结的屏幕状态最终确定一个 `page-state` 切片，加上用于传播和跨路由所有权的 `shared-state` 或 `integration` 切片。
- 可以接受页面状态或共享状态切片已就绪，而某些危险操作或服务器驱动集成切片仍明确延迟或阻塞，前提是有治理的工件使该分离可见。
- 在操作和传播契约明确之前，不要最终确定切片所有权。

### 3.1 仔细改进微交互细节

- 当源真相未说明时，使用允许的边界来细化按钮加载、内联验证时序、悬停或活动状态、焦点可见性、减少动效处理、提示消息与内联错误优先级以及其他不改变业务含义的有边界可访问性细节。
- 优先选择明确的说明，例如"加载保持布局"、"焦点在验证失败后保持可见"或"动效仅传达状态变化"，而非模糊的陈述如"使其更流畅"。
- 在决定安全的默认值时，使用 `references/interaction-quality-guidelines.md` 中的反馈表面阶梯、加载模式阶梯、时序指导和常见故障模式。
- 如果更强的交互模式会引入新的分支、模态框、页面转场或业务规则，则不要在此处添加。

### 4. 积极限制假设

- 仅在 `references/allowed-assumptions.md` 中允许的边界内记录 `assumed_micro_interaction`。
- 如果假设会改变业务含义、添加新分支、添加新屏幕步骤或重新定义权限，则停止并升级，而非将其作为交互真相编写。
- 清晰区分缺失的交互细节和缺失的产品需求真相。
- 对于动效、时序和反馈假设，同时记录原因和约束；说明假设为何在不改变功能含义的前提下提高清晰度。

### 5. 保留相邻工件

- 不要凭记忆重写 `figma-mapping.md`。
- 不要清除或替换 `traceability.json`，包括现有的桥接字段如 `api_contract_mapping` 和 `spec_kit_refs`。
- 如果交互分析揭示出映射或视觉真相的差距，将其记录在 `decisions.md` 中，并将问题交回 `ui-requirement-mapping` 或阻塞它，而非在散文中默默修复映射。
- 如果交互分析揭示出验收冻结的差距，将其记录在 `decisions.md` 中，并将问题交回 `ui-acceptance-contract`，而非在此处修复视觉真相。

### 6. 保守处理状态和阻塞

- 仅在关键交互状态已定义、操作闭环有矩阵支持、传播有矩阵支持、`delivery-slices/index.json` 已最终确定且剩余假设保持在允许的微交互边界内时，才将子需求推进至 `interaction_ready`。
- 如果需求需要某个操作但设计无法承载，则阻塞在 `blocked_missing_design`。
- 如果 Figma 交互证据与需求真相冲突，则阻塞在 `blocked_requirement_figma_conflict`。
- 如果关键业务交互无法从当前材料中解决，则阻塞在 `blocked_missing_requirement`。
- 如果仅 API 差距阻塞了一个操作的实际接线或危险操作语义，但不阻塞框架、导航、本地状态或非危险路径，则将其记录为 `integration_deferred`、`action-blocked-not-visual-blocked` 或等效的有治理说明，而非阻止整个交互阶段。
- 当输入阻塞时，在 `status.json` 中保留恢复意图，包含 `blocked_from_status` 和 `resume_target_status`；不要通过手动编辑绕过恢复。
- 仅在可用时，将单独的管理支持界面用于有治理的日志记录、阻塞处理、状态转换和工件更新。

### 7. 交接前重新审计

- 重新打开 `requirement-slice.md`、`figma-mapping.md`、`interaction-design.md` 和 `traceability.json`。
- 验证每个重要的交互行为都有源支持或明确标注为 `Assumption: Micro Interaction`。
- 验证没有假设改变业务含义，也没有覆盖上游映射真相。
- 如果 `traceability.json` 中已存在后期桥接上下文，包括 `api_contract_mapping`，确认其已被保留。

## 状态和阻塞规则

- 如果需求需要某个操作但设计无法承载，则阻塞在 `blocked_missing_design`。
- 如果 Figma 交互证据与需求真相冲突，则阻塞在 `blocked_requirement_figma_conflict`。
- 如果关键业务交互无法从当前材料中解决，则阻塞在 `blocked_missing_requirement`。
- 不要仅因为 API 操作语义不完整就阻止整个交互阶段，当剩余工作明确是框架级、本地状态、导航或其他安全的部分交互工作时。
- 当这些阻塞仍处于开放状态时，不要将子需求作为交互完成推进。
- 仅当契约有源支持、有验收支持、具备传播意识且受假设限制时，才将子需求推进至 `interaction_ready`。

## 硬约束

- 不要发明业务流程或页面结构。
- 不要添加新字段、步骤、对话框、权限或页面转场。
- 不要将交互真相移入 `ai-delivery-admin`。
- 不要将假设标注为原始的 Figma 或需求事实。
- 仅在批准的边界内保持 `assumed_micro_interaction`。
- 不要覆盖 `figma-mapping.md` 或 `traceability.json`。

## 输出标准

每个交互契约应定义：

- 基于源的交互事实
- 用户操作
- 操作链矩阵
- 状态传播矩阵
- 系统反馈
- 成功、空、加载、错误和禁用状态
- 源真相中已存在的权限或可见性影响
- 导航或本地状态变化
- 动效和转场说明
- 可访问性和输入模态说明
- 对可用性重要的反馈优先级和加载呈现
- 明确的假设和升级事项

如果无治理的管理支持不可用，则将工件真相保留在 `.ai-delivery/` 中，并在本地记录缺失的治理依赖项，而不发明另一个状态或日志存储。

## 自检清单

在报告完成之前，确认以下所有项：

- [ ] 在起草前已阅读 `requirement-slice.md`、`figma-mapping.md` 和 `traceability.json`
- [ ] 子需求可以安全地从 `acceptance_frozen` 推进至 `interaction_ready`
- [ ] 每个关键交互事实都按源或按 `Assumption: Micro Interaction` 标注
- [ ] 每个有意义的操作都出现在"操作链矩阵"中
- [ ] 每个跨表面后果都出现在"状态传播矩阵"中
- [ ] 所有关键状态已定义：成功、空、加载、错误和禁用
- [ ] 当反馈表面和加载呈现对用户流程重要时，它们已明确说明
- [ ] 动效和时序说明有目的性、保守，且不暗示装饰性重新设计
- [ ] 可访问性和辅助功能期望（如焦点可见性、键盘可达性和减少动效处理）在相关时已涵盖
- [ ] 当交互依赖多于一种输入模态时，悬停、触摸、键盘或手势期望已对齐
- [ ] 没有发明新的业务分支、字段、步骤、对话框、权限规则或页面转场
- [ ] `assumed_micro_interaction` 保持在允许的边界内
- [ ] `figma-mapping.md` 和 `traceability.json` 被保留而非覆盖
- [ ] `delivery-slices/index.json` 在矩阵冻结后已最终确定
- [ ] 现有的桥接字段如 `spec_kit_refs` 在已存在的情况下保持完整
- [ ] 任何未解决的仅 API 操作差距作为延迟集成或阻塞的操作接线明确说明，而非隐藏在交互契约内
- [ ] 阻塞项保留了 `blocked_from_status` 和 `resume_target_status`

## 压力场景

在编写或更新交互契约时，将这些作为心理回归测试使用。

### 场景 1：仅缺失加载或焦点行为

预期行为：

- 继续契约
- 记录 `Assumption: Micro Interaction`
- 如果业务含义不变，则不阻塞

### 场景 1b：源显示了一个操作，但未指定进度或完成反馈的呈现方式

预期行为：

- 选择保持方向感的最轻量反馈模式
- 当源真相允许时，优先选择内联或局部反馈而非较重的中断
- 将选择记录为 `Assumption: Micro Interaction` 或 `Source: Existing Pattern`

### 场景 1c：某个流程似乎需要加载，但源未指定加载范围

预期行为：

- 选择与操作范围匹配的最窄加载范围
- 尽可能保留布局和上下文
- 记录用户是否可以继续编辑、必须等待还是可以原地重试

### 场景 2：Figma 暗示了一个确认对话框，但需求未提及

预期行为：

- 不要将对话框编造为真相
- 如果冲突真实存在，则阻塞在 `blocked_requirement_figma_conflict`
- 或明确升级此不匹配

### 场景 3：交互需要一个新的业务决策才能推进

预期行为：

- 阻塞在 `blocked_missing_requirement`
- 记录确切未解决的业务含义
- 不要用友好的默认值修补它

### 场景 4：`figma-mapping.md` 存在，但可执行节点证据过时或薄弱

预期行为：

- 停止并将工作交回 `ui-requirement-mapping`
- 不要在不可信的映射证据之上编写权威的交互契约

### 场景 5：`traceability.json` 已包含桥接上下文，如 `spec_kit_refs`

预期行为：

- 保留这些字段
- 不要替换 `traceability.json`
- 不要发明第二个桥接工件

### 场景 6：现有的团队模式暗示了比源材料支持的更流畅的流程

预期行为：

- 仅在被允许时将其记录为 `Source: Existing Pattern` 或 `Assumption: Micro Interaction`
- 不要让便利性覆盖需求或 Figma 真相

### 场景 7：动效细节缺失，但需要转场以保持状态变化可理解

预期行为：

- 记录简短、功能性的动效说明
- 保持时序保守且转场可中断
- 尊重减少动效期望
- 不要将差距转化为装饰性动画工作

### 场景 8：设计证据中的某个控件依赖悬停或手势提示

预期行为：

- 如果源或现有模式支持，定义等效的焦点、触摸或可见回退行为
- 不要让仅悬停或仅手势的发现方式成为重要操作的唯一路径
- 如果缺失的回退会改变可用性或业务含义，则升级

## 交接

生成交互契约并通过自检后停止。

如果用户希望继续，则将 `interaction-design.md`、`decisions.md` 和保留的有治理子需求包交接给下游阶段。除非用户明确要求下一阶段，否则不要在此技能内执行 Spec Kit 规划或实现。
