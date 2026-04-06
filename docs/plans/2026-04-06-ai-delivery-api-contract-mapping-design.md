# AI Delivery API Contract Mapping Design

## Goal

在现有 `requirement-breakdown -> ui-requirement-mapping -> ui-interaction-design` 主链路中，引入一个可选但受治理的 `api-contract-mapping` 阶段，用来处理 Swagger / OpenAPI / 导出接口协议等 client-facing 接口材料，并把接口契约映射沉淀为标准 Markdown 产物和 `traceability.json` 的机器可消费摘要。

## Problem

当前 `requirement-breakdown` skill 对接口协议只停留在“可选输入”的表述层，没有形成：

- 独立的接口映射阶段
- 标准化的人读产物
- 可并行或补跑的协议处理规则
- 对 `traceability.json` 的字段所有权约束
- 对 `ai-delivery-admin` 的 schema / artifact / UI 适配

这会导致以下问题：

- 即便用户提供了 Swagger / OpenAPI，skill 也没有固定落点
- API 晚到时只能靠人工补记，无法治理式补跑
- UI mapping 与 API mapping 可能抢写 `traceability.json`
- 管理面无法清晰展示“需求 -> API -> UI -> Interaction -> Spec Kit”的链路

## Workflow Position

推荐链路：

- `requirement-breakdown -> api-contract-mapping -> ui-requirement-mapping -> ui-interaction-design`

但本设计不把 API 材料缺失视为默认全局阻塞。具体规则：

- 如果没有提供接口协议，`requirement-breakdown` 仍可继续
- 如果后续补充了 Swagger / OpenAPI，可单独补跑 `api-contract-mapping`
- 如果 API 和 UI 材料都已齐备，允许 `api-contract-mapping` 与 `ui-requirement-mapping` 并行
- 并行前提是两者只更新自己拥有的 `traceability.json` 子树或字段

## New Skill

新增独立 skill：

- `api-contract-mapping`

职责：

- 读取 `requirement-slice.md`、`traceability.json`、`status.json`、`decisions.md`
- 识别并验证 Swagger / OpenAPI / 导出接口协议等 client-facing contract evidence
- 生成 `api-contract-mapping.md`
- 更新 `traceability.json.api_contract_mapping`
- 记录字段缺口、接口缺失、需求/接口冲突、下游重校验信号

非职责：

- 不推断后端内部实现
- 不补设计
- 不重写 requirement truth
- 不覆盖 Figma/UI 追踪字段
- 不把服务端内部不确定性伪装成 client-facing contract gap

## Responsibility Boundary Changes

### requirement-breakdown

保留职责：

- 拆分子需求
- 提取全局规则
- 生成 requirement-level 与 sub-requirement-level 受治理产物

新增职责：

- 识别是否提供 API contract 输入
- 在 `traceability.json` 中初始化 `api_contract_mapping`
- 在 `README.md` / `requirement-slice.md` / `decisions.md` 里保留最小接口依赖事实，不做详细协议映射

移除的隐式职责：

- 不再承担详细接口服务映射
- 不再把 API coverage 表述零散塞进现有文档而没有专门产物

### ui-requirement-mapping

保留职责：

- 基于结构化设计证据写 `figma-mapping.md`
- 更新 Figma/UI 相关 traceability 字段

新增要求：

- 读取 `traceability.json.api_contract_mapping`
- 当 `downstream_revalidation` 明确要求时，在 `decisions.md` 记录重校验结果或待重校验事实
- 不覆盖 `api_contract_mapping.*`

### ui-interaction-design

保留职责：

- 编写 `interaction-design.md`

新增要求：

- 将 `api_contract_mapping.downstream_revalidation` 视为输入之一
- 如果接口契约变化影响交互状态、错误反馈或字段行为，需要记录重校验结论

## Human-Readable Artifact

新增标准产物：

- `api-contract-mapping.md`

位置：

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/api-contract-mapping.md
```

作用：

- 作为人读、审计、交接用的接口契约映射文档
- 保留协议来源、映射依据、字段缺口、错误语义和冲突
- 在 `traceability.json` 之外承载完整上下文，避免把 JSON 变成难维护的大文档

推荐章节：

- `Input Contract Sources`
- `Requirement To API Mapping`
- `API To Requirement Mapping`
- `Request Fields`
- `Response Fields`
- `Error Semantics`
- `Missing Contracts`
- `Field Gaps`
- `Requirement/API Conflicts`
- `Traceability Update Notes`

## Machine-Readable Contract

`traceability.json` 保持现有顶层字段兼容：

- `requirement_refs`
- `figma_nodes`
- `mapping_type`
- `confidence`
- `conflicts`
- `last_verified_at`
- `spec_kit_refs`

新增独立子树：

```json
{
  "api_contract_mapping": {
    "status": "not_provided | pending | mapped | needs_revalidation | blocked_*",
    "source_refs": [],
    "operation_refs": [],
    "field_gaps": [],
    "requirement_conflicts": [],
    "last_verified_at": null,
    "downstream_revalidation": {
      "recommended_targets": [],
      "reason": null,
      "triggered_at": null
    }
  }
}
```

字段约束：

- `requirement-breakdown` 只负责初始化
- `api-contract-mapping` 独占更新 `api_contract_mapping.*`
- `ui-requirement-mapping` 与 `ui-interaction-design` 只消费，不覆盖

## Status And Blockers

### API Contract Mapping Status

- `not_provided`: 未提供接口协议
- `pending`: 已提供协议但尚未完成映射
- `mapped`: 当前协议映射完成
- `needs_revalidation`: 协议晚到或变化，需下游重校验
- `blocked_*`: 安全推进失败

### New Blockers

新增 blocker：

- `blocked_missing_api_contract`
- `blocked_api_contract_conflict`
- `blocked_requirement_api_conflict`

复用 blocker：

- `blocked_verification_failure`
- `blocked_missing_requirement`

原则：

- 只在无法安全推进接口映射时进入 `blocked_*`
- API 晚到本身不默认阻塞整个子需求主状态机

## Parallel And Late-Arrival Rules

### Late Arrival

如果 `requirement-breakdown` 时没有 API 文档：

- `traceability.json.api_contract_mapping.status = not_provided`
- 不阻塞 UI mapping
- 后续补充协议后可以单独运行 `api-contract-mapping`

### Parallel Mapping

如果 API 与 UI 材料同时齐备：

- 允许 `api-contract-mapping` 与 `ui-requirement-mapping` 并行
- 两者只更新各自拥有字段
- 双方都可以在 `decisions.md` 记录事实性说明，但不能覆盖对方结论

### Downstream Revalidation

当 API 结论影响已有 UI / interaction：

- `api_contract_mapping.status = needs_revalidation`
- `downstream_revalidation.recommended_targets` 记录建议重校验阶段
- `downstream_revalidation.reason` 记录触发原因
- `downstream_revalidation.triggered_at` 记录时间

## Codex Repository Changes

需要修改：

- `requirement-breakdown` skill、reference、template、validator
- 新增 `api-contract-mapping` skill 包
- 更新 `ui-requirement-mapping` / `ui-interaction-design` 的输入说明与 handoff
- 更新 `.ai-delivery/requirements/example-requirement` fixture
- 更新 shell validator 和 contract tests
- 更新 onboarding / full-chain docs

## ai-delivery-admin Changes

需要适配：

- shared schema：允许 `traceability.json.api_contract_mapping`
- artifact schema：识别 `api-contract-mapping.md`
- bootstrap / artifact write / read adapters：支持新产物与新字段
- web types / traceability UI / artifact preview：展示 API Contract stage
- MCP / route / write surfaces：在保持兼容的前提下接受新 contract

## Validation Strategy

### Skill Validation

- `validate-project-ai-delivery-skills.sh` 验证新 skill 包
- 校验 `api-contract-mapping.md`、`traceability.json`、Swagger/OpenAPI 关键词、`downstream_revalidation`

### Fixture And Contract Validation

- `example-requirement` fixture 新增 `api-contract-mapping.md`
- `traceability.json` fixture 新增 `api_contract_mapping`

### Runtime Validation

- 无 API 文档时主链路仍可通过
- 补跑 API skill 后可写入 `needs_revalidation`
- UI/Figma 相关写操作不会覆盖 API 子树

### Admin Validation

- schema 测试通过
- read/write API 能识别新 artifact 和新 traceability 子树
- Traceability UI 能展示 API 阶段

## Rollout Result

改造完成后，AI delivery workflow 将从：

- `Requirement -> UI -> Interaction -> Spec Kit`

升级为：

- `Requirement -> API Contract (optional but governed) -> UI -> Interaction -> Spec Kit`

并且：

- 不破坏现有 `traceability.json` 顶层兼容性
- 支持 API 晚到的补跑
- 支持 API 与 UI 并行推进
- 让 `ai-delivery-admin` 能完整感知新的链路阶段
