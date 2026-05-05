# Spec Kit 绑定检查清单

在官方 `speckit-specify`、`speckit-plan` 或 `speckit-tasks` 运行之后，以及在推进 `.ai-delivery` 状态之前，使用此检查清单。

## 最小检查清单

- [ ] 在写入任何内容之前，将 `spec-kit-input.md`、目标切片 `traceability.json` 和目标切片 `status.json` 放在一起阅读。
- [ ] 确认 `spec-kit-input.md` 中的 `requirement_id`、`subreq_id` 和 `slice_id` 与目标切片包匹配。
- [ ] 确认每个被绑定的输出路径确实是由官方 Spec Kit 步骤生成的。
- [ ] 仅更新 `traceability.json.spec_kit_refs`。
- [ ] 保持现有的 `requirement_refs`、`api_refs`、`figma_refs`、`ui_acceptance_refs` 和 `interaction_refs` 不变。
- [ ] 当当前绑定为部分绑定时，保留先前绑定的 `spec_paths`、`plan_paths` 或 `tasks_paths`。
- [ ] 当绑定 spec 输出时，将生成的 spec 路径写入 `traceability.json.spec_kit_refs.spec_paths`。
- [ ] 当绑定 plan 输出时，将生成的 plan 路径写入 `traceability.json.spec_kit_refs.plan_paths`。
- [ ] 当绑定 tasks 输出时，将生成的 tasks 路径写入 `traceability.json.spec_kit_refs.tasks_paths`。
- [ ] 使用 `spec_kit_input_path`、`bound_outputs`、`bound_statuses`、`traceability_synced`、`official_upstream_unchanged`、`updated_at` 和 `updated_by` 写入 `spec-kit-binding.json`。
- [ ] 仅当相应的生成输出存在且 `traceability.json.spec_kit_refs` 已同步时，才推进 `status.json`。
- [ ] 仅对在此次传递中实际绑定的输出使用 `spec_ready`、`plan_ready` 和 `tasks_ready`。
- [ ] 如果切片标识、生成的路径或受管控的上游真实数据存在冲突，停止并打开一个阻塞器，而不是进行绑定。

## 结果格式

最小的 `traceability.json` 补丁应如下所示：

```json
{
  "spec_kit_refs": {
    "spec_paths": ["specs/.../spec.md"],
    "plan_paths": ["specs/.../plan.md"],
    "tasks_paths": ["specs/.../tasks.md"]
  }
}
```
