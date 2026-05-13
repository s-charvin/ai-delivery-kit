---
name: ui-truth-mapping
description: 当需要从设计源（Figma）提取结构化 UI 真值为规范化的 YAML UI 契约以实现 1:1 映射的场景下使用。自动检测并拆分单个设计源中的多个 section（页面、弹窗、状态）。
---

# UI 真值映射

从设计源（Figma）提取结构化 UI 真值并将其冻结为规范化的 YAML 契约。YAML 是唯一输出 — 没有单独的映射文档。

单个设计源可能包含多个顶层 section：不同的页面、弹窗覆盖层或同一页面的多个状态。此技能自动检测并将它们拆分为独立结构化的单元。

此技能只做一件事：读取需求切片 + 设计源 → 产生一个或多个 YAML UI 契约 + section-map。它不管理状态、不决定下一步运行什么、也不处理阻塞项。

## 输入

- 需求切片文档（范围、字段、验收信号）
- 设计源定位符（Figma 文件 key + 节点 ID，或等效）

## 输出

当设计源包含单个页面时：
```
<output-dir>/
└── ui-acceptance-contract.yaml   # 规范化 YAML — 组件树、布局、间距、排版、状态
```

当设计源包含多个独立页面或弹窗时，每个单元一个契约：
```
<output-dir>/
├── <page-or-modal-id>/
│   └── ui-acceptance-contract.yaml
├── <page-or-modal-id>/
│   └── ui-acceptance-contract.yaml
└── section-map.json              # 将每个 section 映射到其分类单元和页面
```

## 模板

使用提供的模板 — 不要发明字段或结构：

```
templates/
├── ui-acceptance-contract-template.yaml   # YAML 契约模板
└── section-map-template.json              # section → 单元映射模板
```

## 硬边界

- 不要发明视觉真值 — 不添加页面、字段、组件或状态。
- 不要仅将截图或节点名称视为充分证据。需要结构化载荷。
- 不要使用顶层 `SECTION` 作为最终可执行节点目标。
- 不要在 YAML 之外创建第二个 UI 验收源。
- 当源证据显示多个可见块、通道或集群时，不要接受 `children: []`。
- 当存在可见文本时不要交付空的 `font`，当存在可见资源时不要交付空的 `icon`/`image`。
- 不要在契约中包含系统 UI：状态栏、系统导航栏、软键盘、设备边框或系统级覆盖层不得出现在组件树中。使用区域的 `safe_area` 来声明系统 UI 重叠。
- 不要给空容器赋予功能角色, 任何 UI 组件需要可见的图标, 样式或文字证据。
- 不要映射空 spacer。没有可见子元素、无文字、无图标、无图片、无背景的容器仅用于布局对称设计考虑, 由 `layout` 捕获，不值得记录。
- 不要凭记忆生成 YAML 契约或 `section-map.json`。在 `templates/` 下找到对应模板文件，逐字复制到输出路径，然后逐字段填充值。保留所有字段键、顺序、YAML 注释和结构。只改动值 — 不添加、删除或重命名字段。每个填充的值必须有设计源依据；无证据时保持模板默认值（`null`、`{}`、`[]`）不变。
- 不要在主会话上下文中为多个单元生成契约。对于 section-map 中识别的每个独立单元（page、modal、shared-shell），派发一个单独的子代理，仅为该单元收集证据并冻结 YAML。唯一例外：仅当用户明确要求不使用子代理，或恰好只有一个单元且 ≤2 个状态帧时跳过子代理派发 — 这些情况简单到可以内联处理而无质量损失。
- 在逐单元子代理内部，一次只处理一个帧 — 永远不要将所有帧批量塞入单个 Figma 查询。每一层逐帧迭代：查询一个帧，填充该帧的字段，然后处理下一个。保持上下文聚焦，防止细节遗漏。
- 三层各自只填充其分配的字段。绝不触碰其他层拥有的字段。Pass 1 拥有 id/type/name/source_node/visible_when/states。Pass 2 拥有 anchor/layout/box。Pass 3 拥有 background/content/interaction/description。

## 工作流

### 1. 确认上游
在接触设计数据之前，先阅读需求切片以理解需要哪些 UI 元素。

### 2. 分析 section 并拆分

**关键 — 先枚举所有框架：** 不要单独查询孤立节点。在**父级/选区级别**（不是特定节点）查询设计源，以获取顶层同级框架的完整列表。在做任何其他事之前，记录每个框架的 id、名称、类型和位置。跳过此步骤会导致整个状态变体被遗漏。

**完整枚举后**，对每个框架进行分类：

**分类：**
| 分类 | 含义 | 处理方式 |
|---|---|---|
| `page` | 全屏页面或屏幕路由 | 结构化为独立的页面级契约 |
| `page-state` | 已分类为 `page` 的框架的替代状态（如加载中、空、错误、已选择、未选择） | 作为屏幕状态归入父 `page` — 不创建单独契约 |
| `modal` | 模态对话框、底部弹出层、气泡或覆盖层 | 结构化为独立的页面级契约 — 不嵌套在页面内部 |
| `shared-shell` | 共享的导航外壳、标签栏或包裹页面的持久框架 | 提取一次作为共享组件；在依赖页面中引用 |
| `ignore` | 非 UI 内容（设计师备注、标注、辅助线） | 完全排除在契约之外 |

**分组规则：**
- 相同名称前缀、不同后缀的框架（如"性别-未选择"、"性别-男"、"性别-女"）→ 归为一个 `page` 下的 `page-state` 变体。它们共享相同外壳/布局，仅内容状态不同。
- 共享相同外壳/布局、仅内容状态不同的 section → 归为一个 `page` 下的 `page-state` 变体。
- 布局不同、导航上下文不同或入口点独立的 section → 拆分为单独的 `page` 单元。
- 模态覆盖层、底部弹出层和对话框 → 始终拆分为独立单元。它们有自己的生命周期、入口触发器和关闭逻辑 — 不是页面的子组件。
- 在 `page` 与 `page-state` 之间犹豫时：检查这些 section 是否通过同一路由/URL 到达。相同路由 → `page-state`。不同路由或由用户动作触发 → `page`。

**验证：** 分类后，确认每个枚举的框架都已分配到某个单元。没有框架被遗漏。如果某个框架无法匹配，重新检查 — 它可能是你忽略的状态变体。

**输出：** 将 `templates/section-map-template.json` 复制到输出路径，然后为每个分类后的框架填充值。严格保留模板定义的所有字段键、顺序和结构 — 绝不凭记忆重新生成。

**section-map 写入后 — 派发逐单元子代理。** 对于 section-map 中的每个独立单元（page、modal、shared-shell），派发一个子代理。每个子代理仅接收其所属单元的帧（每个帧含用于 Figma 查询的 `source_node` 和用于 YAML state id 的 `state_type`）、需求切片、设计源定位符和模板路径。子代理为其分配的单元独立执行阶段 3 — 运行三层增量编辑（骨架 → 布局 → 样式内容），每层一次只处理一个帧，编辑同一个 YAML 文件。所有单元并行派发。主会话不收集证据也不冻结 YAML；仅负责派发、收集结果，然后运行阶段 4 审校。

仅当用户明确要求不使用子代理，或恰好只有一个单元且 ≤2 个状态帧时，跳过子代理派发。

### 3. 三层增量契约构建 *（在逐单元子代理内运行）*

此步骤在每个逐单元子代理内运行。子代理只能访问其分配单元的帧和证据 — 无其他单元的交叉污染。

**执行模型：** 在同一 YAML 文件上执行三层顺序编辑。每层一次只处理一个帧 — 永远不要将所有帧批量塞入单个 Figma 查询。每层只填充其分配的字段，不触碰其他层拥有的字段。

**首先，复制模板。** 找到 `templates/ui-acceptance-contract-template.yaml`，将其逐字复制到本单元的输出路径。三层全部编辑同一个文件。

#### Pass 1 — 骨架层

**用途：** 构建组件树结构和状态声明。

**Figma 查询：** `get_structure(frame_source_node)` — 每帧一次，仅结构级。此层不要使用 `get_code`。

**你填充的字段：**
- `version`、`contract_id`
- `source` — 需求文件名、Figma 文件 key、根节点 ID、缓存路径
- `states` — 每帧一个条目：`id`（来自帧的 `state_type` 分类）和 `source_node`
- `background` — 仅页面级颜色，来自默认/idle 帧
- `regions[].children[]` — 组件树骨架：`id`、`type`、`name`、`source_node`、`visible_when`、递归 `children`

**不要触碰：** `anchor`、`layout`、`box`（width/height/padding）、`background`（组件级）、`content`（text/icon/image/font）、`interaction`、`description`。保持这些为模板默认值（`null`、`{}`、`[]`、`0`）。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 调用 `get_structure(<frame-source-node>)`。
2. 提取组件层级 — 组件类型、嵌套关系、可见元素。
3. **第一个处理的帧：** 在 `regions[].children[]` 中创建所有组件节点。填充 `id`、`type`、`name`、`source_node`。设置 `visible_when: null`（默认状态组件始终可见）。使用 Figma 父子结构递归填充 `children`。
4. **后续帧：** 对此帧中发现的每个组件：
   - 若组件具有相同的 `source_node` 且已存在于树中 → 同一组件在不同状态。不要创建重复项。若其仅特定状态可见则设置或细化 `visible_when` 条件。
   - 若组件具有新的 `source_node` 且树中不存在 → 特定于状态的内容。将其追加到适当父组件的 `children` 中，并设置导致其出现的语义条件的 `visible_when`。
5. 将帧的状态条目添加到 YAML 顶部的 `states` 列表 — 每帧一个 `id` + `source_node`。

**跨状态合并规则：**
- 所有状态中存在的组件：使用默认/idle 帧的 `source_node`，`visible_when: null`。
- 仅部分状态中存在的组件：使用其可见帧的 `source_node`，设置语义条件的 `visible_when`。
- 仅样式在不同状态间变化的组件：单个组件条目，样式差异写入 `states` — 在 Pass 3 中填充。
- 绝不为不同状态创建相同 `id` 的两个组件条目。

**Pass 1 完成后：** YAML 具有完整的 `states` 列表和完整的组件树，包含 `id`、`type`、`name`、`source_node`、`visible_when`。所有其他字段为模板默认值。

#### Pass 2 — 布局层

**用途：** 为每个组件填充定位、尺寸和布局。

**Figma 查询：** `get_code(frame_source_node)` — 每帧一次，代码级。读取 Pass 1 的 YAML，按 `source_node` 查找组件。

**你填充的字段：**
- `anchor` — 每个组件恰好 4 个条目：`start`、`end`、`top`、`bottom`。每个包含：
  - `to`：引用组件 ID、`screen_start`、`screen_end`、`screen_top`、`screen_bottom`
  - `direction`：附着到引用边缘的哪个方向
  - `offset`：与引用边缘的 `<Npx>` 间距，或 `auto` 当父布局控制定位时
  - `note`：当 `offset` 为 `auto` 时必须填写 — 解释偏移量如何计算
- `layout` — `direction`（vertical/horizontal/none）、`align`、`gap`
- `box` — `width`（auto/fill/<Npx>）、`height`（auto/<Npx>）、`padding`（全部 4 方向必需：top/right/bottom/left；无视觉间距时使用 `0`）

**不要触碰：** 所有 Pass 1 字段（`id`、`type`、`name`、`source_node`、`visible_when`、`states`）。同时：`background`（组件级）、`content`（text/icon/image/font）、`interaction`、`description`。即使存在固定 px 也不要在此处写 `description` — Pass 3 会处理。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 读取当前 YAML 文件。找到所有 `source_node` 属于此帧的组件。
2. 调用 `get_code(<frame-source-node>)` 获取精确的定位数据。
3. 为此帧中找到的每个组件提取并填充：
   - **anchor**：计算全部 4 个锚点条目。从参考底部边缘的偏移公式：`offset = 子元素.y − (参考元素.y + 参考元素.height)`。与参考边缘齐平时使用 `0px`。使用 `auto` 当父布局（如列表）控制定位时 — 添加 `note` 解释计算方式。
   - **layout**：从 Figma 自动布局或手动定位数据中提取方向、对齐和间距。
   - **box**：`width` 优先 `auto` > `fill` > `<Npx>`。`height` 优先 `auto` > `<Npx>`。`padding` 全部 4 方向从测量内边距中获取；设计显示齐平时使用 `0`。
4. 移动到下一帧。重复直到所有帧处理完毕。

**Pass 2 完成后：** 每个组件具有完整的 anchor、layout 和 box。`background`（组件级）、`content`、`interaction` 和 `description` 保持为模板默认值。

#### Pass 3 — 样式内容层

**用途：** 为每个组件填充视觉样式、内容和交互。

**Figma 查询：** `get_code(frame_source_node)` — 每帧一次，代码级。可复用 Pass 2 的缓存数据（相同的 `get_code` 查询）。读取 Pass 2 的 YAML 查找组件。

**你填充的字段：**
- `background` — 组件级：`color`、`border`（radius/width/color）、`shadow`、`opacity`
- `content` — 每个组件恰好填充一个插槽：
  - 文本组件：`text`（可见文本内容）+ `font`（family、size、weight、color、height、align）
  - 图标组件：`icon`（src — 资源文件名，size — 显示尺寸）
  - 图片组件：`image`（src、width、height、fit）
- `interaction` — `on`（click/long-press/none）、`action`、`note`
- `states` — 与默认状态的差异。组件状态键名（如 `selected`、`active`、`disabled`），每个为部分组件差异。示例：`{ selected: { background: { border: { color: "#41B8F4" } } } }`。
- `description` — 当 `box.width` 或 `box.height` 使用固定 `<Npx>` 时必须填写；解释为何 `auto` 不适用（如"图标基准尺寸"、"触控目标最小值"）。

**不要触碰：** 所有 Pass 1 字段，所有 Pass 2 字段（`anchor`、`layout`、`box`）。不要修改组件树结构、增加/删除节点或更改 `source_node` 值。不要更改 `visible_when` 条件。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 读取当前 YAML 文件。找到所有 `source_node` 属于此帧的组件。
2. 调用 `get_code(<frame-source-node>)` — 若 Pass 2 已有缓存在 `.ai-delivery/figma-cache/<file-key>/code/<node-id>.json` 中则复用；如未缓存则重新获取。
3. 为此帧中找到的每个组件提取并填充：
   - **background**：颜色填充、边框样式、阴影、透明度。
   - **content**：从 Figma 节点确定内容类型 — 文本节点 → `text`+`font`；矢量/图标节点 → `icon`；图片填充节点 → `image`。恰好填充一个插槽。
   - **interaction**：若组件是交互式的（设计中有 click/long-press 行为），填充 `on`、`action` 和 `note`。
   - **states**：若此组件在 Pass 1 确定的状态间有样式变化，写入各状态的差异。每个差异仅包含组件默认值（Pass 3）中变化的属性。
   - **description**：若 `box.width` 或 `box.height` 使用固定 `<Npx>`，写简要的理由说明。
4. 移动到下一帧。重复直到所有帧处理完毕。

**Pass 3 完成后：** YAML 契约完整。所有字段均使用 design-backed 值填充。

**全部三层完成后：** 子代理将完成的 `ui-acceptance-contract.yaml` 返回给主会话。主会话收集所有单元契约后进入阶段 4。

### 4. 最终契约审校

**强制执行 — 每次 YAML 冻结后运行。** 审校生成的每一份契约（page、modal、shared-shell），不得跳过任何单元。使用子代理纯净执行 — 子代理接收所有契约和 `section-map.json`，返回优化后的契约。

此审校仅规范化布局语义和尺寸。不新增或删除 source-backed 组件、状态、`visible_when` 条件或 `source_node` 值。

**审校顺序（严格遵循，按 pass 层组织）：**

**骨架质量（Pass 1 产出）：**

**S1. 组件树完整性**
- `section-map.json` 中枚举的每个帧的 `source_node` 必须在树中至少有一个对应的组件节点。
- 没有帧被遗漏。

**S2. visible_when 覆盖率**
- 所有非默认状态组件必须有 `visible_when` 条件。
- 条件使用语义化语言（如"选项已被选中"），不使用机械的状态 ID 检查。

**S3. states 列表一致性**
- YAML 中的 `states` 列表必须与 `section-map.json` 中声明的帧一致 — 相同的数量，每个状态有 `id` + `source_node`。

**S4. source 元数据完整性**
- `source.requirement`、`source.design_file`、`source.root_node`、`source.cache` 全部已填充。

**布局质量（Pass 2 产出）：**

**L1. anchor 4 方向完整性**
- 每个组件有全部 4 个 anchor 条目（`start`、`end`、`top`、`bottom`）。
- 每个条目有明确的 `to`、`direction` 和 `offset` — 无 null、无空字符串。
- `offset: "0px"` 用于齐平附着；`offset: "auto"` 必须有 `note` 解释计算方式。
- 组件位于兄弟组件下方 → anchor `top` 到该兄弟组件的 `bottom`，间距为测量值。

**L2. padding 4 方向完整性**
- 每个组件的 `padding` 在全部 4 方向（`top`、`right`、`bottom`、`left`）有明确值。
- 设计显示齐平时使用 `0` — 永远不要让 padding 字段为 `null` 或缺失。
- 含有可见子元素且内边距一致的容器 → padding 反映该容器上的内边距，而非子元素上的固定尺寸。

**L3. width/height 收敛**
- 文字、标签、说明 → `width: "auto"`、`height: "auto"`。
- 横跨可用宽度的卡片、行 → `width: "fill"`。
- **fill 判定规则**：若组件的 px 宽度等于（父容器宽度 − 对称水平间距），使用 `fill` 而非固定 px。
- 仅保留固定 px：图标、头像、最小触控目标（≥44px）、明确设计要求固定宽度的弹窗。

**L4. gap/align 一致性**
- `layout.gap` 和 `layout.align` 值与 Figma 自动布局数据一致。

**样式内容质量（Pass 3 产出）：**

**C1. content slot — 恰好一个**
- 每个叶子节点组件恰好填充一个内容插槽：`text`+`font`、`icon` 或 `image`。
- 无可视子元素、无文字、无图标、无图片的空容器 → 不应存在于树中。

**C2. background 来源可追溯**
- `background.color`、`border`、`shadow`、`opacity` 值可追溯到 Figma fill/stroke/effect 数据。
- 无凭空编造的颜色或效果。

**C3. interaction 完整性**
- 设置了 `interaction.on` 的组件必须有对应的 `action` 和（非平凡时的）`note`。

**C4. fixed px 理由说明**
- 每个保留固定 `width` 或 `height` px 值的组件必须有 `description` 解释为何 `auto` 不适用（如"图标基准尺寸"、"触控目标最小值"）。

**全局检查：**

**G1. 安全区与系统 UI**
- 顶部边缘在系统状态栏下的区域 → `safe_area: "top"`。
- 位于系统导航栏、主页指示条或软键盘上方的区域 → `safe_area: "bottom"`，锚定到 `bottom`，`offset: "0px"`。
- 组件树中无状态栏、导航栏、键盘或设备壳层。

**G2. 键盘适配**
- 含文本输入框、验证码、密码或邮箱字段的页面 → 包含输入区域的 region 必须锚定到 `bottom` 并设 `safe_area: "bottom"`。系统在运行时处理键盘避让。
- 不要用固定像素偏移模拟键盘顶起后的位置。不要把键盘建模为组件或固定高度 spacer。

**输出**：用优化后的版本覆盖每个 `ui-acceptance-contract.yaml`。仅在单元分类变更时更新 `section-map.json`。若固定值有源依据则保留，若 `auto`/`fill` 语义正确则应用。在子代理响应中标注任何模棱两可的情况。

## 组件类型词汇

`container`、`card`、`list`、`list-item`、`form`、`text`、`text-input`、`button`、`image`、`icon`、`tab`、`navigation`、`divider`、`badge`、`modal`、`sheet`、`toast`、`custom`
