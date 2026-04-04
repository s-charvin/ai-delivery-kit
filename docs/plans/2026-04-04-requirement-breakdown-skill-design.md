# Requirement Breakdown Skill Design

## Skill Name

- `requirement-breakdown`

## Goal

将产品总需求拆分为可开发、可追踪、可排序、可阻塞的子需求包，为后续 Figma 映射、交互设计、Spec Kit 规格生成与开发调度提供稳定输入。

## Position In The Workflow

该 skill 位于：

- `Requirement Intake` 之后
- `UI Mapping` 之前

它是整个流程的第一道结构化入口。

## References And Upstream Dependencies

主参考：

- `pre-dev-requirement-breakdown`

依赖：

- `brainstorming` 已完成需求方向确认

下游：

- `ui-requirement-mapping`
- `ui-interaction-design`
- `Spec Kit Phase`

## Responsibilities

- 读取总需求文档
- 抽取全局规则
- 拆分子需求
- 识别共享基建与跨功能依赖
- 生成依赖 DAG
- 标记开放问题与 blocker
- 将可继续推进的子需求状态推进到 `split_ready`

## Non-Responsibilities

- 不写 Spec Kit spec/plan/tasks
- 不绑定 Figma 节点
- 不生成 UI 交互规则
- 不补全缺失的业务真相
- 不为了并行而强拆无意义子模块

## Inputs

必需输入：

- 总需求文档路径

可选输入：

- API 合同
- 现有代码目录
- 设计系统说明
- 业务规则补充文档

## Output Layout

```text
.ai-delivery/requirements/<requirement-id>/
├── requirement.md
├── breakdown-summary.md
├── global-rules.md
├── dependency-graph.json
└── sub-requirements/
    └── <subreq-id>/
        ├── README.md
        ├── requirement-slice.md
        ├── dependency.json
        ├── status.json
        ├── traceability.json
        └── decisions.md
```

## Splitting Principles

### Split By Delivery Meaning

优先按以下标准拆分：

- 可独立开发
- 可独立集成
- 可独立测试
- 可独立验收

### Required Module Types

子需求必须归类到以下类型之一：

- `Global Rule`
- `Shared Foundation`
- `Shared Component`
- `Feature Module`
- `Cross-Feature Infrastructure`

### Dependency Rules

- 共享能力必须早于依赖它的功能模块
- 如果 A 的实现必须依赖 B 的合并结果，则 A `depends_on B`
- 依赖图必须无环

## Minimal Fields Per Sub-Requirement

每个子需求至少包含：

- `subreq_id`
- `title`
- `type`
- `summary`
- `in_scope`
- `out_of_scope`
- `depends_on`
- `blocks`
- `acceptance_signals`
- `open_questions`
- `source_requirement_refs`

## Strong Constraints

### Requirement Conflict

若总需求文档内部存在冲突：

- 子需求不得标记为最终确定版
- 状态进入 `blocked_requirement_conflict`

### Missing Critical Requirement

若缺少关键前置事实：

- 进入 `blocked_missing_requirement`

### Boundary Unclear

若边界判断不足：

- 可以输出“拆分草案”
- 但不得伪装为确定版

### Anti-Fabrication

禁止：

- 提前拆入未来可能需求
- 把 vague requirement 自行合理化为具体业务逻辑
- 把单纯技术切分误当成功能切分

## Suggested Sub-Requirement README Structure

- 标题与 `subreq_id`
- 类型
- 简述
- 输入输出边界
- 上下游依赖
- 验收信号
- 开放问题
- 当前状态

## Completion Criteria

该 skill 完成时必须满足：

- 所有子需求都有唯一 ID
- 所有子需求都有依赖关系或明确声明无依赖
- 所有跨模块公共规则已抽取到 `global-rules.md`
- `dependency-graph.json` 无环
- 每个子需求都可以进入下游 Figma 映射，或被明确阻塞

## Handoff Contract

下游 skill 使用该 skill 的输出时，不需要重新解释总需求，只需读取：

- `requirement-slice.md`
- `global-rules.md`
- `dependency.json`
- `traceability.json`

这样可以减少后续 agent 反复重读整份 PRD 的成本。
