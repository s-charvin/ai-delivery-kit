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

- 喂给 brainstorming 流程：`requirement-slice.md`、每个单元的 冻结宿主组件 / `ui-truth-index.json`（含 UI 时）、API 文档、依赖图。
- 产出：架构、组件分解、状态/转换模型，以及关联 scenario 的响应式布局、内容、交互、动效、资源、主题、无障碍、平台行为、性能与关键取舍。
- 摘要记入子需求 `notes`；只有用户明确批准后才设置 `design_approved: true`。不要把设计文档写进框架自有目录。

## `implement` 使用意见（按切片）

1. `using-git-worktrees` —— UI 切片定位并恢复 Stage 2 worktree；仅当没有已记录切片 worktree 时，才按每切片一个 worktree 创建。
2. `subagent-driven-development`（默认）—— 每任务一个实现者子代理，串行执行；每个子代理内部经 `test-driven-development` 走 TDD。仅对相互独立、文件不重叠的测试/缺陷域并行派发；绝不允许两个实现者同时改同一批切片文件。
3. `requesting-code-review` 驱动[评审循环](../stage-implementation.md#评审循环任务级闭环)：评审者始终是新鲜上下文的子代理；finding 作为修复简报交回实现者并重复评审，直到干净或 `review_loop.max_rounds` 预算耗尽，然后升级给用户。
4. 视觉/运行时验收（仅 UI）—— 执行每个 v2 profile/state/scenario 条目，视觉证据对照已确认 preview，使用项目原生工具验证 behavior，并写入 `visual-acceptance.json`；失败重新进入同一评审循环。
5. `verification-before-completion` —— 合并前做集成检查。
6. 进入 `finish` 前，完整静态分析 + 完整测试必须干净通过。

实现期间一次只编辑一个文件。

## `finish` 使用意见

- `finishing-a-development-branch` —— 结构化合并选项；变基到开发分支（无 merge commit）。
- 只有变基成功且所有门禁保持通过后才设置 `merged`。
- 进入 `merged` 前须用用户当前对话语言写 `verification.md`。保留 `templates/verification-template.md` 的三个 `ai-delivery-verification:*` 标记；缺少时状态 validator 会拒绝 `merged`。

## 可追溯性记录

superpowers 本身不产出规格产物；`spec_refs.tier` 保持规格类档位（spec-kit / openspec / native）不变。worktree 分支名与评审结果记入子需求 `notes` 或 `progress.md`。

## 边界

- 门禁/阻塞器/状态/合并决策永远留在编排器主会话；superpowers 技能只在被派发的工作内运行。
- 不要用 brainstorming 流程替代 Stage 1 的轻量审计。
