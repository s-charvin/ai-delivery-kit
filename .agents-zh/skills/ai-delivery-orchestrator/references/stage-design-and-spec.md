# 阶段 3：方案设计 + Spec 管道

阶段 3 在 `design_mode` 为 `light` 或 `full` 时执行 `solution-design`，随后执行 `spec` → `plan` → `tasks`。`design_mode=none` 跳过方案设计产物与门禁。具体工具取决于按 [framework-adaptation.md](framework-adaptation.md) 选定的框架档位。

分发任何框架动作前，先应用[产物边界协议](framework-adaptation.md#产物边界协议必须)：传入 canonical `.ai-delivery` 输出路径，把框架目录当作只读输入，并跳过任何无法遵守该映射的持久化步骤。

## 何时运行

- `solution-design`：启用 UI truth 时处于 `acceptance_frozen`、否则处于 `split_ready`，且 `design_mode=light`，或 `design_mode=full` 且 `design_approved: false` 的子需求。
- `spec` / `plan` / `tasks`：设计模式门禁已满足的子需求，按 reconcile 输出一步一步执行。

## solution-design 动作（HARD-GATE）

<HARD-GATE>
对 `design_mode=full`：方案设计会话结束后，在用户批准设计之前，不要自行撰写 plan/spec 产物。
不要把方案设计文档写进框架自有目录。
用用户当前对话语言把规范方案设计写入 `design.md`（模板：`templates/design-template.md`，删除其中的语言指令注释）；`notes` 只保留单行指针。`design_mode=light` 在完成短方案记录并通过 AI 自审后设 `design_approved=true`，并将 `design_review.reviewed_design_sha256` 绑定到文件精确字节；`design_mode=full` 仅在用户明确批准当前文件后设置，并使用 `design_review.review_mode=human` 与同一哈希。`state_flow_required=true` 时，设计必须包含完整状态流契约：状态所有权分类、MVI 闭环、业务生命周期、UI 投影、权威转换矩阵、适用的异步时序、不变量和追踪。然后进入 `spec` 动作。
</HARD-GATE>

<HARD-GATE>
当 `design_mode=full` 的方案设计门禁尚未满足时，不要执行 `spec`、`plan` 或 `tasks`。`light` 需要短方案记录并自审，`none` 两者都不需要。
</HARD-GATE>

向方案设计会话（原生流程或已安装框架的设计流程，见 [framework-adaptation.md](framework-adaptation.md)）提供：

- `requirement-slice.md`
- 启用 UI truth 的 unit 在记录的用户已批准 workspace 中由 Stage 2 产出的组件 + 有效 v2 `ui-truth-index.json` 的 profile/state/scenario/coverage 与预览/hash 指针（`ui_truth_mode=figma` 或 `runtime-baseline`）
- API 文档（若有）
- 依赖图

可复用的 Markdown 结构见 `templates/design-state-flow-example.md`；仅在 `state_flow_required=true` 时按需读取。它只是通用参考，必须根据当前需求改写，不能复制成项目事实。

方案设计会话应产出：

- 架构（组件树、数据流、状态管理）
- 路由/导航设计（多屏）
- 组件分解策略
- 数据模型草图
- 状态机与数据到 UI 的转换，包括适用的 loading/refreshing/empty/partial/error/offline/auth/permission/disabled 行为
- 引用负责运行时 coverage 的 UI scenario ID；不要在 `design.md` 重复 Runtime Coverage Plan
- 关键技术决策与权衡

对于有状态客户端切片，将转换矩阵视为权威事实源，并用 Mermaid `flowchart`、`stateDiagram-v2` 及适用的 `sequenceDiagram` 作为验收视图。使用复合/并行状态拆解复杂流程，禁止枚举状态笛卡尔积。每个转换在适用时都必须覆盖 guard、成功、失败、取消、过期结果、并发/幂等、持久化与恢复；不适用的时序必须明确写出 `not_applicable`。仍有未决状态流决策时不得批准设计。

执行 CP-DESIGN 前的语言复核（`light` 自审批准前同样执行）。在 `design.md` 中，所有人类可读的标题、表头/单元格、解释性句子、风险/待决问题说明，以及 Mermaid 节点、连线和参与者标签，都必须改为用户当前对话语言。只有机器语法、ID、键、路径、命令、代码/API/库/协议名称和必要的标准技术术语保留英文。`State set`、`Owner`、`Guard`、`Risk` 等模板表头必须翻译；技术术语因精度需要保留时，先写本地化术语，再在括号中保留英文原词。未解释的英文正文或标题会阻断批准。

用用户当前对话语言把方案设计摘要写入 `design.md`，`notes` 只保留单行指针。`design_mode=full` 仅在用户批准后设 `design_approved: true`，并在 `design_review` 记录当前文件哈希；`light` 记录短方案并自审后设置该字段并记录同一哈希。之后任何 `design.md` 修改都会使批准失效并重新打开此动作。

若方案设计与冻结组件 / 已确认预览或需求冲突 → `blocked_spec_mismatch`。

**暂停：** 仅 `design_mode=full` 使用 CP-DESIGN。继续前等待用户明确批准。

## Spec 管道（框架无关）

当设计模式门禁满足后，按 reconcile 输出的动作执行，使用 [frameworks/](frameworks/) 下所选档位的指南：

分发前，分别通过 binding 的 layout key `spec`、layout key `plan` 与 layout key `tasks` 解析 canonical 输出；`spec/spec.md`、`spec/plan.md` 和 `spec/tasks.md` 只是默认布局示例。三个已解析产物的所有人类可读内容都使用用户当前对话语言。机器键、ID、路径、命令、代码符号和协议字面量保持原样。

1. `spec` → `spec.md` — 对照每个已冻结 unit/scenario id 审计。UI truth 切片的视觉输入是 Stage 2 组件 + 已确认预览集合，不是另一份视觉 spec 文档；保留 Figma 来源视觉保真与已批准运行时行为之间的区别。
2. `plan` → `plan.md` — 审计交付切片顺序，并标出由哪个任务实现或验证每个 scenario id。
3. `tasks` → `tasks.md` — 审计粒度、依赖顺序、文件范围，以及完整的 scenario 到测试/验收覆盖。

每步完成后：

- `spec.md` → `spec_ready`
- `plan.md` → `plan_ready`
- `tasks.md` → `tasks_ready`

无论哪个档位，产物都要记入 `traceability.json` `spec_refs`（见 [framework-adaptation.md](framework-adaptation.md) → 可追溯性）。`spec`、`plan` 与 `tasks` 的每个 `artifacts[]` 条目都必须记录解析后的仓库相对 `canonical_path` 和当前 `content_sha256`，供 artifact-layout validator 检测 drift。不要 fork 或复述框架管道技能来重述仓库本地契约。

## 暂停

所有可执行子需求达 `tasks_ready` 后，进入 CP-001，开发前与用户确认。

## 归档后的产物

子需求进入 `archived` 后，archive 动作只原位更新 `status.json`。canonical
spec、plan、tasks、design 和 verification 继续保留在原路径，不生成快照或
第二份副本；后续需求变更须新建 `<req-id>` 目录。

## API 策略

API 文档直接传给 spec 管道与实现。无独立 API 映射阶段。缺口在 `notes` 记为 `integration_deferred`；不阻塞只读 UI 证据，但生产外壳工作仍等待 CP-UI。

## 不启用 UI truth 的模式

- `ui_truth_mode=none` 或 `existing` 跳过 UI 真值映射（不要求 `acceptance_frozen`）。
- `split_ready` → 仅在 `design_mode` 为 `light` 或 `full` 时进入 `solution-design` → spec 管道。
- `existing` 使用普通项目行为/语义验证；`none` 与 `existing` 合并时跳过 `visual_acceptance_passed`。
