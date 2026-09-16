<!-- ai-delivery-meta: {"version":3,"artifact_type":"design-contract","layout_key":"solution_design","canonical_path":"design.md","updated_at":"<ISO8601>","updated_by":"<agent>"} -->
<!-- ai-delivery-template-language
实例化时保留 ai-delivery-meta 机器键，仅替换时间戳与作者。语言边界：所有人类可读标题、表格和正文使用用户当前对话语言；机器 key、enum、ID、路径、命令、代码符号和协议 token 保持不变。完成后删除本注释。
-->

# 设计契约：{{subreq_id}}

> 本文件是 `{subreq_id}` 唯一持久化的行为与方案设计契约，不是执行计划或文件级任务清单。`status.json` 的评审只对本文件精确 SHA-256 有效。

## 1. 上下文与范围

### 目标
（用户可见或系统可观察的结果。）

### 范围内
- ...

### 范围外
- ...

### 约束与既有权威
- 需求来源：...
- 既有架构/API/项目规则：...
- 启用 UI truth 时：`contracts/ui-truth-index.json`

<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## 2. 行为边界

（明确 actor、输入、输出、排除项、权限、数据所有权和失败边界。）

<!-- ai-delivery:behavior-contract:behavior -->
## 3. 行为契约

| 行为 ID | Given | When | Then | 边界 / 失败行为 |
|---------|-------|------|------|-----------------|
| B-001 | ... | ... | ... | ... |

<!-- ai-delivery:behavior-contract:acceptance -->
## 4. 验收契约

| 验收 ID | 可验证结果 | 证据或命令 |
|---------|------------|------------|
| AC-001 | ... | ... |

<!-- ai-delivery:behavior-contract:traceability -->
## 5. 追踪

| 行为 ID | 需求来源 | UI scenario | 验收 ID |
|---------|----------|-------------|---------|
| B-001 | ... | `not_applicable` / ... | AC-001 |
<!-- ai-delivery:behavior-contract:end -->

## 6. 方案设计

### 架构与数据流
（只写与实现相关的边界、所有权、数据流、导航和集成契约，不写机械步骤。）

### 关键决策
| 决策 | 选择 | 理由与权衡 |
|------|------|------------|
| ... | ... | ... |

### UI 场景引用

启用 UI truth 时引用每个索引 scenario，不重复 Runtime Coverage Plan。

| Unit ID | 场景 IDs | 实现职责 | 验证归属 |
|---------|--------------|----------|----------|
| `not_applicable` / ... | ... | ... | ... |

## 7. 状态流

状态流深度：`not_applicable` / `simple` / `complex`。

真正静态时记录理由；简单流程只填写下面的紧凑状态表。`state_flow_required=true`
仅用于实质改变复杂 guard、并发、过期结果、恢复、持久化或跨表面状态所有权；
此时用适配后的 `design-state-flow-example.md` 替换本小节。

<!-- ai-delivery:state-summary -->
| 转换 ID | 起点 | 事件 / 意图 | Guard | 终点 | UI 结果 / Effect | 失败或恢复 | 验收 |
|---------|------|-------------|-------|------|------------------|------------|------|
| T-001 | ... | ... | ... | ... | ... | ... | AC-001 |

<!-- ai-delivery:user-decisions -->
## 8. 用户决策

当前设计版本包含决策权属于用户的实质产品、行为、资源或体验选择时，设置
`status.json.user_decision_required=true`。当前版本获批后仍保持 `true`；有效的
hash-bound human `design_review` 表示决策已解决。只有当前版本不再包含用户
授权决策时才设为 `false`。技术复杂度不是用户决策。

| 决策 ID | 问题 | 选项与权衡 | 结论 |
|---------|------|------------|------|
| `not_applicable` / D-001 | ... | ... | ... |

## 9. 风险与验证说明

| 风险 | 影响 | 缓解 / 验证 |
|------|------|-------------|
| ... | ... | ... |

改变范围、行为、状态、资源、体验或验收的未决问题必须表示为用户决策。执行
顺序、完成项、待办、阻塞和验证结果属于 `progress.md`。
