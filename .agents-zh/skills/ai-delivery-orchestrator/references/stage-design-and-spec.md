# Stage 3：设计契约

Stage 3 只产出一份 canonical `design.md` 行为与方案设计契约。外部框架可
提供推理方法，但不得新增持久化的 `spec.md`、`plan.md` 或 `tasks.md`。
具体适配见 [framework-adaptation.md](framework-adaptation.md)。

调用框架前必须执行产物边界协议：传入 canonical `design.md` 路径，把框架
目录视为只读输入；无法遵守路径的持久化步骤必须跳过。

## 何时执行

- `ui_truth_mode=none|existing`：`split_ready` 后执行。
- `ui_truth_mode=figma|runtime-baseline`：`acceptance_frozen` 后执行。
- `design.md` hash 变化或评审证据过期时重新执行。

具有当前有效评审且依赖就绪的 `design_ready` 切片直接进入 `implement`，
不等待无依赖的其他切片。

## 输入

- `requirement-slice.md`、全局规则、依赖图和来源引用
- 可用的 API / 协议证据及现有项目架构
- 启用 UI truth 时，Stage 2 冻结组件和当前 v3 `ui-truth-index.json`

仅在 `state_flow_required=true` 时按需读取
`templates/design-state-flow-example.md`，不得把示例行为复制成项目事实。

## 唯一设计契约

用用户当前对话语言实例化 `design-template.md` 并删除语言指令注释。
`design.md` 只保留用户需要决定、实现必须遵守或验收可以核对的信息：

- 上下文、范围和明确的非目标；
- 稳定的 `B-###` 行为契约、`AC-###` 验收契约及追踪关系；
- 架构、所有权、数据流、API 边界和实质权衡；
- 适用的 UI scenario 引用，不重复 Runtime Coverage Plan；
- 与实际复杂度相称的状态流；
- 实质用户决策、风险和验证策略。

不得写文件级修改顺序、机械命令、实现清单或逐段复述来源。

评审前将行为与验收契约同原始需求、用户决定核对，不能仅对照现有代码。
未明确的解释执行 [需求冲突询问规则](stage-breakdown.md)。
按 [测试设计流程](stage-implementation.md) 推导紧凑验收
覆盖摘要，不得把未知预期作为技术默认值批准。

## 状态流深度

- `state_flow_required=false`：使用模板中的紧凑状态表；真正静态时写明原因，
  不生成装饰性图表。
- `state_flow_required=true`：包含状态分类与所有权、MVI/UDF 闭环、业务
  生命周期、UI 投影、权威 `T-###` 转换矩阵、适用的异步时序、不变量、
  非法转换、持久化/恢复和追踪。图表是评审视图，矩阵是事实源。

仅出现 MVI、Redux、Store 等架构名称，或普通 loading/success/failure，
不会自动触发复杂模式。只有实质改变 guard、并发、过期结果、恢复、持久化
或跨表面状态所有权时才设置为 `true`。

## 评审与 CP-DESIGN

`state_flow_required` 只控制文档深度；`user_decision_required` 才控制人工门禁：

- `false`：根据治理证据解决技术问题，自审当前文件，记录
  `design_review.review_mode=self`。
- `true`：用稳定 `D-###` 命名每个实质范围、行为、资源或体验决策，展示
  选项、影响和 `design.md` 绝对路径，并在 CP-DESIGN 暂停。用户明确解决并
  批准当前版本后记录 `review_mode=human`。

`user_decision_required` 描述当前设计版本所需的授权类型，不表示评审仍待
处理。当前版本获批后它仍保持 `true`；有效的 hash-bound human review
使决策不再待处理并允许进入 `design_ready`。只有当前版本不再包含决策权
属于用户的事项时才设为 `false`。

人工评审同时授权批准范围内的实现，不再请求第二次开发授权。两种模式都要
把 `reviewed_design_sha256` 绑定到文件精确 UTF-8 字节，并记录
`reviewed_at` 与 `reviewed_by`，然后设置 `design_ready`。文件变化会使评审
失效；当 `user_decision_required=true` 且变更后的文件缺少有效 hash-bound
human review 时再次进入 CP-DESIGN。

评审前检查语言：标题、表头/单元格、图中标签、正文、风险和决策使用用户
当前对话语言；机器 key、enum、ID、路径、命令、代码/API 符号和 Mermaid
语法保持原样。

## 执行持久化

不得创建 `spec.md`、`plan.md` 或 `tasks.md`。Stage 4 从当前设计契约、
依赖图和代码动态形成最小执行单元。需要跨会话恢复时，才在可选
`progress.md` 中记录已完成、待完成、阻塞、评审和验证命令/结果；它不是
第二份计划，也不能提升 gate。

API 证据直接进入 `design.md` 与实现。`none` / `existing` 跳过 UI Truth
Mapping 与 `visual_acceptance_passed`；另外两种模式必须保留有效冻结证据，
并在 Stage 4 完成对应视觉与动效验收。
