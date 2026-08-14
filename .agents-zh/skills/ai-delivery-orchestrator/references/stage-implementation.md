# 阶段 4：实现

## 何时运行

CP-001 用户确认后，每个处于 `tasks_ready` 的子需求（reconcile 输出 `implement`）。任务简报映射与进度账本规则见 [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md)。

**CP-001 确认前禁止 dispatch。**

## 切片执行顺序

来自各 unit 内嵌的 `meta.unit.type` 与 `meta.unit.dependencies`：`shared-component` → `page` / `component` → `modal`（每个 modal 在其触发 page 之后）。仅当 `meta.unit.dependencies` 列出的 unit 均已 `merged`，该 unit 才能启动。

UI 切片必须对照已冻结、浏览器可预览（hydrate 默认态 + 状态切换）且与需求 scope 对齐的 `ui-contract.html` 实现。**该 HTML 是 Stage 4 唯一的视觉真值。** 绝不要把 `figma-design-to-code` 当作 Stage 2 契约作者。

### 视觉真值 — 默认不要再查 Figma

默认不要跑 `figma-design-to-code`，也不要调用 TemPad（`get_code` / `get_structure`）作为实现前仪式。Stage 2 已经把几何冻进 HTML。再拉一次会制造第二真值，并可能和契约打架（冻结 inset 与事后现场节点坐标不一致）。

仅在下列情况才调用 TemPad / `figma-design-to-code`：

1. 冻结契约缺少任务所需的节点或几何，或
2. 视觉验收失败，且无法从契约 HTML 消解偏差，或
3. 用户明确要求重新拉取 Figma。

若现场 TemPad 与冻结契约不一致，**以冻结契约为准**，除非用户解冻契约，或你正处于明确的契约修复 loop。

### 实现时的布局尺寸

遵循 `data-ui-sizing` 与 review-panel 的布局尺寸表。

- `fill` → 撑满父级；把测得的 inset 做成 padding/margin。**禁止**把预览 px 写成硬编码。
- `hug` → 固有 / 内容尺寸。
- `fixed` → 用快照 px 作显式尺寸（若宿主项目有尺寸缩放，再套该缩放）。

契约 CSS 里的像素宽是为了让画布预览对上 Figma 的画板快照 — **不是运行时常量**。fill 判定为 `fill` 时，按父宽减内边距实现，不要抄快照宽度。

## 执行纪律（抽象链路）

无论哪个框架档位，`implement` 动作都遵循这条链路：

1. **隔离** — 每切片一个 worktree/分支。
2. **任务 loop** — 默认每任务一个实现者、顺序执行；每任务内部走 TDD（红 → 绿 → 重构）。
3. **每任务评审循环** — 每个任务都通过下方[评审循环](#评审循环任务级闭环)收口；只有某一轮评审干净，任务才算完成。
4. **视觉验收**（仅 UI）— 将实现与经评审的 `ui-contract.html` 各状态对照；失败进入同一评审循环。
5. **验证** — 合并前集成检查。
6. **全量 analyze + 全量测试** — 项目静态分析与测试套件须干净通过。

每一步如何执行取决于档位（superpowers 技能、ECC 代理或原生纪律）：见 [frameworks/superpowers.md](frameworks/superpowers.md)、[frameworks/ecc.md](frameworks/ecc.md)、[frameworks/native.md](frameworks/native.md)。

## 评审循环（任务级闭环）

无论哪个框架档位，每个任务与每次视觉验收失败都通过这个循环收口：

```
实现者完成任务
  → 评审者（新鲜上下文）对照任务简报 + spec + 契约评审
  → 干净 → 记录评审结论 → 下一任务
  → 有 finding → finding 清单作为修复简报交回实现者 → 修复 → 复审
  → 经过 review_loop.max_rounds 轮仍不干净 → 停下并升级给用户
```

规则：

- 评审者始终在新鲜上下文中运行（档位支持时用子代理），绝不允许实现者自评。
- 每轮的 finding 与修复摘要记入 `progress.md` 以便追溯。
- 迭代预算 `review_loop.max_rounds` 默认 3。解析优先级：子需求 `decisions.md` 覆盖 → `.ai-delivery/meta/workflow-policy.json` 的 `review_loop.max_rounds` → 默认 3。
- 预算耗尽：暂停，把未解决的 finding 报告给用户，走 `blocked_verification_failure` 或按用户指示处理。**最新一轮评审不干净的工作绝不自动合并。**
- 循环所有者是主编排会话；干净与否以评审者报告为准，而非实现者的声称。

## 子代理策略

```
切片内任务独立且文件不重叠？
  → 否（默认）：每任务一个实现者，顺序执行，双阶段评审
  → 是（少见）：并行派发仅用于独立的 test/bug 域
禁止：两个实现者并行编辑同一切片的同一文件集
```

门禁 / 阻塞 / 状态 / 合并决策始终在主会话。

## 状态更新

- 开始实现时设 `in_dev`。
- 截图匹配经评审的 `ui-contract.html` 后设 `visual_acceptance_passed`（仅 UI）。提升该状态前须写入 `visual-acceptance.md` 或 `visual-acceptance/*.png`。
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

切片完成 → `finish` 动作 → `merged`。见 [handoff-table.md](handoff-table.md)。

## 收尾 / PR

`finish` 动作（rebase 合并）之后：

| 环境 | 推荐下一步 |
|------|------------|
| Cursor | `cursor:babysit` — 处理 PR 评论、修复 CI、保持 merge-ready |
| Cursor（多切片） | 可选 `cursor:split-to-prs` 将并行切片拆成可审 PR |
| Claude / Codex / 手动 | 开 PR、盯 CI、处理评审、重跑项目校验直至通过 |

babysit 与 split-to-prs 为 handoff 推荐，非硬门禁。
