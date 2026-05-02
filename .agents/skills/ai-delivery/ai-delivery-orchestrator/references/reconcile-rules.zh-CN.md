# 对账规则

- 在信任 `todo.md` 之前重新读取 `.ai-delivery`。
- 将 `todo.md` 视为执行面板而非业务真实数据。
- 绝不创建 `todo.json`。
- 任何已完成的步骤必须由 `.ai-delivery` 守卫证明。
- 如果输出存在但守卫未满足，重新运行或阻塞。不得跳过。
- 将 `spec-kit-input.md` 和 `spec-kit-binding.json` 视为衍生的桥梁产物，而非业务真实数据。
- 如果受管控的源产物发生变更，从 `.ai-delivery` 重新生成桥梁产物，而不是直接编辑官方 Spec Kit 输出。
- `todo.md` 可以将一个官方 Spec Kit 运行加本地绑定压缩为一个操作，但完成检查仍来自 `.ai-delivery` 守卫。
