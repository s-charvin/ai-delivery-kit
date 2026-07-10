# 阶段 4：实现

## 何时运行

CP-001 用户确认后，每个处于 `tasks_ready` 的子需求。SDD 映射与进度账本见 [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md)。

**CP-001 确认前禁止 dispatch。**

## 切片执行顺序

按 `section-map.json`：`shared-shell` → `page` → `modal`（每个 modal 在其触发 page 之后）。结构依赖 `merged` 后才启动单元。

## 子代理策略

```
切片内任务独立且文件不重叠？
  → 否（默认）：subagent-driven-development — 每任务一个 implementer，顺序执行，双阶段评审
  → 是（少见）：dispatching-parallel-agents 仅用于独立 test/bug 域
禁止：两个 implementer 并行编辑同一切片的同一文件集
```

门禁 / 阻塞 / 状态 / 合并决策始终在主会话。

## 实现链路（每切片）

1. **`using-git-worktrees`** — 每切片一个 worktree。
2. **`subagent-driven-development`**（默认）— 每任务新子代理；内部用 `test-driven-development`。
3. **`requesting-code-review`** — 首次失败进入自动修复循环，再升级给用户。
4. **视觉验收**（仅 UI）— 截图对照 YAML 契约状态；首次失败自动修复。
5. **`verification-before-completion`** — 合并前集成检查。
6. **全量 analyze + 全量测试** — 项目静态分析与测试套件须全部通过。
7. **`finishing-a-development-branch`** — 结构化合并选项；rebase 到开发分支（无 merge commit）。

## 状态更新

- 开始实现时设 `in_dev`。
- 截图匹配 YAML 后设 `visual_acceptance_passed`（仅 UI）。提升该状态前须写入 `visual-acceptance.md` 或 `visual-acceptance/*.png`。
- rebase 成功后设 `merged`。

## 进度账本（可选）

已完成任务追加到 `.ai-delivery/requirements/<req-id>/progress.md`，以应对上下文压缩。不要把 progress.md 当真相源 — 以产物与 `status.json` 对账。

## 阻塞项

| 触发条件 | 阻塞 |
|----------|------|
| 上游切片未合并 | `blocked_dependency_slice` |
| rebase 失败 | `blocked_merge_conflict` |
| 自动修复后测试/评审/视觉仍失败 | `blocked_verification_failure` |

## 下一 handoff

切片完成 → `finishing-a-development-branch` → `merged`。见 [handoff-table.md](handoff-table.md)。

## 收尾 / PR

`finishing-a-development-branch` 之后：

| 环境 | 推荐下一步 |
|------|------------|
| Cursor | `cursor:babysit` — 处理 PR 评论、修复 CI、保持 merge-ready |
| Cursor（多切片） | 可选 `cursor:split-to-prs` 将并行切片拆成可审 PR |
| Claude / Codex / 手动 | 开 PR、盯 CI、处理评审、重跑项目校验直至通过 |

babysit 与 split-to-prs 为 handoff 推荐，非硬门禁。
