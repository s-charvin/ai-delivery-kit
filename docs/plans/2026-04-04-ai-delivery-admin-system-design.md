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
- MCP 与 skill 暴露

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

- 为 agent 提供标准动作顺序
- 约束“先查依赖、再写日志、再流转状态、再执行动作”的流程

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

- `requirement-slice.md`
- `figma-mapping.md`
- `interaction-design.md`
- `status.json`
- `dependency.json`
- `decisions.md`

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
- `transition_sub_requirement_status`
- `check_dependency_ready`
- `reserve_worktree_slot`
- `record_worktree_created`
- `record_commit`
- `record_merge_result`
- `list_blockers`
- `upsert_artifact`
- `read_traceability`

## Validation Rules

所有写接口都需要校验：

- 状态迁移是否合法
- 依赖是否满足
- 当前是否已有 blocker
- 提交前缀是否符合命名约定
- 并发版本号是否一致

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
