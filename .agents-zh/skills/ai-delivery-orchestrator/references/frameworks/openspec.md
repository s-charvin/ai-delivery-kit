# 框架指南：OpenSpec

已安装 OpenSpec 时，可用其棕地增量推理补充 `solution-design`，但它不拥有
AI Delivery 阶段或持久化产物。

## 检测与产物边界

只读检测既有 `openspec/` 或 CLI；禁止安装或初始化。既有 OpenSpec 内容仅作
证据输入。

允许比较需求切片与现有行为，识别最小可观察 delta，并用 proposal / technical
design 推理完善 canonical `design.md` 的范围、`B-###`、`AC-###`、风险、
状态转换和验证。UI truth 只引用当前 unit/scenario、来源与冻结 scope。

不得创建 OpenSpec change、proposal、design、task list、archive、状态或会话
元数据，也不得运行 `openspec archive`。命令若要求写 `openspec/**` 或单独的
`spec.md`、`plan.md`、`tasks.md`，必须跳过并在会话内应用方法或使用 native。
禁止先生成再搬运。

运行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。
评审方式由 `user_decision_required` 决定。在 `traceability.json`
`source_index.design` 记录方法和 canonical `design.md` 路径/hash；不生成
`spec_refs`。
