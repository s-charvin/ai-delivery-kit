---
name: requirement-breakdown
description: 用于在已批准或接近最终版本的顶层需求材料必须扩展为受治理的 `.ai-delivery` 需求包、依赖元数据和下游就绪的子需求切片时，在 API 契约映射、UI 映射或实现规划之前使用。
---

# 需求分解

项目工作流技能，用于将顶层需求材料转化为宿主仓库内受治理的需求和子需求工件，同时早期提取共享基础，并为下游契约阶段预先播种交付切片候选。

## 概述

将已批准或接近最终版本的需求真相转化为下游技能可以直接使用的分解包。此阶段在 `.ai-delivery/requirements/<requirement-id>/` 下扩展接收包，或者在接收缺失时引导相同的契约，而不重新设计产品或凭空编造缺失的业务真相。目标不仅是划分业务边界，还包括预先嵌入执行边界提示（如能力概况和交付切片候选），以便后续阶段不再需要猜测共享传播或页面状态工作实际属于哪个范围。

## 硬边界

- 不要凭空编造产品真相。
- 不要重新设计产品。
- 不要编写实现代码。
- 不要在此处生成 Spec Kit 规范、计划或任务。
- 不要在此处绑定 Figma 节点或做出视觉真相决策。
- 不要静默掩盖已批准需求来源之间的冲突。
- 不要用无来源的摘要替换有来源的需求真相。
- 不要在 `.ai-delivery/` 之外创建第二个真相存储。
- 不要删除已有的后期工件，如 `figma-mapping.md` 或 `interaction-design.md`。
- 不要将模糊的切片提升为 `split_ready`。
- 不要让 API 的不完整性缩小安全的需求切片范围。

如果请求仍处于探索阶段，需求来源仍在变动，或顶层需求材料尚未足够批准以安全拆分，则停止并告知用户此阶段为时过早。

## 何时使用此技能

- 在需求接收之后，扩展已批准或接近最终版本的需求包
- 将顶层需求材料拆分为可独立跟踪的子需求
- 在 UI 映射之前提取跨领域规则和依赖排序
- 在承载页面的模块意外吸收共享基础和跨功能基础设施之前，提前提取它们
- 记录交付切片候选，而不过早冻结最终实现切片
- 播种受治理的子需求工件，如 `status.json` 和 `traceability.json`

## 何时不使用此技能

- 早期产品探索
- Figma 映射或交互设计
- 编写实现任务或计划
- 基于假设填补缺失的业务逻辑
- 不改变需求真相的后端实现分析

## 必需参考

- [双重真相规则](references/dual-truth-rules.md)
- [阻塞项目录](references/blocker-catalog.md)
- [日志记录检查清单](references/logging-checklist.md)
- [需求切片模板](templates/requirement-slice-template.md)
- [检查清单](references/checklist.md)
- [子需求 README 模板](references/subreq-readme-template.md)

同时匹配宿主仓库中 `.ai-delivery/requirements/` 下已建立的受治理工件形状，而不是发明一个并行的契约。

## 输入

### 必需输入

- 当前已批准的顶层需求材料的路径

### 预期辅助输入

- 当已知时，现有的需求包路径或需求 ID
- 改变需求真相的已批准补充材料

### 可选输入

- API 契约
- 代码库上下文
- 设计系统说明
- 业务规则补充材料

### 缺失输入处理

如果某个来源或工件缺失：

- 如果顶层需求材料缺失、过时或仍在变动中，则停止。
- 如果需求包已存在，则复用而不是创建重复。
- 如果接收工件缺失，则在 `.ai-delivery/requirements/<requirement-id>/` 下引导相同的受治理包，并在 `breakdown-summary.md` 或 `decisions.md` 中记录该引导行为。
- 如果可选补充材料缺失但需求真相仍然充分，则继续并在"未解决问题"下记录缺口。
- 如果缺失的输入移除了安全拆分所需的关键业务事实，则阻塞于 `blocked_missing_requirement`。
- 如果两个已批准的需求来源冲突，则阻塞于 `blocked_requirement_conflict`。
- 如果下游材料（如 Figma 或 API 契约）缺失，除非需求真相本身依赖于它们，否则不要阻塞此阶段。

## 输出目标

生成一个下游技能可以直接使用的需求包，而无需重新解释整个需求来源。以最小压缩保留顶层需求真相：在规范化之前复制或引用关键源文本，并明确标记任何压缩、遗漏或冲突，而不是平滑处理。该包必须保留：

- 根植于 `requirement.md` 的权威需求包
- `breakdown-summary.md` 和 `global-rules.md` 中的需求级摘要
- 无环的 `dependency-graph.json`
- 每个子需求一个受治理的文件夹，包含 `README.md`、`requirement-slice.md`、`dependency.json`、`status.json`、`traceability.json`、`api-contract-mapping.md` 和 `decisions.md`，其中 `README.md` 是人类可读的导航文档，`requirement-slice.md` 是权威的保留来源的契约
- 每个子需求的有来源支持的能力概况，以便下游阶段能够判断该切片是承载页面的、共享状态的、集成密集型的还是仅基础设施的
- 记录为稍后综合的提示的交付切片候选，同时将最终的页面状态切片冻结排除在此阶段之外
- 明确的来源覆盖、关键逐字摘录、依赖关系、验收信号、未解决问题、压缩警告和阻塞项证据
- 一等公民的 `traceability.json` 和 `status.json` 契约，而非非正式的笔记

每个可编辑的 Markdown 或 JSON 工件应遵循仓库的受治理元数据契约，而非临时的文件形状。

## 默认输出布局

```text
.ai-delivery/requirements/<requirement-id>/
├── requirement.md
├── breakdown-summary.md
├── global-rules.md
├── dependency-graph.json
└── sub-requirements/
    └── <subreq-id>/
        ├── README.md
        ├── requirement-slice.md
        ├── dependency.json
        ├── status.json
        ├── traceability.json
        ├── api-contract-mapping.md
        └── decisions.md
```

如果文件夹中已包含后期文件，如 `figma-mapping.md` 或 `interaction-design.md`，则保留它们并仅更新需求分解所拥有的工件。

## 工作流程

### 1. 盘点权威来源

- 仔细阅读顶层需求材料，并在可能时捕获行号或来源位置。
- 确认哪个文件是当前已批准的需求来源，哪些补充材料仅为辅助上下文。
- 确定在进行任何摘要之前，哪些源段落、项目符号或规则块必须逐字复制到子需求工件中。
- 如果一个顶层片段将影响多个子需求或全局规则，则明确记录该共享覆盖范围，而不是静默改写。
- 确定目标需求 ID 和 `.ai-delivery/requirements/` 下的需求文件夹。
- 复用此技能的本地引用和模板，而不是发明新的工件形状。

### 2. 确认或引导需求包

- 当存在时，复用接收阶段创建的需求包。
- 如果包缺失，则在 `.ai-delivery/requirements/<requirement-id>/` 下引导相同的契约，而不是发明另一个目录或命名方案。
- 在编写下游分解输出之前，确保该包内存在 `requirement.md` 作为权威需求工件。

### 3. 确定子需求边界

按交付含义拆分，而非按任意的技术偏好。一个子需求应至少满足以下条件之一：

- 可以独立开发
- 可以独立集成
- 可以独立测试或验收
- 拥有一个连贯的依赖或能力面

仅使用以下子需求类型：

- `Global Rule`（全局规则）
- `Shared Foundation`（共享基础）
- `Shared Component`（共享组件）
- `Feature Module`（功能模块）
- `Cross-Feature Infrastructure`（跨功能基础设施）

必需的拆分规则：

- 在最终确定边界之前，为每个候选子需求使用能力概况进行分类：
  - `contains_page_states`（包含页面状态）
  - `contains_shared_state`（包含共享状态）
  - `contains_integration`（包含集成）
  - `contains_infra_only`（仅包含基础设施）
- 如果一个真相影响多个页面、载体、缓存、所有者或传播目标，则在功能模块消费之前将其提取到"共享基础"或"跨功能基础设施"中。
- 共享基础和共享组件必须在消费它们的功能模块之前拆分出来。
- 适用于两个或更多子需求的跨领域规则属于 `global-rules.md`，而不是放在一个假冒的功能模块中。
- 记录供下游综合的交付切片候选，但暂不冻结最终的页面状态切片。
- 不要仅仅为实现便利而过度拆分。

### 4. 一次性提取共享规则

- 将适用于两个或更多子需求的规则移到 `global-rules.md`。
- 从受影响的子需求中引用这些规则，而不是复制它们。
- 保持 `global-rules.md` 专注于跨领域真相，而非功能本地的行为。

### 5. 编写需求级工件

- 编写 `breakdown-summary.md`，包含输入来源、需求包路径、引导或复用说明、子需求索引、全局阻塞项和全局未解决问题。
- 编写 `dependency-graph.json`，使其反映子需求 DAG 并保持无环。
- 将所有工作流工件真相保留在业务项目的 `.ai-delivery/requirements/` 树中。

### 6. 创建或更新每个子需求包

对于每个子需求：

- 使用 `references/subreq-readme-template.md` 编写 `README.md`。将其视为人类可读的导航文档：包含元数据、顶层需求覆盖、关键逐字摘录、有来源支持的子需求陈述、边界、依赖关系、有来源链接的验收信号、未解决问题、压缩警告和当前状态。
- 编写 `README.md` 和 `requirement-slice.md`，附带能力概况，明确说明承载页面的、共享状态的、集成的和仅基础设施的内容。
- 使用 `templates/requirement-slice-template.md` 编写 `requirement-slice.md`。将其视为权威的下游契约：包含详尽的源需求覆盖、逐字源摘录、规范化的切片陈述、范围边界、依赖契约、交付切片候选、验收信号、未解决问题、歧义或冲突、压缩警告和源需求参考索引。
- 先复制或引用，再进行总结。当原始顶层措辞重要时，不要让 `requirement-slice.md` 仅依赖二阶摘要。
- 不要将模板指导部分（如"模板编写规则"或"模板示例"）复制到生成的工件中。
- 编写 `dependency.json`，包含明确的 `depends_on` 和 `blocks` 声明，即使它们为空。
- 编写 `status.json`，包含当前状态以及阻塞恢复字段，如 `blocked_from_status` 和 `resume_target_status`。
- 播种 `traceability.json` 作为一等公民的受治理工件，包含需求引用、`source_index`、仓库当前的桥接字段、初始化的 `api_contract_mapping` 子树，以及当仓库已经期望它们时，用于能力概况或交付切片候选交接的需求阶段占位符。
- 编写 `api-contract-mapping.md` 作为受治理的占位符工件。如果未提供 API 契约来源，则记录事实上的缺失并将 `traceability.json.api_contract_mapping.status` 初始化为 `missing_nonblocking`。如果提供了 API 契约来源但详细映射推迟到专用阶段，则将其初始化为 `pending`。
- 编写 `decisions.md`，包含阻塞项证据、引导说明、受治理面缺口以及任何明确标记的本地假设。
- 严格分级未解决问题：
  - `non_blocking`：仅当该缺口不改变边界、验收或传播真相时
  - `blocks_acceptance_contract`：当该缺口稍后会影响默认状态、行组成、骨架顺序、空状态或搜索状态或其他屏幕契约真相时
  - `blocks_slice_synthesis`：当该缺口稍后会影响共享传播、集成边界或交付切片所有权时

### 7. 保守设置状态

- 默认将不确定的切片设为 `draft`。
- 仅当切片对下游 UI 映射足够具体，并且包含完整的来源覆盖、关键逐字摘录、清晰的范围、依赖关系、带有来源链接的验收信号、能力概况、交付切片候选、未解决问题、必要时带有压缩警告以及源需求引用时，才将子需求移至 `split_ready`。
- 当任何未解决项被评定为 `blocks_acceptance_contract` 或 `blocks_slice_synthesis` 时，不要将切片提升为 `split_ready`。
- 当提出阻塞项时，从目录中记录最窄的阻塞项，并在 `status.json` 中保留阻塞恢复意图。
- 当可用的独立管理支持面用于受治理日志记录、阻塞项记录或状态转换时，使用它。

### 8. 交接前重新审计

- 在编写工件后重新打开原始需求材料。
- 重新打开 `breakdown-summary.md`、`global-rules.md`、`dependency-graph.json` 和每个子需求文件夹。
- 验证没有需求部分被静默丢弃或过度压缩、依赖图仍然无环、全局规则未重复到功能切片中、每个子需求都拥有所需的文件和引用。
- 验证每个规范化陈述和验收信号都可以追溯到源引用或引用的摘录。
- 如果发现不匹配，修复工件并在停止前重新检查。

## 来源保留编写模式

- 在规范化关键源文本之前，先复制或引用它。
- 保持 `README.md` 对人类更简洁，但保留来源支持。
- 使用 `requirement-slice.md` 作为详尽的下游契约，而不是第二个简短摘要。
- 如果摘要添加了来源从未说过的业务动词、条件或状态转换，将其移到"未解决问题"或"歧义和冲突"中，而不是将其呈现为真相。

### 小示例

```md
顶层来源：
> 用户可以从设置中重命名项目。保存按钮保持禁用状态，直到新名称非空且与当前值不同。

逐字源摘录
### 摘录 1
- `source_ref`: `requirement.md#L14-L15`
- `quoted_text`:
> 用户可以从设置中重命名项目。保存按钮保持禁用状态，直到新名称非空且与当前值不同。

规范化切片陈述
- `statement`: `此切片涵盖设置中的项目名称编辑，包括对空输入或未更改输入的保存禁用门控。`
- `source_basis`: `摘录 1`
- `normalization_type`: `措辞清理`

验收信号
### 信号 1
- `signal`: `当输入为空或未更改时，保存保持禁用状态。`
- `source_ref`: `requirement.md#L15-L15`
- `derived_from`: `逐字摘录`
```

## 状态和阻塞项规则

- 仅当切片对下游 UI 映射足够具体且已通过覆盖、逐字摘录和来源链接的验收信号保留了其关键来源真相时，才将子需求移至 `split_ready`。
- 如果需求来源与其自身或其他已批准的需求来源冲突，则阻塞于 `blocked_requirement_conflict`。
- 如果关键业务事实缺失，则阻塞于 `blocked_missing_requirement`。
- 如果未解决的问题稍后会阻止稳定的屏幕契约，则将其分类为 `blocks_acceptance_contract`。
- 如果未解决的问题稍后会阻止稳定的共享状态或集成切片，则将其分类为 `blocks_slice_synthesis`。
- 如果边界仍然模糊，则编写草稿加未解决问题，并在 `split_ready` 之前停止。
- 当输入阻塞项时，在 `status.json` 中使用 `blocked_from_status` 和 `resume_target_status` 保留恢复意图；不要在之后手动绕过恢复路径。

## 硬性约束

- 仅在 `.ai-delivery/requirements/` 内工作。
- 不要凭空编造产品真相。
- 不要在此处生成 Spec Kit 规范、计划或任务。
- 不要在此处绑定 Figma 节点。
- 不要将工作流真相移到 `ai-delivery-admin` 中。
- 不要让无来源的摘要替换任何 `split_ready` 切片中引用的顶层需求文本。
- 不要用非正式笔记或第二个桥接文件替换 `traceability.json`。

## 输出标准

每个子需求包必须保留：

- 清晰的范围
- 明确的类型
- 明确的来源覆盖
- 关键逐字源摘录（当措辞重要时）
- 明确的依赖关系
- 验收信号
- 未解决问题
- 压缩警告（当规范化可能丢失细微差别时）
- 源需求引用

最低工件预期：

- `breakdown-summary.md`：来源输入、引导或复用说明、子需求索引、全局阻塞项、全局未解决问题
- `global-rules.md`：仅适用于多个子需求的跨领域规则
- `dependency-graph.json`：需求级 DAG，无人为创建的循环
- `README.md`：元数据、导航摘要、顶层需求覆盖、关键逐字摘录、有来源支持的子需求陈述、边界、依赖关系、有来源链接的验收信号、未解决问题、压缩警告、当前状态
- `requirement-slice.md`：元数据、详尽的源需求覆盖、逐字源摘录、规范化切片陈述、范围边界、依赖契约、验收信号、未解决问题、歧义或冲突、压缩警告、源需求参考索引
- `dependency.json`：明确的 `depends_on` 和 `blocks`
- `status.json`：`status`、`blocked_from_status` 和 `resume_target_status`
- `traceability.json`：需求引用、空或初始化的映射字段、初始化的 `api_contract_mapping`、冲突、验证字段以及当仓库期望时现有的桥接契约字段
- `api-contract-mapping.md`：供后期 Swagger 或 OpenAPI 映射使用的占位符或初始化的下游契约阶段
- `decisions.md`：阻塞项、恢复说明、引导说明、受治理面缺口、明确的假设

如果受治理的管理支持不可用，则在本地说明或 `decisions.md` 中记录该缺失依赖，但将工件真相保留在 `.ai-delivery/` 中。

## 自检清单

在报告完成之前，确认以下所有事项：

- [ ] 使用了当前已批准的顶层需求材料
- [ ] 正确复用了需求包或在没有发明新布局的情况下进行了引导
- [ ] 没有需求部分被静默丢弃
- [ ] 拆分为子需求时，没有关键源文本被静默过度压缩
- [ ] `global-rules.md` 仅包含跨领域规则
- [ ] 每个子需求都有唯一的 ID、明确的类型和明确的依赖声明
- [ ] 每个子需求都有针对其所依赖的顶层片段的明确来源覆盖
- [ ] 每个 `split_ready` 候选在规范化摘要之前保留了关键逐字摘录
- [ ] `dependency-graph.json` 是无环的，并且与每个子需求的依赖关系匹配
- [ ] 每个子需求都包含 `README.md`、`requirement-slice.md`、`dependency.json`、`status.json`、`traceability.json`、`api-contract-mapping.md` 和 `decisions.md`
- [ ] 每个验收信号都可以追溯到具体的源引用或摘录引用
- [ ] `status.json` 保留了阻塞恢复字段
- [ ] `traceability.json` 被视作一等公民的受治理工件
- [ ] 模糊的切片保持在 `draft` 或阻塞状态，而不是被强制设为 `split_ready`
- [ ] 没有 Figma 映射、交互设计、Spec Kit 规划或个人发明的产品逻辑泄漏到此阶段

## 压力场景

在编写或更新分解时，将这些作为心智回归测试使用。

### 场景 1：接收包缺失

预期行为：

- 使用相同的受治理契约引导 `.ai-delivery/requirements/<requirement-id>/`
- 确保 `requirement.md` 存在
- 记录引导说明
- 不要发明第二个目录方案

### 场景 2：一条规则适用于多个功能区域

预期行为：

- 将该规则移到 `global-rules.md`
- 从受影响的子需求中引用它
- 不要仅仅为了存储该规则而创建一个假冒的功能模块

### 场景 3：辅助材料不完整，但核心需求真相充分

预期行为：

- 继续分解
- 在"未解决问题"下记录缺失的补充材料
- 不要编造事实
- 除非关键业务事实缺失，否则不要阻塞

### 场景 4：两个已批准的需求来源冲突

预期行为：

- 将受影响的切片阻塞于 `blocked_requirement_conflict`
- 捕获冲突证据
- 在 `split_ready` 之前停止

### 场景 5：需求文件夹已包含后期文件

预期行为：

- 仅更新需求分解所拥有的工件
- 保留 `figma-mapping.md` 和 `interaction-design.md`
- 不要擦除下游工作

### 场景 6：提议的依赖图变得有环

预期行为：

- 重新拆分或保持受影响的切片为草稿
- 不要将有环的 `dependency-graph.json` 发布为最终版本

### 场景 7：仓库已期望 `traceability.json` 中包含桥接数据

预期行为：

- 在 `traceability.json` 内部保留或播种该桥接契约
- 不要发明第二个桥接工件

### 场景 8：顶层需求段落内容密集，容易让人想用摘要替代

预期行为：

- 在规范化之前将关键行复制到"逐字源摘录"中
- 将这些行映射到来源覆盖和验收信号
- 如果压缩该段落会丢失细微差别，则记录压缩警告或未解决问题

### 场景 9：分解期间 API 契约材料尚不可用

预期行为：

- 如果需求真相仍然充分，则继续分解
- 将 `api-contract-mapping.md` 初始化为事实占位符
- 将 `traceability.json.api_contract_mapping.status` 设置为 `missing_nonblocking`
- 用源需求引用播种 `traceability.json.source_index.requirement`，并用非阻塞的缺失契约记录播种 `traceability.json.source_index.api`
- 不要发明端点或字段

## 交接

在产出了需求分解包并通过自检后停止。

如果用户希望继续，则将根植于 `requirement-slice.md`、`api-contract-mapping.md`、`global-rules.md`、`dependency.json` 和 `traceability.json` 的需求包移交给下游阶段。不要在此技能内执行 API 契约映射、UI 映射、交互设计或实现规划，除非用户明确要求进入下一阶段。
