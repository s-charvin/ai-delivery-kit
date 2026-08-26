# 对账规则

每次恢复或继续前，在信任 `todo.md` 之前运行对账。

## 命令

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

Bootstrap 后可用 `.ai-delivery/scripts/` 下的校验器；本 kit 仓库内可用 skill 本地路径。

## 步骤（脚本实现；主会话验证）

1. 重读 `status.json` 并扫描需求产物。
2. 重检守卫（post-freeze 状态的契约校验）。
3. 按 `blocker_scope` 分类每个阻塞。
4. 守卫已满足则不重跑该阶段。
5. 产物存在但守卫失败 → 重跑或开最窄阻塞。
6. 阻塞项留在队列；不依赖它的后续项继续。
7. 输出 `RUNTIME_MODE`、`CHECKPOINT`、`RUNNABLE`、`BLOCKED`、`BLOCKER_SCOPES`、`NEXT_ACTION`、`NEXT_SUBREQ`。动作是抽象的（`solution-design` / `spec` / `plan` / `tasks` / `implement` / `finish`，另含 kit 自有技能）；按 [framework-adaptation.md](framework-adaptation.md) 映射到所选框架档位。

## 运行时模式判定

| 模式 | 条件 |
|------|------|
| `completed` | 所有可执行子需求均为 `merged` |
| `bootstrap` | `status.json` 缺失/不完整或无 `sub_requirements` |
| `confirm_ui` | `split_ready` 且 `ui_truth_mode=figma` 或 `runtime-baseline` 的切片需要 Stage 2 生产代码授权且无其他可运行项 → `CHECKPOINT=CP-UI`、`NEXT_ACTION=none` |
| `confirm_solution_design` | `design_mode=full` 的子需求需方案设计批准且无其他可运行项 → `CHECKPOINT=CP-DESIGN` |
| `confirm_to_dev` | 所有可执行子需求均为 `tasks_ready` → `CHECKPOINT=CP-001` |
| `blocker_recovery` | `current_checkpoint=CP-002` 或仅剩阻塞项 |
| `resume` | 至少一个可运行项；无检查点阻止。完整方案设计待批时仍以 `CHECKPOINT=CP-DESIGN` 提示，其他可运行工作继续推进 |

## 检查点有效性

检查点是凭证，不是历史记录。已记录的检查点只在其守卫仍成立时有效：

- `NEXT_ACTION=ui-truth-mapping` 要求当前存在 `split_ready` 且 `ui_truth_mode=figma` 或 `runtime-baseline` 的切片，且用户明确授权已记录为 `current_checkpoint=CP-UI`。首次到达时输出 `confirm_ui` 与 `NEXT_ACTION=none`；守卫不再成立后，陈旧 CP-UI 失效。
- `confirm_to_dev` 要求当前所有可执行子需求都处于 `tasks_ready`。回退（如某子需求回到 `spec_ready`）后残留的旧 `current_checkpoint=CP-001` 不授权 `implement`。
- `NEXT_ACTION=implement` 额外要求用户确认已记录在 `status.json`（全部 `tasks_ready` 之上叠加 `current_checkpoint=CP-001`）。首次到达全部 `tasks_ready` 时输出 `NEXT_ACTION=none`，直到用户确认。
- 不得把已记录的检查点当作绕过失败守卫的捷径；一律从当前治理真值重新推导。

## 真相层级

1. `.ai-delivery/requirements/<req-id>/status.json` 与治理产物
2. `reconcile-delivery.py` 输出
3. `todo.md` 执行面板（漂移时重写头部）

## 用户入口映射

| 用户意图 | 动作 |
|----------|------|
| 新需求 + 素材 | 对账 → `bootstrap` 或 `resume` |
| 继续编排 | 对账 → `resume`（除非检查点激活）|
| UI truth 能力待授权 | 对账 → 要求 CP-UI → `confirm_ui`；确认后 dispatch `ui-truth-mapping` |
| tasks_ready，继续开发 | 对账 → 要求 CP-001 + 全部 `tasks_ready` → `confirm_to_dev` |
| 阻塞已解决 | 对账 → CP-002 → `blocker_recovery` |

## 可运行队列

可运行项指在当前治理真值下可安全推进、无需编造事实的工作。CP-UI 前，启用 UI truth 的工作仅限只读证据与治理产物；页面外壳、本地状态骨架、导航流、mock 接线及其他生产代码改动，只有进入按 [workspace-policy.md](workspace-policy.md) 解析的用户已批准 workspace 后才可运行。CP-UI 授权受控 UI 工作，不授权 worktree。`ui_truth_mode=existing` 可在无 CP-UI 下进行普通行为和语义工作。

仅有 API 缺口不足以触发 CP-002，若 UI 真值采集或安全局部开发仍可继续。
