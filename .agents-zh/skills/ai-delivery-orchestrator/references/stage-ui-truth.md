# 阶段 2：UI 真值映射

## 何时运行

对每个 `ui_bearing: true` 且有 Figma 设计源的子需求。

## 准备输入

- 阅读 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/requirement-slice.md`。
- 收集 Figma file key 与目标 node id。
- 输出目录设为子需求目录。

## 仅运行 `ui-truth-mapping`（Stage 2）

Stage 2 **只跑 `ui-truth-mapping`**。此阶段不要跑 `figma-design-to-code` — 该技能是实现期消费者，不是契约作者。Stage 2 混用会搞乱归属并跳过 scope/布局门禁。

传入需求切片与设计源。每个独立 unit 产出一份 `ui-contract.html`（schema v2），各自位于子需求下自己的 `<unit-id>/` 目录中。不存在聚合索引文件或配套 YAML/JSON——跨 unit 关系与交付顺序唯一来自各 unit 自身的 `meta.unit.type`（`page` / `modal` / `shared-component` / `component`）与 `meta.unit.dependencies`。

`ui-truth-mapping` 可按自身规则派发 per-unit 子代理。编排器不覆盖 leaf 子代理策略。

**冻结门槛（全部满足）：**

1. 每个 unit 契约校验器打印 `OK`。
2. 浏览器打开后 `[data-ui-state-host]` 显示 **hydrate 后的默认态**（预览脚本存在）；空 host = 未冻结。
3. `[data-ui-state-switcher]` 可切换每个已声明状态并看到对应预览。
4. 契约 root 对齐需求切片 **In Scope**（最小祖先；非无关整页 dump）。
5. 每个 icon/图片/矢量化子树都有证据背书：内联资产字节（含资产 hash）、复用的项目资产，或 review panel 注明的服务端占位/待办项。手绘图形、仅凭 `get_structure` 的重建（structure 不能证明绘制属性：透明度/渐变/描边）与未解析的 `data-src` 空壳不达标。
6. 用户已逐份人工确认 `ui-contract.html`（仅当用户明确豁免复审时可跳过）。hydrate 后的 HTML 就是复审媒介 — 不保存预览截图产物。
7. 若本轮契约集合发生变化（新增、删除、替换契约或 unit id 变更），已完成陈旧指针清扫（`ui-truth-mapping` §9）：`status.json` notes、`visual-acceptance.md`、progress/todo、拆分摘要中没有任何**活跃**指针仍指向已删除/更名的契约。允许保留一行「被 … 取代」的历史注记。

## 完成后

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

每个 unit 的 `ui-contract.html` 各运行一次。

- 仅当每次校验输出 `OK` **且**满足上方冻结门槛（hydrate 预览 + scope 对齐 + icon 资产保真 + 逐份契约用户确认 + 契约集合变化时的陈旧指针清扫）时设置 `acceptance_frozen`。
- 失败 → `blocked_verification_failure` 并附校验输出；不推进状态。
- 更新 `status.json`。

可选批量检查：

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

除状态门禁外，该检查会拒绝需求目录内的**悬空 `ui-contract.html` 指针**（引用的契约路径不存在，且该行未标记为「已删除 / 被取代」的历史注记）。契约集合发生变化时，置 `acceptance_frozen` 前必须运行。

## 无 Figma 链接时

- 非 UI 子需求：跳过（拆分阶段已处理）。
- 无设计的 UI 子需求：`blocked_missing_design`（`blocker_scope: slice_local`）。

## 下一 handoff

`acceptance_frozen` → `design` 动作。见 [handoff-table.md](handoff-table.md)。
