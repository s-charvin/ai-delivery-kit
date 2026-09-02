---
name: ui-truth-mapping
description: 仅当 ai-delivery 编排器已有受治理的 `.ai-delivery` 需求切片处于 Stage 2、CP-UI 已确认，且必须把 Figma 或 runtime-baseline UI 真值冻结为真实宿主栈组件（优先 Flutter）与官方栈验收预览时使用。适用于作用域子树、多状态、Spine/Lottie/shimmer 动效、蒙版/alpha 合成，或修复先前 HTML 契约/整页 dump。泛化 Figma 实现请求不要触发本技能，使用宿主项目惯例或 `figma-design-to-code`。
---

# UI 真值映射

从 Figma 或已批准的 runtime baseline 提取结构化 UI 真值，冻结为**宿主项目里的真实组件**，外加用户能打开的官方栈预览。

编排器在 Figma 提供视觉证据时选择 `ui_truth_mode=figma`；没有稳定 Figma、由需求/项目/明确用户决策提供基线时选择 `ui_truth_mode=runtime-baseline`。本技能绝不把 runtime baseline 说成 Figma 1:1 真值。

**原则 1 — 禁止二次转换。** 写项目已经在用的 Widget/组件。不要先冻一份 HTML（或任何平行赝品）再翻译成 Flutter/React。

**原则 2 — 官方预览。** 使用宿主栈可确定性生成的官方预览。Flutter 静态 scenario 使用 `flutter test --update-goldens` 产出的 golden PNG；动态 scenario 在宿主能生成时还应额外生成测试 GIF。动效捕获目标为 25 FPS（每帧 40 ms），覆盖连续变化区间；不得使用 100 ms 以上的稀疏 keyframe。GIF 以厘秒存储时间，因此 40 ms 可以精确得到 25 FPS。均匀捕获必须显式声明目标速率；带有意停顿或可变帧间隔的捕获必须保留这些时长，不得被恒定帧率选项压缩或拉长时间轴。编码器必须显式接收 25 FPS 的输入/输出速率。每份动效预览必须包含完整的 trigger→settled 转场或至少一个完整循环，只允许简短可审阅的片头/片尾停留，并自动重播。展示前必须解码并核验帧数、总时长与循环元数据。GIF 是本技能唯一治理的动效预览格式：不要新增 WebP/MP4 编码器，也不要把其他格式设为门槛。宿主无法录制 GIF 时不得伪造文件：先取得动效决定、记录预览不可用原因，并把运行时验证延后到 Stage 4。Web 使用该仓已有的预览方式。对话里给用户 **每份预览的绝对路径**。交付索引里只存 **仓内相对路径**。

**原则 3 — 分离可见设计真值与运行时真值。** Figma 只拥有其实际展示的像素与转场。需求拥有产品行为；既有项目规范拥有实现约定；明确用户决策补齐关键缺口。Figma 未展示的运行时 state 绝不称为「1:1 还原 Figma」。不得静默用运行时惯例覆盖 Figma 已展示的像素。

此技能只做一件事：CP-UI 授权后，在受治理 Stage 2 全程使用编排器传入的**用户已批准 workspace**，给定需求切片 + 设计源，在**项目源码树**里定位或创建匹配单元，把视觉真值与已批准的运行时 coverage 冻在那里，出示每个视觉 scenario 的预览路径，并记录 v2 指针/治理索引。它不选择或创建 workspace、不拥有索引以外的流水线状态、不决定下一阶段，也不发明第二份视觉真值文件（YAML/JSON/markdown 不得当像素用）。

## 输入

- 需求切片（范围、字段、验收信号）
- 真值源定位符：`figma` 使用 Figma 文件 key + 节点 id；`runtime-baseline` 使用 requirement/project/user-decision 引用
- 后续需求：目标单元的任何线索（路径、Widget 名，或「尚无已知单元」）

## 输出

每个独立单元：宿主树里的 **生产代码** + 官方预览文件 + 子需求索引中的一行指针。

```
<宿主项目>
├── lib/…/<unit>.dart          # Flutter：真实 Widget（跟邻接文件）
├── test/…/<unit>_golden_test.dart
├── test/goldens/<unit>.png    # 静态审阅媒介
└── test/motion/<unit>.gif     # 可选的 GIF 动效审阅媒介

.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/
└── ui-truth-index.json        # 只做指针 — 不是绘制
```

审阅说明、冻结包以及生产/测试代码中的必要注释，都使用用户当前对话语言。代码符号、测试 API、机器可读键与枚举值、ID、路径、命令和协议字面量必须保持原样。产品 UI 文案仍遵守产品自身的本地化要求。

`ui-truth-index.json` 是 **指针与覆盖台账**，不是图纸。使用 [templates/ui-truth-index-template.json](templates/ui-truth-index-template.json)，保持机器结构不变，并用用户当前对话语言填写人类可读的 `confirmation.note` 与 `coverage[].note`；至少持久化：

| 字段 | 含义 |
|---|---|
| `schema_version` | 整数 `2` |
| `ui_truth_mode` | `figma` 或 `runtime-baseline`，必须与子需求状态一致 |
| `design_source` | `figma` 的 file key/root node/revision，或 `runtime-baseline` 的 evidence origin/source reference，及采集时间 |
| `unit_id` / `type` / `stack` | kebab-case id、`page`/`component`/`modal`/`shared-component`、`flutter`/`web` |
| `source_node` / `dependencies` | Figma 源节点与 unit 依赖 id |
| `component_path` / `component_sha256` | 真实组件仓内相对路径与当前内容 hash |
| `golden_test` / `golden_test_sha256` | Flutter golden 测试与当前内容 hash |
| `motion_decision` | 每个 unit 必填：`animated` 或 `static`、验证方式、独立确认/豁免说明；可选动效预览路径/hash；无法录制时必须写明原因 |
| `profiles[]` | 测试 surface、尺寸、orientation、theme、locale、text scale、reduced motion 与 input mode |
| `states[]` | `state_id`、`evidence_origin`、`source_ref`；Figma 来源 state 还必须有 `source_node` |
| `scenarios[]` | State + profile + coverage dimensions + review mode + 来源；视觉 scenario 指向确定性 preview |
| `coverage[]` | 每个必需运行时维度恰好一条适用性记录 |
| `confirmation` | `confirmed` 或 `waived`、时间/人员；视觉确认绑定 `reviewed_preview_sha256` |

**禁止** 生成 `ui-contract.html`。**禁止** 拷贝 `ui-contract-template.html`（已删除）。**禁止** 把 HTML 翻译成 Flutter。runtime-baseline 只能使用 `requirement`、`project` 或 `user-decision` 来源，不得伪造 Figma 元数据。

## 技术栈

根据仓库自行判断。不要跑复杂探测。

- 看起来像 Flutter（Dart Widget、`pubspec.yaml` 含 Flutter SDK、已有 `test/` golden）→ **Flutter**。本技能按这条路径写。
- 看起来像 Web 应用（该仓已有页面/组件树）→ **Web**。跟 **该仓** 架构（React/Vue/Svelte/纯 HTML — 邻接文件用什么就用什么）。不要假设「契约就是 HTML」。
- 拿不准 → **停下问用户**。不要默认冻一份 HTML 契约。

## 模板（Flutter 静态与动效预览骨架）

```
templates/
├── flutter-golden-preview-test.dart.example
├── flutter-motion-preview-test.dart.example
└── ui-truth-index-template.json
```

静态示例教 `MaterialApp` / `RepaintBoundary` / `matchesGoldenFile` / `--update-goldens` 及注释中的预览规则（PNG 画布 ≠ 运行时尺寸、每个视觉 scenario 一个 `testWidgets`、不要系统栏、不要 Widget 内状态切换器）。动效示例要求先通过真实 Widget API 触发动效，再按累计 keyframe 写 PNG 并使用已有 GIF 编码器；GIF 已足够，不要新增 WebP/MP4 编码器或依赖。**它们都不是 Widget 模板。** 不要把教学注释复制进项目代码；只保留必要注释，并改用用户当前对话语言。Widget 代码必须仿邻接生产文件。不要加宿主项目没有的依赖。

## 快速参考 — 场景 → 单元拆分

不要默认映射整份 Figma 证据。先匹配 **需求体量**：

| 真实场景 | 要冻结的单元 | `get_code` / 根 | 状态 | 不要 |
|---|---|---|---|---|
| 新整页路由（页面本身在范围内） | `page`（共享外壳仅当外壳也被新接受） | 页面内容帧（排除已有所属外壳） | 页面级变体 | Dump 已有单元的持久 tab/nav |
| 已有外壳上的小徽章 / 红点 / 单个控件 | 若现有 Widget 根包含该产物则 **修补**；否则在徽章处 **创建** `component` | 徽章/控件的最小祖先 | 通常无 | 为了扛一个徽章新建整页 Widget |
| 范围内断开的产物 | 每个簇一个 `component` / `modal` | 每簇局部最小祖先 | 按单元需要 | 用全屏当根「两个都罩住」的一个 page |
| 底栏 / 对话框 / 弹出层 | 单独 `modal`；触发器补丁进触发器所在容器 Widget | 弹层帧 | 所有弹层帧作为具名状态 / golden | 把弹层嵌成页面状态；把触发器放进 modal Widget |
| 多状态列表/表单/模块 | 一个 `component`（若路由本身是范围则 `page`） | 作用域模块根 | 每个视觉帧 → 一个 golden（或宿主已有的多 golden 写法） | 同一单元每个状态一个独立 Widget |
| 仅元素属性（`disabled` / `selected`） | 在已有单元里补丁该节点 | 不变 | **不要** 加单元级状态 | 把 `disabled` 做成整单元 golden |
| 带 **变体属性** 或 **动效** 的组件 | 同一单元；记录独立的 `motion_decision` 与动效证据 | 组件/实例根 | 静态 **关键帧** golden + 独立动效决定（宿主能录制时使用 GIF） | 只当静态 PNG 或省略动效表 |
| 同边界 **颜色渐变 + alpha 渐变** / Figma 蒙版 | 同一单元；把兄弟当绘制层之前先跑 **§3b** | 合成后的绘制根 | 一个合成效果 | 两层 `src-over` 覆盖填充 |

## 硬边界

- 仅能由受治理 Stage 2 且对 `ui_truth_mode=figma` 或 `runtime-baseline` 已记录 CP-UI 的切片调用。这是 Stage 2 UI Truth Mapping 内的冻结门槛，不是独立 Stage。仅静态 golden 确认绝不能推进到 `acceptance_frozen`。本技能会在记录的用户已批准 workspace 内写生产代码、golden 测试、预览与 v2 索引，不是无实现的前置检查。Workspace 选择仍归编排器 `workspace-policy.md` 所有。
- **按需求作用域抽取：** 范围内产物决定根 — 覆盖属于 **一个** 单元的产物的最小祖先。断开的产物 → 拆单元。永远不要整页 dump。
- **先写单元拆分计划再取证：** 任何 `get_code` 或组件代码之前填 §1b。
- **只对作用域调 `get_code`。** `get_code` 目标 **必须等于** 计划中的 `source_node`。整页 `get_code` 再裁剪是过程失败。
- **不要发明视觉真值。** 不得有 Figma 证据（`get_code` / `get_structure`）之外的 Figma 来源单元、state、绘制、图标或转场。缺失运行时行为只能来自 requirement、project 或明确 user-decision 证据，并须正确标记来源。
- **真实数据或有意为空。** 范围内绑定数据的值缺失、为 null、为空或尚未可用时，渲染产品真实的空/省略状态。绝不在生产代码里注入假记录、示例图片、占位文案或 fixture 值来填满预览；测试 fixture 只能为夹具机制或有证据的资源提供确定性字节，绝不能用 fixture 字节代替缺失的范围内视觉/数据，或让预览看起来完整。
- **禁止未经批准的占位或视觉替身。** 范围内可见表面、交互、输入、图标、图片或动画必须使用真实宿主控件与有证据的资源。不得用外部注入 Widget/slot、dummy 数据、缩略图、fixture、静态替身、通用图标或「差不多」资源让 scenario 看起来完整。外部注入仅可用于真实依赖边界，且不得承载范围内视觉 UI 或动效本身。
- **缺资源必须取得用户决定。** 必需字体、图标、图片、动画或 effect 无法获取/渲染时，在该边界停下并让用户选择：渲染为空、延后资源并保持 scenario 阻塞，或阻塞 unit。只有用户选择后才能渲染为空并记录受影响 scenario；不得静默 fallback。缺失动效资源时，未经该明确决定不得使用海报帧或静态替代。如果确实需要临时占位来辅助评审，必须另行询问用户是否允许；明确批准必须写明资源与作用域，且占位不得进入生产 UI/数据路径。没有该批准仍然严禁占位。
- **保留所需资源类别。** 必需的矢量/SVG 图标不能用位图、字体字形、平台图标或视觉近似替代；必需的 Spine/Lottie 资源不能用静态图片或手绘动画替代。证据要求的资源类别不可用时，必须按上述缺资源决策处理，不得静默降级资源类别。
- **使用真实交互原语。** 输入必须是可编辑的宿主控件，并具备所需 focus、键盘/IME、校验与语义行为。图标和图片必须来自有证据的项目/设计资源；缺失资源时，熟悉的字形或平台图标也不是授权替身。
- **不要发明布局。** 把几何机械迁入宿主布局系统（Flutter 约束、CSS 等）。不要手写语义化整页而丢掉证据。
- 预览 px 是画板快照，不是运行时尺寸。分类 **fill / hug / fixed**（§5b）。可变文案是 hug 或 fill 加 overflow / min / max — 禁止按样品写成 fixed。
- 禁止把 TemPad `data-hint-*` 拷进产品代码或索引。
- Figma 蒙版 / 仅 alpha 渐变 **不是第二层可见罩色**。跑 §3b。
- 不要把系统 UI（状态栏、手势条、输入法、设备铬）当组件内容 — 用安全区处理。
- 未向用户出示预览绝对路径并取得 **每个视觉 scenario 的显式确认** 不得宣称冻结。仅当用户豁免该具体 scenario 的复审时可跳过。
- 不要在组件旁再造第二份视觉真值文件（禁止把伴生 YAML/JSON/markdown 当绘制）。`ui-truth-index.json` 只做指针。
- 不要扫描仓库里每一份历史文件来找匹配。用需求 id、路由/Widget 语义、已知关系或显式路径定位。
- 不要凭记忆写未经核实的 `delivery.implemented.target`（或等价字段）。
- 任一适用运行时维度未解决时不得冻结。合法 coverage status 只有 `covered` 与带理由的 `not_applicable`。
- 不得为修复可见的无障碍、平台或性能冲突而静默修改 Figma 已展示像素。优先实现不改变像素的语义与命中区域修复；否则停下取得明确设计/用户决策。

## 定位

创建 vs 修补之前做 **实现查找**：是否已有匹配此单元的 Widget/组件？

- 优先用用户或切片已经点名的显式路径。
- **按范围内产物的物理 Figma 容器路由**，不要按需求所属路由。共享 tab 栏上的徽章补丁进该栏的 Widget。
- 恰好一个匹配 → 决策。零 → 创建。多个说得通的匹配 → 停下询问。

## 决策：创建 vs 增量修补

| 情况 | 动作 |
|---|---|
| 没有已有单元匹配 | 在邻接生产文件旁 **创建**。 |
| 恰好一个匹配且改动装得下 | **增量修补。** 只改受影响的子树 / 状态。 |
| 边界 / 路由 / 共享依赖根本变化 | **重建** 该单元；若概念上仍是同一个则保持 id 稳定。 |
| 匹配含糊 | **阻断。** 询问。 |

**重建/拆分的元数据规则：** 继承来的「已经实现」声明必须 **对照当前代码再核实**（定义 + 引用/用法搜索），否则丢掉。

## 工作流

### 1. 确认上游、范围清单与定位

从切片做一份短的 **范围清单**（必须冻结 / 仅上下文 / 忽略）。然后定位。在查询 TemPad **之前** 记录创建 / 修补 / 重建。

### 1b. 单元拆分计划（任何 `get_code` 或组件代码之前必做）

在对话里公布此表（**不要** 写伴生映射文件）：

```
| 产物（节点 id + 标签） | 单元 id | 类型 (page\|component\|modal\|shared-component) | 动作 (create\|patch\|rebuild) | source_node | 状态 | 动态 | get_code 目标（= source_node） |
```

枚举帧是为了分类 — 不是为了冻结。跳过 §1b 单元拆分计划是过程失败。

### 2. 枚举帧是为了分类 — 不是为了冻结

给每帧分类：`page` / `component` / `*-state` / `modal` / `shared-component` / `context` / `ignore` / `dynamics-hint`。

**分组：** 局部范围内 → 优先 `component`/`modal`。断开产物 → 多单元。同一外壳不同内容 → 一个单元的多个状态。Modal 永远自己一个单元；触发器住在触发器的容器里。

### 2c. 动态与动效扫描（每单元必做，§2 之后）

0. **文本提示扫描** — 作用域子树 **以及** 父级 SECTION 兄弟里的 TEXT / 便签 / 标注。关键词：motion、animation、transition、typewriter、shimmer、Spine、skeletal、Lottie、GIF、skeleton、placeholder、API-returned、pulse、loading（以及设计师语言的等价说法）。
1. 在 `source_node` 上做 **候选扫描**（INSTANCE/COMPONENT、图片填充、动效命名图层）。
2. 有工具时做 **动效探测**（`get_node_motion` / 等价）。缺工具时文本提示仍然算数。
3. **资产** — 只有在证据要求且确实提供字节时，才持久化 Spine/骨骼、Lottie、GIF 或视频等原始资源类别；视频源资源绝不是另一种动效预览输出。必需资源不可用时标记 `pending-user` 并停下；未经用户明确决定不得使用海报帧或静态替代，也不得发明文件。记录 trigger、播放/循环策略、中断行为、离屏策略与 reduced-motion fallback。绑定真实数据的资源缺失时，记录真实空/省略结果，不得补 fixture 内容。
4. **分类**（`content-bound`、`component-variant`、`motion-preset`、`design-animation-asset`、`prototype-transition`）。
5. **映射** 到状态 / golden / 动效审阅证据。Golden 只是静态审阅帧，绝不是运行时表面的占位层。绑定真实数据的可见内容必须对应真实值或有意为空。**用户点名的参考实现：** 若用户指向现有代码，**先读它**；预览力学必须匹配该参考（get_code 的 packing 不得悄悄反转生长/显现）。
6. **一致性检查（写组件代码前必做）：** 跨状态/实例的同一铬不能在没有显式证据时得到不均的动效覆盖。不均覆盖是异常 — 停下询问。
7. **每次裁剪后的覆盖复查（必做）：** 把剩余源条款对照剩余目标再读一遍。多条款 SECTION 备注按 unit 拆分。

给用户记一份 **动效与转场** 表（用用户的语言）：Scenario | Trigger | From | To/keyframes | Duration | Easing | Delay | Repeat | Interrupt/reverse/cancel | Reduced-motion fallback | Performance strategy | Reference。每个 UI unit 都必须有明确动效决定：有动效时描述动效契约；没有动效时明确记录并确认「static / no motion」。动效 ≠ 数据绑定。缺失生命周期证据表示 coverage 未解决，不代表可以自选通用动画。静态视觉确认和动效确认/豁免是分开的证据，单张 keyframe PNG 永远不能替代动效验收。宿主能确定性录制时展示 GIF，并把路径和 SHA-256 写入 `motion_decision`；GIF 已足够，不需要其他动效编码器。放进 golden/Widget 注释或对话冻结包 — 不要当成第二份绘制文件。

### 2d. 缺失资源升级

`pending-user` 资产或缺失的绑定数据 → 冻结前停下询问。用户必须明确选择真实资源、批准为空，或阻塞/延后 unit；「先用占位」不是隐含选项。如果技能判断临时占位是唯一可行的评审辅助，必须询问用户明确批准其确切作用域，并让它留在生产 UI/数据路径之外。把决定和受影响 scenario 记入现有冻结记录。

**分派：** 多个独立单元 → 每单元一个子代理，证据隔离。

### 3. 采集最小 TemPad 证据

对每个计划单元 / 状态，只对 **作用域内** `source_node` 调 `get_code`。层次、重叠或 fill vs hug vs fixed 仍含糊时再 `get_structure`。解析每个资产：分类（静态 vs 内容绑定 vs 动效）→ 相同则复用项目已有资产 → 持久化字节（TemPad URL 会过期）→ 永远不要手绘「看起来差不多」的字形。

### 3b. 绘制合成 / 蒙版扫描（`get_code` 之后必做）

同一盒子里重叠的填充 **不会** 自动变成两层绘制。

TemPad 提示（永远不要把 `data-hint-*` 拷进产品代码）：

| 来源 | 信号 | 含义 |
|---|---|---|
| `get_code` | `data-hint-mask="true"` | 此节点是 **蒙版** |
| `get_code` | `data-hint-has-mask="true"` | SVG **已经烘焙** 蒙版 — 不要再叠一层覆盖 |
| `get_structure` | `"isMask": true` | 同蒙版（为 false 时字段省略） |

名称/CSS 出现 mask / 蒙版 / `mask-image` / 混合 ≠ src-over、两填充同边界、或渐变只改 alpha 时也要跑。

| 角色 | 判定 | 冻结为 |
|---|---|---|
| `paint` | 去掉它可见颜色/图像就没了 | 颜色/图像源 |
| `mask` | 去掉它只改变另一层的 alpha/裁剪 | **绘制的** alpha/裁剪 — **不是第二层可见罩色** |
| `overlay` | 另一层没了它仍增加可见颜色 | 独立层 |

同边界不透明 RGB + 渐隐 alpha 的默认 → **一个** 合成效果。实现用 `Mask` / `dstIn` / `ShaderMask` / `mask-image`，不要两层叠填充。着色 vs 蒙版含糊 → 停下询问。

### 3c. Runtime Coverage Plan（写组件代码前必做）

Figma 常只展示一个最终样例，但生产代码必须承受真实的 state、环境、内容与输入变化。收集设计证据后、编写组件代码前，为每个 unit 公布一份 plan。

每个 scenario 使用以下来源顺序：

1. **Figma** — 只对实际展示的像素与转场有权威性。
2. **Requirement** — 对产品行为与验收边界有权威性。
3. **Project** — 对已有设计系统、平台、本地化、无障碍、资源与测试约定有权威性。
4. **User decision** — 前三者无法解决关键行为或可见结果时必须取得。

每个 state 与 scenario 都记录 `evidence_origin`（`figma` / `requirement` / `project` / `user-decision`）及具体 `source_ref`；Figma 来源 state 还记录 `source_node`。来源冲突是 blocker，不得靠猜测合并。

每个 unit 必须把下列每个维度标为带 scenario ids 的 `covered`，或带理由的 `not_applicable`。适用但未解决的行阻止冻结。

| 维度 | 适用性扫描 |
|---|---|
| `state` | 数据/交互模型可达的 initial、loading、refreshing、populated、empty、partial、error、offline、authentication、permission、disabled |
| `layout` | 最小/目标/最大约束、container/viewport breakpoint、orientation、安全区、fixed/sticky 共存、overlay、IME、scroll、z-order、clip、hit testing |
| `content` | 空/短/长/多行/不可断字符串、列表数量、大数字与本地格式、RTL、locale 切换、text scaling/browser zoom、wrap/truncation/expand |
| `interaction` | idle、hover、focus、pressed、selected、expanded、keyboard、pointer/touch、drag/swipe 替代、快速重复、重入、focus trap/return、disabled 行为 |
| `motion` | trigger、from/to 或 keyframes、timing、捕获节奏（目标 25 FPS / 每帧 40 ms）、easing、delay、repeat、interrupt/reverse/cancel、reduced-motion 结果、确定性测试关键帧、repaint/资源生命周期 |
| `assets` | static/content-bound/motion 角色、来源/所有权、vector palette/themeability、fit/crop/focal point、aspect ratio、density、loading/error/empty/offline fallback、cache、semantics |
| `theme` | Figma variable modes、宿主 semantic tokens、支持的 light/dark/high-contrast、contrast 与交互态一致性 |
| `accessibility` | 原生 semantics、name/role/state/value、reading/focus order、可见 focus、screen-reader 更新、平台点击热区、非颜色提示、Web WCAG AA、reduced motion/text scaling |
| `platform` | 支持的平台与输入模式、系统栏/安全区、返回/导航、IME、pointer/touch 惯例、平台原生组件 |
| `performance` | 稳定 loading layout、适用时列表虚拟化、正确图片尺寸、animation/repaint 隔离、controller/资源释放、离屏暂停、项目原生预算 |

每个可编辑输入都必须有明确的状态/IME 矩阵。至少覆盖：未输入且未编辑；已聚焦且正在编辑；已完成且未编辑；平台可展示时的 IME 隐藏与 IME 显示。可达时再补校验、disabled/只读、提交或多行状态。每一行必须绑定可见值、focus、可审阅时的选区/光标、随状态变化的图标/装饰、IME/inset 条件、底部操作布局、滚动/避让行为，以及收起/提交转场。不得仅因字段同页或同布局就从另一行推断。

只创建产品实际支持的 profile；不得生成通用笛卡尔矩阵。每个 profile 记录 `surface.kind`（`viewport` 或 `container`）、测试宽高、可选 device-pixel ratio、orientation、theme、locale、text scale、reduced-motion 与 input mode。Profile 尺寸配置证据与测试，不得转成运行时固定尺寸。

每个 scenario 绑定一个 state 与一个 profile，并列出它证明的 dimensions。像素复审使用 `review_mode: visual`；语义/交互/生命周期检查使用 `behavior`；两者兼有用 `both`。Visual 与 `both` scenario 需要确定性 preview 与明确确认；behavior scenario 需要已批准来源及后续宿主项目原生验证方式。

没有 Figma frame 的运行时 scenario，只能在语义匹配时复用现有项目组件与 token。它们是已批准技术行为，绝不是「1:1 还原 Figma」。若可见无障碍或平台修正与 Figma 冲突，先实现不改变视觉的 semantics/hit-area 修复；否则停下取得设计/用户决策。

### 3d. 资源与渲染计划（`assets` 为 covered 时必做）

对每个图片、SVG、icon、animation、gradient、blur、shadow、mask 或 blend effect 记录：角色、证据/来源、持久化交付路径、尺寸类别、fit/crop/focal point、aspect ratio、density 或 vector scaling、token/theme 行为、loading/error/offline fallback、cache policy、semantics 与 test-harness fixture（绝不作为生产 fallback）。

在语义组件边界解析资源组合，不要只从叶子导出拼装。当多个矢量/图片图层构成一个可复用视觉，且设计源提供组合导出或可导出父级时，持久化并使用该组合资源。不要下载最小叶子再在宿主布局代码里重建几何、蒙版或偏移。只有证据表明运行时状态、主题、动画、无障碍或宿主既有资源管线需要独立控制时才拆开；把原因记入资源计划。

选择能保留证据的最低复杂度宿主原生路径：已有/原生 primitive → 项目既有依赖 → custom painter/shader → 仅对缩放、主题、无障碍仍正确的真正静态输出使用预渲染资源。缺失字体、字重、vector semantics、effect 或运行时资源时阻止冻结；不得静默替换成近似实现。

### 4. 写真实组件（Flutter 优先）

**创建：** 把 Widget 加在邻接文件旁。对齐它们的构造函数风格、主题、间距助手和目录布局。**不要** 拷一份 Dart 模板再填空。

**增量修补：** 打开匹配到的文件；不要重写无关子树。

把证据映射进宿主布局系统：

- Flutter：按几何需要用 `Row`/`Column`/`Stack`/`Positioned`/`Expanded`/`Flexible`/`Wrap`/`SizedBox`/`AspectRatio`。图片：测试里用项目已有的 fixture/`ImageProvider` 惯例 — **golden 测试禁止打真网**。
- Web：在该仓组件里遵守同一纪律。

通过组件真实 API 实现每个 covered scenario。优先使用原生交互 primitive 与项目既有组件；保留 semantic role/name/state、键盘或手势替代、focus order/trap/return、平台点击热区与 screen-reader 播报。宿主已有能力时补聚焦的 behavior/semantics 测试。不得仅为满足本技能新增依赖。

对可编辑控件，从真实控件状态推导视觉变体——focus、当前值、校验、enabled/只读与 IME 可见性——而不是从页面、布局、路由或预览 scenario 名称推导。重复出现的输入组件共用同一状态模型，除非证据明确区分。

若布局或动画代码会预测量文本，必须使用与实际渲染相同的已解析字体族、字重、样式继承、locale、方向、文字缩放/zoom、约束与行高。用默认或仅测试用排版做的测量无效。几何只应在真实换行、行数或有证据的状态变化时改变。

Figma 来源 scenario 精确保留有证据的 font family/可用 weight、line metrics、letter spacing、filter、shadow、gradient、blur、mask、blend mode、clip、opacity 与 stacking。缺字体/effect 或与宿主 renderer 冲突是 blocker，不是允许近似。requirement/project/user-decision 来源 scenario 遵守记录来源并复用宿主设计系统。

把审阅说明（范围内/外、运行时 coverage、动效表、资源、尺寸、合成、无障碍）写成 Widget/golden 注释和冻结对话。那是审计文案，不是产品 UI。

状态 id：kebab-case ASCII（`^[a-z][a-z0-9-]*$`），可当 golden 文件名（`loading`、`empty-state`）。

### 5b. 布局尺寸分类（机械迁移后必做）

`get_code` 的 px 是 **预览几何**。给每个范围内盒子分类（单元根必做；子级不同时也做）：

| 类别 | 含义 | Flutter（典型） | Web（典型） |
|---|---|---|---|
| `fill` | 伸展到父级剩余空间 | `Expanded` / 紧父约束 | `width: 100%` / flex-grow — **不是** 快照 px |
| `hug` | 随内容尺寸 | 子级固有尺寸，可选夹紧 | `width: fit-content` / auto |
| `fixed` | 设计锁定 | `SizedBox` / 显式约束 | 仅锁定时才写死 px |

**fill 判定规则：** 满足任一即 `fill`：Figma FILL / 拉伸约束；测得 px 等于 **父宽减去对称水平内边距**（1px 容差）；节点在视觉上铺满剩余内容列。

**hug：** 文本、芯片、行、任何应跟随内容的盒子（包括比样品更长的 i18n / 服务端字符串）。

**仅 fixed：** 图标、头像、非内容图、最小点击热区、显式锁定。因为 get_code 打了 px 就默认 `fixed` 是过程失败。

**可变内容：** 该轴 hug 或 fill — 永远不要按快照写成 fixed。记录 **overflow 策略**（`wrap` / `ellipsis` / `clip` / `scroll` / `grow-parent`）以及设计或需求锁定时的 min/max。若需求 **和** 设计都沉默 → **停下问用户**。

实现消费分类，不消费快照 `w×h`。把每个快照盒子倒进布局常量是过程失败。fill/hug 的测试断言约束行为，不断言快照相等。

### 6. 官方预览（Flutter golden）

把 `templates/flutter-golden-preview-test.dart.example` 只当 **骨架**，动效捕获使用 `templates/flutter-motion-preview-test.dart.example`。两者都只是骨架。宿主已有 `flutter_test` 惯例则跟它。

```bash
flutter test <golden_test.dart> --update-goldens
```

当请求的审阅范围是完整预览矩阵时，必须执行每个已索引 scenario，并重新生成或重新哈希该矩阵中的每份产物。测试对照已有基线通过，并不证明产物由当前代码写出；未变的 hash 也必须显式记录。

动效要先通过真实 Widget API 触发，再按目标 25 FPS（每帧 40 ms）严格递增的累计 `pump` keyframe 覆盖整个动效区间（GIF 至少两个），并用 `matchesGoldenFile` 写出每个采样 PNG 帧。不得只捕获间隔很大的关键帧后宣称预览流畅。这个官方 matcher 路径优先于重复直接 `RenderRepaintBoundary.toImage` 调用，因为它负责测试绑定的栅格读回生命周期。捕获时间轴必须足够早以展示 trigger，跑完整段转场或一个完整循环，并以短暂 settled 停留结束。帧写出后调用宿主已有 GIF 编码器。均匀 40 ms 采样必须显式接收 25 FPS 的输入/输出速率；有意停顿或可变间隔必须保留声明的每帧时长，不得强制恒定帧率。GIF 已足够。发布前必须解码并核验期望帧数、总时长、终态或完整循环，以及自动循环元数据。没有编码器时记录不可用原因，不得伪造动效文件。

然后把每个静态 preview，以及已生成的每个 GIF 动效 preview 的 **绝对路径** 打印给用户。多个 state/profile 组合 → 多个 golden 与 GIF 动效录制（或宿主已有的 GIF 产出方式）。如果无法录制 GIF，打印已记录的不可用原因，不得发明替代路径。

骨架注释是约束，不是可选装饰。特别是：

- `setSurfaceSize` 是 **PNG 画布**（画板快照），不是运行时宽度锁。fill / hug / fixed 写在 Widget 里。
- 每个可审阅视觉 scenario 一个 `testWidgets`。测试按记录的 profile 配置环境，但不得把画布尺寸变成 Widget 运行时锁定。**禁止** 在 Widget 里做状态切换器或审阅面板（那是已退役的 HTML 预览铬）。
- **禁止** 画状态栏 / 手势条 / 输入法，除非它们是范围内的产品 UI。`MediaQuery` padding / `viewPadding` 置零。
- 动效 = 具名 **关键帧** PNG 加独立确认的动效契约。golden 里循环播放是错的。静态 golden 绝不能替代动效验收。宿主能录制时，确定性 GIF 是动效审阅媒介；动效表留在注释 / 冻结对话，golden 只确认指定静态帧。
- 邻接 golden 已有宿主 Theme / 本地化 / 图片夹具 / golden 脚手架时，跟它们。

本技能的动效审阅格式固定为 GIF。不要为 WebP、WebM、MP4 或其他格式新增编码器、依赖或验收门槛；旧说明中的其他格式不适用于当前契约。

冻结条中的动态 unit 同样只要求 GIF；不存在 GIF 时记录原因并延后运行时验收，不得以其他格式替代。

Web：按该仓已有方式打开/构建组件预览（Storybook、本地路由、静态文件）。打印该 **绝对路径**。不要仅为这个技能加 Playwright。

**冻结条：**

1. 组件能编过 / 宿主预览能打开。
2. 官方预览文件存在；对话出示了其 **绝对路径**（Flutter：golden PNG；宿主可录制时，动态 unit 还需确定性 GIF；无法录制时索引必须写原因并延后运行时验证）。
3. v2 `contracts/ui-truth-index.json` 通过仓内路径 containment、文件类型、SHA-256、依赖、profile、带来源 state、scenario 与十个 coverage 维度校验。
4. 每个视觉 scenario 都有确定性 preview，以及绑定当前 `preview_sha256` 的静态确认/豁免；适用的动效 scenario 另有动效确认/豁免、原因和后续运行时验证方式。能录制时 `motion_decision` 必须记录并向用户出示路径/hash；不能录制时索引必须写原因，Stage 4 用项目原生行为/人工证据验收。
5. 范围匹配切片；图标/图片和交互控件都是真实且有证据；缺失数据呈现真实空/省略状态；不得有未经批准的占位或视觉 fallback；运行时 coverage 已解决；适用时有动效/资源计划；尺寸已分类；§3b 触发时记录了合成。
6. Stage 2 测试通过且最新一轮新鲜上下文评审干净；记录用户已批准 workspace 与可选分支供 Stage 4 复用。Stage 4 必须为每个索引 unit 另行记录动效验收。
7. 若单元集合变了，在同一次变更里清扫需求目录中的陈旧指针。

**不要** 在没有预览路径时凭「Widget 看起来对」宣称冻结。**不要** 用 `contract-preview-*.png` 代替官方 golden。

### 6b. 调整代码前的失败分级

预览不符合预期时，先判定失败归属哪一层再改动：合成/几何语义、捕获或预览
工具、资源可用性、或组件实现。先用最小检查逐项验证候选根因，再做最小代码
改动，并只重新生成受影响证据与新的 hash。

- mask/alpha/blend/clip 效果先验证几何范围、alpha 曲线、合成语义与
  hit-test。画面没有对比源时「看起来没差异」是证据受限，不是效果缺陷的
  证据：不要为了制造差异叠加阴影、假内容或替代视觉，而是记录证据受限。
- 文字几何先按真实字体、locale、方向、文字缩放与约束检查换行和行数，
  再决定是否改尺寸。
- 动效先解码并核对帧数、总时长、循环元数据与 trigger→settled 时间线，
  再重新编码或修改动画代码。
- 输入/IME 视觉先确认控件由真实 focus、value、validation 与 IME 状态驱动，
  再决定是否更换图标或装饰。

### 7. 索引与状态

按 v2 模板写/更新 `.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/ui-truth-index.json`。其中只存指针、环境 profile、coverage、治理 hash/来源/确认元数据，绝不存绘制。

对 `ui_truth_mode=runtime-baseline`，索引中的 `ui_truth_mode` 必须一致，`design_source` 只能使用 `requirement`、`project` 或 `user-decision`，并省略 Figma 专属标识。对 `ui_truth_mode=figma`，顶层来源必须是 Figma；单个 state/scenario 的运行时缺口仍可使用其他允许来源。

仅在冻结条满足后设置 `acceptance_frozen`。失败 → `blocked_verification_failure`。

没有 HTML 校验器，也没有 v1 兼容路径。Kit 状态校验检查完整 v2 矩阵、confirmation 与 preview hash 绑定，以及列出的相对路径能从 **仓库根** 解析。

### 8. 实现之后（Stage 4 消费者）

Stage 4 在同一个用户已批准 workspace **接线** 已经写好的组件（API、路由、状态、挂载）。不得创建第二个 workspace；默认 **禁止** 从 HTML 再画一遍 Flutter，也禁止再查 TemPad。

Stage 4 使用记录的 profile 与项目原生工具验证每个已索引 scenario，然后写结构化 `visual-acceptance.json`。若组件代码变化但每个渲染 preview hash 均不变，更新 component hash 后可保留绑定确认。任一 preview hash 变化都必须重新生成预览并取得新确认，index 才能再次通过。

**引用核实：** 写任何「实现于」声明之前跑引用/用法搜索。只查定义不够。

### 9. 替换或废弃 — 同一次变更内清扫陈旧指针

当单元被删除、替换、或在新 id 下重建：在同一次变更里改写活跃指针（`status.json` 备注、视觉验收、进度/todo）。历史「superseded / deleted / 已删除 / 取代」行可以保留。

## 反模式（过程失败）

- 生成 `ui-contract.html` 或拷任何 HTML 契约模板当冻结媒介。
- **禁止把 HTML 翻译成 Flutter**（或翻译进宿主 Web 栈）。
- 因为旧 HTML 预览有状态切换器和审阅面板，就把它做进 Flutter Widget。
- 写一份伴生 YAML/JSON/markdown 来装 **绘制**。
- 整页 dump；整页 `get_code` 再裁剪；跳过 §1b。
- 把断开的范围内产物塌成一个页面 Widget。
- 按需求所属路由而不是产物的物理容器给小改动路由。
- 仅为了扛一个徽章发明整套外壳 Widget。
- 手写语义化布局而丢掉 `get_code` 几何。
- fill 判定已是 fill 时，把 get_code 的 `w-[Npx]` 抄进实现当硬编码宽度。
- 把每个快照盒子倒进布局常量。
- 把快照 `w×h` 当 fill/hug 的通过/失败标准。
- 跳过 §5b；把可变文案标成 fixed；不问用户就发明 overflow。
- 手绘图标；资产壳不解析；从 structure 重建带蒙版 SVG 却丢掉烘焙蒙版。
- 父级才是有证据的可复用视觉时，只导出叶子矢量/图片，再在宿主布局代码里重建组合资源，且没有记录运行时需要。
- 把蒙版 / 仅 alpha 渐变当成第二层 src-over 覆盖；跳过 §3b；拷贝 `data-hint-*`。
- 需求表明是服务端内容时，把 Figma **示例** 图当下载冻结资产。
- 真实值缺失时向生产 UI 注入假/默认数据或 fixture；正确结果是产品真实的空/省略状态，或取得用户明确决定。
- 未取得明确用户决定，就把证据要求的矢量/SVG、Spine、Lottie 或其他资源类别替换成位图、字形、平台图标、静态图片或手绘近似。
- 使用未经批准的占位、dummy/fixture visual、通用 icon、external widget slot 或静态替代去填范围内表面；未经用户明确决定就选择空渲染。
- 把可编辑输入当成涂绘文字壳，或把有证据的图标/图片替换成熟悉的平台字形。
- 按页面/布局身份选择输入图标或装饰，而不是按控件真实的 focus、值、校验、enabled/只读和 IME 状态；漏掉未输入、编辑中、已完成、IME 隐藏或 IME 显示证据。
- 用与实际渲染不同的排版、locale、方向、缩放或约束预测量文本，然后在真实换行或行数并未变化时改几何。
- 把静态 golden 确认当成动效确认，或在动效未确认/未豁免时进入 `acceptance_frozen`。
- 在 trigger、转场/循环和 settled 状态尚未全部可见时发布动效预览；加入过长空等；编码时压缩或拉长已声明帧时长；或不核验解码时长与自动重播。
- 跳过 §2c；文本提示扫描只扫 `source_node`；截断多条款 SECTION 备注；悄悄改写动效覆盖。
- 交出的动效预览力学与用户点名的参考实现不一致。
- golden 测试里打真网。
- 添加宿主项目没有的 Flutter/Web 依赖。
- 没有绝对预览路径和用户显式确认就宣称冻结。
- 在 CP-UI 前 dispatch 本技能、在记录的用户已批准 workspace 外写生产代码，或在 Stage 4 为同一切片创建第二个 workspace。
- 把 `ui-truth-index.json` 的路径写成文件系统绝对路径（索引必须是仓内相对路径）。
- 缺少 `schema_version`、profile、带来源 state、scenario preview/确认、coverage 或内容 hash；冻结后接受 hash 漂移。
- 漏掉运行时 coverage 维度；把 `unresolved` 当作合法冻结状态；将适用场景标为没有理由的 `not_applicable`。
- 把 requirement/project/user-decision 来源运行时 state 称为「1:1 还原 Figma」；没有 source node 却标为 `figma` 来源。
- `reviewed_preview_sha256` 不再匹配 scenario preview 后仍复用旧确认。
- 把单个画板当作所有 container 尺寸、orientation、theme、locale、text scale、input mode 或 reduced-motion 行为的证据。
- 为修复无障碍/平台冲突而静默改变有证据的像素，没有升级可见冲突。
- 动效只记录 keyframe，却漏掉 trigger、中断、reduced-motion 或资源/性能行为。
- 对适用的内容图片漏掉 loading/error/offline、crop/focal point、density/scaling、cache、fixture 与 semantics 决策。
- 扫描每一个历史单元来「找」匹配；为了小需求重写整个已匹配 Widget。
- 同一症状同时改动业务代码、预览工具和验收证据，而没先分类失败归属层。
- 画面没有对比源时，把「视觉上看不出差异」当作合成/颜色缺陷的证据，并用阴影、假内容或替代视觉制造差异。
