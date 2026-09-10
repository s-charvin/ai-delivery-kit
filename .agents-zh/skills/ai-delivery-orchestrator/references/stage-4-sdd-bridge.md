# 阶段 4：实现衔接

将编排器阶段 4（`implement` 动作）映射到任务级执行与 `.ai-delivery` 进度产物。具体执行方式跟随所选档位 —— [frameworks/superpowers.md](frameworks/superpowers.md)（子代理驱动）、[frameworks/ecc.md](frameworks/ecc.md)（代理驱动）或 [frameworks/native.md](frameworks/native.md)（内联纪律）。

## 何时运行

CP-001 用户确认后，当对账输出 `RUNTIME_MODE=confirm_to_dev` 且 `NEXT_ACTION=implement` 时。

**CP-001 确认前禁止 dispatch 实现工作。**

`ui_truth_mode=figma` 或 `runtime-baseline` 的切片恢复 Stage 2 记录的用户已批准 workspace。禁止再运行 `using-git-worktrees` 为同一切片创建第二个 workspace；`none` 与 `existing` 遵循 [workspace-policy.md](workspace-policy.md)，默认使用当前 checkout。

## tasks.md → 任务简报

对 `tasks.md` 中每个任务行：

| tasks.md 字段 | 执行映射 |
|---------------|----------|
| 任务标题 / ID | 实现者 prompt 标题 |
| 范围 / 文件 | 单文件编辑规则的允许编辑面 |
| 依赖 | 任务间顺序 |
| 验收说明 | TDD 成功标准 |

每个任务一轮执行：新上下文（档位支持时用子代理）→ 实现 → 评审 → 在台账中标记完成。

当评审或实现循环产生具有复用价值的问题时，在开始下一个方案前记录到需求级
`retrospective.md`，然后告诉用户记录了什么。遵循
[retrospective-guidance.md](retrospective-guidance.md)。归档前台账必须存在，
但可以没有问题行；这不增加实现阶段门禁。

## progress.md ↔ 台账

追加到 `.ai-delivery/requirements/<req-id>/progress.md`：

- `tasks.md` 中已完成任务 ID
- 实现者会话备注（阻塞、延期集成）
- 评审结果

`progress.md` 仅为抗压缩辅助。恢复时对账仍以 `status.json` 与磁盘产物为准——不得仅凭 progress 提升门禁。

## 双阶段评审

两个阶段都走[评审循环](stage-implementation.md#评审循环任务级闭环)：实现 → 新鲜上下文评审 → finding 成为修复简报 → 复审，直到干净或 `review_loop.max_rounds` 预算耗尽（然后升级给用户；绝不自动合并）。

1. **每任务评审** — 每个任务完成后；每轮的 finding 与修复摘要记入 `progress.md`。
2. **合并前评审** — 全部任务后做切片级评审；启用 UI truth 能力时再做视觉验收与验证步骤。

## 视觉验收证据（UI truth 能力）

设置 `visual_acceptance_passed` 前，使用 `templates/visual-acceptance-template.json` 实例化 `sub-requirements/<subreq-id>/visual-acceptance.json`。保持机器键/枚举不变，并用用户当前对话语言填写摘要和说明。

schema v2 产物必须绑定当前 v3 `ui-truth-index.json` 的 SHA-256，并恰好为每个已索引 scenario id 提供一条结果。`passed` 证据必须同时匹配冻结的 `evidence_scope` 与 `review_mode`：

- `component-only` 的视觉验收使用索引中的冻结 preview；需要行为验收时使用组件测试或明确的人工行为审阅。不得包含 `runtime-capture`，也不得声称宿主组合通过。
- `host-static` 与 `host-runtime` 必须提供 `runtime-capture`：截图路径/hash、产出截图的测试路径/hash、几何/landmark 断言报告路径/hash、命令、绑定截图 hash 的评审者信息，以及与 `host_binding` 一致的宿主 provenance。

运行时截图路径必须位于索引声明的项目原生测试证据根目录，并且必须在 `.ai-delivery/` 外。`manual` 摘要即使写了截图文件名也仍只是文字，不能替代 `runtime-capture`。`waived` 必须记录用户身份、时间戳与理由。所有文件路径均为仓内相对路径并校验 hash。

no-golden waiver 只作用于对应组件 preview，不会自动要求或豁免宿主截图。motion waiver 只作用于动效验收，不改变静态组件或宿主证据范围。

对于 UI truth 切片，该产物还必须包含 `motion_acceptance`，并为每个已索引 `unit_id` 恰好提供一条记录。记录的 `result` 为 `passed` 或 `waived`；静态 unit 必须以明确的 `test` 或 `manual` 证据通过，绝不能豁免。已索引动效预览的动态 unit 必须提供路径和 SHA-256 一致的 `motion` 证据；宿主无法确定性生成动效预览时，`passed` 必须提供独立的 Stage 4 运行时 `test` 或 `manual` 证据，`waived` 必须记录用户身份、时间戳和理由。静态 golden 证据不能替代每个 unit 独立的动效验收。

有稳定 Figma 参考位图时，image-diff 证据记录 reference/candidate/diff 的路径与 hash、metric、threshold、actual、命令和摘要。没有稳定位图时，使用精确设计数值映射、确定性预览与用户确认；不得声称做过自动像素等价比较。

## 状态链

```
tasks_ready → (CP-001) → in_dev → visual_acceptance_passed（UI truth 能力）→ merged
```

`ui_truth_mode=none` 与 `existing` 跳过 `visual_acceptance_passed`；existing UI 变更使用普通行为和语义证据。

## 切片完成后 handoff

见 [stage-implementation.md](stage-implementation.md) 的 PR / babysit 收尾步骤。
