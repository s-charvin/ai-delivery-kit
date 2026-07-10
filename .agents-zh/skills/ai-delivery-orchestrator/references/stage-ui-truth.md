# 阶段 2：UI 真值映射

## 何时运行

对每个 `ui_bearing: true` 且有 Figma 设计源的子需求。

## 准备输入

- 阅读 `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/requirement-slice.md`。
- 收集 Figma file key 与目标 node id。
- 输出目录设为子需求目录。

## 运行 `ui-truth-mapping`

传入需求切片与设计源。产出 `ui-acceptance-contract.yaml` 与 `section-map.json`。

`ui-truth-mapping` 可按自身规则派发 per-unit 子代理。编排器不覆盖 leaf 子代理策略。

## 完成后

```bash
python3 scripts/validate-ui-contract.py <contract-path> [--section-map <section-map.json>]
```

- 仅当每次校验输出 `OK` 时设置 `acceptance_frozen`。
- 失败 → `blocked_verification_failure` 并附校验输出；不推进状态。
- 更新 `status.json`。

可选批量检查：

```bash
python3 scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

## 无 Figma 链接时

- 非 UI 子需求：跳过（拆分阶段已处理）。
- 无设计的 UI 子需求：`blocked_missing_design`（`blocker_scope: slice_local`）。

## 下一 handoff

`acceptance_frozen` → `superpowers:brainstorming`（设计模式）。见 [handoff-table.md](handoff-table.md)。
