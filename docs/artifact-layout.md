# AI Delivery 产物布局

本文件是客户端 `.ai-delivery/` 工作流的当前布局契约。新需求使用
schema 2.0；旧 schema 中全部处于 `merged` / `archived` 的历史需求只读
兼容，不补造新证据。

## 1. Canonical Home

路径由 `.ai-delivery/meta/project-binding.json` 的 `layout` 定义：

```text
.ai-delivery/
  meta/
    project-binding.json
    workflow-policy.json
  requirements/<req-id>/
    status.json
    requirement.md
    breakdown-summary.md
    global-rules.md
    dependency-graph.json
    progress.md                 # 可选：跨会话恢复记录
    todo.md                     # 非事实源的执行面板
    retrospective.md
    delivery-report.md
    sub-requirements/<SR-xxx>/
      requirement-slice.md
      decisions.md
      README.md
      traceability.json
      design.md                 # 唯一行为与方案设计契约
      verification.md
      contracts/
        ui-truth-index.json     # 仅 figma/runtime-baseline
      visual-acceptance.json    # 仅 figma/runtime-baseline
  retrospectives/
    index.md
```

schema 2.0 不创建 `spec.md`、`plan.md` 或 `tasks.md`。实现时从当前
`design.md`、依赖图、代码和测试动态形成短期执行 brief；文件级修改顺序、
完成项、待办、阻塞和验证结果仅在需要跨会话恢复时写入 `progress.md`。

## 2. 框架隔离

外部框架只提供推理方法与执行纪律，不拥有产物目录。
`.specify/`、`openspec/`、`docs/superpowers/` 和 `.superpowers/` 在编排动作
期间都是只读输入。无法遵守 canonical 输出映射的持久化步骤必须跳过，
不得先生成到外部目录再搬运。

宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。
动作前后必须比较 Git 状态/内容指纹和外部默认输出根的独立文件系统指纹，
包括 ignored 文件、类型、symlink target 和 SHA-256。

`traceability.json` 在 `source_index.design` 中记录 canonical `design.md`
路径、当前 hash、来源关系和采用的推理方法。schema 2.0 不写 `spec_refs`
或 `kind=spec|plan|tasks`；旧终态记录中的这些字段只读保留。

## 3. 状态与设计契约

```text
draft
→ split_ready
→ [acceptance_frozen]
→ design_ready
→ in_dev
→ [visual_acceptance_passed]
→ merged
→ archived
```

方括号状态仅用于 `ui_truth_mode=figma|runtime-baseline`。

每个活跃 schema 2.0 切片都有 `design.md`：

- `state_flow_required=false`：静态行为写明理由；简单状态流使用紧凑表格。
- `state_flow_required=true`：要求状态分类、MVI/UDF 闭环、生命周期、UI
  投影、权威转换矩阵、适用的异步时序、不变量与追踪。
- `user_decision_required=false`：AI 自审，并以 `review_mode=self` 绑定当前
  文件 SHA-256。
- `user_decision_required=true`：仅针对明确命名的实质用户决策进入
  CP-DESIGN，并以 `review_mode=human` 绑定当前文件 SHA-256。该字段描述当前
  设计版本所需的授权类型，批准后仍保持 `true`；是否待确认由当前 human
  review 及其 hash 是否有效决定。

状态流复杂度不会自动产生人工审批。`design.md` 内容变化会使 review hash
失效并重新进入 `solution-design`；当 `user_decision_required=true` 且变更后的
文件尚无有效 human review 时再次进入 CP-DESIGN。有效设计可直接授权其范围
内的开发，不再设置额外的开发确认门槛。

## 4. UI Truth 与验收

- `none`：无可见 UI，不生成 UI truth 或视觉验收产物。
- `existing`：既有视觉表面的行为/语义变更，使用普通行为与语义验证。
- `runtime-baseline` / `figma`：启用 CP-UI、Stage 2、v3
  `ui-truth-index.json`、静态/动效确认及 schema v2
  `visual-acceptance.json`。

真实宿主组件、资源、静态视觉和动效验收约束保持不变。golden 只证明
静态帧；有动效时优先提供确定性 GIF，无法生成时记录原因并在 Stage 4
验收，禁止以 WebP/MP4 或伪造文件补位。

## 5. 验证与归档

`merged` / `archived` 需要带稳定 marker 的 `verification.md`。验证器不依赖
本地化标题。CP-ARCHIVE 后使用 `archive-subrequirement.py` 原位更新状态，
不复制 canonical 产物；后续需求变化创建新的 `<req-id>`。

活跃旧 schema 必须迁移到 2.0 后才能继续；仅历史终态允许只读兼容。
