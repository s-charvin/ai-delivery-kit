# 阻塞项目录

发生阻塞时，记录最窄匹配的阻塞项，继续其他可运行子需求；仅当无安全可运行项时才暂停整个需求。

## 需求拆分

| 阻塞 | 触发条件 |
|------|----------|
| `blocked_missing_requirement` | 源中缺少关键业务事实 |
| `blocked_requirement_conflict` | 两个已批准来源互相矛盾 |
| `blocked_dependency` | 上游子需求未就绪 |

## UI 真值映射

| 阻塞 | 触发条件 |
|------|----------|
| `blocked_missing_design` | 设计证据中缺少所需视觉载体 |
| `blocked_requirement_figma_conflict` | 需求与视觉真值不可调和 |
| `blocked_figma_conflict` | 设计证据自相矛盾 |
| `blocked_missing_state_code` | 最终屏幕状态缺少结构化帧证据 |
| `blocked_missing_visual_truth` | 缺少默认状态、行组合、父外壳或关键资源 |
| `blocked_verification_failure` | 契约校验失败或证据无法验证 |

## Spec Kit 与实现

| 阻塞 | 触发条件 |
|------|----------|
| `blocked_spec_mismatch` | Spec 产出与治理真值冲突 |
| `blocked_dependency_slice` | 上游切片未合并 |
| `blocked_merge_conflict` | rebase/集成失败 |
| `blocked_verification_failure` | 自动修复后测试/评审/视觉验收仍失败 |

## 记录阻塞

更新 `status.json` 中的子需求条目：

```json
{
  "status": "blocked_missing_design",
  "detail": "Figma 文件缺少确认对话框帧",
  "blocked_from_status": "acceptance_frozen",
  "blocker_scope": "slice_local",
  "resume_target_status": "acceptance_frozen",
  "notes": null
}
```

## 恢复

用户解决阻塞后，朝 `resume_target_status` 恢复。

## 最窄阻塞规则

- 优先 `blocked_missing_state_code` 而非 `blocked_missing_design`。
- 优先 `blocked_requirement_figma_conflict` 而非 `blocked_missing_visual_truth`。
- 跨子需求仍有安全可运行项时，不得升级为 `requirement_global`。

## 阻塞范围

- **`slice_local`** — 仅阻塞一个切片/阶段。
- **`action_level_integration`** — 仅阻塞一个操作的真实 API 连线；不阻塞外壳、导航或只读路径。
- **`requirement_global`** — 仅当所有可推导队列项均不可运行。

默认策略：**优先继续最安全的可运行工作**。
