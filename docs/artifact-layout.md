# 产物布局统一规则（One Rule）

本文件是 `ai-delivery-kit` 治理产物的**唯一布局契约**。所有 skill 层与 `coordination/` 引擎都必须遵守：最终产物有且只有一个规范家（canonical home），框架特定目录（`.specify/`、`openspec/`）只是**派生 / 同步视图**，不是真值所在地。

> 适用边界：**仅对新 `ai-delivery init` 的仓库生效**。旧仓库的散落布局不做迁移。

## 1. 规范家（Canonical Home）

所有产物都位于 `.ai-delivery/` 之下；具体路径由 `.ai-delivery/meta/project-binding.json` 的 `layout` 段定义（解析器见 `scripts/layout.py` 与 `coordination/config/paths.py`）。

```
.ai-delivery/
  meta/
    project-binding.json      # layout 段 = 路径常量唯一 JSON 源
    workflow-policy.json
    naming-rules.json
  requirements/<req-id>/
    status.json  requirement.md  breakdown-summary.md  global-rules.md
    dependency-graph.json        # 依赖数据唯一 canonical 形态
    progress.md  todo.md
    delivery-report.md           # 新增：结项报告（archive 动作产出）
    sub-requirements/<SR-xxx>/
      requirement-slice.md  decisions.md  README.md  traceability.json
      design.md                  # 新增：真实设计文件（替代 status.json notes 碎片）
      verification.md            # 新增：verify-before-completion 证据
      spec/  spec.md plan.md tasks.md      # canonical 三件套
      contracts/  ui-contract-index.json  <unit-id>/ui-contract.html
      visual-acceptance.md | visual-acceptance/*.png
      archive/<ISO-ts>/          # flow-forward 冻结区
        spec.md plan.md tasks.md design.md verification.md
        MANIFEST.json            # sha256 清单，不可变性的机器校验依据
```

## 2. 派生视图（Derived Views）

框架目录只承载**同步副本**，不得作为真值：

- `.specify/`：spec-kit 产物视图
- `openspec/changes/<change>/`：OpenSpec 产物视图

同步方向固定为：**框架执行 → 产物落框架目录 → 动作收尾拷回 canonical 并记 hash → 后续 gate 只读 canonical**。不用 symlink（Windows 兼容风险）。`traceability.json.spec_refs` 每项扩展为：

```json
{
  "kind": "spec",
  "tier": "openspec",
  "canonical_path": ".ai-delivery/requirements/<req>/sub-requirements/<SR>/spec/spec.md",
  "derived_paths": ["openspec/changes/<change>/specs/.../spec.md"],
  "content_sha256": "<sha256 of canonical>",
  "sync_state": "synced"
}
```

## 3. spec 演进约定（spec-kit 视角）

- **活跃开发期**（status < `archived`）= **living spec**：`spec/spec.md` 唯一事实源，`plan.md`/`tasks.md` 是派生物，可随 spec 再生。再生前，被推翻的关键决策必须先落入 `decisions.md`（防 rationale 丢失）。
- **完结后**（status = `archived`）= **flow-forward**：`archive/` 区冻结不可变（由 `MANIFEST.json` 的 sha256 校验）；需求变更→开新 `<req-id>/`，旧目录只读引用。

## 4. 统一路径常量

- 唯一 JSON 源：`.ai-delivery/meta/project-binding.json` 的 `layout` 段。
- skill 侧读取器：`.agents/skills/ai-delivery-orchestrator/scripts/layout.py`
- 引擎侧读取器：`coordination/config/paths.py`（不依赖 skill 层，只读同一 JSON）
- hash 规范化（两侧一致）：去 CRLF、去行尾空白、去文末空白后再算 sha256，避免误报。

## 5. 其他收敛规则

- **ui-contract 索引**：新增 `contracts/ui-contract-index.json`；reconcile 的 `find_contracts` 改为索引优先、rglob 兜底并报告孤儿。
- **依赖数据收敛**：`dependency-graph.json` 为唯一 canonical；per-subreq `dependency.json` 降为派生视图。
- **验证器去重**：`.ai-delivery/meta/scripts/*.py` 为运行位置（bootstrap 从 kit 拷贝）；删 reconcile 的三候选路径探测，改经 `layout.py` 解析唯一路径。
- **hooks 收敛**：`.cursor/.claude/.codex` 下同名脚本由 bootstrap 生成 2 行 wrapper 指向 canonical 实现。
- **测试夹具迁出治理区**：`.ai-delivery/requirements/example-requirement/**` → `tests/ai-delivery-contracts/fixtures/example-requirement/**`。
- **native tier 拆 plan/tasks**：统一规则下 `spec/plan.md` 必须真实存在（归档要三件套）；不再允许 `plan_path→tasks.md` 特例。
