# 阶段 2：UI 真值映射

## 何时运行

对每个 `split_ready`、`ui_bearing: true`、有 Figma 设计源且已记录 CP-UI 用户授权的子需求。

Stage 2 会写生产代码，因此它是**受控视觉实现阶段**，不是“不含实现的 mapping”。

## 准备输入

- 阅读 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/requirement-slice.md`。
- 收集 Figma file key 与目标 node id。
- 从仓库判断宿主栈（优先 Flutter）。拿不准就停下问用户。
- 每切片创建或复用一个隔离 worktree/分支，并在 `decisions.md` 或 `progress.md` 记录分支与路径；同一 worktree 贯穿 Stage 3 与 Stage 4。

## 仅运行受控的 `ui-truth-mapping`（Stage 2）

Stage 2 **只跑 `ui-truth-mapping`**。此阶段不要跑 `figma-design-to-code`。Stage 2 混用会搞乱归属。**Stage 4 默认也不再跑** — 接线已经写好的组件（见 [stage-implementation.md](stage-implementation.md)）。

传入需求切片与设计源。每个独立 unit 产出 **真实宿主栈组件**（Flutter：邻接生产文件旁的 Widget + golden 测试）以及官方栈预览。v1 `contracts/ui-truth-index.json` 记录治理元数据：设计 revision、unit 类型/源节点/依赖、逐状态预览与确认/豁免、仓内相对路径及 SHA-256。这些元数据不是第二份绘制真值。禁止生成 `ui-contract.html`。禁止把 HTML 翻译成 Flutter。

`ui-truth-mapping` 可按自身规则派发 per-unit 子代理。编排器不覆盖 leaf 子代理策略。

在切片 worktree 内，对视觉表面沿用 Stage 4 实现纪律：适用时先写聚焦测试，执行红 → 绿 → 重构，生成确定性 golden，并把完成的 unit 交给新鲜上下文代码评审。finding 修复并复审干净后才能冻结。测试命令与评审结论记入 `progress.md`。

**冻结门槛（全部满足）：**

1. 组件能编过 / 宿主预览能打开。
2. 官方预览文件存在；对话出示了其 **绝对路径**（Flutter：`flutter test --update-goldens` 产出的 golden PNG）。
3. v1 `contracts/ui-truth-index.json` 校验通过：仓内相对路径不会逃出 **仓库根**、hash 与当前文件一致、id/type/stack/dependency 合法、每个可复审状态都有独立预览。
4. 范围匹配需求切片 **In Scope**（最小祖先；不是无关整页 dump）。
5. 每个 icon/图片都有证据背书。手绘图形不达标。
6. 每个状态都记录了明确用户确认，或带理由的明确豁免。官方预览就是复审媒介 — 不要用 `contract-preview-*.png` 代替。
7. 若本轮 unit 集合变化，已完成陈旧指针清扫（`ui-truth-mapping` §9）。
8. `ui-truth-mapping` 要求的动效 / 蒙版 / fill-hug-fixed 说明已记录（注释或冻结对话），不是第二份绘制文件。
9. Stage 2 测试通过且最新一轮新鲜上下文评审干净；切片 worktree 证据已记录，供 Stage 4 复用。

## 完成后

没有 HTML 校验器。Kit 状态校验检查 v1 schema、路径边界、文件类型、hash、依赖、状态与确认凭证：

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

- 仅当冻结门槛满足时设置 `acceptance_frozen`。
- 失败 → `blocked_verification_failure`；不要推进状态。
- 更新 `status.json`。

## 若无 Figma 链接

- 非 UI 子需求：跳过（拆分阶段已处理）。
- UI 子需求无设计：`blocked_missing_design`（`blocker_scope: slice_local`）。

## 下一步交接

`acceptance_frozen` → `design` 动作。见 [handoff-table.md](handoff-table.md)。
