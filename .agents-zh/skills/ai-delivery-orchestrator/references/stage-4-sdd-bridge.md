# 阶段 4：SDD 衔接

将编排器阶段 4 映射到 Superpowers SDD 套件与 `.ai-delivery` 进度产物。

## 何时运行

CP-001 用户确认后，当对账输出 `RUNTIME_MODE=confirm_to_dev` 且 `NEXT_SKILL=using-git-worktrees` 时。

**CP-001 确认前禁止 dispatch 实现子代理。**

## tasks.md → SDD 任务简报

对 `tasks.md` 中每个任务行：

| tasks.md 字段 | SDD 映射 |
|---------------|----------|
| 任务标题 / ID | 子代理 prompt 标题 |
| 范围 / 文件 | 单文件编辑规则的允许编辑面 |
| 依赖 | `subagent-driven-development` 内顺序 |
| 验收说明 | 经 `test-driven-development` 的 TDD 成功标准 |

每个任务一轮 SDD：新子代理 → 实现 → 双阶段评审（`requesting-code-review`）→ 在台账中标记完成。

## progress.md ↔ SDD 台账

追加到 `.ai-delivery/requirements/<req-id>/progress.md`：

- `tasks.md` 中已完成任务 ID
- 子代理会话备注（阻塞、延期集成）
- 评审结果

`progress.md` 仅为抗压缩辅助。恢复时对账仍以 `status.json` 与磁盘产物为准——不得仅凭 progress 提升门禁。

## 双阶段评审

1. **每任务评审** — 每个 SDD 任务后 `requesting-code-review`；首次失败自动修复一次再升级给用户。
2. **合并前评审** — 全部任务后做切片级评审；再视觉验收（UI）与 `verification-before-completion`。

## 视觉验收证据（UI）

设置 `visual_acceptance_passed` 前须写入其一：

- `sub-requirements/<subreq-id>/visual-acceptance.md`（清单 + 备注），或
- `sub-requirements/<subreq-id>/visual-acceptance/*.png`（截图）

`validate-delivery-status.py` 弱校验文件存在；不解析图像内容。

## 状态链

```
tasks_ready → (CP-001) → in_dev → visual_acceptance_passed（UI）→ merged
```

非 UI 子需求跳过 `visual_acceptance_passed`。

## 切片完成后 handoff

见 [stage-implementation.md](stage-implementation.md) 的 PR / babysit 收尾步骤。
