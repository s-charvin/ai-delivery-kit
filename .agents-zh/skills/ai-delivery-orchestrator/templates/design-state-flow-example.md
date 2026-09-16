# 通用 MVI 状态流示例

本示例是复杂状态流切片可复用的完整 `design.md` 形态。必须按当前需求适配其
事实与 ID，绝不能把示例行为复制成项目事实。

> 语言边界：本文件是中文参考。输出到其他语言时，标题、表头/单元格、解释性句子，以及 Mermaid 节点、连线和参与者标签都必须改为用户当前对话语言；机器语法、ID、代码/API/库/协议名称和必要技术标识保持原样。

## 上下文与范围

示例描述一个已认证提交流程，不包含账号创建和后台同步。

<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## 行为边界

已认证用户编辑、提交、取消或重试一份草稿。失败保留输入，过期结果被忽略。

<!-- ai-delivery:behavior-contract:behavior -->
## 行为契约

| 行为 ID | Given | When | Then | 边界 / 失败行为 |
|---------|-------|------|------|-----------------|
| B-001 | 有效可编辑草稿 | 用户提交 | 只有一个 active request 拥有可见提交中状态 | 重复输入去重，过期结果忽略 |
| B-002 | 存在 active submission | 请求失败或取消 | 草稿保留输入并回到编辑 | 只有失败发出一次性 Effect |

<!-- ai-delivery:behavior-contract:acceptance -->
## 验收契约

| 验收 ID | 可验证结果 | 证据或命令 |
|---------|------------|------------|
| AC-001 | B-001 只接受 active correlation result | 聚焦 reducer 与 command 测试 |
| AC-002 | B-002 保留输入且 UiEffect 只消费一次 | 聚焦 projection 与恢复测试 |

<!-- ai-delivery:behavior-contract:traceability -->
## 行为追踪

| 行为 ID | 需求来源 | UI scenario | 验收 ID |
|---------|----------|-------------|---------|
| B-001 | REQ-SUBMIT | SC-SUBMIT | AC-001 |
| B-002 | REQ-SUBMIT | SC-FAILURE | AC-002 |
<!-- ai-delivery:behavior-contract:end -->

## 方案设计

状态持有者拥有领域与操作状态；纯投影产生 `UiState`，Effect host 消费一次性
`UiEffect`。副作用在 reducer 外执行，并返回带 correlation 的结果事件。

<!-- ai-delivery:state-flow:start -->
<!-- ai-delivery:state-flow:taxonomy -->
## 状态所有权
| 状态集合 | 所有者 | 事实源 | 生命周期 | 持久化 / 恢复 |
|----------|--------|--------|----------|---------------|
| 领域状态（Domain state） | 状态存储（Store） | 仓储结果（Repository result） | 持久 | 从仓储恢复 |
| 操作状态（Operation state） | 状态存储（Store） | 命令生命周期（Command lifecycle） | 短暂 | 恢复时重置 |
| 本地输入状态（Local input state） | 视图模型（View model） | 用户输入 | 页面 | 仅按明确要求恢复 |
| UiState | 投影函数 | 纯投影 | 派生 | 不持久化 |
| UiEffect | Effect 宿主（Effect host） | 归约器（Reducer）输出 | 一次性 | 不持久化 |

<!-- ai-delivery:state-flow:mvi-loop -->
## MVI 闭环
```mermaid
flowchart LR
  V[视图] -->|SubmitIntent| R[归约器（Reducer）]
  R -->|提交中 + SubmitCommand| S[状态持有者]
  S -->|UiState| V
  R -->|SubmitCommand| E[副作用执行器]
  E -->|SubmitSucceeded / SubmitFailed| R
  R -->|ShowMessage| X[UiEffect 宿主]
```

<!-- ai-delivery:state-flow:lifecycle -->
## 生命周期
```mermaid
stateDiagram-v2
  state "编辑中" as Editing
  state "提交中" as Submitting
  state "已提交" as Submitted
  [*] --> Editing: T-001 打开
  Editing --> Submitting: T-002 提交
  Submitting --> Submitted: T-003 成功
  Submitting --> Editing: T-004 失败 / 重试
  Submitting --> Editing: T-005 取消
  Submitted --> [*]
```

<!-- ai-delivery:state-flow:projection -->
## 投影
`UiState = project(DomainState, OperationState, LocalInputState)`

| 投影 ID（Projection ID） | 条件 | 可见 UI | 交互 |
|---------------|------|---------|------|
| P-001 | 编辑中 + 输入有效 | 启用提交 | 编辑和提交 |
| P-002 | 提交中 | 进度和锁定的提交 | 取消 |
| P-003 | 编辑中 + 失败 | 错误提示和重试 | 编辑和重试 |

<!-- ai-delivery:state-flow:matrix -->
## 转换矩阵
| 转换 ID（Transition ID） | 起点 | 意图 / 事件 | 守卫条件 | 决策 | 终点 | 命令（Command） | 结果事件（Result event） |
|---------------|------|----------------|-------|----------|----|---------|--------------|
| T-001 | none | 打开 | 已认证 | 创建草稿 | Editing | none | none |
| T-002 | Editing | SubmitIntent | 输入有效 | 标记为提交中 | Submitting | SubmitCommand(id) | SubmitSucceeded / SubmitFailed |
| T-003 | Submitting | SubmitSucceeded(id) | 当前请求 ID 匹配 | 提交领域结果 | Submitted | none | none |
| T-004 | Submitting | SubmitFailed(id) | 当前请求 ID 匹配 | 保留输入并展示失败 | Editing | none | none |
| T-005 | Submitting | CancelIntent | 命令可取消 | 使 active id 失效 | Editing | CancelCommand(id) | Cancelled(id) |

<!-- ai-delivery:state-flow:sequences -->
## 异步时序
```mermaid
sequenceDiagram
  participant V as 视图
  participant R as 归约器（Reducer）
  participant E as 副作用执行器
  participant API as API
  V->>R: T-002 提交意图（SubmitIntent）
  R->>E: SubmitCommand(id)
  E->>API: 请求
  API-->>E: 响应
  E-->>R: T-003 或 T-004 结果（result(id)）
  R-->>V: UiState 或 ShowMessage
```

<!-- ai-delivery:state-flow:invariants -->
## 不变量
<!-- ai-delivery:state-flow:stale-result -->
- 不匹配 active correlation ID 的结果视为过期并忽略。
<!-- ai-delivery:state-flow:concurrency -->
- 并发提交使用 request ID 去重，以 active request 为准。
- 相同 request ID 的提交必须幂等。
- 失败不能清除用户输入。
- UiEffect 只消费一次，恢复 UiState 时不能重新构造。

<!-- ai-delivery:state-flow:traceability -->
## 追踪
| ID | 需求 | 场景 | 测试 |
|----|------|------|------|
| T-002 / P-002 | REQ-SUBMIT | SC-SUBMIT | test/submit_test.dart |
<!-- ai-delivery:state-flow:end -->

<!-- ai-delivery:user-decisions -->
## 用户决策

`not_applicable`：治理证据已确定示例行为，没有待用户选择的实质产品、资源或体验决策。

## 风险与验证

- 验证重复提交、取消、过期成功/失败、恢复和 Effect 单次消费。
- 验证 reducer 保持纯函数，恢复状态不重放历史 `UiEffect`。
