---
name: ui-requirement-mapping
description: 当子需求已有受治理的分解产物，且必须在交互设计或实现之前将其绑定到来自 Figma MCP 或兼容提供商 MCP 的已验证结构化设计证据时使用
---

# UI 需求映射

项目本地工作流技能，用于将受治理的子需求片段绑定到已验证的结构化设计证据，并在宿主仓库内生成基于证据的映射交接文档。

## 概述

在 `requirement-breakdown` 之后，当子需求包已存在于 `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/` 目录下时使用本技能。如果 `api-contract-mapping.md` 已存在，则将其视为上游接口契约上下文。如果 API 真值缺失、不完整或仅在动作集成层受阻，本阶段仍可运行在"视觉证据优先"模式下。本阶段将写入 `figma-mapping.md`，原地更新 `traceability.json`，并保留上游创建的受治理产物契约，而非创建新的平行映射存储。

本阶段的主要证据来源是来自 Figma MCP 或兼容提供商 MCP（如 TemPad Dev、F2C 或其他可信的结构化设计提供商）的结构化节点数据。截图或预览可作为可选的支持性上下文缓存，但它们从来不是完成标准，也从不覆盖结构化节点负载。本阶段止于证据绑定加可执行状态发现；它不冻结不可变屏幕契约、最终 API 语义或完整集成真值——这些属于后续关卡。

## 硬边界

- 不得凭空编造视觉真值。
- 不得添加页面、字段、组件、状态或业务流。
- 不得仅凭节点名称作为证据。
- 不得将截图、预览或纯文字描述视为充分的映射证据。
- 不得将顶层 `SECTION` 用作最终可执行节点目标。
- 不得在没有为每个声称的可执行节点提供可信的结构化节点负载的情况下标记映射完成。
- 当最终状态的 `get_code` 仍缺失时，不得将 `SECTION` 加 `get_structure` 视为充分的最终屏幕状态真值。
- 不得使用本阶段冻结最终屏幕契约、布局顺序或复用策略。
- 不得将提供商负载扁平化为缓存中损失信息的替代模式。
- 不得用 sidecar 笔记或第二个桥接产物替换 `traceability.json`。
- 重新运行映射时不得删除 `interaction-design.md` 或其他后续阶段产物。
- 不得手动编辑阻塞状态使其看起来已恢复。
- 不得要求完整的 API 映射才能完成 UI 映射。
- 不得让动作语义、错误码、成功返回语义或服务器副作用中的纯 API 缺口阻塞视觉证据绑定。
- 不得为了看起来映射完整而凭空编造业务交互状态、服务器错误状态、成功传播结果或无来源支持的分支状态。

如果无法从 Figma MCP 或兼容提供商 MCP 获取所需 UI 的可信结构化设计证据，则停止执行并报告本阶段无法安全完成。

## 适用场景

- 将 `requirement-slice.md` 绑定到来自 Figma MCP 或兼容提供商 MCP 的结构化设计证据
- 在交互设计或实现之前生成 `figma-mapping.md`
- 为验收冻结交接生成"可执行屏幕状态"和"映射就绪判定"
- 当受治理契约已支持时，使用已验证节点、置信度、冲突、验证时间和感知提供商证据引用更新 `traceability.json`
- 暴露视觉阻塞项、共享节点和配套 UI，而不会静默扩大业务范围

## 不适用场景

- 需求拆分或需求真值修复
- 交互契约设计
- 最终代码生成
- 通过猜测填补缺失的设计证据
- 用纯文字描述替换原始提供商证据

## 必要参考

- [双重真值规则](references/dual-truth-rules.md)
- [阻塞项分类](references/blocker-catalog.md)
- [日志检查清单](references/logging-checklist.md)
- [Figma 映射模板](templates/figma-mapping-template.md)
- [Figma 获取顺序](references/figma-fetch-order.md)
- [映射检查清单](references/mapping-checklist.md)

还需匹配 `.ai-delivery/requirements/` 下已建立的受治理产物结构以及 `.ai-delivery/figma-cache/` 下的原始证据边界。

## 输入

### 必需输入

- `subreq-id`
- `requirement-slice.md`
- 设计文件、文件 ID、节点目标或等效的设计源定位器

### 期望支持输入

- `api-contract-mapping.md`（当 API 契约映射已完成时）
- `traceability.json`
- `status.json`
- 现有的 `decisions.md`

### 可选输入

- 显式节点列表
- 提供商提示或首选提供商顺序
- 导出的评论
- token 文件
- 设计版本提示
- 供人工审阅使用的可选截图或预览

### 缺失输入处理

如果源或产物缺失：

- 如果 `requirement-slice.md` 缺失或尚不适合映射，则停止执行并将工作交回 `requirement-breakdown`。
- 优先从 `split_ready` 开始；如果片段仍为 `draft` 状态，或因需求或视觉真值不安全而被阻塞，则停止执行而非假装映射正常。如果现有阻塞项仅为 API 相关问题且不妨碍视觉载体识别，则以"视觉证据优先"模式继续。
- 如果旧版文件夹中 `traceability.json` 缺失，则仅修复当前受治理契约，并在 `decisions.md` 中记录此修复；不得创建不同形状的 JSON。
- 如果缓存的结构化证据缺失、过期或未覆盖所需的可执行节点，则使用 Figma 检索顺序刷新它。
- 如果仍无法从受支持的提供商获取可信的结构化节点证据，则停止并阻塞，而非根据截图、预览或记忆进行映射。
- 可选预览可在有帮助时缓存或引用，但它们从来不是完成所必需的。
- 如果 `interaction-design.md` 已存在，则保留它，并在映射发生实质性变化时在 `decisions.md` 中记录所需的重新验证。

## 输出目标

生成下游交互设计或实现可直接使用的映射包。输出必须保留：

- 基于结构的 `figma-mapping.md`
- 更新的 `traceability.json`，包含 `requirement_refs`、`figma_nodes`、`mapping_type`、`confidence`、`conflicts` 和 `last_verified_at`，以及当现有受治理契约已支持时的提供商感知证据引用
- 上游 API 阶段已填充时现有的 `api_contract_mapping` 子树
- 仓库中已有的桥接字段如 `spec_kit_refs`
- 显式的"必需 UI"、"配套 UI"、"共享节点"、"缺失的设计证据"、"冲突"和结构化验证证据
- `.ai-delivery/figma-cache/` 与受治理子需求产物之间的原始证据边界
- 统一的提供商感知缓存，其中每个缓存产物保留兼容性元数据以及 `provider`、`artifact_type` 和 `raw_payload`，不扁平化提供商响应
- 在 `ui-acceptance-contract` 之前命名可执行屏幕状态和映射就绪判定的交接文档
- 当 API 真值对后续关卡尚不充分时，显式的就绪备注如 `ready_for_visual_development`、`integration_deferred`、`action-blocked-not-visual-blocked` 或 `blocked_for_acceptance_due_to_api`

## 默认输出路径

```text
.ai-delivery/figma-cache/<design-source-id>/
├── index.json
└── artifacts/
    └── <artifact-id>.json

.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── figma-mapping.md
├── traceability.json
└── decisions.md
```

推荐的缓存记录结构：

```json
{
  "figma_file_id": "abc123",
  "node_id": "987:654",
  "node_name": "Save Button",
  "subreq_ids": ["profile-settings-edit-form"],
  "last_updated_at": "<ISO8601>",
  "freshness": "fresh | stale | missing | corrupt",
  "provider": "figma-mcp | tempad-dev | f2c | <compatible-provider>",
  "artifact_type": "file_context | node | comments | tokens | assets | preview",
  "source_ref": {},
  "raw_payload": {}
}
```

保持 `raw_payload` 为提供商的原始响应格式。保留现有管理员读取器所需的兼容性元数据，同时添加提供商感知字段。如果提供商返回非 JSON 预览或资产文件，则将二进制文件存储为兄弟产物并从 JSON 包装器中引用，而不是替换原始结构化负载。

## 工作流

### 1. 确认上游分解契约

- 在接触设计证据之前，先读取 `requirement-slice.md`、`api-contract-mapping.md`（如存在）、`traceability.json`、`status.json` 和 `decisions.md`。
- 确认子需求文件夹和 `subreq-id` 与预期范围匹配。
- 优先从 `split_ready` 开始；如果上游范围仍不稳定，则停止而非掩盖分解问题。
- 将 `api_mapped`、`missing_nonblocking` 和 `needs_revalidation` 视为视觉映射的正常准入状态。仅当阻塞项消除了安全识别视觉载体或可执行状态真值的能力时，才将 `blocked_*` 视为准入停止条件。

### 2. 收集或刷新结构化设计证据

- 遵循 `references/figma-fetch-order.md` 中的 Figma 检索顺序。
- 在发出新的提供商请求之前，优先使用 `.ai-delivery/figma-cache/` 中的缓存证据。
- 默认使用 Figma MCP，当它能提供所需的结构化上下文时；兼容提供商如 TemPad Dev 或 F2C 可在它们提供可信的结构化节点负载时进行补充或替代。
- 仅在以下情况下刷新证据：用户请求、缓存缺失、缓存相对于请求的设计版本已过期，或无法从缓存验证所需节点。
- 将每个检索到的产物缓存在 `.ai-delivery/figma-cache/` 下，附带兼容性元数据以及 `provider`、`artifact_type` 和提供商原生 `raw_payload`。

### 3. 保守选择可执行节点

- 仅当请求范围较大时，才将 `SECTION` 作为入口点使用。
- 使用 `get_structure` 缩小层次结构并定位候选载体。
- 从结构化提供商负载收敛到真实的可执行帧、组件或区域。
- 不得将顶层 `SECTION` 用作最终可执行节点目标。
- 为每个最终会输入 `ui-acceptance-contract` 的最终帧或状态要求 `get_code`。
- 不得仅根据节点名称、仅根据截图或纯文字摘要完成映射。
- 当保真度要求相邻 UI 一同交付时，显式记录"配套 UI"。
- 当一个视觉载体属于多个子需求时，显式记录"共享节点"。
- 如果两个结构化提供商在层次结构、节点身份或可执行边界上存在分歧，记录冲突并在无法安全解决时阻塞。
- 缺失默认状态、搜索状态、行组合、父容器、关键状态载体或资产形式必须被视为阻塞证据而非软备注。

### 4. 编写 `figma-mapping.md`

- 使用 `templates/figma-mapping-template.md`。
- 包含设计目标、结构化证据来源、需求到节点映射、节点到需求映射、必需 UI、配套 UI、共享节点、可执行屏幕状态、缺失的设计证据、冲突、映射就绪判定和可追溯性更新备注。
- 对每个映射的需求点，记录提供商、节点 ID、原始产物引用以及结构化负载为何充分。
- 保持缺失设计证据客观。缺失设计证据不是凭空编造视觉真值的许可。
- 当 API 真值不完整但视觉真值可靠时，设置客观判定如 `ready_for_visual_development`、`ready_for_visual_development_but_blocked_for_acceptance_due_to_api` 或等效的受治理备注，而非阻塞整个映射阶段。

### 5. 原地更新 `traceability.json`

- 将 `traceability.json` 视为一等受治理产物，而非可丢弃的 sidecar。
- 保留现有的 `requirement_refs`、现有冲突历史、现有 API 契约映射字段如 `api_contract_mapping`，以及现有桥接字段如 `spec_kit_refs`。
- 仅更新映射所属的事实，如 `figma_nodes`、`mapping_type`、`confidence` 和 `last_verified_at`。
- 如果现有受治理契约已包含提供商引用或证据引用，则原地保留并更新它们。
- 如果契约尚不包含提供商感知证据字段，则不要发明不兼容的 JSON 结构；将完整的提供商和原始产物证据轨迹保留在 `figma-mapping.md` 和 `decisions.md` 中。

### 6. 保守处理状态与阻塞项

- 仅当映射得到可信的结构化节点负载支持、经过冲突审查且基于可执行节点时，才将子需求推进至 `figma_mapped`。
- 如果仅 API 缺口影响动作语义、错误语义、成功返回字段或服务器副作用，但不会改变识别视觉载体的能力，则以"视觉证据优先"模式继续映射，并将缺口记录为 `integration_deferred`、`action-blocked-not-visual-blocked`、`blocked_for_acceptance_due_to_api` 或等效的受治理备注。
- 如果 Figma 派生的结构化证据在不同提供商或检索轮次之间存在自相矛盾，则以 `blocked_figma_conflict` 阻塞。
- 如果需求定义了功能但设计证据没有视觉载体，则以 `blocked_missing_design` 阻塞。
- 如果设计证据显示了需求明确排除的视觉或状态，则以 `blocked_requirement_figma_conflict` 阻塞。
- 如果最终屏幕状态已识别但缺少其状态级 `get_code` 证据，则以 `blocked_missing_state_code` 阻塞。
- 如果所需的视觉真值如默认状态、搜索状态、行组合、父容器或资产形式缺失，则以 `blocked_missing_visual_truth` 阻塞。
- 如果所需的可执行节点无法通过可信的结构化证据验证，则以 `blocked_verification_failure` 阻塞。
- 可选截图或预览永远不会将低置信度结构化证据升级为 `figma_mapped`。
- 当录入阻塞项时，在 `status.json` 中保留恢复意图，包含 `blocked_from_status` 和 `resume_target_status`；不得通过手动编辑绕过恢复。
- 仅在可用时使用独立的管理支持界面进行受治理日志记录、阻塞项处理、状态转换和产物更新。

### 7. 交接前重新审计

- 重新打开 `requirement-slice.md`、`figma-mapping.md` 和 `traceability.json`。
- 验证每个声称的映射仍有结构化证据，包含提供商、节点 ID、原始产物引用和明确的证据基础。
- 验证每个必需的 UI 项都映射到真实的设计证据，且每个共享节点或配套 UI 项都被显式记录。
- 验证缓存的产物保留提供商原生原始负载而非扁平化摘要，同时保持当前管理员读取器所需的兼容性元数据。
- 验证 `traceability.json` 在映射轮次之前存在的桥接字段如 `spec_kit_refs` 和 `api_contract_mapping` 仍被保留。
- 如果实质性映射真值发生变化且 `interaction-design.md` 已存在，则在 `decisions.md` 中记录重新验证需求。

## 状态与阻塞项规则

- 如果需求定义了功能但设计证据没有视觉载体，则以 `blocked_missing_design` 阻塞。
- 如果设计证据显示了需求明确排除的视觉或状态，则以 `blocked_requirement_figma_conflict` 阻塞。
- 如果 Figma 派生的结构化证据在不同提供商或检索轮次之间存在自相矛盾，则以 `blocked_figma_conflict` 阻塞。
- 如果所需的可执行节点无法通过可信的结构化证据验证，则以 `blocked_verification_failure` 阻塞。
- 如果最终状态缺少 `get_code`，则以 `blocked_missing_state_code` 阻塞。
- 如果屏幕验收所需的关键视觉真值缺失，则以 `blocked_missing_visual_truth` 阻塞。
- 不得仅因 API 动作语义、错误码、成功返回字段或危险动作副作用不完整而阻塞本阶段，只要这些缺口不改变视觉载体识别。
- 仅当映射有结构支持且经过冲突审查时，才将子需求推进至 `figma_mapped`；就绪判定仍可能为 `ready_for_acceptance_contract`、`ready_for_visual_development` 或 `ready_for_visual_development_but_blocked_for_acceptance_due_to_api`。

## 硬约束

- 在接触设计证据之前先读取 `requirement-slice.md`。
- 不得凭空编造页面、字段、组件或状态。
- 不得将 `ai-delivery-admin` 视为视觉真值来源。
- 不得将顶层 `SECTION` 用作最终可执行节点目标。
- 未完成 `figma-mapping.md` 和 `traceability.json` 不得完成映射。
- 不得仅根据节点名称、仅根据截图或与结构化负载矛盾的截图完成映射。
- 不得将提供商原始负载扁平化为损失信息的缓存结构。
- 不得替换 `traceability.json` 或发明第二个桥接产物。

## 输出标准

每个映射必须包含：

- 提供商感知的需求到节点映射
- 提供商感知的节点到需求映射
- 必需 UI 列表
- 配套 UI 列表
- 共享节点列表
- 可执行屏幕状态
- 缺失的设计证据列表
- 冲突列表
- 映射就绪判定
- 附带提供商、产物引用、节点 ID 和证据基础的结构化验证证据

如果受治理管理支持不可用，则将产物真值保留在 `.ai-delivery/` 中，并在本地记录缺失的受治理依赖，而不创造替代真值存储。

## 自检清单

在报告完成之前，确认以下所有项：

- [ ] 在接触设计证据之前已读取 `requirement-slice.md`
- [ ] 子需求从更严格的分解契约看可安全映射，优先为 `split_ready`
- [ ] 每个声称的可执行节点存在可信的结构化节点证据
- [ ] 没有仅根据节点名称、仅根据截图或纯文字描述完成的映射
- [ ] 每个映射的可执行节点都记录了提供商和原始产物引用
- [ ] 没有将顶层 `SECTION` 用作最终可执行目标
- [ ] 每个最终可执行屏幕状态都有记录在案的 `get_code` 证据
- [ ] 当存在"配套 UI"和"共享节点"时已显式记录
- [ ] "映射就绪判定"显式且受治理，例如 `ready_for_acceptance_contract`、`ready_for_visual_development` 或 `ready_for_visual_development_but_blocked_for_acceptance_due_to_api`
- [ ] `figma-cache` 产物保留兼容性元数据以及 `provider`、`artifact_type` 和提供商原生 `raw_payload`
- [ ] `traceability.json` 保留现有桥接字段如 `spec_kit_refs`
- [ ] `traceability.json` 仍为第一等受治理产物而非 sidecar 笔记
- [ ] 阻塞项保留 `blocked_from_status` 和 `resume_target_status`
- [ ] 没有后续阶段产物如 `interaction-design.md` 被删除或静默失效

## 压力场景

在编写或更新映射时用作心理回归测试。

### 场景 1：缓存包含预览或截图，但没有所需目标的结构化节点负载

预期行为：

- 使用检索顺序刷新结构化证据
- 不得仅根据预览证据标记映射完成
- 如果仍无法获取可信的结构化证据则阻塞

### 场景 2：存在页面级 `SECTION`，但实际实现目标更深

预期行为：

- 继续深入到可执行帧、组件或区域
- 不得将顶层 `SECTION` 用作最终目标

### 场景 3：一个节点服务于多个子需求

预期行为：

- 在"共享节点"中记录
- 当受治理契约已支持时，在 `traceability.json` 中反映共享所有权
- 不得为了方便而静默分配给一个子需求

### 场景 4：保真度需要严格业务边界之外的相邻 UI

预期行为：

- 记录为"配套 UI"
- 保持业务范围不变
- 不得静默扩大需求

### 场景 5：`interaction-design.md` 已存在且映射发生实质性变化

预期行为：

- 保留 `interaction-design.md`
- 在 `decisions.md` 中记录重新验证需求
- 不得擦除下游工作

### 场景 6：`traceability.json` 已包含桥接数据如 `spec_kit_refs`

预期行为：

- 保留这些现有字段
- 仅更新映射所属的事实
- 不得创建第二个桥接产物

### 场景 7：两个结构化提供商在层次结构或可执行节点身份上存在分歧

预期行为：

- 记录特定于提供商的产物引用和节点 ID
- 捕获冲突而非静默选择一方
- 如果分歧改变映射真值，则以 `blocked_figma_conflict` 阻塞

### 场景 8：提供商仅返回视觉预览数据，没有可信的结构化节点负载

预期行为：

- 仅将预览视为可选的辅助上下文
- 不得标记映射完成
- 继续搜索可信的结构化证据或阻塞

## 交接

在生成映射包并通过自检后停止。

如果用户希望继续，向下游阶段传递 `requirement-slice.md`、`api-contract-mapping.md`（如存在）、`figma-mapping.md`、`traceability.json` 以及在 `decisions.md` 中与映射相关的任何备注。除非用户明确要求下一阶段，否则不得在本技能内执行交互设计或实现。
