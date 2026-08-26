# 产物布局统一规则（One Rule）

本文件是 `ai-delivery-kit` 治理产物的**唯一布局契约**，仅描述客户端 `.ai-delivery/` 工作流。

> 适用边界：**仅对新 `ai-delivery init` 的仓库生效**。旧仓库的散落布局不做迁移。

## 1. 规范家（Canonical Home）

所有产物都位于 `.ai-delivery/` 之下；具体路径由 `.ai-delivery/meta/project-binding.json` 的 `layout` 段定义（skill 解析器：`scripts/layout.py`）。

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
      design.md                  # 新增：规范方案设计文件（solution-design；替代 status.json notes 碎片）
      verification.md            # 新增：verify-before-completion 证据
      spec/  spec.md plan.md tasks.md      # canonical 三件套
      contracts/  ui-truth-index.json   # 仅 ui_truth_mode=figma/runtime-baseline
      visual-acceptance.json      # 仅 UI truth 模式；绑定当前 UI index 与逐 scenario 的结构化验收证据
      archive/<ISO-ts>/          # flow-forward 冻结区
        spec.md plan.md tasks.md design.md verification.md
        MANIFEST.json            # sha256 清单，不可变性的机器校验依据
```

## 2. 框架隔离（无派生治理视图）

外部框架只提供方法与执行纪律，不拥有产物目录。所有流程/治理产物直接写入上面的 canonical `.ai-delivery` 路径；`.specify/`、`openspec/`、`docs/superpowers/`、`.superpowers/` 等目录在编排动作期间只能作为既有只读输入，不能承载同步副本。

调用外部 skill 或命令前必须传入明确 canonical 输出映射。若它不能覆盖默认路径，则跳过该持久化步骤，在当前会话应用其方法并直接写 canonical 产物。禁止先生成到框架目录再复制或搬运。

宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。`traceability.json.spec_refs` 记录使用的框架方法和 canonical hash；兼容字段 `derived_paths` 恒为空：

```json
{
  "spec_refs": {
    "tier": "openspec",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": ".ai-delivery/requirements/<req>/sub-requirements/<SR>/spec/spec.md",
        "derived_paths": [],
        "content_sha256": "<sha256 of canonical>",
        "sync_state": "synced"
      }
    ]
  }
}
```

## 3. spec 演进约定

- **活跃开发期**（status < `archived`）= **living spec**：`spec/spec.md` 唯一事实源，`plan.md`/`tasks.md` 是派生物，可随 spec 再生。再生前，被推翻的关键决策必须先落入 `decisions.md`（防 rationale 丢失）。
- **完结后**（status = `archived`）= **flow-forward**：`archive/` 区冻结不可变（由 `MANIFEST.json` 的 sha256 校验）；需求变更→开新 `<req-id>/`，旧目录只读引用。

## 4. 统一路径常量

- 唯一 JSON 源：`.ai-delivery/meta/project-binding.json` 的 `layout` 段。
- skill 侧读取器：`.agents/skills/ai-delivery-orchestrator/scripts/layout.py`
- coordination MCP（可选）：读取同一 `project-binding.json` layout 段（见 coordination 仓库 `config/paths.py`）
- hash 规范化（两侧一致）：去 CRLF、去行尾空白、去文末空白后再算 sha256，避免误报。

## 5. 能力模式与其他收敛规则

### 5.1 两条独立模式轴

每个 sub-requirement 在 `status.json` 中声明：

- `ui_truth_mode`: `none`（无可见 UI）、`existing`（既有视觉表面的行为/语义变化）、`runtime-baseline`（无稳定 Figma 真值的新可见 UI）或 `figma`（稳定 Figma 证据）。只有后两者启用 CP-UI、Stage 2、`acceptance_frozen`、UI truth index 与 visual acceptance。
- `design_mode`: `none`（不生成 `design.md`）、`light`（短方案设计记录并自审）或 `full`（完整方案设计并需要 CP-DESIGN）。
- `ui_bearing` 保留为与 `ui_truth_mode` 一致性校验字段，不再作为 UI gate 的独立来源。

`design.md` 与 `design-template.md` 是稳定 canonical 路径；人类语义统一称为 `solution-design`。设计文档只引用 UI truth index 中的 `unit_id` / `scenario_id`，Runtime Coverage Plan 的唯一事实源仍是 `contracts/ui-truth-index.json`，不得在 design.md 重复维护。

`design-template.md` 的 `ai-delivery-meta` 固定声明 `artifact_type=solution-design`、`layout_key=solution_design` 与 `canonical_path=design.md`；实例化时只替换时间戳/作者占位符，并删除语言指令注释。

### 5.2 UI truth 索引

- **ui-truth 索引**（已完成）：v2 `contracts/ui-truth-index.json` 只存仓内相对指针与治理信息（truth mode/source、`component_path` / `preview_path` / Flutter `golden_test`、profile/state/scenario/coverage、SHA-256 与预览绑定确认）。不再解析 `#ui-contract-meta`，不再 rglob `ui-contract.html`，也不保留 v1 兼容分支。
- **UI 验收**：`visual-acceptance.json` 绑定当前 `ui-truth-index.json` 哈希，逐 scenario 保存 `passed | waived` 与模式对应的 preview/test/manual/image-diff 证据；旧 Markdown/截图目录存在性不再构成 gate。
- **依赖数据收敛**（已完成）：`dependency-graph.json` 为唯一 canonical；缺失时 reconcile 才 fallback 读 per-subreq `dependency.json` 并输出 `[WARN]`。
- **验证器去重**（已完成）：bootstrap 播种到 `.ai-delivery/scripts/`；reconcile 经 `layout.py` 的 `resolve_validator_script` 单一入口解析。
- **UI git hook 已拆除**：不再注入 `validate-ui-contract.sh` 或 `ui-contract-gate` 规则。升级时从已有 IDE JSON **剥离**旧 hook 组。
- **测试夹具迁出治理区**（已完成）：`tests/ai-delivery-contracts/fixtures/example-requirement/**`；`zero-based-flow.test.sh` 运行时复制到临时目录再断言。
- **native tier 拆 plan/tasks**（已完成）：统一规则下 `spec/plan.md` 必须真实存在（归档要三件套）；不再允许 `plan_path→tasks.md` 特例。

## 6. 验证纪律（verification_policy）

`merged`（以及 Phase 3 后的 `archived`）状态必须有 `verification.md` 硬证据，否则 `validate-delivery-status.py` 拒绝该状态：

- 策略声明于 `.ai-delivery/meta/workflow-policy.json` 的 `verification_policy` 段（新布局仓库由 Go bootstrap 播种，见 `internal/bootstrap/engine.go`）。
- `verification.md` 的人类可读标题与正文使用用户当前对话语言；验证器只检查三个稳定标记，不绑定具体语言：`ai-delivery-verification:review-rounds`、`ai-delivery-verification:commands-results`、`ai-delivery-verification:sign-off`。
- 向后兼容：仅当子需求目录是新布局（存在 `spec/` 目录）时才强制；旧布局 `merged` 不受影响。

## 7. spec 持久化策略（spec_persistence）

执行语义由 `workflow-policy.json` 的 `spec_persistence` 段声明（声明式，超前写入无害）：

- `active: "living"` — 未 `archived` 前，`spec/spec.md` 唯一事实源，plan/tasks 可派生重生成（重生成前关键决策先入 `decisions.md`）。
- `complete: "flow_forward"` — `archived` 后 `archive/<ISO-ts>/` 冻结只读；变更需求须开新 `<req-id>/`，旧目录仅作引用。
- drift 检测：当 `spec/spec.md` 内容 sha256 与 `traceability.json.spec_refs` 记录不一致时，活跃期派生状态（`plan_ready`/`tasks_ready`）降级为 `spec_ready`（`reconcile` 纯推导、不写 status.json；`validate-artifact-layout.py --verify-archive` 报告 `[DRIFT]`），由 skill 层重生成派生物。
