# AI Delivery Master Plan Refactor Design

## Goal

将现有的 `AI Delivery System Implementation Plan` 从“逐步开工施工单”重构为“架构蓝图型主计划”，使其更适合当前的文档设计阶段，并为后续真正进入开发时派生多份 execution plan 提供稳定总纲。

## Why Refactor The Existing Plan

现有实施计划存在以下问题：

- 它把数据契约、后台系统、MCP、Web、skills、测试一次性铺开，更像立即开工用的施工单
- 它默认了开发优先级与实现顺序，但当前阶段还处于完整文档设计阶段
- 它没有把“主计划”和“派生 execution plan”分离，导致后续扩展时容易整份返工
- 它没有充分表达各能力域的边界与后续派生计划之间的职责切分

因此，需要将其升级为一个更稳定的总蓝图。

## New Positioning

新版主计划不再回答“今天先写哪个文件”，而是回答：

- 系统应该如何组织
- 哪些规则是硬约束
- 哪些层是数据真相
- 哪些模块可以扩展
- 后续 execution plan 应该如何从主计划派生

## Approved Refactor Direction

新版主计划采用“架构蓝图型主计划”结构，核心目标是：

- 把“架构真相”和“开发顺序”分离
- 把“系统设计”与“具体 execution plan”分离
- 让后续新增能力不需要频繁推翻总计划
- 为多份派生 execution plan 提供边界与依赖基线

## Approved Main Sections

新版主计划应包含以下章节：

1. `Plan Intent`
2. `Scope And Non-Goals`
3. `System Context`
4. `Architecture Principles`
5. `Domain Model`
6. `Storage Blueprint`
7. `Runtime Blueprint`
8. `Admin System Blueprint`
9. `Skill System Blueprint`
10. `MCP Blueprint`
11. `Observability And Recovery`
12. `Extension Points`
13. `Verification Strategy`
14. `Derived Execution Plans`
15. `Open Decisions`

## Derived Execution Plans

新版主计划最初明确了三份主 execution plan，后续在零起点链路审查后，又补充了一条跨轨 integration repair / full-chain verification plan。

1. `项目内数据层 execution plan`
2. `ai-delivery-admin execution plan`
3. `ai-delivery-skills implementation plan`
4. `integration repair / full-chain verification plan`

### Boundary Of Project Data Execution Plan

职责：

- 负责业务项目内 `.ai-delivery/` 数据目录与契约
- 负责目录结构、文件契约、版本字段、命名规范、样例 requirement 包
- 负责运行态文件如 `dependency-graph.json`、`worktrees.json`、`blockers.json`、`events.ndjson`
- 保证后台与 skill/MCP 能正确消费这些文件

不负责：

- 后台 Web
- MCP server 实现
- skill 本体
- UI 展示逻辑

### Boundary Of `ai-delivery-admin` Execution Plan

职责：

- 负责独立后台项目
- 负责 `adapters / server / web / shared / skills / mcp-server`
- 负责项目绑定、概览读取、状态流转、日志写入、artifact 编辑、blocker 处理
- 负责 `ai-delivery-admin` 内的 1 个 support skill
- 负责 `ai-delivery-admin` 内的 MCP server
- 消费 `.specify/` 与 `.ai-delivery/`，但不重新发明业务数据结构

不负责：

- 定义业务项目内的根数据契约
- 业务项目内 3 个开发 skill 的工作流内容
- Requirement/Figma 业务规则重定义
- 替代 git/worktree 机制本身

### Boundary Of `ai-delivery-skills` Implementation Plan

职责：

- 负责业务项目内的 3 个开发 skill
- 负责这些 skill 的 `references / templates / validator / install-sync scripts`
- 将主计划中的硬约束翻译成 agent 可执行规则
- 在可用时通过 admin support surface 或 MCP 使用受控接口读写状态、日志、artifact
- 串起 `requirement-breakdown -> ui-requirement-mapping -> ui-interaction-design -> Spec Kit`

不负责：

- 后台 Web 页面
- `.ai-delivery/` 根契约定义
- 后台项目整体 server 架构
- `ai-delivery-admin` 内的 support skill
- `ai-delivery-admin` 内的 MCP server
- 最终业务功能开发

### Boundary Of `integration repair / full-chain verification plan`

职责：

- 在首轮实现之后，重新按零起点推演整条链路
- 校验 skill 产物、`.ai-delivery/` 契约、admin 治理面、`.specify/` bridge 是否真正闭环
- 修复跨 execution track 的合同缺口
- 补充 bootstrap、blocked recovery、merge finalization、Spec Kit bridge 等跨层问题

不负责：

- 替代前三条执行线的主体实现
- 重写业务功能开发逻辑
- 推翻既有总架构边界

## Refactor Success Criteria

当本轮重构完成时，新的主计划必须满足：

- 不再以顺序施工任务为主结构
- 明确主计划只是总蓝图，不直接替代 execution plan
- 明确各 execution plan 的边界、依赖与产出
- 能作为后续扩展与派生计划的稳定总纲

## Non-Goals

本次重构不包含：

- 立即编写 3 份 execution plan
- 立即实现后台系统代码
- 立即创建 skill 或 MCP 代码
- 调整当前五份系统设计文档的基本结论
