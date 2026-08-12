# AI Delivery Coordination（独立 skill + MCP 服务）

`ai-delivery-coordination` **不属于** ai-delivery-kit，也**不在** `.ai-delivery/` 布局内。它是独立的 skill + MCP 服务，用户按需安装后通过 MCP 与客户端工作流协作。

| 项 | 值 |
|---|---|
| 独立仓库 | [`s-charvin/ai-delivery-coordination`](https://github.com/s-charvin/ai-delivery-coordination) |
| 集成方式 | **仅 MCP** — kit skill 层禁止 `import` coordination Python |
| 职责边界 | 多方认领、状态机、`hub://` 指针、跨仓依赖协议 |
| kit 职责 | `.ai-delivery/` 客户端工作流（`status.json`、门禁、产物布局） |

## 安装与启用

1. 克隆并安装 coordination（skill + MCP 服务）：

```bash
git clone https://github.com/s-charvin/ai-delivery-coordination.git
cd ai-delivery-coordination
pip install -e ".[dev]"
```

2. 在 Cursor / IDE 中启用 coordination MCP server（见 coordination 仓库 README）。

3. 客户端仓库仅保留 ai-delivery-kit（`ai-delivery init`）— **无需** submodule，**无需**在 `.ai-delivery/` 内放置 coordination 代码。

## 与 kit 的边界

| 层 | 拥有 |
|----|------|
| **kit / `.ai-delivery`** | spec 段状态、子需求布局、`dependency-graph.json`（含可选 `hub_refs` 声明） |
| **coordination MCP** | 执行段认领、节点状态机、hub 指针注册与解析 |
| **桥接** | MCP 工具（`start_loop`、`claim_node`、`register_artifact_ref` 等） |

kit 侧操作指南：`.agents/skills/ai-delivery-orchestrator/references/coordination-mcp-bridge.md`

coordination 侧实现与文档：coordination 仓库 `docs/coordination/artifact-refs-and-claims.md`

产品级 PRD / 场景文档留在本仓库 `docs/prd/`（描述平台能力，非运行时代码）。
