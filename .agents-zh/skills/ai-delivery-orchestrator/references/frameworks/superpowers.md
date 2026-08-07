# 框架指南：superpowers

已安装 superpowers 技能包时，`design` / `implement` / `finish` 动作使用本档位。superpowers 提供执行纪律类技能；编排器为它们提供外围状态机。

## 检测标志

任意用户技能目录中存在 superpowers 技能：

- `~/.claude/skills/superpowers`、`~/.agents/skills/superpowers`，或仓库技能树含 superpowers 技能（如 `using-git-worktrees`、`test-driven-development`）。

绝不自行 clone 或 symlink superpowers。

## 覆盖的动作

| 动作 | superpowers 技能 |
|------|------------------|
| `design` | brainstorming 流程（CP-DESIGN 前的设计探索） |
| `implement` | `using-git-worktrees`、`subagent-driven-development`、`test-driven-development`、`requesting-code-review`、`verification-before-completion` |
| `finish` | `finishing-a-development-branch` |

## `design` 使用意见

- 喂给 brainstorming 流程：`requirement-slice.md`、每个单元的 `ui-contract.html`（含 UI 时）、API 文档、依赖图。
- 产出：架构、组件分解、数据模型草图、错误/空/加载态方案、关键取舍。
- 摘要记入子需求 `notes`；只有用户明确批准后才设置 `design_approved: true`。不要把设计文档写进框架自有目录。

## `implement` 使用意见（按切片）

1. `using-git-worktrees` —— 一个切片一个 worktree。
2. `subagent-driven-development`（默认）—— 每任务一个实现者子代理，串行执行；每个子代理内部经 `test-driven-development` 走 TDD。仅对相互独立、文件不重叠的测试/缺陷域并行派发；绝不允许两个实现者同时改同一批切片文件。
3. `requesting-code-review` —— 首次失败先自动修复，再升级到用户。
4. 视觉验收（仅 UI）—— 对照已评审的 `ui-contract.html` 各状态；首次失败自动修复。
5. `verification-before-completion` —— 合并前做集成检查。
6. 进入 `finish` 前，完整静态分析 + 完整测试必须干净通过。

实现期间一次只编辑一个文件。

## `finish` 使用意见

- `finishing-a-development-branch` —— 结构化合并选项；变基到开发分支（无 merge commit）。
- 只有变基成功且所有门禁保持通过后才设置 `merged`。

## 可追溯性记录

superpowers 本身不产出规格产物；`spec_refs.tier` 保持规格类档位（spec-kit / openspec / native）不变。worktree 分支名与评审结果记入子需求 `notes` 或 `progress.md`。

## 边界

- 门禁/阻塞器/状态/合并决策永远留在编排器主会话；superpowers 技能只在被派发的工作内运行。
- 不要用 brainstorming 流程替代 Stage 1 的轻量审计。
