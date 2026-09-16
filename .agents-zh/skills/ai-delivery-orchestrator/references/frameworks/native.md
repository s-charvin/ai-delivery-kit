# 框架指南：Native

外部框架不存在、不适合当前动作或无法遵守 canonical 路径时使用 native。它是
完整兜底，不是低质量文档管道。

## 产物边界

- 流程/治理产物只写 `.ai-delivery/meta/project-binding.json` 声明的路径。
- 宿主树只允许写生产源代码、项目原生测试、官方预览与运行时资源。
- workspace 遵循 [../workspace-policy.md](../workspace-policy.md)。
- 推进 gate 前执行 [../framework-adaptation.md](../framework-adaptation.md)
  的产物边界审计。

## `solution-design`

主会话读取需求切片、全局规则、依赖图、项目架构、API 和 UI truth 证据，按用户
当前对话语言实例化 `design-template.md`，记录范围、`B-###`、`AC-###`、
追踪、实质方案决策和适用状态流深度。

`user_decision_required=false` 时自审并以 `review_mode=self` 绑定当前
SHA-256；为 `true` 时通过 CP-DESIGN 记录 `review_mode=human`。所有
validator 通过后才能设置 `design_ready`。

不得创建 `spec.md`、`plan.md` 或 `tasks.md`。

## `implement`

1. 解析批准 workspace；启用 UI truth 时复用 Stage 2 workspace。
2. 从 `design.md`、依赖、当前代码/测试和可选 `progress.md` 形成最小执行单元。
3. 执行 red → green → refactor。
4. 按 [闭环评审](../stage-implementation.md#review-loop-closed-loop) 评审，直到
   clean 或预算耗尽。
5. 仅在跨会话恢复需要时更新 `progress.md`，不得把它变成第二份计划。

## `finish`

运行项目分析与完整相关测试，完成所需视觉/动效验收，写带稳定 marker 的本地化
`verification.md`，rebase 后仅在所有 gate 仍有效时设置 `merged`。

在 `traceability.json` `source_index.design` 记录 native 方法和 canonical
`design.md` 路径/hash；schema 2.0 不生成 `spec_refs`。
