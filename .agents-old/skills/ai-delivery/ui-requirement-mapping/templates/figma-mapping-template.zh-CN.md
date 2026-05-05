<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# Figma 映射

## 设计目标

- `design_source`:
- `design_source_id`:
- `requested_scope`:
- `provider_candidates`:
- `cache_root`:

## 结构化证据来源

### 证据项 1

- `provider`:
- `artifact_type`:
- `artifact_ref`:
- `raw_payload_ref`:
- `node_ids`:
- `freshness_or_version`:
- `why_trusted`:
- `optional_preview_ref`:

## 需求到节点映射

### 映射项 1

- `requirement_point`:
- `provider`:
- `node_ids`:
- `artifact_refs`:
- `evidence_basis`:
- `confidence`:

## 节点到需求映射

### 节点项 1

- `provider`:
- `node_id`:
- `artifact_ref`:
- `requirement_points`:
- `mapping_type`:

## 必需 UI

- `item`:
- `provider`:
- `node_ids`:
- `artifact_refs`:

## 配套 UI

- `item`:
- `why_needed`:
- `provider`:
- `node_ids`:
- `artifact_refs`:

## 共享节点

- `node_or_region`:
- `provider`:
- `shared_with`:
- `artifact_refs`:

## 可执行屏幕状态

### 屏幕状态 1

- `screen_state_id`:
- `state_type`:
- `executable_node_id`:
- `parent_shell_node_id`:
- `required_get_code_artifact_refs`:
- `notes`:

## 缺失的设计证据

- `requirement_point`:
- `missing_evidence`:
- `attempted_providers`:
- `notes`:

## 冲突

- `conflict`:
- `providers_or_artifacts`:
- `impact`:
- `resolution_path`:

## 可追溯性更新备注

- `preserved_fields`:
- `changed_fields`:
- `provider_or_evidence_refs_handling`:

## 映射就绪判定

- `status`: `ready_for_acceptance_contract | blocked_missing_state_code | blocked_missing_visual_truth`
- `blocking_reasons`:
- `next_gate`: `ui-acceptance-contract | requirement-breakdown | blocked`

---

## 模板编写规则

1. `figma-mapping.md` 是下游交互设计和实现的受治理映射契约。它必须有证据支持，而非以截图为主导。
2. 每个映射的需求点应注明 `provider`、相关的 `node_ids` 以及一个或多个原始 `artifact_ref` 值。
3. `raw_payload_ref` 应指向缓存的提供商产物，而非转述摘要。
4. 由 `artifact_ref` 引用的缓存产物应保留当前管理员读取器所需的兼容性元数据以及提供商感知的原始负载字段。
5. 使用 `why_trusted` 和 `evidence_basis` 解释为何结构化负载足以支持映射声明。
6. `optional_preview_ref` 仅为可选的支持性上下文。切勿将其作为完成标准依赖。
7. 如果多个提供商存在分歧，请在"冲突"下记录分歧，而非静默选择其中一种解释。
8. 不要将"模板编写规则"或"模板示例"部分复制到生成的映射产物中。

## 模板示例

```md
# Figma 映射

## 设计目标
- `design_source`: `Figma file`
- `design_source_id`: `abc123`
- `requested_scope`: `Profile Settings edit form`
- `provider_candidates`: `figma-mcp, tempad-dev`
- `cache_root`: `.ai-delivery/figma-cache/abc123/`

## 结构化证据来源
### 证据项 1
- `provider`: `figma-mcp`
- `artifact_type`: `node`
- `artifact_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `raw_payload_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `node_ids`: `987:654`
- `freshness_or_version`: `verified against current file version`
- `why_trusted`: `The payload includes node type, hierarchy, text label, disabled variant, and parent frame context.`
- `optional_preview_ref`: `.ai-delivery/figma-cache/abc123/artifacts/preview-profile-save-button.json`

## 需求到节点映射
### 映射项 1
- `requirement_point`: `Save remains disabled until there is a valid change.`
- `provider`: `figma-mcp`
- `node_ids`: `987:654`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `evidence_basis`: `Structured node payload shows disabled save button variant under the edit form state.`
- `confidence`: `high`

## 节点到需求映射
### 节点项 1
- `provider`: `figma-mcp`
- `node_id`: `987:654`
- `artifact_ref`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`
- `requirement_points`: `Save remains disabled until there is a valid change.`
- `mapping_type`: `direct`

## 必需 UI
- `item`: `Disabled save button state`
- `provider`: `figma-mcp`
- `node_ids`: `987:654`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-save-button.json`

## 配套 UI
- `item`: `Form field dirty-state container`
- `why_needed`: `The button state is only meaningful inside the form state carrier.`
- `provider`: `figma-mcp`
- `node_ids`: `987:610`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-form.json`

## 共享节点
- `node_or_region`: `Profile header shell`
- `provider`: `figma-mcp`
- `shared_with`: `profile-settings-shell`
- `artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-shell.json`

## 可执行屏幕状态
### 屏幕状态 1
- `screen_state_id`: `profile-settings-edit-idle`
- `state_type`: `idle`
- `executable_node_id`: `987:610`
- `parent_shell_node_id`: `987:500`
- `required_get_code_artifact_refs`: `.ai-delivery/figma-cache/abc123/artifacts/node-profile-form-code.json`
- `notes`: `The top-level section narrowed scope, but the executable state is the edit-form frame plus its state carrier.`

## 缺失的设计证据
- `requirement_point`: `Retryable avatar upload failure`
- `missing_evidence`: `No explicit error-state node was found in current structured payloads.`
- `attempted_providers`: `figma-mcp, tempad-dev`
- `notes`: `Block or hand back if the failure state is required for mapping completeness.`

## 冲突
- `conflict`: `TemPad Dev and Figma MCP disagree on whether the disabled save button is a separate variant node or a state inside the parent component.`
- `providers_or_artifacts`: `figma-mcp node-profile-save-button.json; tempad-dev component-save-button.json`
- `impact`: `Could change executable-node granularity.`
- `resolution_path`: `Do not finalize until the executable node boundary is resolved.`

## 可追溯性更新备注
- `preserved_fields`: `requirement_refs, spec_kit_refs`
- `changed_fields`: `figma_nodes, confidence, last_verified_at`
- `provider_or_evidence_refs_handling`: `Provider-specific refs remain in figma-mapping.md because traceability.json does not yet define provider-aware evidence fields.`

## 映射就绪判定
- `status`: `ready_for_acceptance_contract`
- `blocking_reasons`: `none`
- `next_gate`: `ui-acceptance-contract`
```
