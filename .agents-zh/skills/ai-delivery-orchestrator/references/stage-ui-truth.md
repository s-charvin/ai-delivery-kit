# 阶段 2：UI 真值映射

## 何时运行

对每个 `split_ready` 且 `ui_truth_mode=figma` 或 `runtime-baseline`、已记录 CP-UI 用户授权的子需求。`none` 与 `existing` 不进入此阶段。

Stage 2 会写生产代码，因此它是**受控视觉实现阶段**，不是“不含实现的 mapping”。

## 准备输入

- 阅读 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/requirement-slice.md`。
- `figma` 模式收集 Figma file key 与目标 node id；`runtime-baseline` 模式收集定义运行时基线的 requirement、project 或 user-decision 来源，不得伪造 Figma 来源。
- 从仓库判断宿主栈（优先 Flutter）。拿不准就停下问用户。
- 按 [workspace-policy.md](workspace-policy.md) 解析用户已批准 workspace。除非用户为当前子需求明确批准了准确的项目内 worktree，否则使用当前 checkout；在 `decisions.md` 或 `progress.md` 记录选择，并贯穿 Stage 3 与 Stage 4 复用。

## 仅运行受控的 `ui-truth-mapping`（Stage 2）

Stage 2 **只跑 `ui-truth-mapping`**。此阶段不要跑 `figma-design-to-code`。Stage 2 混用会搞乱归属。**Stage 4 默认也不再跑** — 接线已经写好的组件（见 [stage-implementation.md](stage-implementation.md)）。

传入需求切片与模式对应的真值来源。每个独立 unit 产出 **真实宿主栈组件**（Flutter：邻接生产文件旁的 Widget + golden/behavior tests），并为每个视觉 scenario 生成官方栈预览。写组件代码前，必须完成 `ui-truth-mapping` 的 Runtime Coverage Plan，覆盖 state、layout、content、interaction、motion、assets、theme、accessibility、platform、performance。适用缺口必须引用 requirement/project/user-decision 证据；未解决的缺口阻止冻结。绑定数据无真实值时保持空/省略，fixture 只能用于测试夹具。每个 UI unit 都必须明确记录动效契约，或记录并确认「static / no motion」；静态 golden 确认与动效确认/豁免是两道独立门禁。

v2 `contracts/ui-truth-index.json` 记录治理元数据：truth mode/source、适用时的设计 revision、unit 类型/源节点/依赖、环境 profile、带来源的 state、具体 scenario、完整适用性 coverage、仓内相对路径、SHA-256，以及绑定预览 hash 的确认。这些元数据不是第二份绘制真值。禁止生成 `ui-contract.html`。禁止把 HTML 翻译成 Flutter。Figma 来源的 scenario 保留有证据的像素；其他来源的运行时 scenario 不得称为 1:1 还原 Figma。

`ui-truth-mapping` 可按自身规则派发 per-unit 子代理。编排器不覆盖 leaf 子代理策略。

在用户已批准 workspace 内，对视觉表面沿用 Stage 4 实现纪律：适用时先写聚焦测试，执行红 → 绿 → 重构，生成确定性 golden，并把完成的 unit 交给新鲜上下文代码评审。finding 修复并复审干净后才能冻结。测试命令与评审结论记入 `progress.md`。

**冻结门槛（全部满足）：**

1. 组件能编过 / 宿主预览能打开。
2. 官方预览文件存在；对话出示了其 **绝对路径**（Flutter：`flutter test --update-goldens` 产出的 golden PNG；宿主可录制时，动态 unit 还需 GIF；无法录制 GIF 时索引必须记录原因并延后运行时验证）。
3. v2 `contracts/ui-truth-index.json` 校验通过：仓内相对路径不会逃出 **仓库根**、hash 与当前文件一致、id/type/stack/dependency 合法、profile 与带来源的 state 完整、每个视觉 scenario 都有独立预览，且十个 coverage 维度全部解决。
4. 范围匹配需求切片 **In Scope**（最小祖先；不是无关整页 dump）。
5. 每个 icon/图片和交互控件都是真实且有证据。手绘 glyph、涂绘输入壳、外部视觉 slot、dummy/fixture visual、伪造数据和静默 fallback 都不通过。资源不可用时，必须由用户明确选择为空、延后或阻塞；技能不得自行选择。如果确实需要临时占位来辅助评审，必须另行询问用户明确批准其确切作用域，并让它留在生产 UI/数据路径之外；没有该批准一律禁止。
6. 每个视觉 scenario 都记录静态视觉确认或带理由的明确豁免，且 `reviewed_preview_sha256` 与当前 preview hash 一致。适用的动效 scenario 还要记录动效确认或有理由的动效豁免与后续运行时验证方式。能确定性录制 GIF 时，在 `motion_decision` 写入并向用户出示路径/hash；不能录制 GIF 时，索引必须说明原因，Stage 4 用项目原生行为/人工证据验收。GIF 已足够，不要新增其他动效格式或编码器。官方预览就是复审媒介 — 不要用 `contract-preview-*.png` 代替。
7. 若本轮 unit 集合变化，已完成陈旧指针清扫（`ui-truth-mapping` §9）。
8. `ui-truth-mapping` 要求的运行时 coverage、动效生命周期或明确无动效决定、资源/渲染、蒙版/合成、无障碍与 fill-hug-fixed 说明已记录（注释或冻结对话），不是第二份绘制文件。静态 golden 永远不能替代动效验收。
9. Stage 2 测试通过且最新一轮新鲜上下文评审干净；用户已批准 workspace 证据已记录，供 Stage 4 复用。Stage 4 的结构化验收必须为每个索引 unit 记录一条独立动效验收。
10. Stage 2 产物边界路径审计已对比边界协议要求的入口/出口 Git 状态/内容指纹账本与独立文件系统指纹。目录指纹包含 ignored 文件，并覆盖外部 skill 声明的每个默认输出根，至少包括 `docs/superpowers/**`、`.superpowers/**`、`.specify/**` 与 `openspec/**`；因此能捕获被 `.gitignore` 隐藏的写入，以及进入动作前已 dirty 路径上的再次写入。`.ai-delivery/` 外只允许新增或修改生产源码、项目原生测试、golden/官方预览和运行时资源。任何新增或修改且位于 `.ai-delivery/` 外的流程/治理产物都设置 `blocked_verification_failure`；不得冻结或推进状态。在 canonical `progress.md` 记录审计结论与精确越界路径，不删除用户既有文件。

## 完成后

没有 HTML 校验器，也没有 v1 兼容分支。Kit 状态校验检查 v2 schema、路径边界、文件类型、hash、依赖、profile、带来源的 state、scenario、完整 coverage 与预览绑定确认凭证：

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

- 仅当冻结门槛满足时设置 `acceptance_frozen`。
- 失败 → `blocked_verification_failure`；不要推进状态。
- 更新 `status.json`。

## 若无 Figma 链接

- `ui_truth_mode=none` 或 `existing`：跳过；使用普通项目行为/语义验证。
- `ui_truth_mode=figma` 无有效 Figma 源：`blocked_missing_design`（`blocker_scope: slice_local`）。
- `ui_truth_mode=runtime-baseline` 无 requirement、project 或 user-decision 来源：`blocked_missing_visual_truth`（`blocker_scope: slice_local`）。

## 下一步交接

`acceptance_frozen` → 按 `design_mode` 进入 `solution-design`。见 [handoff-table.md](handoff-table.md)。
