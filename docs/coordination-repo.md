# Coordination（独立仓库）

`coordination` 引擎已从本仓库拆出，单独版本管理：

| 项 | 值 |
|---|---|
| 本地路径（submodule） | `coordination/` |
| 独立仓库 | [`../coordination`](https://github.com/s-charvin/coordination)（与 `ai-delivery-kit` 同级） |
| 集成方式 | **仅 MCP** — skill 层禁止 `import` coordination Python |

## 克隆 ai-delivery-kit（含 submodule）

```bash
git clone --recurse-submodules https://github.com/s-charvin/ai-delivery-kit.git
# 或已克隆后：
git submodule update --init --recursive
```

## 仅开发 coordination

```bash
git clone https://github.com/s-charvin/coordination.git
cd coordination
pip install -e ".[dev]"
pytest tests/unit --ignore=tests/unit/test_task10_crew.py --ignore=tests/unit/test_crew_bridge.py
```

## 与 skill 层的桥接

- 操作指南：`.agents/skills/ai-delivery-orchestrator/references/coordination-mcp-bridge.md`
- 实现：`coordination/orchestration/skill_bridge.py`、`coordination/mcp/loop_registry.py`（在 coordination 仓库内）

产品级 PRD / 场景文档仍留在 `docs/prd/`（描述平台能力，非运行时代码）。
