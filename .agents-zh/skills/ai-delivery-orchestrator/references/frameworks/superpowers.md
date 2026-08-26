# 框架指南：superpowers

已安装 superpowers 技能包时，`solution-design` / `implement` / `finish` 动作使用本档位。superpowers 提供执行纪律类技能；编排器为它们提供外围状态机。

## 检测标志

任意用户技能目录中存在 superpowers 技能：

- `~/.claude/skills/superpowers`、`~/.agents/skills/superpowers`，或仓库技能树含 superpowers 技能（如 `using-git-worktrees`、`test-driven-development`）。

绝不自行 clone 或 symlink superpowers。

## 覆盖的动作

| 动作 | superpowers 技能 |
|------|------------------|
| `solution-design` | brainstorming 流程（方案设计探索；仅 `design_mode=full` 触发 CP-DESIGN） |
| `implement` | `using-git-worktrees`、`subagent-driven-development`、`test-driven-development`、`requesting-code-review`、`verification-before-completion` |
| `finish` | `finishing-a-development-branch` |

## 产物边界

- 调用 superpowers skill 前，传入当前需求/子需求 canonical 根目录和明确的输出映射。superpowers 只提供推理、TDD、评审、worktree 与收尾纪律；所有持久化产物都由编排器决定位置。
- 禁用 `docs/superpowers/**`、`.superpowers/**` 等框架默认路径，并从当前 binding 解析每个目标。`brainstorming` 的已批准结果写入 layout key `solution_design`；plan 内容写入 layout key `plan`；评审 finding、修复简报、检查清单与代理/会话元数据写入适用的 `progress`、`decisions` 或 `verification` key。
- 若 superpowers 步骤必须写框架自有文件且不接受 canonical 映射，则不运行该持久化步骤；在会话内执行其方法并直接写等价 canonical 产物。禁止先生成框架文件再搬运。
- 宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。任何门禁推进前，执行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。

## `solution-design` 使用意见

- 喂给 brainstorming 流程：`requirement-slice.md`、每个启用 UI truth 的单元的冻结宿主组件 / `ui-truth-index.json`、API 文档和依赖图。
- 产出：架构、组件分解、状态/转换模型、scenario ID 引用和关键取舍。Runtime Coverage 保留在 UI truth index。
- 规范方案设计写入子需求 `design.md`，`notes` 只保留指针；完成所需评审后设置 `design_approved: true`（`design_mode=light` 在 AI 自审后设置，`design_mode=full` 仅在用户明确批准后设置）。`design_mode=none` 保持 `false`。不要把方案设计文档写进框架自有目录。

## `implement` 使用意见（按切片）

1. `using-git-worktrees` —— UI 切片定位并恢复 Stage 2 worktree；仅当没有已记录切片 worktree 时，才按每切片一个 worktree 创建。
2. `subagent-driven-development`（默认）—— 每任务一个实现者子代理，串行执行；每个子代理内部经 `test-driven-development` 走 TDD。仅对相互独立、文件不重叠的测试/缺陷域并行派发；绝不允许两个实现者同时改同一批切片文件。
3. `requesting-code-review` 驱动[评审循环](../stage-implementation.md#评审循环任务级闭环)：评审者始终是新鲜上下文的子代理；finding 作为修复简报交回实现者并重复评审，直到干净或 `review_loop.max_rounds` 预算耗尽，然后升级给用户。
4. 视觉/运行时验收（仅 `ui_truth_mode=figma` 或 `runtime-baseline`）—— 执行每个 v2 profile/state/scenario 条目，视觉证据对照已确认 preview，使用项目原生工具验证 behavior，并写入 `visual-acceptance.json`；失败重新进入同一评审循环。
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
- 即使 superpowers 自身默认指令要求其他路径，也不得让它在 `.ai-delivery/` 外持久化流程/治理产物。
