---
name: ui-truth-mapping
description: 当 Figma 设计需要在实现前变成项目里的真实组件（优先 Flutter）并给出官方栈预览时使用 — 尤其证据是整页但需求只命中子树、需要多状态可审阅预览、必须审计动效/Spine/Lottie/shimmer、重叠填充/渐变或 Figma 蒙版可能是 alpha 合成而非独立覆盖层、或先前整页 dump / 用 HTML 契约当翻译层 / 没有出示预览路径时。
---

# UI 真值映射

从设计源（Figma）提取结构化 UI 真值，冻结为**宿主项目里的真实组件**，外加用户能打开的官方栈预览。

**原则 1 — 禁止二次转换。** 写项目已经在用的 Widget/组件。不要先冻一份 HTML（或任何平行赝品）再翻译成 Flutter/React。

**原则 2 — 官方预览。** Flutter：`flutter test --update-goldens` 产出的 golden PNG。Web：该仓已有的组件预览方式。对话里给用户 **绝对路径**。交付索引里只存 **仓内相对路径**。

此技能只做一件事：给定需求切片 + 设计源，在**项目源码树**里定位或创建匹配单元，把视觉真值冻在那里，出示预览路径，并记录指针索引。它不拥有索引以外的流水线状态、不决定下一阶段，也不发明第二份视觉真值文件（YAML/JSON/markdown 不得当像素用）。

## 输入

- 需求切片（范围、字段、验收信号）
- 设计源定位符（Figma 文件 key + 节点 id，或等效）
- 后续需求：目标单元的任何线索（路径、Widget 名，或「尚无已知单元」）

## 输出

每个独立单元：宿主树里的 **生产代码** + 官方预览文件 + 子需求索引中的一行指针。

```
<宿主项目>
├── lib/…/<unit>.dart          # Flutter：真实 Widget（跟邻接文件）
├── test/…/<unit>_golden_test.dart
└── test/goldens/<unit>.png    # 审阅媒介

.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/
└── ui-truth-index.json        # 只做指针 — 不是绘制
```

`ui-truth-index.json` 是 **指针**，不是图纸。每行：

| 字段 | 含义 |
|---|---|
| `unit_id` | 稳定单元 id（kebab-case） |
| `stack` | `flutter` \| `web` |
| `component_path` | 真实组件相对仓库根的路径 |
| `preview_path` | 预览文件相对仓库根（Flutter = golden PNG） |
| `golden_test` | 仅 Flutter：golden 测试相对路径 |

**禁止** 生成 `ui-contract.html`。**禁止** 拷贝 `ui-contract-template.html`（已删除）。**禁止** 把 HTML 翻译成 Flutter。

## 技术栈

根据仓库自行判断。不要跑复杂探测。

- 看起来像 Flutter（Dart Widget、`pubspec.yaml` 含 Flutter SDK、已有 `test/` golden）→ **Flutter**。本技能按这条路径写。
- 看起来像 Web 应用（该仓已有页面/组件树）→ **Web**。跟 **该仓** 架构（React/Vue/Svelte/纯 HTML — 邻接文件用什么就用什么）。不要假设「契约就是 HTML」。
- 拿不准 → **停下问用户**。不要默认冻一份 HTML 契约。

## 模板（仅 Flutter golden 骨架）

```
templates/
└── flutter-golden-preview-test.dart.example
```

示例只教 `MaterialApp` / `RepaintBoundary` / `matchesGoldenFile` / `--update-goldens`，以及注释里的预览规则（PNG 画布 ≠ 运行时尺寸、每个状态一个 `testWidgets`、不要系统栏、不要 Widget 内状态切换器）。**它不是 Widget 模板。** Widget 代码必须仿邻接生产文件。不要加宿主项目没有的依赖。

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
| 带 **变体属性** 或 **动效** 的组件 | 同一单元；动效记在 golden 的注释 / 审阅说明 | 组件/实例根 | 静态 **关键帧** golden；动效规格写在说明里 | 只当静态 PNG 且省略动效表 |
| 同边界 **颜色渐变 + alpha 渐变** / Figma 蒙版 | 同一单元；把兄弟当绘制层之前先跑 **§3b** | 合成后的绘制根 | 一个合成效果 | 两层 `src-over` 覆盖填充 |

## 硬边界

- **按需求作用域抽取：** 范围内产物决定根 — 覆盖属于 **一个** 单元的产物的最小祖先。断开的产物 → 拆单元。永远不要整页 dump。
- **先写单元拆分计划再取证：** 任何 `get_code` 或组件代码之前填 §1b。
- **只对作用域调 `get_code`。** `get_code` 目标 **必须等于** 计划中的 `source_node`。整页 `get_code` 再裁剪是过程失败。
- **不要发明视觉真值。** 不得有 Figma 证据（`get_code` / `get_structure`）之外的单元、状态、绘制或图标。
- **不要发明布局。** 把几何机械迁入宿主布局系统（Flutter 约束、CSS 等）。不要手写语义化整页而丢掉证据。
- 预览 px 是画板快照，不是运行时尺寸。分类 **fill / hug / fixed**（§5b）。可变文案是 hug 或 fill 加 overflow / min / max — 禁止按样品写成 fixed。
- 禁止把 TemPad `data-hint-*` 拷进产品代码或索引。
- Figma 蒙版 / 仅 alpha 渐变 **不是第二层可见罩色**。跑 §3b。
- 不要把系统 UI（状态栏、手势条、输入法、设备铬）当组件内容 — 用安全区处理。
- 未经用户对预览（绝对路径）的 **逐单元显式确认** 不得宣称冻结。仅当用户豁免复审时可跳过。
- 不要在组件旁再造第二份视觉真值文件（禁止把伴生 YAML/JSON/markdown 当绘制）。`ui-truth-index.json` 只做指针。
- 不要扫描仓库里每一份历史文件来找匹配。用需求 id、路由/Widget 语义、已知关系或显式路径定位。
- 不要凭记忆写未经核实的 `delivery.implemented.target`（或等价字段）。

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

0. **文本提示扫描** — 作用域子树 **以及** 父级 SECTION 兄弟里的 TEXT / 便签 / 标注。关键词：motion、animation、transition、typewriter、shimmer、Lottie、GIF、skeleton、placeholder、API-returned、pulse、loading（以及设计师语言的等价说法）。
1. 在 `source_node` 上做 **候选扫描**（INSTANCE/COMPONENT、图片填充、动效命名图层）。
2. 有工具时做 **动效探测**（`get_node_motion` / 等价）。缺工具时文本提示仍然算数。
3. **资产** — 有字节则持久化 Lottie/GIF/视频；否则 `pending-user`，只留海报帧 — 不要发明文件。
4. **分类**（`content-bound`、`component-variant`、`motion-preset`、`design-animation-asset`、`prototype-transition`）。
5. **映射** 到状态 / golden / 占位。**用户点名的参考实现：** 若用户指向现有代码，**先读它**；预览力学必须匹配该参考（get_code 的 packing 不得悄悄反转生长/显现）。
6. **一致性检查（写组件代码前必做）：** 跨状态/实例的同一铬不能在没有显式证据时得到不均的动效覆盖。不均覆盖是异常 — 停下询问。
7. **每次裁剪后的覆盖复查（必做）：** 把剩余源条款对照剩余目标再读一遍。多条款 SECTION 备注按 unit 拆分。

给用户记一份 **动效与转场** 表（用用户的语言）：状态 | 位置 | 效果 | 参考。动效 ≠ 数据绑定。放进 golden/Widget 注释或对话冻结包 — 不要当成第二份绘制文件。

### 2d. 缺失资源升级

`pending-user` 资产 → 冻结前停下询问（文件或显式豁免）。

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

### 4. 写真实组件（Flutter 优先）

**创建：** 把 Widget 加在邻接文件旁。对齐它们的构造函数风格、主题、间距助手和目录布局。**不要** 拷一份 Dart 模板再填空。

**增量修补：** 打开匹配到的文件；不要重写无关子树。

把证据映射进宿主布局系统：

- Flutter：按几何需要用 `Row`/`Column`/`Stack`/`Positioned`/`Expanded`/`Flexible`/`Wrap`/`SizedBox`/`AspectRatio`。图片：测试里用项目已有的 fixture/`ImageProvider` 惯例 — **golden 测试禁止打真网**。
- Web：在该仓组件里遵守同一纪律。

把审阅说明（范围内/外、动效表、资产、尺寸、合成）写成 Widget/golden 注释和冻结对话。那是审计文案，不是产品 UI。

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

把 `templates/flutter-golden-preview-test.dart.example` 只当 **骨架**。宿主已有 `flutter_test` 惯例则跟它。

```bash
flutter test <golden_test.dart> --update-goldens
```

然后把 PNG 的 **绝对路径** 打印给用户。多状态 → 多个 golden（或宿主已有写法）。

骨架注释是约束，不是可选装饰。特别是：

- `setSurfaceSize` 是 **PNG 画布**（画板快照），不是运行时宽度锁。fill / hug / fixed 写在 Widget 里。
- 每个可审阅状态一个 `testWidgets`。**禁止** 在 Widget 里做状态切换器或审阅面板（那是已退役的 HTML 预览铬）。
- **禁止** 画状态栏 / 手势条 / 输入法，除非它们是范围内的产品 UI。`MediaQuery` padding / `viewPadding` 置零。
- 动效 = 具名 **关键帧** PNG。golden 里循环播放是错的。动效表留在注释 / 冻结对话。
- 邻接 golden 已有宿主 Theme / 本地化 / 图片夹具 / golden 脚手架时，跟它们。

Web：按该仓已有方式打开/构建组件预览（Storybook、本地路由、静态文件）。打印该 **绝对路径**。不要仅为这个技能加 Playwright。

**冻结条：**

1. 组件能编过 / 宿主预览能打开。
2. 官方预览文件存在；对话出示了其 **绝对路径**。
3. `contracts/ui-truth-index.json` 列出仓内相对的 `component_path` + `preview_path`（Flutter 另加 `golden_test`）且这些文件存在。
4. 范围匹配切片；图标/图片有证据；有动态时有动效表；尺寸已分类；§3b 触发时记录了合成。
5. 用户确认了预览（除非豁免）。
6. 若单元集合变了，在同一次变更里清扫需求目录中的陈旧指针。

**不要** 在没有预览路径时凭「Widget 看起来对」宣称冻结。**不要** 用 `contract-preview-*.png` 代替官方 golden。

### 7. 索引与状态

写/更新 `.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/ui-truth-index.json`。只做指针。

仅在冻结条满足后设置 `acceptance_frozen`。失败 → `blocked_verification_failure`。

没有 HTML 校验器。Kit 状态校验检查索引存在，且列出的相对路径能从 **仓库根** 解析。

### 8. 实现之后（Stage 4 消费者）

Stage 4 **接线** 已经写好的组件（API、路由、状态、挂载）。默认 **禁止** 从 HTML 再画一遍 Flutter，也禁止再查 TemPad。

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
- 把蒙版 / 仅 alpha 渐变当成第二层 src-over 覆盖；跳过 §3b；拷贝 `data-hint-*`。
- 需求表明是服务端内容时，把 Figma **示例** 图当下载冻结资产。
- 跳过 §2c；文本提示扫描只扫 `source_node`；截断多条款 SECTION 备注；悄悄改写动效覆盖。
- 交出的动效预览力学与用户点名的参考实现不一致。
- golden 测试里打真网。
- 添加宿主项目没有的 Flutter/Web 依赖。
- 没有绝对预览路径和用户显式确认就宣称冻结。
- 把 `ui-truth-index.json` 的路径写成文件系统绝对路径（索引必须是仓内相对路径）。
- 扫描每一个历史单元来「找」匹配；为了小需求重写整个已匹配 Widget。
