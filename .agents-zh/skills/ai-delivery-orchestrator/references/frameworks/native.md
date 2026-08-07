# 框架指南：原生档（内置兜底）

**未安装**任何外部框架（spec-kit / OpenSpec / superpowers / ECC）时使用本档位。它是编排器的质量下限：子需求目录内的轻量产物 + 内置纪律规则。原生档产出必须与框架档同等可追溯。

所有原生产物都放在切片旁：`.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`。

## `design` 动作（原生设计流程）

在主会话内联完成（无需单独工具）：

1. 读取 `requirement-slice.md`、冻结的 `ui-contract.html`（含 UI 时）、API 文档、依赖图。
2. 产出：架构草图、组件分解、数据模型、错误/空/加载态方案、关键取舍。
3. 把精简摘要追加到子需求 `notes` 字段并向用户展示。
4. CP-DESIGN：只有用户明确批准后才设置 `design_approved: true`。

## `spec` 动作 — `spec.md`

创建 `sub-requirements/<subreq-id>/spec.md`，固定四段：

```markdown
# <subreq-id> Spec

## Problem
<一段：什么坏了或缺失了>

## Goal
<可观察的结果，用验收相关行为表述>

## Scope
- In scope: ...
- Out of scope: ...

## Acceptance Criteria
- [ ] 可测试的标准 1
- [ ] 可测试的标准 2
```

含 UI 的切片先对照冻结的 `ui-contract.html` 各状态审计，再设置 `spec_ready`。

## `plan` + `tasks` 动作 — `tasks.md`

原生档把 plan 与 tasks 合并进一个文件以保持轻量。创建 `sub-requirements/<subreq-id>/tasks.md`：

```markdown
# <subreq-id> Tasks

## Plan
<2-5 句：方案、关键文件/组件、排序理由>

## Tasks
- [ ] T1 <任务> — files: <编辑面> — test: <测试指针或验证方式>
- [ ] T2 ...
```

规则：

- 一个任务 = 一个可实现步骤，带明确编辑面与测试指针。
- 按依赖排序；共享组件先于使用方。
- 设置 `tasks_ready` 前审计粒度与文件范围。

原生档下，`traceability.json` 的 `spec_refs.plan_path` 也指向 `tasks.md`（其中的 Plan 段即 plan 产物）。

## `implement` 动作 — 内置纪律

不需要子代理框架，但纪律不可妥协：

1. **隔离** —— 一个切片一个分支；仓库支持时用 worktree。
2. **TDD 先行** —— 生产代码前先写失败测试；保持 红 → 绿 → 重构 的循环。
3. **小步走** —— 一次一个文件，小提交并以子需求 id 作前缀。
4. **评审循环** —— 每任务完成后，把评审作为独立一遍走[评审循环](../stage-implementation.md#评审循环任务级闭环)：像在评审别人的代码一样，对照任务验收说明与 spec 验收标准重读 diff；finding 成为修复清单，修复后复审，直到干净或 `review_loop.max_rounds` 预算（默认 3）耗尽 —— 然后升级给用户，绝不自动合并。
5. **完成前验证** —— 跑项目静态分析与完整测试套件；没有证据绝不声称任务完成。

## `finish` 动作 — 内置合并清单

1. 完整静态分析 + 完整测试干净通过。
2. 视觉验收证据已落档（仅 UI）：`visual-acceptance.md` 或 `visual-acceptance/*.png`。
3. 变基到开发分支（无 merge commit）；解决冲突后重跑测试。
4. 开/合并 PR，然后设置 `merged`。

## 可追溯性记录

子需求 `traceability.json`：

- `spec_refs.tier`：`"native"`
- `spec_refs.spec_path`：`sub-requirements/<subreq-id>/spec.md`（实际使用相对仓库根的路径）
- `spec_refs.plan_path` / `tasks_path`：`sub-requirements/<subreq-id>/tasks.md`
- `source_index.spec`：`ref_type` 为 `spec` / `tasks` 的条目

## 边界

- 原生产物绝不离开子需求目录；不要发明全仓库的 `specs/` 树。
- 用户之后安装了框架，新的子需求可以切换档位（记入 `decisions.md`）；已推进的子需求保持原档位。
