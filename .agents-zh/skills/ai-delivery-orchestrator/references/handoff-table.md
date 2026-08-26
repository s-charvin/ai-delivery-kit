# Handoff 表

每个阶段恰好有一个合法的下一站动作。不要即兴跳步。动作是抽象的；具体工具见 [framework-adaptation.md](framework-adaptation.md)。kit 自有技能（`requirement-breakdown`、`ui-truth-mapping`）保持原名。

| 当前完成态 | 唯一下一站 | 禁止 |
|------------|-----------|------|
| 拆分决策待定 | 用户确认后 → `requirement-breakdown` 或跳过单切片包 | `ui-truth-mapping`、`spec`/`plan`/`tasks` |
| `split_ready` + 轻量审计通过（`ui_truth_mode=figma` 或 `runtime-baseline`） | CP-UI 暂停 → 用户授权受控视觉实现 | 批准前改生产代码或 dispatch `ui-truth-mapping` |
| CP-UI 已确认 | 解析用户已批准 workspace，再运行 `ui-truth-mapping`（TDD + golden + 评审） | 把 Stage 2 当成不含实现的 mapping，或把 CP-UI 当作 worktree 同意 |
| `split_ready` + 轻量审计通过（`ui_truth_mode=none` 或 `existing`） | `design_mode` 为 `light` 或 `full` 时进入 `solution-design`，否则进入 `spec` | 不应为无 UI truth 切片强制 UI gate |
| `acceptance_frozen`（校验器 OK） | 按 `design_mode` 进入 `solution-design` | 方案设计门禁满足前进入 `spec` |
| 方案设计门禁满足（`design_mode=none`，或 `light`/`full` 且 `design_approved: true`） | `spec` → `plan` → `tasks` | `tasks_ready` 前写业务代码 |
| 所有可执行子需求达 `tasks_ready` | CP-001 暂停 → 用户确认 | 静默进入开发 |
| CP-001 已确认 | Stage 4：`implement` | 同切片文件并行实现者 |
| 切片实现完成 | `finish` → 设置 `merged` | 子代理合并或推进门禁 |

## 状态 → 下一站映射（供 reconcile 使用）

| 子需求状态 | ui_truth_mode | design_mode / 审批 | 下一站 |
|------------|----------------|----------------|--------|
| `draft` | 任意 | 任意 | `requirement-breakdown` |
| `split_ready` | `figma` 或 `runtime-baseline` | 任意 | 等待 CP-UI；确认后 → `ui-truth-mapping` |
| `split_ready` | `none` 或 `existing` | `none` | `spec` |
| `split_ready`（启用的 UI truth gate 完成后） | 任意 | `light` 且 `design_approved=false` | `solution-design` → 自动满足门禁 |
| `split_ready` / `acceptance_frozen` | 任意 | `full` 且 `design_approved=false` | `solution-design` → CP-DESIGN |
| `split_ready` / `acceptance_frozen` | 任意 | `full` 且 `design_approved=true` | `spec` |
| `spec_ready` | 任意 | 门禁满足 | `plan` |
| `plan_ready` | 任意 | 门禁满足 | `tasks` |
| `tasks_ready` | 任意 | 门禁满足 |（等待 CP-001；确认后对账输出 `implement`）|
| `in_dev` | 任意 | 门禁满足 | `implement` |
| `visual_acceptance_passed` | `figma` 或 `runtime-baseline` | 门禁满足 | `finish` |
| `merged` | 任意 | 任意 | 无 |
| `blocked_*` | 任意 | 任意 | `NEXT_ACTION=none`；先解决阻塞；继续其他可运行子需求 |

## 方案设计批准

- 所需方案设计产物完成后，将子需求条目的 `design_approved` 设为 `true`：`design_mode=light` 在 AI 自审后设置，`design_mode=full` 仅在用户明确批准后设置；`design_mode=none` 保持 `false`。
- `design_mode=light` 记录短方案并自审，不触发 CP-DESIGN；`none` 不创建 `design.md`。
- `notes` 只保留短指针，规范产物需要时落在 `design.md`。
- `design_mode=full` 门禁未满足时不得进入 `spec`/`plan`/`tasks`。
