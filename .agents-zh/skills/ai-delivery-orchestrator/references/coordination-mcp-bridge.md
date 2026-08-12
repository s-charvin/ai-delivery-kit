# Coordination MCP 桥接

`ai-delivery-coordination` 是**独立 skill + MCP 服务**（不属于本 kit，也不在 `.ai-delivery/` 内）。skill 层**禁止** `import` 其 Python 模块。一切自主执行须经用户安装的 coordination **MCP 工具**完成。

## 轻约束原则（面向 AI）

coordination 是**状态 + 协议**层，不是产物格式警察：

| 原则 | 含义 |
|------|------|
| 形态自治 | 业务方与 hub 方自行决定产物存哪、什么格式。coordination **不校验**目录树或 schema。 |
| 状态 + 提示 | 更新任务状态时可附带 `context` / `artifact_hints`（自由文本或 JSON，类似提示词扩充）。coordination 只存转发，**不解析语义**。 |
| AI 自决消费 | 使用方根据 `hub://` 指针、hints 与自身上下文自行获取产物。不强制拉内容，注册时不做 sha256 门禁。 |
| 仅核心协议 | 状态机合法边、认领租约、`hub://` 解析、跨管线环检测、审计。 |

kit 的 `.ai-delivery/` 布局契约仍约束经 `ai-delivery init` 播种的治理仓；coordination **不**把该契约推广到第三方 hub。

## 何时使用

- 带检查点恢复、停滞与成本监督的 ECC 式 implement 循环
- 跨方任务认领 / 状态 / 依赖调度（无需共享文件系统）
- 人工介入（`intervene_loop`）而不手改 `status.json`

日常受治理交付仍走 reconcile + 抽象动作（`design` / `spec` / `implement` / `finish` / `archive`）。循环模式可选，且**永不**绕过门禁、`verification.md` 或 CP-ARCHIVE。

## MCP 工具 — 循环

| 工具 | 用途 |
|------|------|
| `start_loop` | `req_root` → 经 `skill_bridge` 加载 `status.json`，启动 `LoopRunner` |
| `stop_loop` | 取消 runner |
| `loop_status` | 检视 runner + 节点状态 |
| `stall_report` | ALR-1/2/4/15 停滞可见性 |
| `intervene_loop` | 人工：`pause` / `resume` / `cancel` / `retry_node` / `skip_node` / `approve_overbudget` |

`resume` 与 `approve_overbudget` **必须**提供非空 `reason`（审计）。

## MCP 工具 — hub 指针与认领

| 工具 | 用途 |
|------|------|
| `register_pipeline` | 注册管线元数据（包装 `create_pipeline`） |
| `register_artifact_ref` | 登记 `hub://pipeline/node@version` + 可选 `uri` / `hints`（**仅指针**） |
| `resolve_hub_ref` | 解析指针 → `{uri, version, hints, status}` — **不拉内容** |
| `list_artifact_refs` | 列出已登记指针 |
| `claim_node` / `release_claim` | 租约认领（冲突返回 `E_ALREADY_CLAIMED`） |
| `report_node_status` | 合法状态转移 + 可选 `context` / `artifact_hints` |
| `list_claimable_nodes` | READY 且未认领；上游是否满足（只看状态 / 是否有 ref） |
| `schedule_dependents` | 节点 `done` 后解锁下游 BLOCKED→READY；发出跨管线通知并尝试 hub 解阻 |
| `apply_hub_upstream_done` | 跨 pipeline 上游 `done` 后解锁依赖方 BLOCKED→READY |
| `list_notices` / `ack_notices` | 轮询 / 确认 coordination 通知（webhook 为 best-effort） |

### 无 kit 方 CLI

```bash
coordination-cli register --pipeline X --node Y --version 1 --uri ...
coordination-cli resolve hub://X/Y@1
coordination-cli notices --pipeline X --unread
```

### SR ↔ hub:// 映射

子需求 `SR-001` 在 pipeline `login-client` 下的规范指针：

`hub://login-client/SR-001@1`

`pipeline_id` 默认取 `status.json` → `requirement_id`。

### 状态映射（flush_back）

| Coordination | Kit `status.json` |
|--------------|-------------------|
| `pending_review` / `review` / `in_progress` | `in_dev` |
| `done` | `merged` |
| `ready` / spec 段 `blocked_*` | 不回写 |

### `start_loop` + `respect_claims`

`start_loop(req_root, respect_claims=true)` 时，循环**仅调度**已有有效 claim 租约的 READY 节点。

### 认领工作流

1. `register_pipeline`（一次）→ 各方发布产物后 `register_artifact_ref`。
2. `list_claimable_nodes` → `claim_node`。
3. 用各自原有存储完成工作；可选 `report_node_status` 附带 hints。
4. 合法转移到 `done` 后 `schedule_dependents`，供他方认领。

### AI 消费指南

1. 调用 `resolve_hub_ref("hub://…")` 或 `list_claimable_nodes`。
2. 读取 `uri` + `hints` + `context`。
3. 自行 clone / open / download。失败则重试或问人 — coordination **不保证**可达。

## 真值边界

| 层 | 拥有 |
|----|------|
| 各方 / hub | 产物字节与存储形态 |
| Skill（`status.json`） | spec 段：`draft` … `tasks_ready`、`archived`、CP 检查点 |
| Coordination STORE | 节点状态机、认领租约、依赖就绪 |
| Coordination REFREG | `hub://` 指针 + 可选 uri/hints（非内容） |
| `skill_bridge.flush_back` | **只**写回 kit `status.json` 的执行段，然后 reconcile |

跨仓执行**必须**经 coordination MCP — 不得本地伪造 hub 状态。

## 操作清单（循环）

1. 确认 reconcile 队列正常（重自治前 `tasks_ready` + CP-001）。
2. 用绝对路径 `req_root` 调用 `start_loop`。
3. 监控 `loop_status` / `stall_report`；停滞或超预算用 `intervene_loop`。
4. 切片到 `merged` 后回到 skill 层 `finish` / `archive` — 循环**不会**自动归档。

实现参考（[ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination)）：`orchestration/skill_bridge.py`、`mcp/loop_registry.py`、`mcp/ref_claim_tools.py`、`repo/hub_ref.py`。
