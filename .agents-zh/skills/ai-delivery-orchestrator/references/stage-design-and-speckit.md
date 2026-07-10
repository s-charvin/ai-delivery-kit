# 阶段 3：设计 + Spec Kit 管道

## 何时运行

- 设计：每个处于 `acceptance_frozen`（UI）或 `split_ready`（非 UI）且 `design_approved: false` 的子需求。
- Spec Kit：每个 `design_approved: true` 且状态就绪进入下一 speckit 步骤的子需求。

## Brainstorming 设计（HARD-GATE）

<HARD-GATE>
在呈现 brainstorming 设计并获得用户明确批准之前，不要 invoke `speckit-specify`、`speckit-plan` 或 `speckit-tasks`。
</HARD-GATE>

向 `superpowers:brainstorming` 提供：

- `requirement-slice.md`
- `ui-acceptance-contract.yaml`（若 UI）
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

若设计与 YAML 契约或需求冲突 → `blocked_spec_mismatch`。

**暂停：** 设计批准为检查点 CP-DESIGN。等待用户明确批准。

## Spec Kit 管道

当 `design_approved: true`：

1. `speckit-specify` → `spec.md` — 对照 YAML 屏幕状态审计（UI）。
2. `speckit-plan` → `plan.md` — 对照交付切片顺序审计。
3. `speckit-tasks` → `tasks.md` — 审计粒度、依赖顺序、文件范围。

每步完成后：

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

不要 fork 官方 `speckit-*` 技能来重述仓库本地契约。

## 暂停

所有可执行子需求达 `tasks_ready` 后，进入 CP-001，开发前与用户确认。

## API 策略

API 文档直接传给 Spec Kit 与实现。无独立 API 映射阶段。缺口在 `notes` 记为 `integration_deferred`；不阻塞 UI 映射或外壳工作。

## 非 UI 子需求

- 跳过 UI 真值映射（不要求 `acceptance_frozen`）。
- `split_ready` → 设计 brainstorming → Spec Kit。
- 合并时跳过 `visual_acceptance_passed`。
