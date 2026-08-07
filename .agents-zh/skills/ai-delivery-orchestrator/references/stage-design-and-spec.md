# 阶段 3：设计 + Spec 管道

阶段 3 执行两个抽象动作：`design`（需批准）与 `spec` → `plan` → `tasks`。具体工具取决于按 [framework-adaptation.md](framework-adaptation.md) 选定的框架档位。

## 何时运行

- `design`：每个处于 `acceptance_frozen`（UI）或 `split_ready`（非 UI）且 `design_approved: false` 的子需求。
- `spec` / `plan` / `tasks`：每个 `design_approved: true` 的子需求，按 reconcile 输出一步一步执行。

## design 动作（HARD-GATE）

<HARD-GATE>
编排器设计模式：设计会话结束后，在用户批准设计之前，不要自行撰写 plan/spec 产物。
不要把设计文档写进框架自有目录。
摘要存入子需求 `notes`；仅用户批准后设 `design_approved=true`；然后进入 `spec` 动作。
</HARD-GATE>

<HARD-GATE>
在呈现设计并获得用户明确批准之前，不要执行 `spec`、`plan` 或 `tasks` 动作。
</HARD-GATE>

向设计会话（原生流程或已安装框架的设计流程，见 [framework-adaptation.md](framework-adaptation.md)）提供：

- `requirement-slice.md`
- 各 unit 的 `ui-contract.html`（若 UI）
- API 文档（若有）
- 依赖图

设计会话应产出：

- 架构（组件树、数据流、状态管理）
- 路由/导航设计（多屏）
- 组件分解策略
- 数据模型草图
- error/empty/loading 处理方案
- 关键技术决策与权衡

摘要存入 `notes`。用户批准后设 `design_approved: true`。

若设计与 HTML 契约或需求冲突 → `blocked_spec_mismatch`。

**暂停：** 设计批准为检查点 CP-DESIGN。等待用户明确批准。

## Spec 管道（框架无关）

当 `design_approved: true`，按 reconcile 输出的动作执行，使用 [frameworks/](frameworks/) 下所选档位的指南：

1. `spec` → `spec.md` — 对照 HTML 契约的 states 审计（UI）。UI 切片的视觉输入是经评审的 `ui-contract.html`，不是另一份 spec 文档。
2. `plan` → `plan.md` — 对照交付切片顺序审计。
3. `tasks` → `tasks.md` — 审计粒度、依赖顺序、文件范围。

每步完成后：

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

无论哪个档位，产物都要记入 `traceability.json` `spec_refs`（见 [framework-adaptation.md](framework-adaptation.md) → 可追溯性）。不要 fork 或复述框架管道技能来重述仓库本地契约。

## 暂停

所有可执行子需求达 `tasks_ready` 后，进入 CP-001，开发前与用户确认。

## API 策略

API 文档直接传给 spec 管道与实现。无独立 API 映射阶段。缺口在 `notes` 记为 `integration_deferred`；不阻塞 UI 映射或外壳工作。

## 非 UI 子需求

- 跳过 UI 真值映射（不要求 `acceptance_frozen`）。
- `split_ready` → `design` → spec 管道。
- 合并时跳过 `visual_acceptance_passed`。
