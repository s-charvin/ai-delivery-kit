# AI Delivery Admin System Design

## Goal

设计一个独立、本地部署、项目绑定式的后台管理系统，用于展示和管理业务项目中的 `.specify/` 与 `.ai-delivery/` 数据。

该系统只负责：

- 读取
- 展示
- 编辑
- 校验
- 日志记录
- 状态流转
- MCP 与 admin support skill 暴露

它不拥有业务真相，不迁移业务数据，不替代 git。

## Recommended Stack

推荐采用：

- `TypeScript`
- `Node.js`
- `React` Web 控制台
- `Hono` 或同类轻量服务端框架
- `zod` 进行 schema 校验
- 文件系统适配器读取 `.specify/` 与 `.ai-delivery/`
- 单机 SQLite 仅保存后台自身运行配置与最近索引缓存

说明：业务真相仍然保存在项目文件夹中，SQLite 不作为业务数据源。

## Project Layout

假设独立后台项目位于：

- `/Users/charvin/Projects/ai-delivery-admin`

建议目录：

```text
/Users/charvin/Projects/ai-delivery-admin/
├── server/
├── web/
├── mcp-server/
├── skills/
├── adapters/
├── shared/
└── tests/
```

说明：

- `skills/` 目录只用于存放 admin support skill
- 3 个业务开发 skill 不在此项目中维护
- 3 个业务开发 skill 应随业务项目放置，建议直接位于 `<project-root>/.agents/skills/`

## Responsibilities By Layer

### Adapter Layer

职责：

- 解析 `.specify/`
- 解析 `.ai-delivery/`
- 对不同版本的数据结构做兼容
- 将文件映射为统一领域对象

建议对象：

- `ProjectOverview`
- `Requirement`
- `SubRequirement`
- `TraceabilityRecord`
- `ExecutionEvent`
- `Blocker`
- `WorktreeRecord`

### Control API Layer

职责：

- 绑定项目目录
- 返回项目概览
- 提供状态流转与 blocker 管理
- 提供日志追加接口
- 提供结构化文件读取与回写接口

### MCP Layer

职责：

- 暴露给 AI 的标准化工具接口
- 屏蔽底层文件结构细节
- 在写入前做校验与规则检查

### Skill Layer

职责：

- 提供 admin support skill
- 为 agent 提供标准动作顺序
- 约束“先查依赖、再写日志、再流转状态、再执行动作”的流程
- 明确要求通过 MCP 或受控 API 完成治理类写操作

说明：

- 这一层不拥有 `requirement-breakdown`、`ui-requirement-mapping`、`ui-interaction-design`
- 这 3 个 skill 是业务项目侧的开发 skill，不属于后台项目

### Web Console

职责：

- 可视化展示
- 人工编辑
- 阻塞处理
- 日志与追踪回放

## Project Binding Model

每个后台实例可绑定多个业务项目。

绑定配置建议包含：

- `project_id`
- `project_root`
- `display_name`
- `default_main_dev_branch`
- `specify_path`
- `ai_delivery_path`
- `created_at`
- `updated_at`

后台系统启动后：

1. 读取绑定列表
2. 校验项目根目录存在
3. 校验 `.specify/` 与 `.ai-delivery/` 可读
4. 建立内存索引
5. 提供 UI/MCP/skill 查询能力

## Core Pages

### Project Dashboard

显示：

- 总需求数
- 子需求数
- 当前进行中的子需求
- blocker 数量
- 最近事件
- 当前依赖波次

### Requirement Explorer

显示：

- 总需求树
- 子需求树
- 子需求状态
- 依赖关系

### Traceability View

显示：

- Requirement -> Sub Requirement -> Figma Nodes -> Interaction -> Spec Kit -> Runtime State

### Execution Board

显示：

- 状态列
- 可并行节点
- 主开发分支状态
- worktree 占用与 merge 队列

### Logs Timeline

显示：

- 主会话事件
- subagent 事件
- 事件过滤与重放

### Artifact Editor

允许编辑：

- `requirement.md`
- `breakdown-summary.md`
- `global-rules.md`
- `README.md`
- `requirement-slice.md`
- `figma-mapping.md`
- `interaction-design.md`
- `traceability.json`
- `decisions.md`

说明：

- `dependency-graph.json` 必须走专用 dependency graph 更新面，并同步派生 `dependency.json` 与 runtime graph
- `status.json` 必须走 transition / resume 受控状态机
- `dependency.json` 是派生文件，不在通用 artifact editor 中自由编辑

### Governed Artifact Coverage

后台系统必须把以下内容视为一等治理产物：

- requirement 级 artifact
  - `requirement.md`
  - `breakdown-summary.md`
  - `global-rules.md`
  - `dependency-graph.json`
- sub-requirement bootstrap artifact
  - `README.md`
  - `requirement-slice.md`
  - `dependency.json`
  - `status.json`
  - `traceability.json`
  - `decisions.md`
- downstream design artifact
  - `figma-mapping.md`
  - `interaction-design.md`

说明：

- `traceability.json` 不是附属文件，而是核心治理对象
- `figma-cache/` 中的 screenshot、node dump、token 等原始证据不应按通用文档编辑逻辑处理
- raw Figma cache 更适合走“读取、索引、freshness 判断”边界

### Blocker Center

显示：

- blocker 类型
- 影响范围
- 触发时间
- 待决议内容
- 恢复动作

## MCP Tool Surface

建议提供以下工具：

- `bind_project`
- `get_project_overview`
- `list_requirements`
- `list_sub_requirements`
- `get_sub_requirement_detail`
- `append_execution_log`
- `create_requirement_package`
- `create_sub_requirement_package`
- `update_requirement_dependency_graph`
- `transition_sub_requirement_status`
- `update_blocker`
- `resume_sub_requirement_after_blocker`
- `check_dependency_ready`
- `reserve_worktree_slot`
- `record_worktree_created`
- `record_commit`
- `record_merge_result`
- `finalize_merge_and_unlock`
- `list_blockers`
- `upsert_artifact`
- `read_traceability`
- `list_figma_cache_entries`
- `get_figma_cache_status`

## Validation Rules

所有写接口都需要校验：

- bootstrap 路径是否合法
- artifact 类型是否属于受控范围
- 状态迁移是否合法
- 依赖是否满足
- 当前是否已有 blocker
- blocked 状态是否具备合法恢复目标
- worktree 的 `base_branch` 是否符合主开发分支约束
- 提交前缀是否符合命名约定
- 并发版本号是否一致
- merge 收敛动作是否联动更新必要运行态

不通过时：

- 拒绝写入
- 生成或更新 blocker
- 记录失败日志

## File Editing Policy

### Human And AI Use The Same API

人和 AI 都通过同一套 API 编辑结构化文件。

这样可以保证：

- 规则一致
- 审计一致
- 日志一致
- 冲突处理一致

### Create And Update Policy

后台治理面必须同时支持：

- create：用于 `Requirement Intake` 与子需求 bootstrap
- update：用于后续 requirement / mapping / interaction / decision 的版本化更新

对于 create：

- 初始版本必须显式落盘
- 必须写入 `updated_at` 与 `updated_by`
- 不允许无版本的隐式创建

对于 update：

- 必须携带当前版本
- 版本不匹配时拒绝覆盖

### Concurrency Handling

建议每个可编辑产物都包含：

- `version`
- `updated_at`
- `updated_by`

并发修改时：

- 如果版本不匹配，拒绝覆盖
- 返回冲突详情
- 允许用户或 agent 显式重试

## Failure Policy

### Logging Failure

如果日志写入失败：

- 本次动作应视为未完成
- 不允许“执行成功但未记账”

### Corrupted File

如果结构化文件损坏：

- 标记为 `invalid`
- 阻止相关状态推进
- 生成 blocker

### Stale Figma Cache

如果 Figma 缓存过旧：

- 标记 `stale`
- 不自动猜测刷新结果
- 仅在用户要求或规则命中时刷新

## Figma Cache Boundary

后台系统对 `figma-cache/` 的职责应以读取与索引为主：

- 展示 cache 是否存在
- 展示是否过旧或损坏
- 展示与哪个子需求存在绑定关系

不建议将以下内容纳入通用 artifact 编辑器：

- screenshot 二进制文件
- 原始 node dump
- token 原始导出

这些内容更适合作为 skill 生成的原始证据，由后台提供 freshness 与可见性管理。

## Runtime Control Boundary

MCP daemon 启停、状态查看、日志查看属于 admin runtime 管理能力。

它们的边界应为：

- 默认对 Web 管理界面可用
- 仅在明确设计专用 runtime tools 时才对 agent 暴露
- 不作为 3 个项目内 workflow skill 的主依赖

这样可以避免 runtime 控制和 workflow truth 混在一起。

## Testing Strategy

- Adapter 单测：解析、schema 校验、坏文件恢复
- API 集成测试：状态流转、日志写入、blocker 生成、编辑保存
- MCP 集成测试：常见 agent 调用链
- Web E2E：项目绑定、看板查看、编辑、阻塞处理
- 并发恢复测试：主会话与 subagent 同时写入时的冲突检测与恢复

## Non-Goals

本设计不包含：

- 远程 SaaS 部署
- 多租户权限体系
- 云端协作编辑
- 业务代码编译或部署能力
