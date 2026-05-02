<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# API 契约映射

## 输入契约来源

### 来源项 1

- `source_type`: `swagger | openapi | json | yaml | other`
- `source_path_or_ref`:
- `version_or_revision`:
- `scope_notes`:
- `validation_status`:

## 需求到 API 映射

### 映射项 1

- `requirement_point`:
- `source_ref`:
- `operation_refs`:
- `coverage`: `covered | partial | not_covered`
- `notes`:

## API 到需求映射

### 操作项 1

- `method`:
- `path`:
- `operation_id`:
- `mapped_requirement_points`:
- `notes`:

## 请求字段

### 请求项 1

- `operation_ref`:
- `field_path`:
- `field_type`:
- `required`:
- `semantics`:
- `requirement_basis`:

## 响应字段

### 响应项 1

- `operation_ref`:
- `field_path`:
- `field_type`:
- `semantics`:
- `requirement_basis`:

## 错误语义

### 错误项 1

- `operation_ref`:
- `status_or_code`:
- `surface`:
- `meaning`:
- `requirement_basis`:

## 作用副作用矩阵

### 操作项 1

- `action_id`:
- `operation_ref`:
- `request_contract`:
- `success_return_semantics`:
- `error_semantics`:
- `local_state_effect`:
- `upstream_downstream_propagation_expectation`:
- `revalidation_targets`:

## 缺失契约

- `missing_contract`:
- `why_missing`:
- `affected_requirement_points`:

## 字段缺口

### 缺口项 1

- `location`:
- `gap_type`: `field_gap | semantic_gap`
- `needed_additions`:
- `affected_requirement_points`:

## 需求/API 冲突

### 冲突项 1

- `issue`:
- `requirement_ref`:
- `api_ref`:
- `impact`:
- `resolution_path`:

## 可追溯性更新说明

- `status`:
- `source_refs_handling`:
- `source_index_update`: `traceability.json.source_index.api`
- `operation_refs_handling`:
- `action_side_effects`:
- `propagation_targets`:
- `client_semantic_gaps`:
- `downstream_revalidation`:

---

## 模板编写规则

1. `api-contract-mapping.md` 是一个子需求的可读治理级 API 映射契约。
2. 仅记录面向客户端的接口实情。不得分析服务器内部实现。
3. 应同时显式列出"需求到 API 映射"和"API 到需求映射"，以便缺口和越界可见。
4. 如果 API 契约缺少字段或语义，将其记录在"字段缺口"或"缺失契约"下，而非猜测。
5. 如果需求与 API 不一致，将问题记录在"需求/API 冲突"下，并在需要时阻塞。
6. "可追溯性更新说明"应解释写入 `traceability.json.api_contract_mapping` 的内容。
7. 不得将"模板编写规则"或"模板示例"部分复制到生成的产物中。

## 模板示例

```md
# API Contract Mapping

## Input Contract Sources
### Source Item 1
- `source_type`: `openapi`
- `source_path_or_ref`: `contracts/profile-settings.openapi.yaml`
- `version_or_revision`: `2026-04-06`
- `scope_notes`: `涵盖个人资料设置更新端点。`
- `validation_status`: `parsed`

## Requirement To API Mapping
### Mapping Item 1
- `requirement_point`: `用户可以从设置中重命名项目。`
- `source_ref`: `requirement.md#L12-L15`
- `operation_refs`: `PATCH /projects/{projectId}`
- `coverage`: `partial`
- `notes`: `端点存在但未直接暴露保存门控语义。`

## API To Requirement Mapping
### Operation Item 1
- `method`: `PATCH`
- `path`: `/projects/{projectId}`
- `operation_id`: `updateProject`
- `mapped_requirement_points`: `从设置中重命名项目`
- `notes`: `重命名操作不需要单独的端点。`

## Request Fields
### Request Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `field_path`: `body.name`
- `field_type`: `string`
- `required`: `true`
- `semantics`: `新项目名称`
- `requirement_basis`: `requirement.md#L12-L15`

## Response Fields
### Response Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `field_path`: `response.name`
- `field_type`: `string`
- `semantics`: `更新后的项目名称`
- `requirement_basis`: `requirement.md#L12-L15`

## Error Semantics
### Error Item 1
- `operation_ref`: `PATCH /projects/{projectId}`
- `status_or_code`: `409`
- `surface`: `内联验证或 toast`
- `meaning`: `名称冲突`
- `requirement_basis`: `待解答问题`

## Action Side Effects Matrix
### Action Item 1
- `action_id`: `rename-project-submit`
- `operation_ref`: `PATCH /projects/{projectId}`
- `request_contract`: `body.name 必须携带提议的项目名称。`
- `success_return_semantics`: `响应返回更新后的项目名称负载。`
- `error_semantics`: `409 表示名称冲突；通用 500 对于重试 UX 仍欠规范。`
- `local_state_effect`: `成功后，当前项目名称应在活跃屏幕状态中更新。`
- `upstream_downstream_propagation_expectation`: `任何显示项目标题的其他载体应刷新或消费更新后的负载。`
- `revalidation_targets`: `ui-interaction-design, delivery-slice synthesis`

## Missing Contracts
- `missing_contract`: `无专用的验证预览端点`
- `why_missing`: `需求提到了禁用保存逻辑，但契约未暴露额外的服务器验证细节。`
- `affected_requirement_points`: `保存门控`

## Field Gaps
### Gap Item 1
- `location`: `PATCH /projects/{projectId} response`
- `gap_type`: `semantic_gap`
- `needed_additions`: `澄清未更改的名称返回无操作响应还是验证错误。`
- `affected_requirement_points`: `保存门控`

## Requirement/API Conflicts
### Conflict Item 1
- `issue`: `需求期望可重试的错误语义，但 API 契约仅暴露了通用 500。`
- `requirement_ref`: `requirement.md#L17-L18`
- `api_ref`: `contracts/profile-settings.openapi.yaml#/paths/...`
- `impact`: `交互和错误表面决策无法安全完成。`
- `resolution_path`: `阻塞并请求澄清面向客户端的错误语义。`

## Traceability Update Notes
- `status`: `mapped | missing_nonblocking | pending | needs_revalidation | blocked_*`
- `source_refs_handling`: `已在 traceability.json.api_contract_mapping.source_refs 中记录`
- `source_index_update`: `已在 traceability.json.source_index.api 中记录`
- `operation_refs_handling`: `已在 traceability.json.api_contract_mapping.operation_refs 中记录`
- `action_side_effects`: `已在 traceability.json.api_contract_mapping.action_side_effects 中记录`
- `propagation_targets`: `已在 traceability.json.api_contract_mapping.propagation_targets 中记录`
- `client_semantic_gaps`: `已在 traceability.json.api_contract_mapping.client_semantic_gaps 中记录`
- `downstream_revalidation`: `ui-requirement-mapping, ui-interaction-design`
```
