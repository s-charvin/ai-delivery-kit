# 本仓协作偏好

仅适用于 ai-delivery-kit 本仓，不作为安装资源分发给其他项目。

- 默认在当前 main checkout 工作，保留已有未提交变更。
- 没有明确指令时，不创建或切换 branch/worktree，不 stage、commit、push 或 release。
- 每次任务及阶段开始先回顾本文件与根 AGENTS.md；文件补丁逐文件进行。
- Git 提交信息使用英文。
- `docs/` 保留面向使用者和发布的正式文档，包括 `docs/guides/`、`docs/artifact-layout.md` 和 `docs/CHANGELOG.md`，正常纳入提交。
- 内部开发计划、需求草稿、研究、审查、评估与验收产物写入本地 `.local-development/`，不提交；不要为排除这些产物而忽略或删除正式文档。
- 已有授权持续有效，不重复索取同一确认；后续明确用户指令优先于这些默认偏好。
