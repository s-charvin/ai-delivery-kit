# 阶段 4：实现衔接

将编排器阶段 4（`implement` 动作）映射到任务级执行与 `.ai-delivery` 进度产物。具体执行方式跟随所选档位 —— [frameworks/superpowers.md](frameworks/superpowers.md)（子代理驱动）、[frameworks/ecc.md](frameworks/ecc.md)（代理驱动）或 [frameworks/native.md](frameworks/native.md)（内联纪律）。

## 何时运行

CP-001 用户确认后，当对账输出 `RUNTIME_MODE=confirm_to_dev` 且 `NEXT_ACTION=implement` 时。

**CP-001 确认前禁止 dispatch 实现工作。**

## tasks.md → 任务简报

对 `tasks.md` 中每个任务行：

| tasks.md 字段 | 执行映射 |
|---------------|----------|
| 任务标题 / ID | 实现者 prompt 标题 |
| 范围 / 文件 | 单文件编辑规则的允许编辑面 |
| 依赖 | 任务间顺序 |
| 验收说明 | TDD 成功标准 |

每个任务一轮执行：新上下文（档位支持时用子代理）→ 实现 → 评审 → 在台账中标记完成。

## progress.md ↔ 台账

追加到 `.ai-delivery/requirements/<req-id>/progress.md`：

- `tasks.md` 中已完成任务 ID
- 实现者会话备注（阻塞、延期集成）
- 评审结果

`progress.md` 仅为抗压缩辅助。恢复时对账仍以 `status.json` 与磁盘产物为准——不得仅凭 progress 提升门禁。

## 双阶段评审

两个阶段都走[评审循环](stage-implementation.md#评审循环任务级闭环)：实现 → 新鲜上下文评审 → finding 成为修复简报 → 复审，直到干净或 `review_loop.max_rounds` 预算耗尽（然后升级给用户；绝不自动合并）。

1. **每任务评审** — 每个任务完成后；每轮的 finding 与修复摘要记入 `progress.md`。
2. **合并前评审** — 全部任务后做切片级评审；再视觉验收（UI）与验证步骤。

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
