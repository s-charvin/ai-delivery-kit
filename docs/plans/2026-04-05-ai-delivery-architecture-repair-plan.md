# AI Delivery Architecture Repair Plan

## Goal

基于零起点流程审查结果，修复 AI Delivery 架构中“设计方向正确但跨层合同还未完全闭环”的部分，使后续实现可以围绕一套真正打通的系统真相继续推进。

## Repair Scope

本修复计划只处理跨层合同与流程闭环问题，不重新定义：

- 双主源原则
- 3 个项目内 skill 的职责边界
- `ai-delivery-admin` 与业务项目分离的总体架构
- worktree / dependency / merge 的基本治理目标

## Repair Tracks

### Track 1: Requirement Intake Bootstrap Contract

目标：

- 明确零起点时 `requirement-id` 的创建责任
- 明确 `requirement.md` 的初始落位、版本与命名
- 明确 `requirement-breakdown` 与 `Requirement Intake` 的责任边界

需要产出：

- requirement bootstrap contract
- requirement package create surface design
- degraded local bootstrap 规则

### Track 2: Governed Artifact Coverage Expansion

目标：

- 让 admin 管理面真正覆盖 skill 产出的核心结构化文件

必须覆盖：

- `requirement.md`
- `breakdown-summary.md`
- `global-rules.md`
- `dependency-graph.json`
- `README.md`
- `requirement-slice.md`
- `figma-mapping.md`
- `interaction-design.md`
- `dependency.json`
- `status.json`
- `traceability.json`
- `decisions.md`

同时要区分：

- 结构化治理产物
- raw Figma cache 证据
- runtime 运行态记录

### Track 3: Blocked-State Recovery Model

目标：

- 让 blocker 不仅能阻塞，还能恢复

需要定义：

- `blocked_from_status`
- `resume_target_status`
- blocker 关闭后的恢复动作
- 合法 resume 规则

### Track 4: Merge Finalization And Dependency Unlock

目标：

- 让“merge 完成”成为完整 runtime 收敛动作，而不只是 merge queue 的一条记录

需要联动：

- `status.json`
- `worktrees.json`
- `merge-queue.json`
- `task-board.json`
- `dependency-graph.json`

### Track 5: Spec Kit Bridge Contract

目标：

- 打通 `.ai-delivery` 与 `.specify/` 的正式桥接

需要定义：

- `requirement_id / subreq_id` 与 Spec Kit identity 的映射
- bridge 触发时机
- bridge 结果的回写位置
- 失败或冲突时的 blocker 策略

### Track 6: Runtime Control Boundary

目标：

- 把 runtime daemon 管理和 workflow truth 完整分层

需要明确：

- runtime start/stop/logs 属于 admin runtime 管理
- workflow skill 不以 runtime control 为主依赖
- 只有显式设计专用 runtime tools 时，agent 才能通过治理面直接操作 runtime

### Track 7: Schema Alignment And Contract Tests

目标：

- 让 skill、shared schemas、adapters、admin API 对同一份 artifact 有同一套字段理解

需要补充：

- artifact coverage matrix
- adapter/schema 对齐规则
- traceability 契约测试
- blocked / merge / bootstrap 的 contract tests

## Plan Repair Targets

本次计划修复至少要同步到以下文档：

- `2026-04-04-ai-delivery-overall-chain-design.md`
- `2026-04-04-ai-delivery-admin-system-design.md`
- `2026-04-04-ai-delivery-implementation-plan.md`
- `2026-04-04-requirement-breakdown-skill-design.md`
- `2026-04-04-ui-requirement-mapping-skill-design.md`
- `2026-04-04-ui-interaction-design-skill-design.md`

## Follow-Up Implementation Guidance

架构修复完成后，后续实现不应直接“凭理解补代码”，而应至少派生一条专门的 integration repair / full-chain verification 执行计划，用来落实：

- bootstrap create surfaces
- governed artifact expansion
- blocked-state recovery
- merge finalization
- Spec Kit bridge
- cross-layer contract verification

## Success Criteria

修复完成后，应满足：

- 从空项目开始，第一份 requirement 可以被明确创建
- 3 个项目内 skill 的核心输出都能被后台治理面识别并管理
- blocked 状态有明确定义的恢复路径
- merge 完成会联动更新 downstream 可执行状态
- `.ai-delivery` 到 `.specify/` 的桥接不再只是概念性描述
- runtime control 与 workflow truth 的边界清晰
