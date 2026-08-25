# 框架指南：原生档（内置兜底）

**未安装**任何外部框架（spec-kit / OpenSpec / superpowers / ECC）时使用本档位。它是编排器的质量下限：子需求目录内的轻量产物 + 内置纪律规则。原生档产出必须与框架档同等可追溯。

所有原生产物都放在切片旁：`.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`。

## `design` 动作（原生设计流程）

在主会话内联完成（无需单独工具）：

1. 读取 `requirement-slice.md`、冻结宿主组件 / `ui-truth-index.json`（含 UI 时）、API 文档、依赖图。
2. 产出：架构草图、组件分解、数据/状态转换模型、关联 scenario 的响应式/内容/交互/动效/资源/主题/无障碍/平台/性能决策，以及关键取舍。
3. 将设计写入 `design.md`（规范设计文件，见 `docs/artifact-layout.md`）并向用户展示精简摘要；`notes` 只保留短状态标记。
4. CP-DESIGN：只有用户明确批准后才设置 `design_approved: true`。

## `spec` 动作 — `spec/spec.md`

创建 `spec/spec.md`，固定四段：

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

含 UI 的切片先对照每个已冻结 unit/scenario id 审计并保留其证据来源，再设置 `spec_ready`。

## `plan` 动作 — `spec/plan.md`

创建带 `## Plan` 段的 `spec/plan.md`：

```markdown
# <subreq-id> Plan

## Plan
<2-5 句：方案、关键文件/组件、排序理由>
```

## `tasks` 动作 — `spec/tasks.md`

创建带 `## Tasks` 段的 `spec/tasks.md`：

```markdown
# <subreq-id> Tasks

## Tasks
- [ ] T1 <任务> — files: <编辑面> — test: <测试指针或验证方式>
- [ ] T2 ...
```

规则：

- 一个任务 = 一个可实现步骤，带明确编辑面与测试指针。
- 按依赖排序；共享组件先于使用方。
- 设置 `tasks_ready` 前审计粒度与文件范围。

原生档保持 plan 与 tasks 为独立规范文件（`spec/plan.md`、`spec/tasks.md`），确保所有档位归档的 spec/plan/tasks 三件套一致。

## `implement` 动作 — 内置纪律

不需要子代理框架，但纪律不可妥协：

1. **隔离** —— UI 切片恢复已记录的 Stage 2 worktree/分支；仅当切片尚无工作区时，才创建一个切片分支（仓库支持时用 worktree）。
2. **TDD 先行** —— 生产代码前先写失败测试；保持 红 → 绿 → 重构 的循环。
3. **小步走** —— 一次一个文件，小提交并以子需求 id 作前缀。
4. **评审循环** —— 每任务完成后，把评审作为独立一遍走[评审循环](../stage-implementation.md#评审循环任务级闭环)：像在评审别人的代码一样，对照任务验收说明与 spec 验收标准重读 diff；finding 成为修复清单，修复后复审，直到干净或 `review_loop.max_rounds` 预算（默认 3）耗尽 —— 然后升级给用户，绝不自动合并。
5. **完成前验证** —— 跑项目静态分析与完整测试套件；没有证据绝不声称任务完成。

## `finish` 动作 — 内置合并清单

1. 完整静态分析 + 完整测试干净通过。
2. 结构化视觉/运行时验收已落档（仅 UI）：`visual-acceptance.json` 绑定当前 v2 index，并以模式对应证据通过或明确豁免每个 scenario。
3. 变基到开发分支（无 merge commit）；解决冲突后重跑测试。
4. 开/合并 PR；只有使用用户当前对话语言写完并签署 `verification.md` 后才设置 `merged`。保留 `templates/verification-template.md` 的三个 `ai-delivery-verification:*` 标记；缺少时状态 validator 会拒绝 `merged`。

## 可追溯性记录

子需求 `traceability.json`：

- `spec_refs.tier`：`"native"`
- `spec_refs.spec_path`：`sub-requirements/<subreq-id>/spec/spec.md`
- `spec_refs.plan_path`：`sub-requirements/<subreq-id>/spec/plan.md`
- `spec_refs.tasks_path`：`sub-requirements/<subreq-id>/spec/tasks.md`
- `source_index.spec`：`ref_type` 为 `spec` / `plan` / `tasks` 的条目

## 边界

- 原生产物绝不离开子需求目录；不要发明全仓库的 `specs/` 树。
- 用户之后安装了框架，新的子需求可以切换档位（记入 `decisions.md`）；已推进的子需求保持原档位。
