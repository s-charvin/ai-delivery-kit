---
name: ai-delivery-orchestrator
description: 当需求文档需要经 UI truth、唯一设计契约、实现验证与合并门禁治理的端到端交付时使用。存在 `.ai-delivery` 状态或用户提供新需求文档时，作为唯一入口。
---

# AI 交付编排器

需求 → 实现的唯一入口。Leaf 技能（`requirement-breakdown`、`ui-truth-mapping`）提供方法。唯一已安装的 `ai-delivery` CLI 是当前协议、适用性、动作检查和状态转换的执行权威；本技能组织调查、产物和 handoff，不复制另一规则表。

尊重用户实际的 workspace、分支、集成和发布选择。已有授权在已审范围内持续有效，不因框架默认偏好重复询问；新的产品/资源决定仍走现有门禁。可选[原生 hook](references/native-hooks.md)使用同一程序，无 hook 也完整可用。外部框架需要 Python/Node 时仅是用户显式选择的能力，不成为 kit 运行依赖。

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

使用唯一需求级 `retrospective.md` 收集全部已知交付问题。UI、逻辑、迁移、架构、集成、测试及工具一视同仁。用户明确指出的所有问题都须记录，即使很小、已修、未复现、根因未知、暂不解决或没有复用价值；测试全绿不能排除用户观察。下一次尝试前记录现象、来源和假设，不伪造确定缺陷或根因。创建或维护前阅读 [references/retrospective-guidance.md](references/retrospective-guidance.md)，详细收集规则、UI调查及完整性核对集中在那里。

统一分类和正文，同机制补全原RET，独立机制融入分类及问题地图；禁止“2026-11-03补审”“本轮新增”、游离文末补充或第二份UI台账。批次收尾和归档前，利用现有来源逐项核对全部已知发现，尤其每个用户问题的具体案例和处置状态。索引资格不能过滤需求级收录。真正无问题也须有台账，完成核对后再更新唯一reviewed-at。

问题地图的每一行都必须由 AI 声明 `knowledge_type`、`reuse_scope`、
`index_decision`、`confidence` 和 `importance`。归档命令仅当这些字段依次为
`reusable`、`project` 或 `domain`、`include`、`confirmed`、`high` 或 `critical`
时，才将问题路由到项目索引。临时决策、仅需求适用的变更、未确认根因和机械修正
可以保留在台账中，但不会进入索引。

归档前检查是否存在旧的 `problem-index:v1` 或六列表格。发现旧格式时，先读取完整台账，
原位升级为 `problem-index:v2`，再调用归档命令。必须保留所有问题 ID、详情章节、锚点、证据和结论；
只依据已有证据分类。若无法确认复用范围、置信度或重要性，设置保守的不可索引元数据
（`index_decision=exclude`、`confidence=unverified`）。不得静默丢弃旧问题，也不得根据标题推断 `include`。

每次更新台账后，告诉用户 `RET-###` 编号、增加了什么以及文件路径。它不是实现阶段门禁，
但归档前必须存在并更新 reviewed-at。
恢复会话时读取当前问题地图；出现新现象时，将项目复盘索引作为路由表，只加载匹配的历史问题章节。
只有适用条件和当前证据都匹配才算命中，关键词相似不够。

## 用户输入及辅助材料

接收、恢复及执行中每次收到用户消息时，先定位需求／任务，完整保存原文，再解释执行。初始和相关补充、纠正、选择及续接同存该需求 `prompts/` 的一份连续任务组；恢复续写原组，独立任务才用下个文件编号。实际重复输入与可得附件仍须保存；历史缺口如实说明，不重构冒充原文。详见[保存及产物约定](references/framework-adaptation.md)和[唯一原文模板](templates/user-prompt-record-template.md)。这不授权回写归档需求，也不改变宿主存储与权限规则。

新建辅助材料前阅读[轻量产物组织](references/framework-adaptation.md)：复用已有正文与入口、保留原始证据，新自由命名材料用序号／日期前缀，固定协议路径不变。不增加目录／命名门禁或自动整理历史。

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

传统 Android View 任务在 Stage 1 能力审计时读取 [Android View 适配](references/framework-adapters/android-view.md)，设计和实现继续复用。按功能边界区分旧架构延续与独立新功能的 Kotlin/MVI/Flow/ViewBinding 标准。

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

```sh
ai-delivery context --project . --req <req-id> --subreq <subreq-id> --role recovery --format json
ai-delivery check --project . --req <req-id> --subreq <subreq-id> --intent <intent> --to <target-status> --format json
```

CLI 返回当前切片的 JSON 事实与动作诊断；从当前 status 与 handoff 表选择动作。context 材料齐全不等于动作授权。当前程序不输出旧脚本的键值队列协议。规则：[references/reconcile-rules.md](references/reconcile-rules.md)。

用 `ai-delivery check --help` 查询核心当前合法意图，用 `advance --help` /
`context --help` 查询真实参数；未初始化项目也可使用。`analysis` 是 context
角色，`analyze` 才是 check 意图。workflow 的 `finish` 包含完成纪律与集成动作；
其 CLI 就绪检查使用 `merge`，不能传 `--intent finish`。merge 检查成功不代表
已经执行集成，也不授予新的权限。

kit 只接受当前协议：包括终态在内的 status 必须为 schema `2.0`。不支持的数据停止依赖路由，报告实际与要求格式，并提供 [升级指引](references/version-upgrade.md) 中两种平级选择：用户自行备份后迁移，或显式备份重建。不补造历史批准，不自动执行任一方案。

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
- `.ai-delivery/` 外只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。在完整批次入口/出口及推进门禁前，对比 Git 状态/内容指纹账本，并为外部 skill 声明的每个默认输出根建立包含 ignored 文件的独立文件系统指纹，至少覆盖上述四个禁写根。路径、状态、类型、符号链接目标或 SHA-256 漂移能捕获动作前已 dirty 或 ignored 路径上的再次写入。发现新增或修改且位于 `.ai-delivery/` 外的流程/治理产物时，设置 `blocked_verification_failure`。
- 正常路径不要求用户安装或选择框架/技能；适配已安装的现状。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的子需求未 `acceptance_frozen` 不得进入 `solution-design`；`none` 与 `existing` 跳过该 gate。`acceptance_frozen` 同时要求静态视觉确认与每个适用 unit 的动效确认/豁免。
- 只有模式启用且明确确认、记录 CP-UI 后，才能 dispatch `ui-truth-mapping`。Stage 2 在用户已批准 workspace 中写生产代码，执行 TDD/golden 测试并完成新鲜上下文评审闭环。
- UI truth 切片未 `visual_acceptance_passed` 不得声称 `merged`；`none` 与 `existing` 使用普通行为/语义证据。
- 仍有安全可运行项时，不得将 slice-local 阻塞升级为需求全局。
- 门禁 / 阻塞 / 状态 / 合并决策永不交给子代理。默认同一实现者连续完成完整批次；leaf 技能和框架均按 Stage 4 所有权、产出边界与成本条件委派，单元数量不自动触发子代理。
- 编排器方案设计模式不要把文档写进框架自有目录；规范方案设计写入子需求 `design.md`，`notes` 只保留短指针。
- `design.md` 是唯一持久化的行为与方案设计契约。不得创建 `spec.md`、`plan.md` 或 `tasks.md`，也不得把文件级执行步骤塞入 `design.md`。跨会话恢复信息按需写 `progress.md`。
- `state_flow_required=true` 时，canonical `design.md` 必须包含状态分类、MVI 闭环、生命周期图、UI 投影、权威转换矩阵、适用异步时序、不变量和追踪。该深度不触发人工门禁。
- 设计评审仅在 `reviewed_design_sha256` 匹配当前文件、`user_decision_required=true` 时模式为 `human`、否则为 `self`，且时间戳/评审者存在时有效。`user_decision_required` 描述当前版本所需的授权类型，批准后仍保持 `true`；是否待处理由 review 有效性决定。文件变化重新打开 `solution-design`；当该 human-authority 版本缺少有效 hash-bound review 时再次进入 CP-DESIGN。
- 对 `ui_truth_mode=figma` 或 `runtime-baseline`，每个 UI unit 尚未具备真实宿主组件、十个维度的按适用性运行时 coverage、每个视觉 scenario 的官方栈预览及已向用户出示的**绝对路径**，以及有效 v3 `contracts/ui-truth-index.json` 之前，不得设置 `acceptance_frozen`。每个 scenario 必须冻结 `evidence_scope` 与 `scope_decision`；只有 `host-static` 和 `host-runtime` 可以携带有效 `host_binding`，`component-only` 明确把宿主组合排除在验收声明外。路径/hash/来源/profile/scenario/coverage、当前预览 hash 绑定确认、独立动效确认/豁免（静态 unit 必须确认无动效）与干净的 Stage 2 评审仍为必需。宿主无法录制动效时，索引必须记录原因并把运行时验收延后到 Stage 4；Stage 4 在 `visual_acceptance_passed` 前必须为每个 unit 写独立动效验收。Stage 2 由 `ui-truth-mapping` 负责真实组件，所选提供方技能（包括官方 `figma:figma-design-to-code`）在其门槛下采集证据，也禁止生成 `ui-contract.html`。可见数据缺失必须呈现真实空/省略状态，禁止伪造内容。
- Stage 4：`ui_truth_mode=figma` 或 `runtime-baseline` 的切片复用 Stage 2 用户已批准 workspace；不得创建第二个 workspace 或重画组件。`component-only` 复用组件 preview 与行为测试，不宣称宿主视觉通过；`host-static` 通过项目原生确定性工具捕获索引中的生产宿主；`host-runtime` 在昂贵的原生生命周期检查前先做设备/资源/视觉 smoke。运行时截图必须位于 `.ai-delivery/` 外、索引声明的原生测试证据根目录，并绑定索引宿主 provenance。`existing` 使用已有组件和普通行为/语义验证，`none` 没有 UI truth 产物。默认不要再查 TemPad 或官方 Figma；已冻结组件 + 已确认预览才是视觉真值。遵循 fill / hug / fixed（fill = 父宽减内边距，不是快照 px）。禁止把平行预览翻译到另一宿主栈。
- `ui_truth_mode=figma` 或 `runtime-baseline` 的 UI truth 工作未先 `acceptance_frozen` + `visual_acceptance_passed`、有效 v3 `ui-truth-index.json`，以及按冻结证据范围覆盖全部已索引 scenario 的 schema v2 结构化 `visual-acceptance.json` 时，不得 `merged`；`none` 与 `existing` 按普通验证收口。
- 仅在 CP-ARCHIVE 确认后通过 `ai-delivery archive --confirm-archive --expected-snapshot <snapshot-id>` 设置 `archived`。该动作只原位更新 `status.json`，不得创建 `archive/<ISO-ts>/`、复制 canonical 产物或写入 `MANIFEST.json`。已完成需求目录保留为历史事实源；后续变更须使用新的 `<req-id>` 目录。
- 最新一轮评审不干净时不得声称任务完成或合并；评审循环预算耗尽时升级给用户。
- 实现阶段逐文件修改，尊重用户实际集成选择；仅在已授权分支流程需要时 rebase，不自动 commit、push 或 release。

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

`implement` 动作使用所选档位，并依据实际所有权与依赖选择顺序执行或分派。派发前执行[保持既有所有权的 brief 约定](references/stage-4-sdd-bridge.md)，传递宿主规范、既有权威、修改边界与结果导向的验证要求。brief 从当前 `design.md`、代码证据和 `progress.md` 形成，不持久化第二份计划或任务清单。需求拆分仅是跟踪边界；框架对小单元或独立测试的偏好不能授权新增生产 owner。无论哪个档位，都执行依赖安全的 TDD 与完成前集成评审。

链路：解析已批准 workspace 并复用 Stage 2 选择 → 同一实现者执行定向 TDD → 独立集成批次评审 → 必要视觉/运行时验收 → 核对当前证据并补齐最终范围内的缺失检查 → 合并。按实现指南的验证与证据复用规则执行，阶段变化不要求重跑仍有效检查。

UI truth 切片：接线已经写好的组件（API / 路由 / 状态 / 挂载）；`existing` UI 只做普通行为/语义验证；默认不要再查 TemPad 或官方 Figma。

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

先定位所属需求／任务，完整保存可得用户输入到原提示词组；恢复不重复保存仅重新读取的消息，再运行以下流程。

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

归档前从原始用户输入和已知发现逐项反查RET案例及处置状态，遗漏直接整合正文，再更新reviewed-at，详见复盘指导。客观归档检查不证明语义完整性。

所有可执行子需求 `merged` 后，运行显式归档检查并处理 CP-ARCHIVE。执行最后一条归档命令前，先把 `templates/delivery-report-template.md` 实例化为使用用户当前对话语言的临时模板，删除其中的 `ai-delivery-template-language` 注释，并保留所有占位符。对每个子需求运行 `ai-delivery archive --confirm-archive --expected-snapshot <snapshot-id>`，仅原位推进状态至 `archived`，不得复制 canonical 产物或生成快照；最后一条命令须通过 `--delivery-report-template <path>` 传入准备好的模板。需求必须有 `retrospective.md`，还要把 `templates/retrospective-index-template.md` 实例化为使用用户当前对话语言的模板，删除语言指令并保留标记和占位符，在最后一条命令通过 `--retrospective-index-template <path>` 传入。归档命令要求唯一且可解析的 `<!-- ai-delivery-retrospective:reviewed-at:<RFC3339Nano-with-timezone> -->` 标记，其日历日期必须与归档日期一致；然后读取台账带标记的问题地图，仅将明确符合资格的高价值问题幂等更新到 `.ai-delivery/retrospectives/index.md`。会检查客观地图／详情结构，但不会创建、重写、总结或语义审计台账。没有合格问题的台账有效且不写新的索引文件或索引行；台账缺失或过期则阻断归档，并告知用户登记了哪些问题行以及哪些问题因资格字段缺失或不符合而跳过。已本地化的 `delivery-report.md` 不存在时，不得声称 `completed`。当每个子需求均为 `archived` 时，需求进入 `completed`；canonical 产物原位保留，后续变更须新建 `<req-id>` 目录。

## 编排形态（不变量）

以下规则防止编排退化，适用于主会话与对账 dispatch：

1. **主会话即编排者** — 单个人工会话驱动顺序管线（Pattern 4），阶段之间不得插入 router persona。
2. **Dispatch 指引是导航，不是另一规则引擎** — 使用当前 CLI 事实和动作诊断，不重建旧 reconcile 队列，也不引入重新推导核心规则的 persona。
3. **Subagent 仅叶子、深度 ≤ 1** — 实现与评审可按 tier 规则委派 subagent；编排器不得嵌套编排 persona。
4. **禁止模式** — persona 调 persona 链、仅转述上一阶段的「顺序编排器」层、深层 persona 树。
5. **评审永不自动合并** — `merged` / `archived` 须有干净的 `verification.md` 证据与适用 gate；预算耗尽必须暂停等待用户。

本 kit 只负责单仓治理交付（`.ai-delivery/`、`status.json`、门禁）。多方协同不在本 skill 范围内 — 需要时另行安装 [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination)。

## 规范上下文与质量闭环

开工、恢复、阶段/范围变化和独立评审前，读取并执行 [质量闭环](references/delivery-quality-loop.md)。
使用同一只读上下文入口；新 policy v4 的 verification v2 绑定当前输入、原生结果与新鲜上下文评审。
区分知识、已确认规范及任务决定；证据无效先修取证，真实失败定向纠错，沿用三轮预算。
已登记 sources 且 writable 的规范允许在授权范围维护，导入默认只读，不为通过检查自行降标。
不引入 Trellis/Helix 的第二任务状态、自动提交、逐单元人审或无限循环。
