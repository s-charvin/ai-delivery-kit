# 本仓协作偏好

仅适用于 ai-delivery-kit 本仓，不作为安装资源分发给其他项目。

- 默认在当前 main checkout 工作，保留已有未提交变更。
- 没有明确指令时，不创建或切换 branch/worktree，不 stage、commit、push 或 release。
- 每次任务及阶段开始先回顾本文件与根 AGENTS.md；文件补丁逐文件进行。
- Git 提交信息使用英文。
- 不提交本地开发文档和验收产物：`docs/evaluations/`、`docs/guides/`、`docs/plans/`、`docs/prd/`、`docs/research/`、`docs/superpowers/`、`docs/artifact-layout.md`、`docs/CHANGELOG.md`；保留本地文件并遵循 `.gitignore`。
- 已有授权持续有效，不重复索取同一确认；后续明确用户指令优先于这些默认偏好。
