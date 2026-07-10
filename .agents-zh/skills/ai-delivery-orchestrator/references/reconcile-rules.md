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
7. 输出 `RUNTIME_MODE`、`CHECKPOINT`、`RUNNABLE`、`BLOCKED`、`BLOCKER_SCOPES`、`NEXT_SKILL`、`NEXT_SUBREQ`。

## 运行时模式判定

| 模式 | 条件 |
|------|------|
| `completed` | 所有可执行子需求均为 `merged` |
| `bootstrap` | `status.json` 缺失/不完整或无 `sub_requirements` |
| `confirm_design` | 可运行子需求需设计且 `design_approved=false` → `CHECKPOINT=CP-DESIGN` |
| `confirm_to_dev` | 所有可执行子需求均为 `tasks_ready` → `CHECKPOINT=CP-001` |
| `blocker_recovery` | `current_checkpoint=CP-002` 或仅剩阻塞项 |
| `resume` | 至少一个可运行项；无检查点阻止 |

## 真相层级

1. `.ai-delivery/requirements/<req-id>/status.json` 与治理产物
2. `reconcile-delivery.py` 输出
3. `todo.md` 执行面板（漂移时重写头部）

## 用户入口映射

| 用户意图 | 动作 |
|----------|------|
| 新需求 + 素材 | 对账 → `bootstrap` 或 `resume` |
| 继续编排 | 对账 → `resume`（除非检查点激活）|
| tasks_ready，继续开发 | 对账 → 要求 CP-001 + 全部 `tasks_ready` → `confirm_to_dev` |
| 阻塞已解决 | 对账 → CP-002 → `blocker_recovery` |

## 可运行队列

可运行项指在当前治理真值下可安全推进、无需编造事实的工作。例如：Figma 证据采集、页面外壳、本地状态骨架、导航流、mock 接线、只读路径。

仅有 API 缺口不足以触发 CP-002，若 UI 真值采集或安全局部开发仍可继续。
