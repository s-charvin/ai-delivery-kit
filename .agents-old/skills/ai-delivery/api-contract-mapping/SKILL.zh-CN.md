---
name: api-contract-mapping
description: 当子需求拥有已治理的分解产物，且必须在 UI 映射之前或同时映射到 Swagger、OpenAPI 或其他面向客户端的 API 契约材料时使用。
---

# API 契约映射

项目本地工作流技能，用于将已治理的子需求切片绑定到已验证的面向客户端的 API 契约证据，并在宿主仓库中生成标准化的 API 映射产物。

## 概述

在 `requirement-breakdown` 之后，当子需求包已存在于 `.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/` 下时使用此技能。此阶段写入 `api-contract-mapping.md`，原地更新 `traceability.json.api_contract_mapping`，并保留上游创建的已治理契约产物，而非创建并行的契约存储。

此技能在工作流中为可选项，仅当未提供可信的 API 契约材料时可不执行。如果提供了 Swagger、OpenAPI 或导出的面向客户端接口契约，则此技能是进行映射的治理位置。如果 API 契约材料延迟到达，应重新运行此技能，而不是将迟到的 API 发现塞入 UI 或交互产物中。目标不仅仅是查找端点，而是冻结一个包含请求含义、响应含义、关联语义、错误映射和成功副作用的行为语义契约，使后续交互或传播工作无需猜测。

此阶段不作为整个需求的全局前置门控。缺失或不完整的 API 实情通常应先降级为 `missing_nonblocking`、`pending`、`needs_revalidation` 或操作级别的注释，同时 UI 映射、Shell 工作、本地状态工作、交互骨架以及其他安全的局部前端工作可在尚未依赖缺失 API 实情的情况下继续推进。

## 硬边界

- 不得编造面向客户端的 API 实情。
- 不得分析服务器内部实现，除非其改变了面向客户端的契约。
- 不得编造端点、请求字段、响应字段、状态值、分页或错误语义。
- 当成功副作用或关联语义仍未知时，不得将已定位到的端点视为足够。
- 不得用旁注或第二个桥接产物替换 `traceability.json`。
- 不得覆盖由其他阶段拥有的非 API 可追溯性字段。
- 不得删除后期阶段产物，如 `figma-mapping.md` 或 `interaction-design.md`。
- 不得手动编辑被阻塞状态以使其看起来已恢复。

缺失或不完整的 API 契约材料默认不会阻塞早期前端阶段。如果无法为请求范围获取可信的面向客户端契约证据，则将缺口记录为 `missing_nonblocking`，除非缺失的契约使得该切片的下一安全阶段无法进行、与需求实情矛盾或造成安全/数据风险。

按 `切片 + 阶段` 判断阻塞严重程度，而非按整个需求判断。API 缺口不会阻塞 UI 映射、UI Shell 工作、本地状态管理、交互骨架、安全的局部实现或只读路径，除非这些活动确实依赖于缺失的 API 实情。

## 此技能适用于

- 将 `requirement-slice.md` 映射到 Swagger 或 OpenAPI 材料
- 生成 `api-contract-mapping.md`
- 使用已治理的 API 映射事实更新 `traceability.json.api_contract_mapping`
- 暴露缺失的面向客户端契约、字段缺口以及需求或 API 冲突
- 生成下游 UI 和交互阶段可直接使用的作用副作用矩阵
- 当延迟的 API 实情可能影响 UI 映射或交互设计时，触发已治理的 `downstream_revalidation`

## 此技能不适用于

- 需求拆分
- Figma 节点映射
- 交互设计
- 服务器架构分析
- 新增业务逻辑设计
- 实现代码或任务规划

## 所需参考

- [双重实情规则](references/dual-truth-rules.md)
- [阻塞目录](references/blocker-catalog.md)
- [日志检查清单](references/logging-checklist.md)
- [检查清单](references/checklist.md)
- [API 契约映射模板](templates/api-contract-mapping-template.md)

同时应匹配宿主仓库 `.ai-delivery/requirements/` 下已建立的治理产物形态，而非创建并行的契约。

## 输入

### 必填输入

- `subreq-id`
- `requirement-slice.md`
- 可选的面向客户端 API 契约来源，如 Swagger、OpenAPI 或导出的契约文件

### 预期辅助输入

- `traceability.json`
- `status.json`
- 已有的 `decisions.md`

### 可选输入

- 显式操作列表
- API 版本提示
- 相关需求补充材料
- 仅用于定位契约证据的生成的 SDK 代码片段

### 缺失输入处理

如果某个来源或产物缺失：

- 如果 `requirement-slice.md` 缺失或仍过于模糊，则停止并将工作交还给 `requirement-breakdown`。
- 如果用户要求 API 映射但不存在可信的面向客户端 API 契约来源，则将实际缺失情况写入 `api-contract-mapping.md`，将 `traceability.json.api_contract_mapping.status` 设置为 `missing_nonblocking`，更新 `traceability.json.source_index.api`，并继续不需要 API 最终性的后续 UI 映射、Shell、本地状态、交互骨架或安全的局部开发阶段。
- 如果旧版文件夹中缺少 `traceability.json`，则仅修复当前的治理契约并在 `decisions.md` 中记录该修复；不得设计不同的 JSON 结构。
- 如果多个 Swagger、OpenAPI 或导出的 API 来源在面向客户端实情上存在分歧，则阻塞为 `blocked_api_contract_conflict`。
- 如果需求实情与 API 契约实情不一致，则阻塞为 `blocked_requirement_api_conflict`。
- 如果来源无法安全解析或验证，则阻塞为 `blocked_verification_failure`。

## 输出目标

生成下游 UI 映射、交互设计或 Spec Kit 规划可直接使用的 API 映射包。输出必须保留：

- 有来源支持的 `api-contract-mapping.md`
- 更新后的 `traceability.json.api_contract_mapping` 子树，包含状态、来源引用、操作引用、字段缺口、需求冲突、验证时机、`downstream_revalidation`、`action_side_effects`、`propagation_targets` 和 `client_semantic_gaps`
- 现有的非 API 可追溯性字段，如 `requirement_refs`、`figma_nodes`、`spec_kit_refs` 和桥接上下文
- 显式的缺失契约、字段缺口以及需求或 API 冲突
- 请求契约、响应语义、关联语义、错误映射和成功副作用的显式行为语义

## 默认输出路径

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── api-contract-mapping.md
├── traceability.json
└── decisions.md
```

## 工作流

### 1. 确认上游分解契约

- 在接触 API 材料之前，先读取 `requirement-slice.md`、`traceability.json`、`status.json` 和 `decisions.md`。
- 确认子需求范围仍与预期的 API 映射范围一致。
- 优先从 `split_ready` 状态开始，但在 API 契约材料于 UI 映射之后到达时，允许后期重新运行。

### 2. 收集并验证 API 契约证据

- 盘点所提供的 Swagger、OpenAPI、JSON、YAML 或等效契约来源。
- 优先使用仓库原生的契约文件，而非转述的笔记。
- 在有用时，使用 `jq` 等工具处理 JSON，以及使用安全的基于行的读取方式处理 YAML 或 Markdown 导出的文件。
- 忽略服务器内部实现材料，除非其改变了面向客户端的契约。

### 3. 保守地将需求点映射到 API 操作

- 仅映射 API 契约中实际体现的需求点。
- 记录精确的操作引用，如方法、路径和操作 ID（若存在）。
- 如果 API 部分覆盖了需求，则将缺口记录为"字段缺口"或"缺失契约"，而非猜测。
- 如果一个 API 操作为多个需求点服务，则明确记录该共享覆盖关系。
- 对于每个可触发 API 调用或消费其结果的用户可见操作，记录该操作级别的请求契约、响应语义、关联语义、错误映射和成功副作用。
- 区分普通的细节缺失与真正的"操作级集成阻塞器"；除非该切片的下一个安全阶段确实无法在缺少相关 API 实情的情况下继续，否则不要升级为 `blocked_*`。

### 4. 编写 `api-contract-mapping.md`

- 使用 `templates/api-contract-mapping-template.md`。
- 包含输入来源、需求到 API 映射、API 到需求映射、请求字段、响应字段、错误语义、作用副作用矩阵、缺失契约、字段缺口、需求或 API 冲突以及可追溯性更新说明。
- 保持文档事实性和契约范围性。不要将后端实现的不确定性转化为编造的面向客户端缺口。

### 5. 原地更新 `traceability.json`

- 将 `traceability.json` 视为一等治理产物，而非可丢弃的旁注。
- 仅更新 `api_contract_mapping.*`。
- 保留现有的顶层字段，如 `requirement_refs`、`figma_nodes`、`mapping_type`、`confidence`、`conflicts`、`last_verified_at` 和 `spec_kit_refs`。
- 当映射揭示了操作闭环或传播影响时，使用 `action_side_effects`、`propagation_targets` 和 `client_semantic_gaps` 更新 `traceability.json.api_contract_mapping`。
- 当延迟或变更的 API 实情可能影响 `ui-requirement-mapping` 或 `ui-interaction-design` 时，使用 `downstream_revalidation`。

### 6. 保守处理状态和阻塞

- 当未提供可信的 API 契约来源且缺失的 API 实情不会使下一个前端/设计步骤不安全时，使用 `missing_nonblocking`。
- 当来源存在但映射工作尚未完成时，使用 `pending`。
- 仅当 API 映射有可信的面向客户端契约证据支持且该阶段在端点、请求字段、响应语义、关联语义、错误映射或成功副作用方面无未解决的缺口时，才使用 `mapped`。
- 当新的或变更的 API 实情可能影响下游 UI 或交互产物时，使用 `needs_revalidation`。
- 仅当当前切片的下一个安全步骤无法进行时，才使用 `blocked_missing_api_contract`、`blocked_api_contract_conflict`、`blocked_requirement_api_conflict`、`blocked_security_or_data_risk` 或 `blocked_verification_failure`。
- 将危险的操作接线、不可逆行为确认、服务器驱动分支和完整的集成声明视为 API 缺口的主要阻塞面；默认不利用这些缺口来阻塞早期的视觉或 Shell 阶段。
- 当进入阻塞状态时，在 `status.json` 中使用 `blocked_from_status` 和 `resume_target_status` 保留恢复意图；不得通过手动编辑绕过恢复。
- 仅在可用时，将独立的管理支持界面用于治理的日志记录、阻塞处理、状态转换和产物更新。

### 7. 交接前重新审核

- 重新打开 `requirement-slice.md`、`api-contract-mapping.md` 和 `traceability.json`。
- 验证每个声明的操作、字段、错误语义、字段缺口和冲突仍与来源契约一致。
- 验证 `traceability.json` 仍保留了非 API 字段（如 `spec_kit_refs`）。
- 验证 `downstream_revalidation` 仅在实际需要时设置。
- 验证每个具有下游 UI 影响的操作都在作用副作用矩阵中有条目，或已明确标注为缺失契约实情。

## 状态与阻塞规则

- 如果不存在可信的面向客户端 API 契约来源，则记录为 `missing_nonblocking`，除非缺失使得实现不可能或造成安全/数据风险。
- 如果多个契约来源在面向客户端实情上存在分歧，则阻塞为 `blocked_api_contract_conflict`。
- 如果需求与 API 实情不一致，则阻塞为 `blocked_requirement_api_conflict`。
- 如果来源无法安全解析或验证，则阻塞为 `blocked_verification_failure`。
- 默认将缺失的端点、请求字段、响应语义、关联语义、错误映射或成功副作用视为非阻塞缺口；仅当当前切片和当前阶段无法安全推进时才升级处理。
- API 缺口通常应阻塞危险操作的实际接线、不可逆操作、服务器驱动分支或完整的交付声明，而非早期 UI 映射或安全的局部前端工作。
- 仅当结果有来源支持、经过冲突审查且在映射范围内行为语义完整时，才将 API 契约映射阶段标记为 `mapped`。

## 硬约束

- 在接触 API 材料之前，先读取 `requirement-slice.md`。
- 仅在 `.ai-delivery/requirements/` 内工作。
- 不得将工作流实情移至 `ai-delivery-admin`。
- 不得用旁注或第二个桥接产物替换 `traceability.json`。
- 不得覆盖非 API 可追溯性字段。

## 输出标准

每个 API 映射必须包含：

- 有来源支持的契约清单
- 需求到 API 映射
- API 到需求映射
- 请求和响应字段覆盖率
- 错误语义
- 作用副作用矩阵
- 缺失契约
- 字段缺口
- 需求或 API 冲突
- 可追溯性更新说明

如果治理的管理支持不可用，则将产物实情保留在 `.ai-delivery/` 中，并在本地记录缺失的治理依赖项，且不设计替代的实情存储。

## 自查清单

在报告完成之前，确认所有以下事项：

- [ ] 在接触 API 材料之前已读取 `requirement-slice.md`
- [ ] 仅使用了可信的面向客户端契约证据
- [ ] 没有将服务器内部实现细节误分类为面向客户端的缺口
- [ ] 已编写 `api-contract-mapping.md`
- [ ] 已更新 `traceability.json.api_contract_mapping`，且未覆盖其他可追溯性字段
- [ ] "作用副作用矩阵"为每个映射的操作捕获了请求契约、成功返回语义、本地状态影响和重新验证目标
- [ ] `downstream_revalidation` 仅在合理时设置
- [ ] 阻塞时选择了范围最窄的阻塞器
- [ ] 任何 `blocked_*` 结果均基于该切片的下一个安全阶段而非整个需求进行论证
- [ ] 现有的桥接字段（如 `spec_kit_refs`）已保留

## 压力场景

### 场景 1：用户调用此技能，但实际上没有可用的 Swagger 或 OpenAPI 来源

预期行为：

- 完成治理记录，不编造端点
- 将 `traceability.json.api_contract_mapping.status` 设置为 `missing_nonblocking`
- 使用缺失契约记录更新 `traceability.json.source_index.api`
- 保持 UI 映射和其他安全的非集成阶段可运行
- 不得根据需求文本编造端点

### 场景 2：需求清晰，但 API 契约不完整

预期行为：

- 编写可用的操作映射
- 记录"字段缺口"或"缺失契约"
- 不得将部分覆盖视为完全覆盖
- 不得阻塞无关的 UI 优先工作，除非缺失的 API 实情阻止了该切片的下一个安全阶段

### 场景 3：API 契约在 UI 映射完成后才到达

预期行为：

- 更新 `traceability.json.api_contract_mapping`
- 当新的 API 实情可能影响 UI 或交互产物时，设置 `needs_revalidation`
- 不得覆盖 Figma 或交互字段

### 场景 4：两个契约导出文件不一致

预期行为：

- 阻塞为 `blocked_api_contract_conflict`
- 捕获冲突证据
- 止步于 `mapped` 状态之前

## 交接

在生成 `api-contract-mapping.md`、更新 `traceability.json.api_contract_mapping` 并通过自查后停止。

如果用户希望继续，则将下游阶段所需的 `requirement-slice.md`、`api-contract-mapping.md`、`traceability.json` 及 `decisions.md` 中的任何映射相关说明交接出去。除非用户明确要求进入下一阶段，否则不得在此技能内部执行 UI 映射、交互设计或实现规划。
