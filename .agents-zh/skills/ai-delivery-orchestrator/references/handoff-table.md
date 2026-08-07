# Handoff 表

每个阶段恰好有一个合法的下一站动作。不要即兴跳步。动作是抽象的；具体工具见 [framework-adaptation.md](framework-adaptation.md)。kit 自有技能（`requirement-breakdown`、`ui-truth-mapping`）保持原名。

| 当前完成态 | 唯一下一站 | 禁止 |
|------------|-----------|------|
| 拆分决策待定 | 用户确认后 → `requirement-breakdown` 或跳过单切片包 | `ui-truth-mapping`、`spec`/`plan`/`tasks` |
| `split_ready` + 轻量审计通过（UI） | `ui-truth-mapping` | `spec`/`plan`/`tasks`、实现 |
| `split_ready` + 轻量审计通过（非 UI） | `design` | 跳过设计批准 |
| `acceptance_frozen`（校验器 OK） | `design` | 设计批准前 `spec` |
| 设计已批准（`design_approved: true`） | `spec` → `plan` → `tasks` | `tasks_ready` 前写业务代码 |
| 所有可执行子需求达 `tasks_ready` | CP-001 暂停 → 用户确认 | 静默进入开发 |
| CP-001 已确认 | Stage 4：`implement` | 同切片文件并行实现者 |
| 切片实现完成 | `finish` → 设置 `merged` | 子代理合并或推进门禁 |

## 状态 → 下一站映射（供 reconcile 使用）

| 子需求状态 | ui_bearing | design_approved | 下一站 |
|------------|------------|-----------------|--------|
| `draft` | 任意 | 任意 | `requirement-breakdown` |
| `split_ready` | true | 任意 | `ui-truth-mapping` |
| `split_ready` | false | false | `design` |
| `split_ready` | false | true | `spec` |
| `acceptance_frozen` | true | false | `design` |
| `acceptance_frozen` | true | true | `spec` |
| `spec_ready` | 任意 | true | `plan` |
| `plan_ready` | 任意 | true | `tasks` |
| `tasks_ready` | 任意 | true |（等待 CP-001；确认后对账输出 `implement`）|
| `in_dev` | 任意 | true | `implement` |
| `visual_acceptance_passed` | true | true | `finish` |
| `merged` | 任意 | 任意 | 无 |
| `blocked_*` | 任意 | 任意 | `NEXT_ACTION=none`；先解决阻塞；继续其他可运行子需求 |

## 设计批准

- 仅在 `design` 动作会话且用户明确批准后，将子需求条目的 `design_approved` 设为 `true`。
- 设计摘要存入 `notes`。
- `design_approved` 为 false 时不得进入 `spec`/`plan`/`tasks`。
