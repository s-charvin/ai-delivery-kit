# 框架指南：原生档（内置兜底）

**未安装**任何外部框架（spec-kit / OpenSpec / superpowers / ECC）时使用本档位。它是编排器的质量下限：子需求目录内的轻量产物 + 内置纪律规则。原生档产出必须与框架档同等可追溯。

原生流程/治理产物使用当前 binding 声明的 canonical `.ai-delivery` 路径。默认布局把子需求产物放在切片旁：`.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`。

## 产物边界

- 所有流程/治理产物使用 `.ai-delivery/meta/project-binding.json` 声明的 canonical 路径；需求级 status、todo、progress 和交付报告仍保留在各自声明的需求级路径。
- 宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。不得创建仓库根级设计、plan、review、report、checklist 或 session 文件。
- 推进任何门禁前，执行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。任何新增或修改且位于 `.ai-delivery/` 外的流程/治理产物都设置 `blocked_verification_failure`。
- 按 [../workspace-policy.md](../workspace-policy.md) 解析执行 workspace。原生档不得从隔离偏好或 checkpoint 推导 worktree 同意。

进入 spec 管道前，解析 binding 的 layout key `spec`、layout key `plan` 与 layout key `tasks`。下文文件名都只是默认布局示例。

## `solution-design` 动作（原生方案设计流程）

在主会话内联完成（无需单独工具）：

1. 读取 `requirement-slice.md`、启用时的 UI truth 产物、API 文档与依赖图。
2. 产出：架构草图、组件分解、数据/状态转换模型、scenario ID 引用与关键取舍。`state_flow_required=true` 时，按 `design-template.md` 补齐状态分类、MVI 闭环、生命周期/投影图、权威转换矩阵、适用异步时序、不变量和追踪。Runtime Coverage 细节留在 `contracts/ui-truth-index.json`。
3. 将方案设计写入 layout key `solution_design` 解析出的路径（默认 `design.md`），并向用户展示精简摘要；`notes` 只保留短状态标记。
4. 完成所需评审后设置 `design_approved: true`：`design_mode=full` 仅经 CP-DESIGN 用户明确批准后设置；`design_mode=light` 完成短方案并通过 AI 自审后设置，不触发 CP-DESIGN。记录包含精确 design SHA-256、评审模式、时间戳和评审者的 `design_review`。`design_mode=none` 保持 `false`。

## `spec` 动作

在 layout key `spec` 解析出的产物中固定写四段：

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

## `plan` 动作

在 layout key `plan` 解析出的产物中写 `## Plan` 段：

```markdown
# <subreq-id> Plan

## Plan
<2-5 句：方案、关键文件/组件、排序理由>
```

## `tasks` 动作

在 layout key `tasks` 解析出的产物中写 `## Tasks` 段：

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

原生档保持由 `plan` 与 `tasks` 解析出的产物彼此独立，确保所有档位归档的 spec/plan/tasks 三件套一致。

## `implement` 动作 — 内置纪律

不需要子代理框架，但纪律不可妥协：

1. **解析 workspace** —— 默认使用当前 checkout，UI 切片复用 Stage 2 用户已批准 workspace。创建或复用 worktree 必须取得当前子需求的明确确认并使用准确的项目内路径；禁止外部路径与工具自动选址。
2. **TDD 先行** —— 生产代码前先写失败测试；保持 红 → 绿 → 重构 的循环。
3. **小步走** —— 一次一个文件，小提交并以子需求 id 作前缀。
4. **评审循环** —— 每任务完成后，把评审作为独立一遍走[评审循环](../stage-implementation.md#评审循环任务级闭环)：像在评审别人的代码一样，对照任务验收说明与 spec 验收标准重读 diff；finding 成为修复清单，修复后复审，直到干净或 `review_loop.max_rounds` 预算（默认 3）耗尽 —— 然后升级给用户，绝不自动合并。
5. **完成前验证** —— 跑项目静态分析与完整测试套件；没有证据绝不声称任务完成。

## `finish` 动作 — 内置合并清单

1. 完整静态分析 + 完整测试干净通过。
2. 结构化视觉/运行时验收已落档（仅 `ui_truth_mode=figma` 或 `runtime-baseline`）：layout key `visual_acceptance` 解析出的 schema v2 产物绑定当前 v3 index，并以范围对应证据通过或明确豁免每个 scenario。
3. 变基到开发分支（无 merge commit）；解决冲突后重跑测试。
4. 开/合并 PR；只有使用用户当前对话语言写完并签署 layout key `verification` 解析出的产物后才设置 `merged`。保留 `templates/verification-template.md` 的三个 `ai-delivery-verification:*` 标记；缺少时状态 validator 会拒绝 `merged`。

## 可追溯性记录

子需求 `traceability.json` 只使用 canonical `artifacts[]` 结构。为每个 `kind`（`spec`、`plan`、`tasks`）添加一个字段完整的对象：

```json
{
  "spec_refs": {
    "tier": "native",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": "<由 layout key spec 解析出的仓库相对路径>",
        "derived_paths": [],
        "content_sha256": "<canonical 内容的 sha256>",
        "sync_state": "synced"
      }
    ]
  }
}
```

另为每个产物添加一条 `source_index.spec` 记录，`ref_type` 为 `spec` / `plan` / `tasks`。不得发出或混入旧版的按 kind 独立 path 字段。

## 边界

- 原生流程/治理产物绝不离开 canonical `.ai-delivery` 路径；不要发明全仓库的 `specs/` 树。
- 用户之后安装了框架，新的子需求可以切换档位（记入 `decisions.md`）；已推进的子需求保持原档位。
