---
name: ai-delivery-orchestrator
description: 当需求文档需要经 UI truth、唯一设计契约、实现验证与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）为纯工具，不感知管道。本技能拥有状态、门禁、阻塞与 handoff。

```
需求 → [拆分？] → 能力审计 → 设计契约 → 实现 + 验证 → 合并 → 归档
```

编排器是**框架无关**的：它输出抽象阶段动作，并适配用户已安装的任何 AI 开发框架。绝不要求用户安装任何东西。

## 场景指导

在常规需求分析中，检查场景目录中的触发条件：参阅
[references/scenario-guidance.md](references/scenario-guidance.md)，只选择与需求或交付情境匹配的
场景；没有匹配项时继续使用常规工作流规则。场景目录是可选、按触发条件使用的指导性内容，
这项检查属于已有分析，不得增加阶段、产物、门槛或后续维护义务。将实质决策写入宿主工作流
已有记录或当前动作报告；选中场景的关系不清楚时记录 `unknown` 并询问，不要默认兼容。
该参考不替代宿主工作流自身的规则。

## 复盘台账

使用需求级 `retrospective.md` 记录交付问题和最终复盘。
创建或更新前阅读 [references/retrospective-guidance.md](references/retrospective-guidance.md)。
归档前该文件必须存在，即使没有问题记录；最终复盘时更新 reviewed-at 标记。
在证据仍然可用时记录可复用的失败、错误的 AI 方案、用户/评审纠偏或验证失败；开始下一个方案前先记录失败方案。
不要记录普通机械修正。保持带标记的问题地图与详细问题记录的总分结构。

每次更新台账后，告诉用户 `RET-###` 编号、增加了什么以及文件路径。它不是实现阶段门禁，
但归档前必须存在并更新 reviewed-at。
恢复会话时读取当前问题地图；出现新现象时，将项目复盘索引作为路由表，只加载匹配的历史问题章节。
只有适用条件和当前证据都匹配才算命中，关键词相似不够。

## 产物语言

- 内置模板文本只是英文源默认值，不是最终输出语言。输出语言取决于用户当前对话，不取决于仓库、框架或源模板语言。
- 人类可读内容包括 Markdown 标题、表头和单元格、列表标签、解释性正文、评审证据、设计契约正文、风险和待决问题说明，以及 Mermaid 节点、连线和参与者标签。以上内容都必须使用用户当前对话语言；更新已有产物时同样适用。
- 机器可读键、枚举值、ID、路径、命令、代码符号、Mermaid 语法关键字和协议字面量必须保持原样。`flowchart`、`stateDiagram-v2`、`sequenceDiagram` 等 Mermaid 语法关键字保留英文；附着其上的标签属于人类可读内容，必须本地化。
- 只有真实 API、库、协议、代码符号，或为保持精度而必须使用英文的标准技术名词可以保留英文。其他术语首次出现时先写本地化术语，再在括号中保留英文原词，例如“归约器（`Reducer`）”。`State set`、`Owner`、`Guard`、`Risk` 等英文模板表头不是受保护的机器文本，不得直接照搬。
- 在 `design_ready` 或 CP-DESIGN 前执行语言复核：扫描标题、表头、图表标签、说明、正文和评审笔记；翻译未解释的英文；确认保留的英文确实属于受保护标识或已明确引入的技术术语。未解释的英文正文或标题属于本地化缺陷。
- Markdown 模板实例化后，删除 `ai-delivery-template-language` 指令注释；JSON 模板保持结构不变，只本地化人类可读的描述值。

## 框架适配（每会话执行一次）

执行任何阶段动作之前：

1. 按 [references/framework-adaptation.md](references/framework-adaptation.md) 自查环境（已安装框架：spec-kit / OpenSpec / superpowers / ECC；都没装 → 原生档）。
2. 为当前动作选择档位（设计推理或执行纪律）。
3. 在子需求 `decisions.md` 记录一次选择。

动作 → 指南分发表与 loop 模型：[references/framework-adaptation.md](references/framework-adaptation.md)。各框架使用指南：`references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`。

## 管道

| 阶段 | 抽象动作 | 门禁 |
|------|----------|------|
| 1 | `requirement-breakdown` + 轻量审计 | `split_ready` |
| 2 | 按能力启用的 `ui-truth-mapping`（仅 `ui_truth_mode` 需要时） | 启用时为 `acceptance_frozen` |
| 3 | `solution-design`（唯一行为与方案设计契约为 `design.md`） | `design_ready`；仅实质用户决策触发 CP-DESIGN |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |
| 6 | `archive` | `archived`（全部子需求） |

阶段细节：[references/stage-breakdown.md](references/stage-breakdown.md)、[stage-ui-truth.md](references/stage-ui-truth.md)、[stage-design-and-spec.md](references/stage-design-and-spec.md)、[stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md)、[stage-implementation.md](references/stage-implementation.md)。

## 状态模型

```
draft → split_ready → [acceptance_frozen] → design_ready → in_dev → [visual_acceptance_passed] → merged → archived
```

方括号状态按能力启用：`ui_truth_mode=none` 与 `existing` 跳过 UI truth 冻结和视觉验收。每个活跃 schema 2.0 切片都有一份 `design.md`。`user_decision_required=true` 表示当前设计版本需要用户授权；只有该版本缺少有效 hash-bound human review 时，CP-DESIGN 才处于待处理状态。

真相源：`.ai-delivery/requirements/<req-id>/status.json`。逐字复制 [templates/status-template.json](templates/status-template.json) 的结构，并本地化其中人类可读的描述值；禁止凭记忆生成结构。使用用户当前对话语言实例化 [templates/todo-template.md](templates/todo-template.md)（非真相源）。

| 字段 | 用途 |
|------|------|
| `status` | 当前状态或 `blocked_*` |
| `ui_bearing` | `true` / `false` — 切片是否拥有 UI 表面；校验器要求它与 `ui_truth_mode` 一致 |
| `ui_truth_mode` | `none` / `existing` / `runtime-baseline` / `figma` — 切片所需的 UI truth 能力 |
| `state_flow_required` | 仅当切片实质改变复杂 guard、并发、过期结果、恢复、持久化或跨表面状态所有权时为 `true`；架构名称与普通 loading/error 不触发 |
| `user_decision_required` | 当前设计版本包含决策权属于用户的实质产品、行为、资源或体验选择时为 `true`；批准后仍保持 `true`，当前字节是否已获有效人工授权由 `design_review` 记录 |
| `design_review` | 结构化评审元数据（`review_mode`、`reviewed_design_sha256`、`reviewed_at`、`reviewed_by`），绑定当前 `design.md` 的精确字节 |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | 阻塞清除后的恢复目标 |

## 对账优先

每次恢复或继续前，在信任 `todo.md` 之前运行对账：

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile 输出抽象动作（`solution-design` / `implement` / `finish` / `archive`，另含 kit 自有技能）— 绝不输出第三方技能名。规则：[references/reconcile-rules.md](references/reconcile-rules.md)。

当前状态模板为 schema `2.0`。恢复时，所有活跃旧条目必须重新审计并迁移后才能路由；`merged`/`archived` 历史记录只读兼容，不补造设计或评审证据。

## Handoff 表

每个阶段仅有一个合法下一站动作。完整表：[references/handoff-table.md](references/handoff-table.md)。

| 完成态 | 下一站 |
|--------|--------|
| `split_ready` + 审计（`ui_truth_mode=figma` 或 `runtime-baseline`） | CP-UI → `ui-truth-mapping` |
| `split_ready` + 审计（`ui_truth_mode=none` 或 `existing`） | `solution-design` |
| `acceptance_frozen` | `solution-design` |
| 当前 hash 绑定的 `design.md` 评审 | `design_ready` → 对该依赖就绪切片执行 Stage 4 `implement` |
| 切片完成 | `finish` |

## 暂停点

1. 拆分/跳过边界存在实质歧义时 — 与用户解决命名的范围或所有权决策；明确结果自动推进
2. 启用 UI truth 能力写生产代码前 — CP-UI，授权受控视觉实现（workspace 选择是独立的用户决策）
3. `user_decision_required=true` 且当前设计缺少有效 hash-bound human review 时 — CP-DESIGN，解决命名决策并把人工评审绑定到当前 `design.md`；评审同时授权批准范围内实现
4. 评审循环预算耗尽 — 报告未解决 finding 并等待用户
5. 所有子需求 `merged` 后 — CP-ARCHIVE，标记 `archived` 前确认原位收敛状态

## 硬边界

- 不要把工作流真相移出 `.ai-delivery`。
- Workspace 选择遵循 [references/workspace-policy.md](references/workspace-policy.md)。默认使用当前 checkout；创建或复用 worktree 必须另外取得当前子需求的用户明确确认，批准路径必须为 `<project-root>/.worktrees/<req-id>-<sr-id>`。CP-UI、CP-DESIGN、框架默认值和旧隔离字段都不构成同意。
- 外部 skill 的默认设置绝不授权框架自有产物路径。外部 skill 只提供方法与执行纪律：调用前传入 canonical `.ai-delivery` 输出路径；持久化步骤无法遵守时，跳过该步骤并直接写等价 canonical 产物。禁止先在 `docs/superpowers/**`、`.superpowers/**`、`.specify/**`、`openspec/**` 或其他宿主树框架目录生成流程/治理产物再搬运。
- `.ai-delivery/` 外只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。推进任何门禁前，对比入口/出口 Git 状态/内容指纹账本，并为外部 skill 声明的每个默认输出根建立包含 ignored 文件的独立文件系统指纹，至少覆盖上述四个禁写根。路径、状态、类型、符号链接目标或 SHA-256 漂移能捕获动作前已 dirty 或 ignored 路径上的再次写入。发现新增或修改且位于 `.ai-delivery/` 外的流程/治理产物时，设置 `blocked_verification_failure`。
- 正常路径不要求用户安装或选择框架/技能；适配已安装的现状。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的子需求未 `acceptance_frozen` 不得进入 `solution-design`；`none` 与 `existing` 跳过该 gate。`acceptance_frozen` 同时要求静态视觉确认与每个适用 unit 的动效确认/豁免。
- 只有模式启用且明确确认、记录 CP-UI 后，才能 dispatch `ui-truth-mapping`。Stage 2 在用户已批准 workspace 中写生产代码，执行 TDD/golden 测试并完成新鲜上下文评审闭环。
- UI truth 切片未 `visual_acceptance_passed` 不得声称 `merged`；`none` 与 `existing` 使用普通行为/语义证据。
- 仍有安全可运行项时，不得将 slice-local 阻塞升级为需求全局。
- 门禁 / 阻塞 / 状态 / 合并决策永不交给子代理。Leaf 技能可按自身规则使用子代理（`ui-truth-mapping` per-unit、Stage 4 按所选执行档位）。
- 编排器方案设计模式不要把文档写进框架自有目录；规范方案设计写入子需求 `design.md`，`notes` 只保留短指针。
- `design.md` 是唯一持久化的行为与方案设计契约。不得创建 `spec.md`、`plan.md` 或 `tasks.md`，也不得把文件级执行步骤塞入 `design.md`。跨会话恢复信息按需写 `progress.md`。
- `state_flow_required=true` 时，canonical `design.md` 必须包含状态分类、MVI 闭环、生命周期图、UI 投影、权威转换矩阵、适用异步时序、不变量和追踪。该深度不触发人工门禁。
- 设计评审仅在 `reviewed_design_sha256` 匹配当前文件、`user_decision_required=true` 时模式为 `human`、否则为 `self`，且时间戳/评审者存在时有效。`user_decision_required` 描述当前版本所需的授权类型，批准后仍保持 `true`；是否待处理由 review 有效性决定。文件变化重新打开 `solution-design`；当该 human-authority 版本缺少有效 hash-bound review 时再次进入 CP-DESIGN。
- 对 `ui_truth_mode=figma` 或 `runtime-baseline`，每个 UI unit 尚未具备真实宿主组件、十个维度的按适用性运行时 coverage、每个视觉 scenario 的官方栈预览及已向用户出示的**绝对路径**，以及有效 v3 `contracts/ui-truth-index.json` 之前，不得设置 `acceptance_frozen`。每个 scenario 必须冻结 `evidence_scope` 与 `scope_decision`；只有 `host-static` 和 `host-runtime` 可以携带有效 `host_binding`，`component-only` 明确把宿主组合排除在验收声明外。路径/hash/来源/profile/scenario/coverage、当前预览 hash 绑定确认、独立动效确认/豁免（静态 unit 必须确认无动效）与干净的 Stage 2 评审仍为必需。宿主无法录制动效时，索引必须记录原因并把运行时验收延后到 Stage 4；Stage 4 在 `visual_acceptance_passed` 前必须为每个 unit 写独立动效验收。Stage 2 仅通过 `ui-truth-mapping` 写真实组件 — 绝不经由 `figma-design-to-code`，也禁止生成 `ui-contract.html`。可见数据缺失必须呈现真实空/省略状态，禁止伪造内容。
- Stage 4：`ui_truth_mode=figma` 或 `runtime-baseline` 的切片复用 Stage 2 用户已批准 workspace；不得创建第二个 workspace 或重画组件。`component-only` 复用组件 preview 与行为测试，不宣称宿主视觉通过；`host-static` 通过项目原生确定性工具捕获索引中的生产宿主；`host-runtime` 在昂贵的原生生命周期检查前先做设备/资源/视觉 smoke。运行时截图必须位于 `.ai-delivery/` 外、索引声明的原生测试证据根目录，并绑定索引宿主 provenance。`existing` 使用已有组件和普通行为/语义验证，`none` 没有 UI truth 产物。默认不要再查 TemPad / 不要跑 `figma-design-to-code`；已冻结组件 + 已确认预览才是视觉真值。遵循 fill / hug / fixed（fill = 父宽减内边距，不是快照 px）。禁止把平行预览翻译到另一宿主栈。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的 UI truth 工作未先 `acceptance_frozen` + `visual_acceptance_passed`、有效 v3 `ui-truth-index.json`，以及按冻结证据范围覆盖全部已索引 scenario 的 schema v2 结构化 `visual-acceptance.json` 时，不得 `merged`；`none` 与 `existing` 按普通验证收口。
- 仅在 CP-ARCHIVE 确认后通过 `scripts/archive-subrequirement.py` 设置 `archived`。该动作只原位更新 `status.json`，不得创建 `archive/<ISO-ts>/`、复制 canonical 产物或写入 `MANIFEST.json`。已完成需求目录保留为历史事实源；后续变更须使用新的 `<req-id>` 目录。
- 最新一轮评审不干净时不得声称任务完成或合并；评审循环预算耗尽时升级给用户。
- 实现阶段一次只改一个文件；分支用 rebase 合并（禁止 merge commit）。

## 状态转换门禁

| 目标状态 | 硬要求 |
|----------|--------|
| `acceptance_frozen` | 仅 `ui_truth_mode=figma` 或 `runtime-baseline`：CP-UI 已记录；用户已批准 workspace 证据已记录；真实组件能编过；Stage 2 TDD/评审干净；十个运行时维度均为 `covered` 或有理由的 `not_applicable`；预览路径、v3 index 路径/hash/来源/profile/scenario/coverage、证据范围、能力判定、必需宿主绑定、预览绑定静态确认与动效确认/豁免均有效 |
| `design_ready` | `design.md` 含范围、行为、验收、追踪、方案决策和适用状态流深度；评审 hash 与模式当前有效 |
| `merged`（UI truth） | UI truth 模式已有 `acceptance_frozen` + `visual_acceptance_passed` + 有效 v3 index + schema v2 结构化验收；`existing` 使用普通行为/语义证据，`none` 跳过视觉验收 |
| `archived` | 原位收敛状态；canonical 产物保留在原路径，后续变更须使用新的需求目录 |

## 拆分决策

**跳过**（全部满足）：单屏、无共享状态、单人开发、无横切规则、文档约 300 词以内。

**拆分**（任一满足）：2+ 屏、共享状态、多人协作、跨特性基础设施。

说明理由后执行。细节：[references/stage-breakdown.md](references/stage-breakdown.md)。

## 轻量审计（非方案设计探索）

`split_ready` 后，主会话对每个子需求 inline 执行 4 项检查（缺口、冲突、状态、权限），再确定 `ui_truth_mode`、`state_flow_required` 与 `user_decision_required`。严重问题 → 阻塞；否则写入 `notes`。

## Stage 4（摘要）

`implement` 动作按所选档位执行。下一最小执行 brief 从当前 `design.md`、代码证据和 `progress.md` 动态形成，不持久化第二份计划或任务清单。无论哪个档位，都执行依赖安全的 TDD 与完成前评审。

链路：解析已批准 workspace并复用 Stage 2 选择 → 最小实现单元（TDD）→ 代码评审 → 按需在 `visual-acceptance.json` 记录完整验收 → 完成前验证 → 全量测试 → 合并。

UI truth 切片：接线已经写好的组件（API / 路由 / 状态 / 挂载）；`existing` UI 只做普通行为/语义验证；默认不要再查 TemPad / 不要跑 `figma-design-to-code`。

完整 runbook：[references/stage-implementation.md](references/stage-implementation.md)。

## 阻塞项

最窄阻塞优先；优先继续最安全的可运行工作。校验失败用 `blocked_verification_failure`。目录：[references/blocker-catalog.md](references/blocker-catalog.md)。

## 需求一致性与验收

全过程执行 [需求冲突询问规则](references/stage-breakdown.md)：
业务行为不明确或技术方案与需求冲突时，受影响实现前必须取得用户决定。
设计和完成时均回查原始来源。所有 UI 模式执行
[编码前测试设计](references/stage-implementation.md)。
Stage 2 完成子需求静态/动效证据后整批验收。启用 UI truth 时，Stage 4
进入 visual_acceptance_passed 前还须完成
[最终人工 UI 验收](references/stage-implementation.md)，
自动化证据不能单独放行。

## API 策略

API 文档直接进入 `design.md` 与实现。缺口按影响记录为风险、`integration_deferred` 或 blocker。

## 用户入口

1. 检查 `.ai-delivery/requirements/*`、`status.json`，运行对账。
2. 如果存在则读取 `.ai-delivery/retrospectives/index.md`，筛选匹配的问题行并只加载链接的章节。
   当前需求有 `retrospective.md` 时，读取其问题地图以恢复未完成排查。
3. 推荐 `continue req-xxx` 或 `create req-yyy`。
4. continue/create 选择明确时自动路由；只有不同选择会实质改变治理需求或 workspace 时暂停。

| 意图 | 模式 |
|------|------|
| 新需求 + 素材 | `bootstrap` 或 `resume` |
| 继续编排 | `resume` |
| UI truth 能力待授权 | `confirm_ui`（CP-UI） |
| 实质用户设计决策待解决 | `confirm_solution_design`（CP-DESIGN） |
| 阻塞已解决 | `blocker_recovery`（CP-002） |

## 运行时模式

`bootstrap` | `resume` | `confirm_ui` | `confirm_solution_design` | `blocker_recovery` | `closing` | `completed`

检查点：CP-UI（启用 UI truth 的生产代码前）、CP-DESIGN（实质用户设计决策）、CP-002（硬阻塞，仅当无可运行项）、CP-ARCHIVE（原位归档前）。

## 完成

所有可执行子需求 `merged` → `runtime_mode` 为 `closing`（CP-ARCHIVE）。执行最后一条归档命令前，先把 `templates/delivery-report-template.md` 实例化为使用用户当前对话语言的临时模板，删除其中的 `ai-delivery-template-language` 注释，并保留所有占位符。对每个子需求运行 `scripts/archive-subrequirement.py`，仅原位推进状态至 `archived`，不得复制 canonical 产物或生成快照；最后一条命令须通过 `--delivery-report-template <path>` 传入准备好的模板。需求必须有 `retrospective.md`，还要把 `templates/retrospective-index-template.md` 实例化为使用用户当前对话语言的模板，删除语言指令并保留标记和占位符，在最后一条命令通过 `--retrospective-index-template <path>` 传入。归档命令要求唯一且可解析的 `<!-- ai-delivery-retrospective:reviewed-at:<ISO-8601> -->` 标记，其日历日期必须与归档日期一致；然后读取台账带标记的问题地图，并幂等更新 `.ai-delivery/retrospectives/index.md`。不会创建、重写、总结或审计台账。没有问题行的台账有效且不写索引行；台账缺失或过期则阻断归档，并告知用户登记了哪些问题行。已本地化的 `delivery-report.md` 不存在时，不得声称 `completed`。当每个子需求均为 `archived` 时，需求进入 `completed`；canonical 产物原位保留，后续变更须新建 `<req-id>` 目录。

## 编排形态（不变量）

以下规则防止编排退化，适用于主会话与对账 dispatch：

1. **主会话即编排者** — 单个人工会话驱动顺序管线（Pattern 4），阶段之间不得插入 router persona。
2. **Dispatch 表是数据，不是 router** — `ACTION_BY_STATUS` / 对账输出的是抽象动作名；不得引入重新推导或转述该表的 persona。
3. **Subagent 仅叶子、深度 ≤ 1** — 实现与评审可按 tier 规则委派 subagent；编排器不得嵌套编排 persona。
4. **禁止模式** — persona 调 persona 链、仅转述上一阶段的「顺序编排器」层、深层 persona 树。
5. **评审永不自动合并** — `merged` / `archived` 须有干净的 `verification.md` 证据与适用 gate；预算耗尽必须暂停等待用户。

本 kit 只负责单仓治理交付（`.ai-delivery/`、`status.json`、门禁）。多方协同不在本 skill 范围内 — 需要时另行安装 [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination)。
