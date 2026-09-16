# 对账规则

每次恢复或继续前先运行 reconcile，不得把 `todo.md` 当事实源。

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

## 对账契约

1. 重读 `status.json`、治理产物与依赖图。
2. 按当前状态重跑契约 validator。
3. 按 `blocker_scope` 分类阻塞。
4. 当前 guard 与证据有效时不重复阶段。
5. 缺失或过期证据重新打开最窄动作；`design_review` hash 失效重新进入
   `solution-design`。
6. 保留 blocked 切片，同时继续所有无依赖的 runnable 切片。
7. 输出 `RUNTIME_MODE`、`CHECKPOINT`、`RUNNABLE`、`BLOCKED`、
   `BLOCKER_SCOPES`、`NEXT_ACTION` 与 `NEXT_SUBREQ`。

schema 2.0 动作只有 `solution-design`、`implement`、`finish`、`archive`
以及 kit 自有技能。不得输出或重建 `spec`、`plan`、`tasks`。活跃旧 schema
必须迁移并重做设计能力审计；旧 `merged` / `archived` 只读兼容。

## Runtime mode

| Mode | 条件 |
|------|------|
| `completed` | 所有可执行切片均 `archived` |
| `closing` | 所有可执行切片均 `merged` → CP-ARCHIVE / `archive` |
| `bootstrap` | `status.json` 缺失、不完整或没有子需求 |
| `confirm_ui` | eligible UI truth 切片等待 CP-UI 且无其他 runnable 项 |
| `confirm_solution_design` | `user_decision_required=true` 且当前设计没有有效人工评审，且无其他 runnable 项 |
| `blocker_recovery` | `current_checkpoint=CP-002` 或只剩 blocked 项 |
| `resume` | 至少一项可运行；待处理 CP-DESIGN 可见但不阻塞独立切片 |

不存在开发确认 mode。依赖就绪的 `design_ready` 直接进入 `implement`。

## Checkpoint 有效性

- `ui-truth-mapping` 需要当前 eligible 切片和明确 CP-UI；CP-UI 不授权 worktree。
- CP-DESIGN 只绑定明确命名的实质用户决策和当前 `design.md` 精确字节，
  同时授权批准范围内的实现。
- 陈旧 checkpoint 不能越过失败 guard，必须从治理事实重新推导。

## 事实层级

1. `status.json` 与治理产物
2. reconcile 输出
3. 可在漂移时重写的 `todo.md`

依赖和明确 blocker 决定顺序；一个切片等待设计或用户输入，不得阻塞无依赖
切片。CP-UI 前，启用 UI truth 的生产工作不可运行；`existing` 使用普通行为
与语义验证。
