# Handoff 表

每个阶段恰好有一个合法的下一站技能。不要即兴跳步。

| 当前完成态 | 唯一下一站 | 禁止 |
|------------|-----------|------|
| 拆分决策待定 | 用户确认后 → `requirement-breakdown` 或跳过单切片包 | `ui-truth-mapping`、`speckit-*` |
| `split_ready` + 轻量审计通过（UI） | `ui-truth-mapping` | `speckit-*`、实现 |
| `split_ready` + 轻量审计通过（非 UI） | `superpowers:brainstorming`（设计模式） | 跳过设计批准 |
| `acceptance_frozen`（校验器 OK） | `superpowers:brainstorming`（设计模式） | 设计批准前 `speckit-*` |
| 设计已批准（`design_approved: true`） | `speckit-specify` → `plan` → `tasks` | `tasks_ready` 前写业务代码 |
| 所有可执行子需求达 `tasks_ready` | CP-001 暂停 → 用户确认 | 静默进入开发 |
| CP-001 已确认 | Stage 4：`using-git-worktrees` + `subagent-driven-development` | 同切片文件并行 implementer |
| 切片实现完成 | `finishing-a-development-branch` → 设置 `merged` | 子代理合并或推进门禁 |

## 状态 → 下一站映射（供 reconcile 使用）

| 子需求状态 | ui_bearing | design_approved | 下一站 |
|------------|------------|-----------------|--------|
| `draft` | 任意 | 任意 | `requirement-breakdown` |
| `split_ready` | true | 任意 | `ui-truth-mapping` |
| `split_ready` | false | false | `superpowers:brainstorming` |
| `split_ready` | false | true | `speckit-specify` |
| `acceptance_frozen` | true | false | `superpowers:brainstorming` |
| `acceptance_frozen` | true | true | `speckit-specify` |
| `spec_ready` | 任意 | true | `speckit-plan` |
| `plan_ready` | 任意 | true | `speckit-tasks` |
| `tasks_ready` | 任意 | true |（等待 CP-001；确认后对账输出 `using-git-worktrees`）|
| `in_dev` | 任意 | true | `subagent-driven-development` |
| `visual_acceptance_passed` | true | true | `finishing-a-development-branch` |
| `merged` | 任意 | 任意 | 无 |
| `blocked_*` | 任意 | 任意 | `NEXT_SKILL=none`；先解决阻塞；继续其他可运行子需求 |

## 设计批准

- 仅在 `superpowers:brainstorming` 设计会话且用户明确批准后，将子需求条目的 `design_approved` 设为 `true`。
- 设计摘要存入 `notes`。
- `design_approved` 为 false 时不得进入 `speckit-*`。
