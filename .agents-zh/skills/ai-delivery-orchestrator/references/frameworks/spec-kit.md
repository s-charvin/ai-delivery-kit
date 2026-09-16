# 框架指南：spec-kit

已安装 spec-kit 时，可用其需求与设计推理补充 `solution-design`，但它不拥有
AI Delivery 阶段或持久化产物。

## 检测与产物边界

只读检测 `.specify/` 或 `specify` CLI；禁止安装、初始化或升级。`.specify/**`
始终是只读输入。

允许使用 spec-kit 的问题澄清、歧义检查、constitution 分析和设计推理来完善
唯一 `design.md`，并审计 `B-###`、`AC-###`、来源/UI 追踪、状态行为、权衡
与验证策略。

禁止运行会创建或修改 `.specify/**`、`spec.md`、`plan.md`、`tasks.md`、
checklist、状态或 agent 元数据的 `/speckit-*` 持久化步骤。无法脱离这些写入
运行时，在会话内应用方法或切回 native。禁止先生成再搬运。

运行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。
评审方式由 `user_decision_required` 决定，与是否存在 spec-kit 无关。

在 `traceability.json` `source_index.design` 记录采用的方法以及 canonical
`design.md` 路径/hash；schema 2.0 不生成 `spec_refs`。
