# AI Delivery Coordination（独立仓库）

`ai-delivery-coordination` 是与本 kit 配套的编排引擎，已拆出单独版本管理：

| 项 | 值 |
|---|---|
| 本地路径（submodule） | `ai-delivery-coordination/` |
| 独立仓库 | [`s-charvin/ai-delivery-coordination`](https://github.com/s-charvin/ai-delivery-coordination)（可与 `ai-delivery-kit` 同级克隆） |
| 集成方式 | **仅 MCP** — skill 层禁止 `import` coordination Python |

## 克隆 ai-delivery-kit（含 submodule）

```bash
git clone --recurse-submodules https://github.com/s-charvin/ai-delivery-kit.git
# 或已克隆后：
git submodule update --init --recursive
```

## 仅开发 ai-delivery-coordination

```bash
git clone https://github.com/s-charvin/ai-delivery-coordination.git
cd ai-delivery-coordination
pip install -e ".[dev]"
pytest tests/unit --ignore=tests/unit/test_task10_crew.py --ignore=tests/unit/test_crew_bridge.py
```

## 与 skill 层的桥接

- 操作指南：`.agents/skills/ai-delivery-orchestrator/references/coordination-mcp-bridge.md`
- 实现：`ai-delivery-coordination/orchestration/skill_bridge.py`、`ai-delivery-coordination/mcp/loop_registry.py`（在独立仓库内）

产品级 PRD / 场景文档仍留在 `docs/prd/`（描述平台能力，非运行时代码）。
