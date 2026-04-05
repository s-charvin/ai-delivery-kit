# AI Delivery Admin Requirement Grouping Design

## Goal

在不改变 `.ai-delivery/requirements/<requirement-id>/...` 现有真相契约的前提下，重构 `ai-delivery-admin` 的 Web 控制台，让总需求与子需求形成真正可管理的分级展示，并支持在多总需求并行开发时按总需求查看全链路数据。

## Governing References

- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-admin-system-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-master-plan-refactor-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-overall-chain-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-requirement-breakdown-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-requirement-mapping-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-interaction-design-skill-design.md`

## Problem

当前 Web 页面虽然保留了 `requirement -> sub-requirement` 的基本数据关系，但多个页面仍以平铺子需求为主：

- `Requirement Explorer` 只是在 requirement 卡片下简单列出子需求
- `Traceability` 直接从全量 sub-requirement 列表选择
- `Artifact Editor` 直接从全量 sub-requirement 列表选择
- `Execution Board` 只按状态平铺，不便于在多个总需求之间快速切换

当产品连续提出多个总需求并分期推进时，用户很难快速回答：

- 当前正在看的子需求属于哪个总需求
- 某个总需求下有多少子需求、多少阻塞、多少正在推进
- 某个总需求的 traceability、artifact 编辑和执行状态是否一致

## Non-Goals

本次设计明确不做：

- 不新增 `phase`、`epic`、`initiative` 等新的持久化层级
- 不改变 `.ai-delivery/requirements/` 目录结构
- 不新增服务端 requirement 聚合契约
- 不重定义 execution/runtime/blocker 的底层治理规则

## Approved Direction

采用“前端派生 requirement 聚合模型”的方向：

- 保留现有 `/requirements` 与 `/sub-requirements` API 作为真相来源
- 在 Web 层派生 `RequirementGroup`
- 用统一的 requirement 级上下文串联浏览、追踪、编辑和执行页

这样可以在不扩大契约边界的情况下提升管理能力，并保持与既有设计文档一致。

## Information Architecture

### Shared Requirement View Model

Web 层新增一个派生视图模型，例如 `RequirementGroup`，至少包含：

- `requirement_id`
- `title`
- `summary`
- `sub_requirements`
- `sub_requirement_count`
- `in_progress_count`
- `blocked_count`
- `status_counts`
- `has_open_blocker`
- `matches_filters`

该模型只在前端内存中派生，不写回 `.ai-delivery/`。

### Requirement Explorer

`Requirement Explorer` 升级为 requirement 树形浏览器：

- requirement 头部显示总览指标
- requirement 可折叠与展开
- 子需求永远显示在对应 requirement 下面
- 子需求支持按状态或类型分组排序
- 页面提供搜索、状态筛选、仅看 blocked、排序方式切换

页面的核心用途从“浏览一个平面列表”升级为“按总需求治理一组子需求”。

### Requirement-Scoped Cross-Page Navigation

页面级上下文新增 `selectedRequirementId`。

其效果是：

- `Traceability` 先选 requirement，再选该 requirement 下的 sub-requirement
- `Artifact Editor` 先选 requirement，再选该 requirement 下的 sub-requirement
- `Execution Board` 增加 requirement 过滤入口，只看选中总需求的执行项

这样用户在切换页面时，不会丢掉“我现在正在看哪个总需求”的上下文。

## Interaction Design

### Requirement Explorer Interactions

- 默认全部 requirement 展开，但允许逐个折叠
- 搜索优先匹配 requirement 标题、摘要和 sub-requirement 标题
- 选择“仅看 blocked”时：
  - requirement 级别若没有 blocker 子项则整体隐藏
  - requirement 内只显示 blocker 子项
- 排序至少支持：
  - 按 requirement 标题
  - 按 blocker 数量
  - 按进行中数量

### Traceability And Artifact Selection

- 当切换 requirement 时，如果当前 sub-requirement 不属于新 requirement，则自动切到该 requirement 的第一个子需求
- 当某个 requirement 没有子需求时，显示空态，不保留旧子需求内容
- requirement 选择控件显示 requirement 标题和子需求数量，减少误选

### Execution Board Filtering

- requirement 过滤不改变底层 board 数据
- 仅改变页面渲染集合
- 状态列继续保留，但每列只显示当前 requirement 的项目

## Data Flow

### Source Of Truth

- requirement 树仍来自 `/api/projects/:projectId/requirements`
- traceability 仍来自 `/api/projects/:projectId/traceability/:subreqId`
- artifact detail 仍来自 `/api/projects/:projectId/sub-requirements/:subreqId`
- execution board 仍来自 `/api/projects/:projectId/execution-board`

### Derived Flow

1. `App.tsx` 读取 requirements、sub-requirements、execution board 等现有 payload
2. Web 层派生 `RequirementGroup[]`
3. `selectedRequirementId` 决定可见 requirement 范围
4. `selectedSubreqId` 始终从当前 requirement 的子需求集合中选出
5. 下游页面只消费当前 requirement 范围内的集合

## Error Handling

- 如果 requirement 数据为空，`Requirement Explorer` 显示空态
- 如果 requirement 有记录但子需求为空，显示“已创建 requirement 包但尚未拆分子需求”的空态
- 如果过滤条件导致结果为空，显示“当前筛选无结果”的空态
- 如果用户切换 requirement 后当前选中的 sub-requirement 失效，自动重置而不是报错
- 如果 traceability 或 artifact 详情加载失败，保留当前 requirement 上下文，只替换详情区为错误提示

## Testing Strategy

### Web Tests

新增或更新 Web 测试覆盖：

- requirement explorer 的树形展示、折叠、筛选、blocked-only 行为
- traceability 的 requirement 先选再选 sub-requirement 行为
- artifact editor 的 requirement 先选再选 sub-requirement 行为
- execution board 的 requirement 过滤行为
- App 级别在页面切换时对 `selectedRequirementId` 和 `selectedSubreqId` 的联动

### Verification

- 先跑新增/修改的目标 Web 测试，完成 TDD red-green
- 再跑完整 `npm test`
- 再跑 `npm run typecheck`

说明：当前仓库已有一个与真实 `/Users/charvin/Projects/Codex` 环境漂移相关的基线失败，需在最终汇报中和本次需求分层改动的验证结果分开说明。

## Expected Outcome

重构完成后，用户应能以总需求为单位完成以下动作：

- 浏览某个总需求下的全部子需求
- 看清该总需求的 blocker、状态分布与推进情况
- 在 traceability、artifact 编辑、execution board 之间保持同一总需求上下文
- 在多个总需求并行存在时快速切换并定位目标数据
