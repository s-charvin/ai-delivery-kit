# Coordination MCP 桥接

`ai-delivery-coordination/` 是与 ai-delivery-kit 配套的**可独立部署引擎**。skill 层**禁止** `import` 其 Python 模块。一切自主执行须经运行中的 coordination 服务 **MCP 工具**完成。

## 何时使用

- 需要 ECC 风格的长时 implement 循环（检查点恢复、停滞监控、成本预算）
- 需要人工介入（`intervene_loop`）且不想手改 `status.json`

常规治理交付仍走 reconcile + 抽象动作（`design` / `spec` / `implement` / `finish` / `archive`）。循环模式为可选，**不得**绕过门禁、`verification.md` 或 CP-ARCHIVE。

## MCP 工具

| 工具 | 用途 |
|------|------|
| `start_loop` | `req_root` → `skill_bridge` 加载 `status.json`，启动 `LoopRunner` |
| `stop_loop` | 取消运行 |
| `loop_status` | 查看 runner 与节点状态 |
| `stall_report` | ALR-1/2/4/15 停滞可见性 |
| `intervene_loop` | 人工：`pause`、`resume`、`cancel`、`retry_node`、`skip_node`、`approve_overbudget` |

`resume` 与 `approve_overbudget` **必须**提供非空 `reason`（审计）。

## 真值边界

| 层 | 拥有 |
|----|------|
| Skill（`status.json`） | Spec 段：`draft` … `tasks_ready`、`archived`、检查点 |
| Coordination 引擎 | 执行视图：`in_dev`、`merged`、`blocked_*` |
| `skill_bridge.flush_back` | **仅**写回执行段状态，然后运行 `reconcile-delivery.py` |

引擎不缓存对账结论；每次 flush 后 reconcile 重新推导 `next_action`。

## 操作清单

1. 确认对账队列正常（重自治前须 `tasks_ready` 且 CP-001 已清）。
2. 用绝对路径 `start_loop(req_root=...)`。
3. 监控 `loop_status` / `stall_report`；停滞或超预算（ALR-15）用 `intervene_loop`。
4. 切片到 `merged` 后回到 skill 层 `finish` / `archive` — 循环**不会**自动归档。

实现参考（[ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) 仓库）：`orchestration/skill_bridge.py`、`mcp/loop_registry.py`。
