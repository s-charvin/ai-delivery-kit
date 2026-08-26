# Workspace 与 Worktree 策略

本策略是 Stage 2、Stage 4 和所有执行框架选择工作区的唯一权威。**worktree 是可选的。**默认使用当前 checkout。

## 同意边界

- 创建或复用 worktree 都必须取得当前子需求的用户明确确认。历史偏好、已记录的 worktree、框架默认值、dirty 文件、时间压力、CP-UI 和 CP-001 都不构成授权。CP-UI 与 CP-001 不授权 worktree。
- 询问前必须展示拟使用的准确路径、分支，以及任何必要的 `/.worktrees/` ignore 改动。唯一允许的 worktree 路径是 `<project-root>/.worktrees/<req-id>-<sr-id>`。
- 用户拒绝时使用当前 checkout。保留无关的用户改动；只有发生具体文件冲突或其他真实 blocker 时才停止。
- 将批准的选择与路径记录到当前子需求 canonical `decisions` 或 `progress` 产物。该批准仅对同一子需求的后续阶段有效，绝不授权其他切片。
- 将旧 `require_isolated_worktree` 值视为废弃输入；不得把它当作用户同意或强制要求。

## 项目内路径约束

从 Git common directory 推导项目根目录，不得把外部 linked worktree 的 checkout 路径误作项目根。批准的 worktree 必须等于解析后的 `<project-root>/.worktrees/<req-id>-<sr-id>`；`.worktrees/` 下的其他名称也不合法。禁止 `/private/tmp`、`/tmp`、平台托管 worktree 根目录、兄弟仓库、用户主目录 worktree 根目录以及其他任何外部路径。

仅当原生或外部 worktree 工具必须接受准确的项目内路径时，才可调用。若工具自行选址或只提供外部路径，则跳过该工具。取得用户确认后，改用受控的 `git worktree add <exact-project-local-path> <branch>`；禁止先在外部创建再搬运。

首次创建项目内 worktree 前，确保 `.worktrees/` 不污染主 checkout 的状态。优先沿用项目既有约定。如果必须修改 `/.worktrees/` `.gitignore`，要在 worktree 确认问题中展示准确改动；禁止静默修改 ignore 规则。

## 已存在的外部 worktree

每个 action 进入时，都要比较当前 checkout 与从 Git common directory 推导出的项目根。如果会话已经运行在 `/private/tmp/...` 或其他外部 worktree，立即停止生产编辑，并询问用户选择切换到：

1. 项目当前 checkout；或
2. 准确的项目内路径 `<project-root>/.worktrees/<req-id>-<sr-id>`。

用户回答前不得继续生产编辑，并保持外部 worktree 原样。切换 workspace 不授权迁移、重建或删除外部 worktree，且仍禁止复用外部 worktree。任何迁移、重建、清理或删除都必须另行取得明确确认，并点名准确动作与目标。只读检查与 canonical `.ai-delivery` 状态报告仍可进行。

## 框架覆盖规则

调用每个外部 skill 前，必须传入本策略与准确的已批准 workspace。强制隔离、原生工具优先选址、自动复用、临时目录 fallback 等外部默认规则一律失效。`using-git-worktrees` 只提供操作方法，无权决定是否使用 worktree 或选择其路径。

Stage 2 与 Stage 4 复用同一个**用户已批准 workspace**；它可以是当前 checkout，也可以是批准的项目内 worktree。框架不得为该切片创建第二个 workspace。
