# API 契约映射检查清单

- 确认 `requirement-slice.md` 存在且足够清晰以进行映射
- 确认已首先读取 `traceability.json`、`status.json` 和 `decisions.md`
- 在将 API 契约来源视为输入之前，验证其是否存在
- 仅盘点面向客户端的契约证据，如端点、字段、状态值、分页和错误语义
- 验证关联语义和成功副作用，而不仅仅是端点是否存在
- 忽略服务器内部实现细节，除非其改变了面向客户端的契约
- 编写 `api-contract-mapping.md`
- 包含作用副作用矩阵，含请求契约、成功返回语义、错误语义、本地状态影响和重新验证目标
- 仅更新 `traceability.json.api_contract_mapping`
- 当契约揭示了下游状态影响时，更新 `action_side_effects`、`propagation_targets` 和 `client_semantic_gaps`
- 保留现有的 `spec_kit_refs`、`figma_nodes` 及其他非 API 可追溯性字段
- 当 API 结论可能影响 UI 映射或交互设计时，标记 `downstream_revalidation`
- 在遇到 `blocked_missing_api_contract`、`blocked_api_contract_conflict`、`blocked_requirement_api_conflict` 或 `blocked_verification_failure` 时停止
- 当端点、请求字段、响应语义、关联语义、错误映射或成功副作用缺失时，选择阻塞而非猜测
- 不得编造端点、字段或错误行为
