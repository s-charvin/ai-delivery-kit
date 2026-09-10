# 阶段 4：实现

## 何时运行

CP-001 用户确认后，每个处于 `tasks_ready` 的子需求（reconcile 输出 `implement`）。任务简报映射与进度账本规则见 [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md)。

**CP-001 确认前禁止 dispatch。**

## 切片执行顺序

按子需求依赖图以及 `ui-truth-index.json` 持久化的 UI unit 类型/依赖执行：`shared-component` → `page` / `component` → `modal`（每个 modal 在其触发 page 之后）。仅当列出的依赖 unit 已在切片工作区完成，该 unit 才能启动。

`ui_truth_mode=figma` 或 `runtime-baseline` 的切片必须继续使用 **Stage 2 使用的同一个用户已批准 workspace**，并对照已冻结宿主栈组件以及 `ui-truth-index.json` 记录的 v3 profile/state/scenario coverage、证据范围、宿主绑定与已确认视觉预览实现。**该组件 + 预览集合是 Stage 4 唯一的视觉真值。** Stage 4 负责业务接线、scenario 验证与剩余任务；不得创建第二个 workspace 或重画组件。`existing` 使用已有组件和普通行为/语义验证，`none` 没有 UI truth 产物。绝不要把 `figma-design-to-code` 当作 Stage 2 作者。禁止把一个宿主栈的平行预览翻译到另一宿主栈。

新增集成抽象之前，先追溯宿主对同类操作的既有所有权与调用路径：API/client、transport、序列化、repository/use-case、依赖注入和测试缝。路径仍匹配时就扩展它。不要仅为一次新操作或更容易测试而平行引入 adapter、client、repository、transport 或注入架构；新层必须有既有项目边界或明确需求决策。

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

使用 v3 index 中精确记录的 profile 与 scenario；不得发明通用设备/主题笛卡尔积。对 covered 维度采用项目原生检查：

- state/数据生命周期、可达的 error/offline/permission/disabled 路径，以及快速重复进入；
- container/viewport 边界、orientation、安全区、fixed/sticky overlay、IME、scroll、clip 与 hit testing；每个可编辑输入在适用时都要覆盖未输入/未编辑、编辑中、已完成/未编辑、IME 隐藏与 IME 显示，视觉由真实控件状态驱动；
- 长文本/不可断词/本地化/RTL、text scaling 或 zoom、列表数量与数值/日期边界；
- hover/focus/pressed/selected/expanded、keyboard/pointer/touch/gesture 替代、focus trap/return 与语义播报；
- 动效 trigger/keyframe/timing/interruption/reduced-motion/资源生命周期，以及适用的性能检查；审阅产物必须展示完整转场或循环、没有过长空等、自动重播，并能解码出期望帧数与总时长；有索引动效预览时必须使用它，无法录制时用项目原生行为/人工证据；
- 图片/矢量的 loading/error/offline、crop/focal/aspect/density/theme/cache/semantics 行为；
- 支持的主题、contrast/state parity、平台语义、输入模式与原生无障碍要求。

不得仅为执行矩阵新增依赖。使用项目已有 golden/screenshot、widget/component、semantics/accessibility、integration 与 performance 工具。只有用户给出身份、时间戳和理由时才能明确 waived 某个 scenario。

### 按证据范围执行

- `component-only`：复用已冻结真实组件 preview 与组件行为测试。记录宿主未覆盖边界，不得新增或暗示宿主视觉通过。
- `host-static`：通过索引中已有测试入口进入，挂载索引中的生产宿主，确定性准备状态/资源，捕获索引边界，并验证全部必见元素和空间约束。
- `host-runtime`：先执行低成本环境、资源与视觉 smoke。只有视觉 smoke 通过后才执行昂贵的原生生命周期套件。捕获索引中的生产宿主，并验证同一组必见元素/空间约束。

禁止为满足宿主证据而构造虚构页面。真实宿主无法按冻结方式挂载或截图时，停止并把 scenario 退回修正能力判定；不得静默降级或伪造通过截图。宿主截图与断言报告必须放在 `.ai-delivery/` 外、索引声明的项目原生测试证据根目录。

若组件代码变化，但重新生成的所有视觉 preview hash 均不变，可更新组件 hash 并保留现有预览绑定确认。任一 preview hash 变化都必须重新生成预览并取得新确认；陈旧 `reviewed_preview_sha256` 必须阻止推进。

存在稳定 Figma 参考位图时，以项目原生 image-diff 记录 reference/candidate/diff hash、metric、threshold、actual 与命令。没有稳定位图时，要求精确设计数值映射、确定性预览和用户确认；不得声称执行过自动像素比较。

## 执行纪律（抽象链路）

无论哪个框架档位，`implement` 动作都遵循这条链路：

1. **解析 workspace** — 遵循 [workspace-policy.md](workspace-policy.md)。`ui_truth_mode=figma` 或 `runtime-baseline` 复用已记录的 Stage 2 用户已批准 workspace；其他切片默认使用当前 checkout。只有为当前子需求取得明确确认后，才能创建或复用项目内 worktree。
2. **任务 loop** — 默认每任务一个实现者、顺序执行；每任务内部走 TDD（红 → 绿 → 重构）。
3. **每任务评审循环** — 每个任务都通过下方[评审循环](#评审循环任务级闭环)收口；只有某一轮评审干净，任务才算完成。
4. **视觉/运行时验收**（仅 `ui_truth_mode=figma` 或 `runtime-baseline`）— 在其 profile 与证据范围下执行每个 v3 scenario。视觉 scenario 对照已确认预览，behavior scenario 验证 state/interaction/motion/assets/theme/accessibility/platform/performance 预期，并记录 schema v2 结构化 `visual-acceptance.json`，且为每个索引 unit 写一条独立动效验收。宿主范围必须有 hash 绑定的 `runtime-capture` 证据；`component-only` 不得宣称宿主覆盖。静态 golden 不能满足动效记录。`ui_truth_mode=existing` 使用普通行为/语义证据，`none` 没有视觉验收产物。失败进入同一评审循环。fill/hug 盒子不以快照 `w×h` 相等为通过。绑定数据无真实值时必须验收为空/省略，而不是伪造 fixture 内容。
5. **验证** — 合并前集成检查；在 `verification.md` 中使用用户当前对话语言记录人类可读证据（模板：`templates/verification-template.md`，删除其中的语言指令注释）。
6. **全量 analyze + 全量测试** — 项目静态分析与测试套件须干净通过。

在声称验证门禁干净通过前，必须把每个失败归类为：本次引入的回归、既有基线、环境/工具链失败，或测试与契约矛盾。可行时，针对最窄失败证据在未修改基线下重跑，并记录命令、观察结果和归类。基线或环境失败不等于通过，必须取得用户明确豁免或建立范围明确的阻塞项。若测试与已批准契约矛盾，先解决契约/测试决策，再决定是否修改生产行为。

每一步如何执行取决于档位（superpowers 技能、ECC 代理或原生纪律）：见 [frameworks/superpowers.md](frameworks/superpowers.md)、[frameworks/ecc.md](frameworks/ecc.md)、[frameworks/native.md](frameworks/native.md)。

### 改代码前的失败分类

当分诊结果具有复用价值时，在尝试另一个方案前追加到需求级
`retrospective.md`，随后告诉用户问题编号和记录的结论。这是记忆辅助，不是
当前证据的替代品，也不是实现阶段门禁；归档前仍必须存在并更新 reviewed-at。

任务卡住或 scenario 失败时，先判断失败归属并验证最小候选原因，再改业务代码。
候选原因大致按这个顺序检查：状态传播 / 接线；拷贝与引用语义；模型表达方式；
时间与异步顺序；资源可用性或尚未确认的协议。然后做最小改动，并只重跑最窄的
失败证据。

常见故障类别与默认修法：

- **异步恢复与 live 用户状态竞态。** 延迟初始化或恢复必须以用户已推进的 live
  状态为本地事实：把配置与外观合并进去，但绝不用后到的快照覆盖 live 进度。
- **状态写入没有到达实际渲染 owner。** 异步初始化或 hydrate 后，必须验证状态变更会
  通知真正的渲染 owner；内容身份变化时，还要重置不应复用的有状态渲染器。覆盖空态到
  已加载、重新进入和旧实例路径；只改模型但视图没有观察到，不算转换成功。
- **调试门控泄漏进生产。** 临时 early return、mock 或禁用路径必须显式、可观测
  且隔离。调用方必须能区分「结果为空」与「被禁用」；绝不在共享生产路径里留下
  静默调试禁用。
- **把运行时回调当成完成的证明。** 完成或转场事件可能过早、在错误轨道或乱序
  触发。把它们当作候选信号，并用最小已播放时长加业务层超时兜底保护视觉/流程
  时长。
- **切换时两个可见层重叠。** 定义单一可见层 owner，真实资源 ready 后原子切换；
  延迟几帧只是降低复现率。
- **同一视觉实体存在多套布局算法。** 把几何、居中与尺寸统一到单一布局/坐标真源，
  而不是逐表面修常量。
- **把多个状态折叠成一个标志。** 不要把「请求已触发」「步骤已进入」「服务端已完成」
  「本地仍需要」「凭证仍有效」压成一个布尔。请求时机、生命周期、持久化语义、
  一次性权限与重启行为分开建模；同会话请求去重；失败不伪造成功。
- **来源数据被本地默认值替换。** 在 UI 和协议边界保留来源拥有的身份、值和顺序。未获
  契约授权时，不得硬编码文案或 ID、排序或规范化来源有序列表，也不得伪造 fallback。
  用非默认来源值贯穿选择、状态投影和输出边界做回归验证。
- **准备工作与展示开关耦合。** 资源准备/上传的身份和结果必须独立于后续的展示或发布
  开关。按来源身份缓存可复用结果，让开关只改变输出投影。generation token 只能阻止过时
  结果写回，不能取消已经发出的请求。用已完成、进行中和开关往返场景验证请求次数与资源
  身份；在选择重传或删除前，先在协议边界确认复用、解绑和清理语义。
- **多个入口的能力判定分裂。** 多个视图展示同一来源资源或能力时，按身份计算一个带明确
  来源、加载/错误/空状态和平台边界的结果，再由各入口投影。不要让入口各自计算局部布尔值，
  也不要用一个平台的证据宣称另一个平台的原生行为。用同一身份贯穿所有适用入口测试，未
  支持的平台必须明确保持未证明。
- **埋点把「变化」当成「展示」。** 首次进入、恢复进入、重复渲染与步骤切换语义
  不同。首次曝光显式补发，事件生产与消费成对落地；尚未实现的服务端事件标记为
  未完成，不用本地事件冒充。
- **半成品代码污染验证。** 每个中间状态保持可编译，生产与消费成对落地，散落
  字符串换成型化常量，切片测试前先跑静态检查。中间状态不是验收证据。
- **增量文本按存储单元切片。** 字节/码元索引不是用户可见字符边界。打字机、截断、
  预览和流式文本必须使用宿主提供的 grapheme 感知 API（或等价的 Unicode 安全表示），
  并为代理对、组合字符及其他多码元字符增加回归用例。绝不能把半个字符传给渲染器。

### 决策纠偏后同步退役被替代产物

用户在交付中途确认新决策、纠偏或缩小范围时，要在同一变更批次或紧接的后续中，
退役被替代的实现假设、测试、接线、分支、缓存行为与文档表述。不要把旧路径留作
fallback，也不要加兼容 shim。临时假设或猜测（endpoint、token 键、过期时间、
错误码、迁移事实）必须在记录中显式标记，绝不能写成已确认事实。

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
- 仅当 `ui_truth_mode=figma` 或 `runtime-baseline`，且 schema v2 `visual-acceptance.json` 绑定当前 v3 index、每个 scenario 均按冻结范围带所需证据通过或明确 waived 后，才设 `visual_acceptance_passed`。
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

所有子需求均为 `merged` 后，reconcile 进入 `runtime_mode=closing`（CP-ARCHIVE）。执行最后一条归档命令前，先用用户当前对话语言实例化 `templates/delivery-report-template.md`，删除语言指令注释并保留全部占位符。逐个运行 `scripts/archive-subrequirement.py` 原位推进状态至 `archived`，不得生成快照或复制 canonical 产物；最后一条命令通过 `--delivery-report-template <path>` 传入准备好的模板。全部子需求均为 `archived` 且已本地化的 `delivery-report.md` 存在后，需求才进入 `completed`。

## 收尾 / PR

在 `finish` 动作创建提交（rebase 合并）之前：

创建提交前，检查 `git diff --cached --name-status`，并与任务声明的文件范围逐项比较。
只暂存任务所有的路径；用户原有的已暂存、未暂存、未跟踪、被忽略或生成文件都不等于
同意纳入本次提交。禁止使用宽泛的 add/commit 命令继承他人的暂存区。若暂存集合被污染，
只从 index 移除无关路径并保留其工作区内容，然后重新检查暂存差异再提交。

| 环境 | 推荐下一步 |
|------|------------|
| Cursor | `cursor:babysit` — 处理 PR 评论、修复 CI、保持 merge-ready |
| Cursor（多切片） | 可选 `cursor:split-to-prs` 将并行切片拆成可审 PR |
| Claude / Codex / 手动 | 开 PR、盯 CI、处理评审、重跑项目校验直至通过 |

babysit 与 split-to-prs 为 handoff 推荐，非硬门禁。
