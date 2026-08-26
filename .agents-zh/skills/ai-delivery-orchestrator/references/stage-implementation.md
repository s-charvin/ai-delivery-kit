# 阶段 4：实现

## 何时运行

CP-001 用户确认后，每个处于 `tasks_ready` 的子需求（reconcile 输出 `implement`）。任务简报映射与进度账本规则见 [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md)。

**CP-001 确认前禁止 dispatch。**

## 切片执行顺序

按子需求依赖图以及 `ui-truth-index.json` 持久化的 UI unit 类型/依赖执行：`shared-component` → `page` / `component` → `modal`（每个 modal 在其触发 page 之后）。仅当列出的依赖 unit 已在切片工作区完成，该 unit 才能启动。

`ui_truth_mode=figma` 或 `runtime-baseline` 的切片必须继续使用 **Stage 2 创建的同一个切片 worktree**，并对照已冻结宿主栈组件以及 `ui-truth-index.json` 记录的 v2 profile/state/scenario coverage 与已确认视觉预览实现。**该组件 + 预览集合是 Stage 4 唯一的视觉真值。** Stage 4 负责业务接线、scenario 验证与剩余任务；不得创建第二个 worktree 或重画组件。`existing` 使用已有组件和普通行为/语义验证，`none` 没有 UI truth 产物。绝不要把 `figma-design-to-code` 当作 Stage 2 作者。禁止从 HTML 再画一遍 Flutter。

### 视觉真值 — 默认不要再查 Figma

默认不要跑 `figma-design-to-code`，也不要调用 TemPad（`get_code` / `get_structure`）作为实现前仪式。Stage 2 已经把真实 Widget/组件冻进仓库。再拉一次会制造第二真值，并可能和已确认预览打架。

仅在下列情况才调用 TemPad / `figma-design-to-code`：

1. 冻结组件缺少任务所需的几何，或
2. 视觉验收失败，且无法从已确认预览消解偏差，或
3. 用户明确要求重新拉取 Figma。

若现场 TemPad 与冻结组件 / 已确认预览不一致，**以冻结组件为准**，除非用户解冻该 unit，或你正处于明确的修复 loop。

只有 Figma 来源的 scenario 才可声称 1:1 还原 Figma。requirement/project/user-decision 来源的 scenario 属于已批准运行时行为。不得用运行时惯例静默修改 Figma 已展示的像素；与无障碍/平台/性能冲突的可见修改须经过明确修复决策。

### 实现时的布局尺寸

遵循 Stage 2 的 fill / hug / fixed 分类。预览 px 是画板快照 — **不是运行时常量**。

- `fill` → 撑满父级；把测得的 inset 做成 padding/margin。**禁止**把预览 px 写成硬编码。
- `hug` → 固有 / 内容尺寸，加上尺寸表里的 overflow / min / max。
- `fixed` → **仅当**表写明 fixed 时，用快照 px 作显式尺寸（若宿主项目有尺寸缩放，再套该缩放）（图标、头像、资产盒、明确锁死）。

fill 判定为 `fill` 时，按父宽减内边距实现，不要抄快照宽度。**禁止**把每个快照 `width`/`height`/`left`/`top` dump 成布局常量。

若盒子是 content-bound / i18n / 可变长度，且尺寸表（或需求 / 设计）没写 overflow / min / max → **停下问用户**。禁止用快照 px 发明锁死。

优先约束布局（flex / stretch / 固有尺寸）。少量不变 chrome 的 fixed 或 min-size 可以；把整张画板抄成常量不行。

`fill`/`hug` 盒子的测试和视觉验收断言约束行为（随父级拉伸、短内容 hug、长内容钳制）— **不是**与快照 `w×h` 相等。用快照 px 给 `fill`/`hug` 盒子打分的 visual-acceptance 是评审发现项，不是通过。

### 运行时 scenario 验证

使用 v2 index 中精确记录的 profile 与 scenario；不得发明通用设备/主题笛卡尔积。对 covered 维度采用项目原生检查：

- state/数据生命周期、可达的 error/offline/permission/disabled 路径，以及快速重复进入；
- container/viewport 边界、orientation、安全区、fixed/sticky overlay、IME、scroll、clip 与 hit testing；
- 长文本/不可断词/本地化/RTL、text scaling 或 zoom、列表数量与数值/日期边界；
- hover/focus/pressed/selected/expanded、keyboard/pointer/touch/gesture 替代、focus trap/return 与语义播报；
- 动效 trigger/keyframe/timing/interruption/reduced-motion/资源生命周期，以及适用的性能检查；
- 图片/矢量的 loading/error/offline、crop/focal/aspect/density/theme/cache/semantics 行为；
- 支持的主题、contrast/state parity、平台语义、输入模式与原生无障碍要求。

不得仅为执行矩阵新增依赖。使用项目已有 golden/screenshot、widget/component、semantics/accessibility、integration 与 performance 工具。只有用户给出身份、时间戳和理由时才能明确 waived 某个 scenario。

若组件代码变化，但重新生成的所有视觉 preview hash 均不变，可更新组件 hash 并保留现有预览绑定确认。任一 preview hash 变化都必须重新生成预览并取得新确认；陈旧 `reviewed_preview_sha256` 必须阻止推进。

存在稳定 Figma 参考位图时，以项目原生 image-diff 记录 reference/candidate/diff hash、metric、threshold、actual 与命令。没有稳定位图时，要求精确设计数值映射、确定性预览和用户确认；不得声称执行过自动像素比较。

## 执行纪律（抽象链路）

无论哪个框架档位，`implement` 动作都遵循这条链路：

1. **隔离** — `ui_truth_mode=figma` 或 `runtime-baseline` 复用已记录的 Stage 2 worktree/分支；只有尚无工作区的其他切片才在此创建一个 worktree/分支。
2. **任务 loop** — 默认每任务一个实现者、顺序执行；每任务内部走 TDD（红 → 绿 → 重构）。
3. **每任务评审循环** — 每个任务都通过下方[评审循环](#评审循环任务级闭环)收口；只有某一轮评审干净，任务才算完成。
4. **视觉/运行时验收**（仅 `ui_truth_mode=figma` 或 `runtime-baseline`）— 在其 profile 下执行每个 v2 scenario。视觉 scenario 对照已确认预览，behavior scenario 验证 state/interaction/motion/assets/theme/accessibility/platform/performance 预期，并记录结构化 `visual-acceptance.json`。`ui_truth_mode=existing` 使用普通行为/语义证据，`none` 没有视觉验收产物。失败进入同一评审循环。fill/hug 盒子不以快照 `w×h` 相等为通过。
5. **验证** — 合并前集成检查；在 `verification.md` 中使用用户当前对话语言记录人类可读证据（模板：`templates/verification-template.md`，删除其中的语言指令注释）。
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
- 每轮的 finding 与修复摘要记入 `progress.md` 以便追溯，并追加到 `verification.md` 中由稳定标记识别的评审轮次区域。
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
- 仅当 `ui_truth_mode=figma` 或 `runtime-baseline`，且 `visual-acceptance.json` 绑定当前 v2 index、每个 scenario 均带所需证据通过或明确 waived 后，才设 `visual_acceptance_passed`。
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

所有子需求均为 `merged` 后，reconcile 进入 `runtime_mode=closing`（CP-ARCHIVE）。执行最后一条归档命令前，先用用户当前对话语言实例化 `templates/delivery-report-template.md`，删除语言指令注释并保留全部占位符。逐个运行 `scripts/archive-subrequirement.py` 冻结 `archive/<ISO-ts>/` + `MANIFEST.json` 并推进到 `archived`；最后一条命令通过 `--delivery-report-template <path>` 传入准备好的模板。全部子需求均为 `archived` 且已本地化的 `delivery-report.md` 存在后，需求才进入 `completed`。

## 收尾 / PR

`finish` 动作（rebase 合并）之后：

| 环境 | 推荐下一步 |
|------|------------|
| Cursor | `cursor:babysit` — 处理 PR 评论、修复 CI、保持 merge-ready |
| Cursor（多切片） | 可选 `cursor:split-to-prs` 将并行切片拆成可审 PR |
| Claude / Codex / 手动 | 开 PR、盯 CI、处理评审、重跑项目校验直至通过 |

babysit 与 split-to-prs 为 handoff 推荐，非硬门禁。
