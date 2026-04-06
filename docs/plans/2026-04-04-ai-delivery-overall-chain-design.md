# AI Delivery Overall Chain Design

## Goal

在当前项目中落地一套可监控、低人工指挥、强约束、面向高保真开发的 AI 研发链路。

这套链路需要同时满足以下目标：

- 以 `Requirement` 作为功能真相源
- 以 `Figma` 作为视觉真相源
- Requirement 与 Figma 一旦冲突必须阻塞升级，agent 不允许自行补需求或补 UI
- 子需求必须可拆分、可追踪、可排序、可恢复执行
- 开发必须遵守独立 `worktree`、依赖顺序、提交前缀、先合并回主开发分支再解锁后继开发的规则
- 主会话与 subagent 的执行日志必须统一沉淀到后台系统

## Tool Selection Summary

### Commonality Of The Three Candidates

`Spec Kit`、`Superpowers`、`OpenSpec` 都在解决同一类问题：把聊天式 AI 编程变成有流程、有制品、有约束的工程化开发。

三者共性：

- 都强调先有规范，再推进实现
- 都强调 agent 不应直接无约束地产出代码
- 都允许流程扩展与角色定制
- 都能服务于多步骤的复杂研发任务

### Key Differences

| 方案 | 核心定位 | 强项 | 弱项 | 本方案中的角色 |
| --- | --- | --- | --- | --- |
| `Spec Kit` | 规格驱动骨架 | constitution、spec、plan、tasks 的完整链路 | 对项目级运行态、日志态、调度态支持不够强 | 选用，作为规格与实现计划主骨架 |
| `Superpowers` | agent 执行纪律系统 | brainstorming、TDD、worktree、review、subagent 工作流 | 不负责项目级制品存储与状态管理 | 选用，作为 agent 行为约束层 |
| `OpenSpec` | 轻量变更工单层 | 变更目录、平行 change 管理、棕地增量迭代 | 与 Spec Kit 在 spec/change 层重合较高 | 不直接采用，但吸收其 change-folder 思路 |

### Why The Final Choice Is `Spec Kit + Superpowers`

本设计最终选择：

- `Spec Kit` 负责规格驱动产物
- `Superpowers` 负责开发执行纪律
- 自建 `AI Delivery Admin` 负责运行时管理、日志、追踪、阻塞、展示、编辑

不直接采用 `OpenSpec` 的主要原因：

- 与 `Spec Kit` 在“规格与任务制品”这一层有较多重叠
- 本方案更需要一个项目级控制平面，而不是第二套变更规范系统
- 采用 `Spec Kit + Superpowers + 自建控制层` 后，职责边界更清晰，也更便于后续升级

## Architecture Overview

本方案采用三层结构：

1. `Spec Kit Layer`
说明：保存 `constitution / spec / plan / tasks` 等规范产物。

2. `AI Delivery Control Data Layer`
说明：保存在业务项目中的 `.ai-delivery/`，负责需求拆分、Figma 映射、交互设计、依赖图、运行状态、日志与追踪。

3. `AI Delivery Admin Layer`
说明：独立本地项目，负责读取 `.specify/` 与 `.ai-delivery/`，以 Web、MCP、skill 的方式提供展示、编辑、调度与日志能力。

## Repository Boundary

业务项目只保存数据，不保存后台系统代码。

```text
<project-root>/
├── .specify/
├── .ai-delivery/
├── .codex/
│   └── skills/
│       └── ai-delivery/
└── docs/plans/
```

后台系统是单独项目：

```text
<ai-delivery-admin>/
├── server/
├── web/
├── mcp-server/
├── skills/                  # 仅放 admin support skill
└── adapters/
```

## Skill Placement

- `requirement-breakdown`
- `ui-requirement-mapping`
- `ui-interaction-design`

这 3 个 skill 是业务项目本地资产，用于直接支撑需求开发流程，建议放在：

```text
<project-root>/.agents/skills/
```

`ai-delivery-admin` 不拥有这 3 个业务开发 skill。

`ai-delivery-admin` 仅提供：

- 1 个 admin support skill
- 1 个 MCP 服务

用于给 agent 提供受控的日志、状态流转、blocker、artifact 操作能力。

## Dual Source Of Truth

### Rule

- `Requirement` 管功能真相
- `Figma` 管视觉真相
- 两者冲突时，系统必须进入阻塞态
- agent 不允许自作主张补需求、补页面、补字段、补状态、补流程

### Allowed Inference Boundary

仅允许做以下受限推断：

- 微交互默认值
- 可用性层默认行为
- 与现有系统完全一致且不改变业务语义的弱推断

所有受限推断都必须显式记录为：

- `assumed_micro_interaction`
- 或写入 `decisions.md`

## Hidden Data Directories

```text
.ai-delivery/
├── requirements/
├── figma-cache/
├── runtime/
├── logs/
└── meta/
```

### Responsibilities

- `requirements/`：总需求、子需求、切片、决策、追踪
- `figma-cache/`：Figma 原始结构、节点、截图、注释、token 缓存
- `runtime/`：依赖图、看板、主开发分支、worktree、merge queue、blocker
- `logs/`：主会话与 subagent 的统一事件日志
- `meta/`：项目绑定、命名约定、工作流策略

## End-To-End Workflow

主链路定义如下：

1. `Requirement Intake`
2. `Sub-Requirement Breakdown`
3. `Figma Mapping & Cache`
4. `Interaction Design`
5. `Spec Kit Phase`
6. `Development Dispatch`
7. `Merge Back To Main Dev`
8. `Done`

## Requirement Intake Bootstrap

零起点流程默认项目里还不存在对应的 `requirement-id` 目录。

因此 `Requirement Intake` 必须负责：

- 创建 `.ai-delivery/requirements/<requirement-id>/`
- 创建初始 `requirement.md`
- 创建空的 canonical `dependency-graph.json`
- 写入最小 requirement 级元信息

推荐路径：

- admin 可用时，通过受控 create surface 完成 bootstrap
- admin 不可用时，只允许在 `.ai-delivery/` 内按同一契约本地创建，不允许另建旁路存储

`requirement-breakdown` 不应再假设 requirement 包天然存在；它应当扩展 intake 已创建的包，或在缺失时按同一 bootstrap 契约补齐。

## Requirement Breakdown Expansion Boundary

在 `Requirement Intake` 之后，`requirement-breakdown` 负责补齐：

- `breakdown-summary.md`
- `global-rules.md`
- `dependency-graph.json`
- 各子需求目录与初始 artifact

说明：

- `status.json` 只能通过状态流转或恢复动作更新
- `dependency.json` 是 requirement DAG 同步后的派生视图，不是手工编辑真相
- `figma-mapping.md` 与 `interaction-design.md` 不应由 intake bootstrap 预先占位

这意味着后台治理面必须把这些文件也纳入一等 artifact 范围，而不能只治理后续的 UI 与交互文档。

## Sub-Requirement State Machine

```text
draft
-> split_ready
-> figma_mapped
-> interaction_ready
-> spec_ready
-> planned
-> dependency_satisfied
-> worktree_created
-> in_progress
-> review_pending
-> merge_pending
-> merged_main_dev
-> done
```

阻塞态：

```text
blocked_requirement_conflict
blocked_figma_conflict
blocked_requirement_figma_conflict
blocked_dependency
blocked_missing_design
blocked_missing_requirement
blocked_merge_conflict
blocked_verification_failure
```

## Blocked State Recovery

阻塞态不是终态，而是可恢复态。

系统必须为每次阻塞保留：

- `blocked_from_status`
- `resume_target_status`
- 触发 blocker 的原因与恢复条件

恢复规则：

- blocker 被关闭，不等于自动完成后续状态流转
- 必须通过显式恢复动作回到合法的活跃状态
- 不允许通过手工改 `status.json` 绕过恢复流程

## Dependency, Worktree, Merge And Parallel Rules

### Dependency Rules

- 只有当前置依赖全部到达 `merged_main_dev` 后，子需求才允许进入 `dependency_satisfied`
- 不允许提前从主开发分支创建未来子需求的 worktree
- 依赖图必须无环

### Worktree Rules

- 每个子需求必须使用独立 worktree
- worktree 必须基于“指定主开发分支”创建
- 一个子需求一个 worktree，不允许多个子需求共用

### Commit Rules

- 每个子需求的提交信息必须带固定前缀
- 推荐格式：`[SR-023] feat: add xxx`
- 提交前缀规则保存在 `.ai-delivery/meta/naming-rules.json`

### Merge Rules

- 子需求开发完成后，必须先合并回指定主开发分支
- 冲突需要在合并阶段解决
- 后继依赖节点只有在前置节点 `merged_main_dev` 后才解锁

### Merge Finalization Rules

`merge` 完成必须被视为一个联动收敛动作，而不是一条孤立记录。

至少应联动更新：

- `merge-queue.json`
- 子需求 `status.json`
- `worktrees.json`
- `task-board.json`
- `dependency-graph.json` 的下游可执行状态

如果只记录 merge 结果而不联动这些运行态文件，系统就无法真正解锁后继开发。

### Parallel Rules

- 仅允许在同一依赖波次内并行
- 并行节点必须写集不冲突
- 每个 subagent 必须拥有自己的 worktree、日志流、状态文件
- 不满足条件的子需求必须在主会话顺序执行

## Spec Kit Bridge

`Spec Kit Phase` 不应只停留在概念层。

当子需求到达 `interaction_ready` 后，系统必须存在一条正式桥接路径，将：

- `.ai-delivery` 中的 `requirement_id / subreq_id`
- requirement 切片、Figma 映射、交互契约

映射到 `.specify/` 中的 spec / plan / tasks identity。

桥接要求：

- 允许从 `.ai-delivery` 追溯到 `.specify/`
- 允许从 `.specify/` 追溯回 source requirement 与 sub-requirement
- bridge 失败时产生 blocker，而不是静默跳过

## Logging And Observability

所有动作必须统一写入后台系统，包括：

- 状态变化
- Figma 拉取与缓存
- spec/plan 生成
- worktree 创建
- 测试执行
- commit / merge / conflict
- blocker 创建与恢复

主会话与 subagent 使用同一事件模型，仅以 `session_type` 区分。

建议事件字段：

- `event_id`
- `timestamp`
- `project_id`
- `requirement_id`
- `subreq_id`
- `session_id`
- `session_type`
- `event_type`
- `status_before`
- `status_after`
- `message`
- `metadata`

## Design Package Index

本设计包包含以下五份文档：

1. `2026-04-04-ai-delivery-overall-chain-design.md`
2. `2026-04-04-ai-delivery-admin-system-design.md`
3. `2026-04-04-requirement-breakdown-skill-design.md`
4. `2026-04-04-ui-requirement-mapping-skill-design.md`
5. `2026-04-04-ui-interaction-design-skill-design.md`

## Non-Goals

本设计当前不包含：

- 直接实现后台系统代码
- 直接实现三个自定义 skill
- 直接创建实际 MCP server
- 直接创建业务项目中的 `.ai-delivery/` 生产目录结构
- 自动解决 Requirement/Figma 冲突
