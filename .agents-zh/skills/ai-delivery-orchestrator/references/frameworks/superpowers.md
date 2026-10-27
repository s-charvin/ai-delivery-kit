# 框架指南：superpowers

已安装 superpowers 时，用于 `solution-design`、`implement` 和 `finish`
的方法与纪律；编排器仍拥有状态机和全部持久化产物。

## 产物边界

- 调用前传入 canonical 根、准确输出映射和
  [workspace-policy.md](../workspace-policy.md) 已批准的 workspace。
- `docs/superpowers/**` 与 `.superpowers/**` 默认输出禁用。设计只写
  layout key `solution_design`；跨会话进度、评审和验证分别写 canonical
  `progress`、`decisions` 或 `verification`。不持久化 plan/task list。
- 无法遵守路径的持久化步骤不得运行；禁止先生成再搬运。
- 宿主树只允许写生产源码、项目原生测试、官方预览和运行时资源。

## `solution-design`

用 brainstorming 方法分析需求切片、UI truth、API 和依赖图，把范围、行为、
验收、架构、状态流和权衡写入唯一 `design.md`。
`user_decision_required=false` 时自审；为 `true` 时通过 CP-DESIGN。
评审必须绑定文件准确 SHA-256。

## `implement`

默认当前 checkout，并复用 Stage 2 workspace。每次从当前设计契约、依赖、代码、
测试和可选 `progress.md` 形成一个临时执行 brief。仅当 subagent-driven 方法
接受该 brief 且不创建计划/任务产物时使用，否则按 native 执行。每个单元内部
执行 TDD，并通过
[闭环评审](../stage-implementation.md#review-loop-closed-loop) 直到 clean。

实施 brief 必须遵循[保持既有所有权的约定](../stage-4-sdd-bridge.md#ownership-preserving-execution-brief)。
宿主规范和既有生命周期权威约束分工；小单元与易测建议不能自行形成代码边界。
并行分派既要编辑范围不重叠，也要状态所有权独立。

随后完成每个 v3 scenario 的视觉/运行时验收、`verification-before-completion`
和完整分析/测试。`finish` 使用完成分支的方法，但仍按项目规则 rebase 且不生成
merge commit。

在 `traceability.json` `source_index.design` 记录使用的方法和 canonical
`design.md` 路径/hash；不生成 `spec_refs`。gate、blocker、status 和 merge
决定始终留在主编排会话。
