# 阶段 2：UI 真值映射

## 何时运行

对每个 `ui_bearing: true` 且有 Figma 设计源的子需求。

## 准备输入

- 阅读 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/requirement-slice.md`。
- 收集 Figma file key 与目标 node id。
- 从仓库判断宿主栈（优先 Flutter）。拿不准就停下问用户。

## 仅运行 `ui-truth-mapping`（Stage 2）

Stage 2 **只跑 `ui-truth-mapping`**。此阶段不要跑 `figma-design-to-code`。Stage 2 混用会搞乱归属。**Stage 4 默认也不再跑** — 接线已经写好的组件（见 [stage-implementation.md](stage-implementation.md)）。

传入需求切片与设计源。每个独立 unit 产出 **真实宿主栈组件**（Flutter：邻接生产文件旁的 Widget + golden 测试）以及官方栈预览。指针只记在 `contracts/ui-truth-index.json`（仓内相对的 `component_path`、`preview_path`，Flutter 另加 `golden_test`）。禁止生成 `ui-contract.html`。禁止把 HTML 翻译成 Flutter。

`ui-truth-mapping` 可按自身规则派发 per-unit 子代理。编排器不覆盖 leaf 子代理策略。

**冻结门槛（全部满足）：**

1. 组件能编过 / 宿主预览能打开。
2. 官方预览文件存在；对话出示了其 **绝对路径**（Flutter：`flutter test --update-goldens` 产出的 golden PNG）。
3. `contracts/ui-truth-index.json` 列出的仓内相对路径能从 **仓库根** 解析。
4. 范围匹配需求切片 **In Scope**（最小祖先；不是无关整页 dump）。
5. 每个 icon/图片都有证据背书。手绘图形不达标。
6. 用户已逐份人工确认预览（仅当用户明确豁免复审时可跳过）。官方预览就是复审媒介 — 不要用 `contract-preview-*.png` 代替。
7. 若本轮 unit 集合变化，已完成陈旧指针清扫（`ui-truth-mapping` §9）。
8. `ui-truth-mapping` 要求的动效 / 蒙版 / fill-hug-fixed 说明已记录（注释或冻结对话），不是第二份绘制文件。

## 完成后

没有 HTML 校验器。Kit 状态校验检查索引与列出的文件：

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
