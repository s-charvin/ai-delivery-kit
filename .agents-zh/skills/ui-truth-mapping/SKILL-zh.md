---
name: ui-truth-mapping
description: 当 Figma 设计需要在 1:1 实现前冻结为 HTML UI 契约（schema v2）时使用 — 尤其证据是整页但需求只命中子树（红点、tip、sheet）、需要多状态可切换预览、或既有合同整页 dump / 不像 Figma / 未 hydrate 预览时。
---

# UI 真值映射

从设计源（Figma）提取结构化 UI 真值，并将其冻结为每个单元一份的规范化 `ui-contract.html` 文件（schema v2）。HTML 文件是唯一输出 — 没有单独的映射文档，也没有与之并存的 YAML 或 JSON 伴生文件。

单个设计源可能包含多个独立单元：不同的页面、弹窗覆盖层、共享组件（导航外壳、标签栏），或**需求范围内的组件子树**。每个单元恰好对应一份 `ui-contract.html`。同一单元的多个状态（加载中、空、错误、已选择/未选择）都存放在这一个文件内，以 `<template data-ui-state>` 区块表达 — 它们永远不是独立契约。

**浏览器预览对每份契约都是强制要求（单状态文件也保留预览基础设施以保持一致）。** 每个状态（含默认态）都放在 `<template data-ui-state>` 中。原生 `<template>` 不会被浏览器渲染 — 模板内固定的 `script[data-ui-state-preview]` 会在加载时 hydrate `[data-ui-state-host]`，并由 `[data-ui-state-switcher]` 切换状态。不要在未 hydrate 的空 host 上宣称布局保真。

此技能只做一件事：给定需求切片 + 设计源，定位是否已存在匹配契约（有则复用），否则新建，然后冻结或增量修补每个单元恰好一份的 `ui-contract.html`。它不管理自身元数据以外的交付状态、不决定下一步运行什么，也不处理自身硬门禁之外的阻塞项。

## 输入

- 需求切片文档（范围、字段、验收信号）
- 设计源定位符（Figma 文件 key + 节点 ID，或等效）
- 针对已有单元的后续需求：目标契约的任何线索（显式路径、单元 ID，或"尚无已知契约"）

## 输出

每个独立单元一份 `ui-contract.html`：

```
<output-dir>/
├── <unit-id>/
│   └── ui-contract.html   # schema v2 — 元数据 + token + DOM + 状态预览 + 审查面板
├── <unit-id>/
│   └── ui-contract.html
```

没有聚合索引文件。跨单元关系（例如某页面依赖某个共享组件）存放在各自单元自己的 `unit.dependencies` 元数据中。

## 模板

使用提供的模板 — 不要发明结构：

```
templates/
└── ui-contract-template.html   # HTML 契约 v2 模板 — 元数据、token、DOM、预览、审查面板
```

## 快速参考 — 场景 → 单元拆分

禁止默认把整份 Figma 证据一股脑映射。先按**需求体量**选型：

| 真实场景 | 应冻结的单元 | `source_node` / root | 状态 | 禁止 |
|---|---|---|---|---|
| 新建完整路由（页面本身在 In Scope） | `page`（仅当 shell 也是新验收时才另建 `shared-component`） | 页面内容 frame（排除已有独立契约的 shell） | 页面级变体放进本文件 | 把已有 tab/nav shell dump 进验收真值 |
| 既有 shell 上的小红点 / badge / 单控件 | 若已有契约的 `source_node` 盖住该产物 → **patch**；否则 **create** 以 badge/控件子树为 root 的 `component` | 仅 badge/控件的最小祖先 | 通常无单元态（元素级 patch）；仅当整单元视觉翻转才建状态模板 | 仅为红点新建 `messages-page` / 整根 shell 契约 |
| In Scope 产物断连（列表 tip + composer CTA） | **每个簇**一个 `component` / `modal` | 各簇局部最小祖先 | 按单元需要 | 用整页 root 的单个 `page`「一把抓」 |
| Bottom sheet / dialog / popover | 单独 `modal`；触发按钮 patch 进按钮所在物理容器契约 | sheet/dialog frame | 所有 sheet frame → `<template data-ui-state>`；必须 hydrate + switcher | 把 sheet 嵌成 page 状态；省略 preview 脚本；把触发按钮放进 modal 契约 |
| 多状态列表/表单/模块 | 一个 `component`（若路由本身即范围则用 `page`） | 作用域模块 root | 每个视觉 frame → 一个 template；hydrate + switcher 强制 | 一态一份契约；空默认 template |
| 仅元素属性（`disabled` / `selected`） | 在既有单元上 patch 该节点 | 不变 | **不要**加单元级状态模板 | 把 `disabled` 做成整单元 `<template data-ui-state>` |
| 带 **变体属性** 或 **动效** 的组件（pulse、Lottie、GIF、prototype） | 仍属同一单元；补 `meta.dynamics[]` + review-panel 清单 | 组件/instance root | 预览用**静态关键帧** state template；动效规格写在 `dynamics` | 把动效压成静态 PNG；遗漏设计提供的动画资源 |

## 动态与动效 — 现状与缺口

| 动态关切 | 现已覆盖？ | 方式 |
|---|---|---|
| 整单元视觉状态（loading / empty / error / 选中外壳） | **是** | 兄弟 frame → `meta.states[]` + `<template data-ui-state>` + switcher |
| 仅元素属性（`disabled`、tab `selected`） | **是** | patch 节点属性 — 不做单元级状态模板 |
| 服务端/用户**内容**（头像、上传图、实时 badge 数字） | **部分** | 资产步骤可标 `content-bound`；**尚无**结构化 `dynamics` 清单 |
| Figma **组件变体**属性（`State=Hover`） | **否** | frame 可能被误当成 state；变体轴未主动发现 |
| **动效**（Figma Motion preset、关键帧、smart animate） | **否** | HTML 预览仅静态快照；未要求 `get_node_motion` |
| 设计提供的**动画资源**（Lottie / GIF / video） | **否** | 仅有静态矢量/位图资产路径 |

**§2c 的目标：** 主动发现动态组件与展示效果，分类、持久化设计资源，并用 `meta.dynamics[]` + review panel 暴露给实现方。

### 动态分类（`meta.dynamics[].kind`）

| `kind` | 含义 | HTML 冻结 | 设计资源 |
|---|---|---|---|
| `content-bound` | 服务端/用户/API 数据 | 几何 + 占位；Figma 图仅为示例 | 无 — 在 `implementation_notes` 写绑定字段 |
| `component-variant` | Figma 组件属性轴 | 每变体值一个 state 或元素 patch | 每变体的静态预览 frame |
| `motion-preset` | Figma Motion / 原型动效 | **静态关键帧** 供布局审查 | `static_preview` 引用 frame id |
| `design-animation-asset` | 设计提供的 Lottie/GIF/video | 海报帧 + 项目内动画文件 | **必填** path + hash |
| `prototype-transition` | 帧间过渡（时长、缓动） | 仅文档 — 合同内不可播放 | 写在 `implementation_notes` |

`meta.dynamics` 可选；全静态时用 `[]`。非空时须在 review panel 逐条列出，且在 DOM 节点上标 `data-ui-dynamic` + `data-ui-dynamic-id`。

每条 `meta.dynamics[]` 还应记录**依据从哪来**、**资源是否齐**：

| 字段 | 取值 | 含义 |
|---|---|---|
| `evidence_source` | `figma-structure` \| `figma-text-hint` \| `requirement-slice` \| `user-confirmed` | 图层/变体/动效探测 vs 设计师**文案/便签** vs 需求文档 vs 用户对话 |
| `hint_text` | 字符串（可选） | `figma-text-hint` 时原文逐字引用 |
| `hint_node` | Figma 节点 id（可选） | 标注 TEXT/便签节点 — 不是被描述的 UI 节点 |
| `asset_status` | `resolved` \| `pending-user` \| `not-applicable` \| `waived` | 资源已入库 / **须向用户索要** / 不适用 / 用户明确豁免 |

### 图层不规范是常态 — 不能只靠规范命名

设计师的图层管理往往**不规范**。动态信息可能只出现在：

- 旁边的 **TEXT / 便签 / 说明**（「动态」「Lottie」「资源另附」「占位图」「接口返回」…）
- **静态截图**代替动效（Figma 内无动画文件）
- **完全不在 Figma** — 资源稍后通过网盘/聊天另发

**规则：**

1. **文案提示是「是否动态」的一等证据** — 不能凭此编造曲线或资源字节；记 `evidence_source: "figma-text-hint"` + 原文 `hint_text`。
2. **把提示映射到目标 UI 节点** — 看位置邻近与语义；**多个候选时问用户**，禁止猜。
3. **描述动效/占位/资源另附的说明不要标成 `ignore`** — 进入 §2c；只有版本号、署名等无关 meta 才可 ignore。
4. **资源不在 Figma 很常见** — 提示或需求提到 Lottie/GIF/video 但取不到字节 → `asset_status: "pending-user"`，合同只冻海报/占位几何，并 **§2d 向用户索要**。
5. 只有完成 **结构扫描 + 文案扫描 + 需求关键词** 且均无动态信号时，才可写 `dynamics: []`。

## 硬边界

- **按需求局部抽取：** 先读需求切片的 **In Scope**。列出必须出现的视觉产物（如拒信 tip、Appeal CTA、举报 sheet）。契约 root 取**覆盖属于本单元的 in-scope 产物的最小祖先子树** — 禁止默认整屏拷贝。**当 in-scope 产物在 Figma 树中断连**（最小公共祖先是整页 — 如消息列表里的 tip *加* composer 里的 CTA），**拆成多个 `component` / `modal` 单元，每个产物簇一份**，各自取局部最小祖先 root。绝不要为了「一个 root 覆盖全部」把断连产物压成单份整页契约 — 那是整页 dump 反模式的变体。未进范围的整页 chrome 仅作定位上下文（`data-ui-scope="context"` / `ignore`），不得当作验收真值。
- **取证前必须有单元拆分计划：** 填完 §1b 计划（产物 → 单元 → 作用域 `source_node` → `get_code` 目标）之前，禁止调用 TemPad 或拷贝模板。跳过计划、直接从整页选区开写，是流程失败。
- **只对作用域调 `get_code`：** 对每个计划单元的 `source_node`（及其状态帧）调用。**禁止**对整屏 page `get_code` 再裁剪，也禁止整页 dump 后把多余部分标成 `context`。
- **微小变更的 create vs patch：** 若已有契约拥有该物理容器 → **增量修补**（只增改 in-scope 节点；更新 `unit.requirements` + review-panel `in_scope`；不要把整个 shell 扩进 `in_scope`）。若不存在匹配契约 → **新建 `component`**，root 取产物最小祖先 — **不要**仅为挂一个 badge 而发明整根新的 `shared-component` / `page` dump。
- 不要发明视觉真值 — 不添加超出 Figma 证据支持范围的单元、状态、组件或字段。
- 不要发明布局 — DOM 结构、尺寸、定位、间距、层级必须从 TemPad `get_code` **机械转移**。只允许添加 `data-ui-*` / `data-figma-node` / `data-evidence` 标注。用手写语义化 flex/grid 重写并丢掉 get_code 几何是流程失败。
- 不要发明或重绘 icon/图片图形。每个 icon 或图片必须来自设计资产本身（机械转移资产字节），或逐字**复用项目已有资产**。当 `get_code` 返回资产空壳（`<svg data-src="...">` 或资产 URL）时，必须取得资产字节并持久化（内联 SVG 字节或保存为项目资产文件，并标注资产 hash）— 不允许留下空壳，更不允许手画一个「看起来差不多」的近似图形。仅仅「像」设计稿的 icon 是伪造真值。
- `get_structure` 只是**几何证据** — 从不证明绘制属性。颜色、透明度、渐变、描边必须来自 `get_code` token 或资产字节；仅由 structure 引用的元素不得携带凭记忆补上的绘制值（把 20% 透明度的拖拽条重建成纯黑就是伪造真值）。
- 不要把 Figma 中的每张图都当静态设计资产。区分**静态设计 icon**（冻结资产真值）与**动态/服务端提供的内容**（头像、用户上传、服务端徽章 — Figma 图只是举例）。依据需求上下文判断；动态内容只冻结几何 + 占位语义并在 review panel 注明，绝不把示例内容下载为冻结资产。
- 当作用域子树含 COMPONENT/INSTANCE、动效命名图层，或需求提到 animation/Lottie/GIF/video 时，**禁止跳过 §2c 动态扫描** — 仅在确认全单元为静态快照后才可写 `dynamics: []`。
- **禁止**用手绘静态 icon 近似 Lottie/GIF/video — 应标为 `design-animation-asset`，可获取时持久化文件，预览用海报关键帧。
- 存在变体 frame 或 `componentProperties` 时**禁止忽略 Figma 组件变体** — 映射为 `component-variant` 与/或 state 模板。
- 有 figma-bridge 时应对候选节点调用 `get_node_motion`；禁止无证据编造 easing/时长。
- **禁止**在 `ui-contract.html` 内嵌 autoplay 动画 — 合同预览保持静态关键帧；运行时动效由 `meta.dynamics` 交给实现方。
- 描述动效、占位、**资源另附**的设计师**文案/便签**不要标成 `ignore` — 它们是 §2c 动态线索。父级 SECTION 上、不在 `source_node` 内的过渡动画备注同样是一等证据；禁止只扫冻结根而丢掉画布备注。
- 不要把「加载完成→success」这类过渡备注当成每个状态上的循环；记 `prototype-transition`。
- review-panel 已有动效表时，`meta.dynamics[]` 必须同步，禁止只写表不写 meta。
- 文案指向多个 UI 节点时**禁止猜测** — 问用户指明节点或提供资源。
- 存在 `asset_status: "pending-user"`（或 review panel 里 `pending:`）时**禁止宣布 frozen**，除非用户在本会话**明确豁免** — 此时改 `waived` 并在 review panel 引用原话。
- 资源「可能在设计师网盘」**不是**跳过理由 — 必须 **§2d 主动问用户** 提供文件或路径。
- **禁止**只靠 `animate`/`lottie` 图层名发现动态 — **必须做 §2c 步骤 0 文案扫描**。
- 未经**逐份契约的用户显式确认**不得宣布冻结。每份生成或修补的 `ui-contract.html` 都必须提交用户人工复审；仅当用户明确豁免复审时才可跳过此门禁。
- 不要仅将截图或节点名称视为充分证据。需要结构化的 `get_code`/`get_structure` 载荷。
- 不要在 `ui-contract.html` 之外创建第二个 UI 真值源 — 不允许有并存的 YAML、JSON 或 markdown 映射/笔记文件。
- 不要将系统 UI 建模为契约内容：状态栏、系统导航、软键盘和设备外壳绝不能作为 `data-ui-kind` 值出现。改用受影响单元上的 CSS 安全区处理。
- 不要给空容器赋予功能性 `data-ui-kind`；每个 `data-ui-id` 元素都需要可见文字、图标、图片或明确的结构证据。
- 不要让 `data-ui-id` 元素缺少 `data-figma-node` 或 `data-ui-kind` 中的任意一个 — 每份真值单元都必须可溯源。
- 不要给上下文 chrome 加真值标注。带 `data-ui-scope="context"` 的元素只为保留 in-scope 子树的布局几何而存在；它们**不得**携带 `data-ui-id`、`data-ui-kind` 或 `data-figma-node`。上下文是定位，不是验收真值 — 混用会制造出门禁无法治理的第二冻结面。
- 不要在没有 `[data-ui-review-panel]` 中匹配说明的情况下使用 `data-evidence="inferred"` — 静默推断是流程失败。
- 不要凭记忆生成 `ui-contract.html`。将 `templates/ui-contract-template.html` 逐字复制到输出路径，然后逐字段填充值。保留四个受限区域（`#ui-contract-meta`、`<style>` token、`<main data-ui-contract>`、`[data-ui-review-panel]`）— 绝不新增第五个自由结构区域。必需的预览基础设施（`[data-ui-state-switcher]`、`[data-ui-state-host]`、`script[data-ui-state-preview]`）位于 `<main>` 内部，必须从模板保留。
- 不要删除或重写 `script[data-ui-state-preview]`。没有它，默认态与其它状态在浏览器中都不可见。
- 不要将所有帧批量塞入单个 Figma 查询。一次处理一个帧：查询它、填充其证据、再处理下一个。
- 不要为了寻找匹配项而扫描或比对仓库中每一份历史 `ui-contract.html`。通过需求 ID、组件/路由语义、已知的单元关系，或用户显式指定的路径来定位候选契约 — 绝不做全仓库盲扫。
- 匹配存在歧义（存在多个可能候选）时，不要修补匹配到的契约 — 先停止并要求用户澄清，再触碰任何文件。
- 不要在缺少完整 `delivery.implemented` 对象（`type`、`target`、`requirement`、`version`、`status`）的情况下声称 `delivery.status: "implemented"` 或 `"merged"`。
- 不要写入未经核实的 `delivery.implemented.target`。target 是对代码的断言，需要**两步代码核实**：① 实现符号已定义；② 用引用/使用搜索（findReferences 或调用点 grep）确认该单元**实际挂载/实例化的位置**。带着未经核实的 target 声明 `implemented` 是伪造真值，与手绘 icon 同级 — 包括凭记忆填写或从旧契约继承的 target。
- 不要仅凭校验器打印 `OK` 就声称 `frozen` / 1:1 保真 — `OK` 只代表 schema 通过；冻结前还需浏览器 hydrate 后的默认态预览与 scope 对齐。

## 定位：需求查找与实现反查

在决定新建还是增量修补之前，先执行实现反查：检查该单元是否已存在匹配的 `ui-contract.html`。

- 优先使用用户或需求切片已明确给出的路径。
- **按 in-scope 产物的物理 Figma 容器路由，而非按需求所属路由。** 微小变更（红点、badge、单个控件）往往物理上落在另一个单元的 `source_node` 子树内 — 例如共享 tab bar 上的未读红点、既有页面内某按钮的 disabled 态。此时应 **patch** 其 `unit.source_node` 包含该产物的契约，即使需求名义上属于另一个路由。按需求路由在这里会把产物 fork 到错误的契约，分裂共享组件的真值。若尚无此类契约，则为产物子树 **新建 `component`**（见快速参考）— 绝不用整页顶替。
- 否则按需求 ID（`unit.requirements` 包含此子需求）、组件/路由语义（`unit.route_or_trigger`、`unit.title`），或已知的共享组件依赖关系进行搜索。
- Figma 节点 ID 是**定位到文件之后的 patch 锚点** — 而不是跨全仓库的发现主键。不要仅凭节点 ID 在所有契约文件间搜索。
- 恰好一个匹配 → 进入"决策"环节。零匹配 → 新建。多个可能匹配 → STOP，报告候选项，请用户选择。

## 决策：新建 vs 增量修补

| 情况 | 处理方式 |
|---|---|
| 没有既有契约匹配此单元 | **新建。** 复制模板，运行下方完整工作流。 |
| 恰好一个契约匹配，且此次需求变更能容纳其中（新增状态、内容修改、微调布局） | **增量修补。** 仅原地编辑受影响的子树、状态和元数据字段。不触碰无关单元和无关子树。 |
| 单元边界、路由或共享依赖发生根本性变化 | **重建**该单元的契约；若单元在概念上仍是同一个，保持其 `contract_id`/`unit.id` 不变。 |
| 匹配存在歧义 | **阻塞。** 不要猜测；先请用户澄清，再触碰任何文件。 |

**重建/拆分的元数据规则：** 机械转移只约束 DOM，不约束元数据断言。重建或拆分既有契约时，从旧契约继承的 `delivery` 对象必须**对照当前代码重新核实**（§8 两步 target 核实）后才能携带；否则把 `delivery.status` 回退为实现前的值（如 `"frozen"`）并丢弃 `implemented` — 等新实现定位后再回填。

## 工作流

### 1. 确认上游、范围清单并定位

先读需求切片的 **In Scope** / **Out of Scope**（或等效段落），在接触设计数据之前建立简短的**范围清单**：

1. **必须冻结的视觉产物** — 切片要验收的一切（组件、tip、CTA、sheet…）。
2. **仅作定位的上下文 chrome** — 帮助定位但不参与验收的周边页面结构。
3. **忽略** — 备注、标注、设备外壳。

然后执行上方的"定位"步骤。在查询 TemPad 之前记录决策（新建 / 增量修补 / 重建）。

契约的 `unit.source_node` / `source.root_node` 必须是覆盖属于本单元的 must-freeze 产物的**最小祖先** — 当切片只命中子树时，禁止默认取整屏 page frame。**若 must-freeze 产物断连**（最小公共祖先是整页），不要扩大一个单元的 root 把它们全部吞下：拆成多个 `component` / `modal` 单元，各自取局部最小祖先 root。「最小祖先」规则是逐单元的，绝不是逐需求全局的。落在同一局部子树下的产物（如同一消息行簇下的红叹号 + tip）保持**一个**单元 — 仅当簇断连时才拆分。

### 1b. 单元拆分计划（在任何 `get_code` 或 HTML 之前强制）

在会话中公开此计划即可（聊天即可 — **不要**另建伴生映射文件）。每个 must-freeze 产物都有行之后，才能拷贝模板：

```
| 产物 (node id + 标签) | 单元 id | 类型 (page\|component\|modal\|shared-component) | 动作 (create\|patch\|rebuild) | source_node (作用域 root) | 状态 (或 "element-patch") | 动态 (static \| content-bound \| variant \| motion \| animation-asset) | get_code 目标 (= source_node) |
```

填表规则：
- 先按快速参考匹配需求体量。
- `get_code` 目标**必须等于**该单元的 `source_node`。单元是子树时，绝不要把整屏 page 列为「上下文取证」目标。
- 同一局部祖先下的相连产物 → 一行 / 一单元。断连产物 → 多行。
- 小红点且无容器契约 → `type=component`，`source_node`= badge 最小祖先 — 不是新的 shell `page`/`shared-component`。

### 2. 枚举帧是为了分类 — 不是为了冻结

**枚举帧是为了发现状态与 overlay**，不是为了决定契约范围。只在父级/选区查询足够列出同级帧（id、名称、类型、位置），用于发现 §1b 已计划单元的状态/modal。跳过发现仍会导致漏状态 — 但**枚举绝不把冻结范围扩大到单元拆分计划之外**。不是已计划单元之状态的帧，归为 `context` 或 `ignore`，不是新的验收单元。

对每个帧分类：

| 分类 | 含义 | 处理方式 |
|---|---|---|
| `page` | 本身在 In Scope 内的全屏**路由**变更 | 一份 `unit.type: "page"` 的 `ui-contract.html` |
| `component` | 需求范围内的子树 / 控件 / tip / 内联模块（非整页路由） | 一份 `unit.type: "component"` 的 `ui-contract.html` — 优先于整页拷贝 |
| `page-state` / `component-state` | 已分类单元的替代状态（加载中、空、错误、已选择、未选择） | 该单元文件内的一个 `<template data-ui-state>` 区块 — 不创建单独契约 |
| `modal` | 模态对话框、底部弹出层、气泡或覆盖层 | 一份 `unit.type: "modal"` 的 `ui-contract.html` — 绝不嵌套在页面内 |
| `shared-component` | 共享的导航外壳、标签栏或包裹页面的持久框架 | 一份 `unit.type: "shared-component"` 的 `ui-contract.html`；被依赖它的页面通过 `unit.dependencies` 引用 |
| `context` | 仅用于定位 in-scope 子树的页面 chrome | 从验收 DOM 省略，或带 `data-ui-scope="context"` 保留 — 绝不当作冻结真值 |
| `ignore` | 无关 meta（版本号、署名）或范围外 chrome | 完全排除在契约之外 |
| `dynamics-hint` | 描述动效、占位、**Figma 外资源**的 TEXT/便签/说明 | **不**当作 UI 真值冻结 — 喂给 §2c；记 `hint_node` + 原文；映射到目标 UI 节点 |

**分组规则：**
- 当 In Scope 是局部变更（tip、badge、sheet 入口、单个控件）→ 优先 `component` 或 `modal`，**不要**把 Figma 整屏 dump 成 `page`。
- **断连的 in-scope 产物 → 多个单元，而非一份整页契约。** 当 must-freeze 产物落在断连的 Figma 子树中、最小公共祖先是整页时（如消息列表里的拒信 tip *加* composer 里的 Appeal CTA），把每个产物簇分配到各自的 `component`（或 `modal`）单元。绝不要把它们压成 root 为整屏的单份 `page` 契约 — 那是包装成「一个 root 覆盖全部」的整页 dump 反模式。典型拆分：`reject-tip` component + `appeal-cta` component；`top-badge` component + `report-sheet` modal + sheet 的触发按钮（patch 进按钮物理容器所在的契约）。
- 共享相同外壳/布局、仅内容状态不同的帧 → 归为同一单元的状态变体。
- 布局不同、导航上下文不同或入口点独立的帧 → 拆分为独立单元。
- 模态覆盖层、底部弹出层和对话框 → 始终是独立单元。它们有自己的生命周期、入口触发器和关闭逻辑 — 绝不是某个页面契约内的子模板。**触发按钮不属于 modal 契约** — 把它 patch 进按钮物理容器（按钮所在的 page 或 component）的契约。modal 在 `unit.route_or_trigger` 记录其触发方式（如 `"triggered by report-button click on message-row"`）；容器在 `unit.dependencies` 记录对 modal 的依赖。
- **元素级属性变体不是状态模板。** 单个元素的属性变更（按钮 `disabled`、输入框 `readonly`、图标 `active`、tab `selected`）patch 到该元素既有节点上 — 它**不**衍生单元级 `<template data-ui-state>`。单元级状态用于评审需要切换查看的整单元视觉变化（loading / empty / error / logged-out）。若只有一个元素变化，patch 其视觉属性；状态模板留给整单元变体。
- 在 `page` 与状态之间犹豫时：检查这些帧是否通过同一路由/URL 到达。相同路由 → 状态。不同路由或由用户动作触发 → 独立单元（按情况选 `page` / `modal` / `component`）。
- 在 `component` 与 `component-state` 之间犹豫时：同一组件实例、同一触发上下文下仅视觉内容不同 → 该组件的状态。不同实例或不同触发上下文 → 独立的 `component` 单元。

**依赖方向：** `unit.dependencies` 从消费方指向被消费方 — 渲染共享 tab bar 的页面在其 `dependencies` 列出 tab bar 的单元 id；动作打开 modal 的页面列出 modal 的单元 id。被消费方（tab bar、modal）**不**反向引用其消费方。

**验证：** 确认每个枚举的帧都已分配到单元、状态、context 或 ignore。没有帧被遗漏。确认 §1 的每个 must-freeze 产物都出现在某个单元的 DOM 中。

### 2c. 动态与动效扫描（每单元强制，在 §2 帧列表之后）

在本单元第一次 `get_code` 之前：

0. **文案提示扫描（图层乱也必须做）** — 列出所有 TEXT/便签/说明（文案**或图层名**命中关键词）。扫 **两圈**，不要只扫冻结根：
   1. **作用域子树**（`unit.source_node` 与各 state `source_node`）。
   2. **父级 SECTION / 画布兄弟（必做）** — 设计师备注经常画在 unit 根**外面**，与页面 Frame 同级。对父 SECTION 做浅层 `get_structure`，收集不在任何 `source_node` 内的 TEXT/便签。用空间邻近、箭头、或点名状态的文案（「加载完成」「过渡」「打字机」）映射到本 unit。
   - 关键词例如：动态、动效、动画、过渡、打字机、扫光、Lottie、GIF、视频、骨架屏、占位、示例图、接口返回、资源另附、另发、外链、pulse、loading、placeholder、typewriter。
   - 标为 `dynamics-hint`；记 `hint_node`、**完整原文**（多行备注禁止截断）、推测的目标 UI 节点。
   - 描述 **状态过渡**（如「加载完成后…」）记 `prototype-transition`，**不要**当成每个状态模板上的循环。
   - 多候选 unit/节点 → **先问用户**。不要因为备注不在 `source_node` 内就标 `ignore`。
1. **候选扫描** — `get_structure` + 需求关键词：`INSTANCE`/`COMPONENT` 变体（**没有变体也不代表静态**）、用户内容类图片、动效命名图层（仅加分项）。
2. **动效探测** — 含文案指向的节点；有 figma-bridge 则 `get_node_motion`；仅 TemPad 时记「未探测」，**文案与需求仍有效**。
3. **设计动画资源** — 能取到字节则持久化，`asset_status: "resolved"`；提示/需求有资源但 Figma 无文件 → `pending-user`，只冻海报帧，**禁止编造文件**。
4. **分类** + 填 `evidence_source` / `asset_status`。
5. **映射到契约**（同英文版）。

发布**动态清单**（会话内，无旁路文件）：

```
| dynamic-id | 目标节点 | kind | evidence_source | 文案依据 | asset_status | 静态预览 | 实现提示 |
```

确认 **步骤 0–1 + 需求** 均无动态后，才写 `dynamics: []` 与 `none — static Figma snapshots only`。

### 2d. 缺资源升级（冻结前强制）

任一 `asset_status: "pending-user"`（或 review panel `pending:`）时，**先向用户发结构化索要清单**，再称 frozen — 除非用户已明确豁免。

聊天模板：

```
【ui-truth-mapping 待补充资源】<unit-id>
以下项在 Figma/需求中有动态或资源说明，但仓库内尚无可用文件。请提供资源或明确豁免后再冻结契约：

1. <dynamic-id> — <kind>
   - 依据：<evidence_source> / 原文：「<hint_text>」
   - 关联节点：<figma_node>
   - 需要：<.json|.gif|.mp4|… 或项目内路径>
   - 当前合同：仅冻结静态海报帧 / 占位几何
```

用户补文件后：持久化、更新 `design_asset`、`resolved`、重跑 validator。用户豁免后：`waived` + review panel 引用原话。

**派发：** 对于多于一个的独立单元，派发逐单元子代理…

### 3. 收集最小 TemPad 证据 *（派发时在逐单元子代理内运行）*

对每个**已计划单元**（及其每个状态帧），一次处理一个：

1. 对单元拆分计划中的**作用域** `source_node` / 状态 `source_node` 调用 `get_code` — 绝不要对整屏 page「先取再剪」。整页 `get_code` 再裁剪是流程失败，即便把多余部分标成 `context`。
2. 只把该作用域节点返回的 markup 转入该单元的 `<template>`。不要粘贴整页 DOM dump 再删除/隐藏兄弟。
3. 仅当同一作用域节点在 `get_code` 后仍有层级/几何/重叠歧义时，才调用 `get_structure`。默认不要调用。
4. 在编写 DOM 之前，记录你打算引用的每个 `data-figma-node` — 不得凭空捏造节点 ID。
5. **解析 `get_code` 返回的每一个资产引用**（`<svg data-src="...">`、图片填充、资产 URL），在写 DOM 之前逐一处理：
   1. **先分类：** 静态设计 icon，还是动态/服务端内容（头像、用户上传、服务端渲染徽章）？由需求上下文决定 — Figma 图可能只是举例。动态内容 → 冻结容器几何 + 占位符，并在 review panel 注明「服务端提供」；不下载示例图。
   2. **复用检查：** 在目标项目现有资产目录中查找同款 icon（目录结构以目标项目实际为准，不做预设）。已存在 → 引用它，并把现有资产路径记录进 review panel，不重复搬运字节。
   3. **简单矢量** → 取得资产字节，把 SVG 逐字内联进契约，并标注资产 hash。把所有资产 URL 视为**易失效**（部分 TemPad 环境由会话结束即失效的临时本地服务器提供资产）— 必须现在持久化字节，事后绝不引用 URL。
   4. **复杂/位图资产** → 下载原图并持久化到项目资产目录；契约引用持久化后的路径（相对项目根的路径，绝不引用资产 URL）。
   5. **无法获取**（MCP 无字节返回、下载失败、格式不支持）→ 在 review panel 记为待办项并提交用户决策（提供资产、替代方案或暂缓）；若阻塞冻结，记录 `blocked_missing_visual_truth`（关键资产）。**不要**兜底重绘 — 猜画 icon 是流程失败。若暂缓资产必须以 `data-src` 空壳留在契约中，该元素必须携带 `data-ui-asset` 元数据 — 校验器会拒绝任何没有它的 `data-src` 元素。

   注意：`get_code` 可能把整个子树作为**一个**矢量资产返回（如 sheet 拖拽条）。资产字节才是唯一完整真值 — 不要用 `get_structure` 重建子元素：structure 只携带几何，会静默丢掉绘制属性（fill-opacity、渐变、描边）。

### 4. 逐字复制模板（新建）或打开已匹配文件（修补）

**新建：** 找到 `templates/ui-contract-template.html`，将其逐字复制到 `<output-dir>/<unit-id>/ui-contract.html`。四个区域（`#ui-contract-meta`、`<style>`、`<main data-ui-contract>`、`[data-ui-review-panel]`）保持完整；保留模板中的 `[data-ui-state-switcher]`、`[data-ui-state-host]`、`script[data-ui-state-preview]`；绝不新增第五个自由区域。

**增量修补：** 直接打开定位到的文件。不要在已有契约上重新复制模板。若已匹配文件缺少预览基础设施（较旧的 v2 文件或预览前草稿），按以下顺序补齐，不重写无关真值 DOM：
1. 将既有真值 DOM（每个 `data-ui-id` 子树）移入 `<main>` 内新建的 `<template data-ui-state="default">`。这是结构搬迁，不是重写 — 原样保留节点、属性和顺序。
2. 从当前模板补加空的 `[data-ui-state-host]` 与 `[data-ui-state-switcher]`，并逐字复制 `script[data-ui-state-preview]`。
3. 回填 `meta.states` 一条 `{ "id": "default", "source_node": <unit.source_node>, "default": true }`，并在 `<main>` 上设 `data-ui-state-default="default"`。
4. 保持四个区域完整；不引入第五个。

### 5. 填充或修补单元 HTML

- `#ui-contract-meta` — 填充 `schema_version: 2`、`contract_id`、`source`（`requirement`/`design_file`/`root_node`）、`unit`（`id`/`type`/`title`/`route_or_trigger`/`requirements`/`source_node`/`dependencies`）、`states`（每帧一条，恰好一条 `default: true`）、`revision`、`delivery.status`。`unit.type` 为 `page` | `modal` | `shared-component` | `component`。`unit.source_node` 为 §1 的范围 root。**State id 必须是 kebab-case 小写 ASCII**（`^[a-z][a-z0-9-]*$`，如 `loading`、`empty-state`）— 预览脚本用 state id 拼接 CSS 选择器，遇到空格、引号或方括号会失效。**默认态** = 评审首次打开页面时看到的状态（通常是 `loaded`/`success`，而非瞬态 `loading`/`error`），这样 hydrate 后的预览匹配屏幕的主视觉，而非一闪而过的帧。
- `<style>` — 从 `get_code` **机械转移**有证据的 CSS（含几何：宽高、定位、inset、gap、padding、margin、display、flex/grid、z-index、排版、颜色）。TemPad 返回规范 token 绑定时优先 `var(--token)`；否则保留字面值。禁止用重写的语义化样式表替代 get_code 布局。
- `<main data-ui-contract>` —
  - 保留 `[data-ui-state-switcher]` 与空的 `[data-ui-state-host]`。
  - **每一个**已声明状态（含默认态）都放入 `<template data-ui-state="<id>">`。将 get_code DOM 转入 template；只加标注属性。
  - 仅当共享 chrome 在范围内且各状态完全相同时，才可放在 host 外；否则在每个状态模板内复制。
  - 范围外的定位 chrome（context）可放在 host 外以保留几何，但必须标 `data-ui-scope="context"`，且**不得**携带 `data-ui-id` / `data-ui-kind` / `data-figma-node`。context 不是真值；校验器会拒绝真值标注的 context。
  - `<main>` 上的 `data-ui-unit-id`/`data-ui-unit-type`/`data-ui-state-default` 必须与 meta 一致。
  - 每个真值元素携带唯一 `data-ui-id`、`data-ui-kind`、`data-figma-node`。
  - 原样保留 `script[data-ui-state-preview]`，以便打开浏览器即 hydrate 默认态并可切换。
- `[data-ui-review-panel]` — 必须包含：
  - `dt[data-ui-scope="in_scope"]` / `dd` 列出 must-freeze 产物（节点 id + 标签）；此处列出的每个节点 id 必须出现在 DOM 中某个非 context 的 `data-figma-node` 上（校验器会交叉校验）。
  - `dt[data-ui-scope="out_of_scope"]` / `dd` 列出上下文 chrome 或 `"none"`；
  - 资产说明：每个 icon/图片 — 其处置方式（内联资产字节 + 资产 hash、复用的项目资产路径、服务端占位，或**待办：等待用户决策**）。不允许有来历不明的 icon。
  - 推断说明：每个 `data-evidence="inferred"` 都要有匹配的 `dt[data-ui-evidence-for]`/`dd`。
- 增量修补：只触碰此次需求实际变更的子树、状态和元数据字段。不触碰无关 `data-ui-id` 子树、无关状态及其它单元的 `unit.dependencies`。

一次处理一个帧 — 绝不将所有帧批量塞入单次查询或单次编辑。

### 6. 浏览器审查

在浏览器（或 IDE 渲染预览）中打开契约 HTML。预览脚本必须在不展开审查面板的情况下，将默认态 hydrate 进 `[data-ui-state-host]`：

- 确认 **hydrate 后的默认态**布局匹配 Figma 范围 root（几何 + 内容），而不是空 host 或手写近似。
- 若 host 看起来空白：检查（1）预览脚本在场，（2）默认 template 非空，（3）`--color-text` / `--color-surface` 是合法 CSS 颜色（绝不能残留无效 token `#PLACEHOLDER` — IDE 暗色画布会把黑字藏掉）。模板因此为 `html, body` 强制浅色底 + `color-scheme: light`；用证据色覆盖，不要写占位字符串。
- 用 `[data-ui-state-switcher]` 逐一切换**每个**已声明状态；每次激活后的 host 内容必须匹配其源帧。
- 逐一比对**每个 icon/图片**与其证据：内联字节必须与取得的资产载荷一致；复用资产必须与项目文件一致；服务端占位必须可见地是占位。即便几何完全正确，「看起来是对的 icon」的重绘图也不通过本项检查。
- 展开 `[data-ui-review-panel]`，确认范围清单、资产说明、每个 `data-figma-node` 与推断说明清晰准确。
- hydrate 后的 HTML **就是**复审媒介。不要生成或保存预览截图产物（如 `contract-preview-*.png`）— 人直接审核 HTML，截图会与契约漂移。
- 绝不假设「校验器 OK ⇒ 看起来像 Figma」。
- **用户确认门禁：** 把每份契约提交用户人工确认（路径 + 打开方式 + review panel 摘要）。在用户显式确认前不得宣布冻结 — 除非用户已明确豁免本轮复审。

### 7. 运行校验器

在交付项目 / kit 根目录（包含 `scripts/validate-ui-contract-html.py` 的目录）执行：

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

仅当输出 `OK` 时才继续。失败则修复契约并重新运行 — 绝不在失败的契约上声称 `acceptance_frozen`。校验器 `OK` 是必要非充分条件：冻结前仍需 §1/§1b/§6 的 hydrate 预览与需求范围对齐。

**校验器自动检查的内容：** schema/DOM 结构、单一单元 root、`data-ui-id` 唯一性 + `data-figma-node`/`data-ui-kind` 存在性（拒绝 placeholder figma 节点）、预览基础设施存在、**每个**状态模板非空且含可见文字/媒体、`in_scope`/`out_of_scope` 清单存在、**in_scope 节点 id 与 DOM 中冻结的 `data-figma-node` 值交叉校验**、context chrome 未携带真值标注、推断说明覆盖每个 `data-evidence="inferred"`、`data-src` 资产空壳携带 `data-ui-asset` 元数据、交付字段。

**校验器无法检查的内容（仍是 §6 流程检查）：** `unit.source_node` 的最小性（无法访问 Figma 树 — 你必须确认范围 root 是局部最小祖先，而非整页）、布局对 Figma 的保真度（机械转移 vs 手写重写）、**icon 资产保真**（SVG path vs 取得的资产字节 — 校验器看不到 Figma 资产）、浏览器 hydrate 的保真度（打开看）、state/default 选择的语义正确性。`OK` ≠ 「看起来像 Figma」且 ≠ 「scope 匹配切片」— 那些是人工/§6 门禁。

### 8. 开发完成后 — 回填交付信息并重新校验

单元实现完成后，编辑同一文件的 `#ui-contract-meta`：

- 将 `delivery.status` 设为 `"implemented"`（合并后设为 `"merged"`）；
- 填充 `delivery.implemented`：`type`、`target`（代码位置）、`requirement`、`version`、`status`。

**写入 `target` 前必须核实** — 针对当前代码库的两步强制核实：

1. **定义核实：** 确认实现符号存在（类/组件/部件的定义）。
2. **引用核实：** 运行引用/使用搜索（findReferences，或 grep 实例化/调用点），定位该单元**实际挂载或实例化的位置**。挂载点才是 target — 即使它与定义文件不同。只做定义核实不充分（符号完全可能定义在一个文件、挂载在另一个文件）。

把核实到的位置写入 `target`（两者不同时，定义文件与挂载文件都写上）。绝不凭记忆填写 target，也绝不在未重新运行两步核实的情况下从被取代的旧契约携带 target；若暂时定位不到实现，保持 `delivery.status` 为实现前的值，而不是猜一个 target 凑齐对象。

重新运行校验器 — 它会强制要求当 `delivery.status` 为 `"implemented"` 或 `"merged"` 时，`delivery.implemented` 必须完整。不要创建单独的实现追踪文件；同一份 HTML 内的这次回填就是唯一的实现记录。

### 9. 替换或废弃 — 同一次变更内清扫陈旧指针

不存在聚合索引文件，契约的指针散落在需求目录各处（`status.json` notes、`visual-acceptance.md`、progress/todo 记录、拆分摘要）。当契约被**删除、替换或以变更后的 unit id 重建**时，引用清扫完成前该变更不算完成：

1. 扫描需求目录（`.ai-delivery/requirements/<req-id>/`）中对旧 unit id / 旧契约路径的每一处引用。
2. 把每个**活跃**指针（`status.json` notes、`visual-acceptance.md` 的 Contract 条目、progress/todo、拆分摘要）改指新契约路径 / unit id。
3. 允许保留一行历史注记（「已删除 / 被 `<new unit id>` 取代」）— 但活跃指针不得继续指向已不存在的契约文件。
4. 条件允许时运行需求状态校验器（`scripts/validate-delivery-status.py <status.json> --req-root <req-dir>`）；它会机械化地拒绝悬空的 `ui-contract.html` 指针。

## 组件类型词汇

`container`、`card`、`list`、`list-item`、`form`、`text`、`text-input`、`button`、`image`、`icon`、`tab`、`navigation`、`divider`、`badge`、`modal`、`sheet`、`toast`、`custom`

## 反模式（视为流程失败）

- 在 `ui-contract.html` 之外再写一份 YAML、JSON 或 markdown 文件来承载 UI 真值。
- 切片 In Scope 只命中局部子树时，仍做 Figma **整页 dump**（拒信 tip、sheet、badge…）。
- **整页 `get_code` 再裁剪**（或「先全转，再把多余标成 context」），而不是对每个计划单元的作用域 `source_node` 调 `get_code`。
- **跳过 §1b 单元拆分计划**，直接从整页 Figma 选区开写模板。
- **把断连的 in-scope 产物压成一份整页契约**（root = 整屏），而不是拆成各带局部最小祖先 root 的逐簇 `component` / `modal` 单元。
- 跳过 §1 范围清单 / §1b 计划，把无关的导航 / 列表 / composer chrome 冻成验收真值。
- **按需求所属路由路由微小变更**（红点、badge、disabled 态），而不是按产物的物理 Figma 容器路由，把产物 fork 进错误契约。
- **仅为挂一个微小 in-scope 产物而发明整根新的 `shared-component` / `page` dump**（且尚无匹配容器契约时）— 应新建作用域 `component`，或 patch 既有容器契约。
- **给上下文 chrome 加真值标注**（`data-ui-scope="context"` 同时带 `data-ui-id` / `data-ui-kind` / `data-figma-node`）— context 仅为定位。
- **为单个元素的属性变体衍生单元级状态模板**（按钮 `disabled`、输入框 `readonly`），而不是 patch 该元素的属性。
- **把 modal 的触发按钮放进 modal 契约**，而不是 patch 进按钮物理容器所在的契约。
- 用手写语义化 flex/grid 布局替代 `get_code` 几何的机械转移。
- **手写 icon 或图片图形**（重绘一个「差不多」的 SVG），而非机械转移设计资产字节或复用项目已有资产。
- 在冻结契约里留下未解析的 `get_code` 资产空壳（`data-src` / 资产 URL）— 资产字节必须内联或持久化进项目，并标注资产 hash。
- 用 `get_structure` 几何重建资产空壳子树（`get_code` 把整个子树导出为一个 SVG 资产时，如拖拽条），静默丢掉绘制属性（fill-opacity、渐变、描边）— structure 只是几何证据。
- 需求上下文表明内容是服务端提供（头像、用户上传、动态徽章）时，仍把 Figma **示例图**下载为冻结资产。
- 无法获取的资产静默重绘，而不是记为待办项交由用户决策。
- 把预览截图（`contract-preview-*.png` 等）当作交付产物保存 — hydrate 后的 HTML 才是复审媒介。
- 未经逐份契约的用户显式确认即宣布冻结（除非用户明确豁免复审）。
- 凭记忆写入 `delivery.implemented.target`，或在未对照当前代码重新核实的情况下从被取代的旧契约继承 target。
- 只做定义核实就回填 `target` — 必须先通过引用/使用搜索确认实际挂载/实例化文件；两者不同时，两个位置都属于 `target`。
- 删除或重建契约（unit id 变化）时不清扫需求目录中的陈旧指针 — `status.json` notes、`visual-acceptance.md`、progress/todo、拆分摘要中的活跃引用必须在同一次变更内改指新契约。
- 把默认态（或任意状态）只放进 `<template>` 并删除/省略 `script[data-ui-state-preview]`，导致浏览器显示空 host。
- 在 hydrate / switcher 未工作时声称已完成浏览器默认态审查，或未逐一切换**每个**已声明状态。
- 将状态栏、导航栏、键盘或设备外壳建模为 `data-ui-kind` 内容，而不是使用 CSS 安全区处理。
- 使用 `data-evidence="inferred"` 却没有匹配的审查面板说明。
- 在 `data-figma-node` 或 `unit.source_node` 中残留模板 `PLACEHOLDER-*` 值（校验器拒绝 placeholder figma 节点；source_node 最小性是 §6 流程检查）。
- 扫描每一份历史契约文件来"寻找"某个单元，而不是使用需求 ID、语义或用户显式指定的路径。
- 为一个很小的需求变更重写整份已匹配的契约，而不是做增量修补。
- 未做 hydrate 预览与 scope 对齐，仅凭校验器 `OK` 声称 `acceptance_frozen`/`frozen`/`implemented`/`merged`。
- 不先复制模板就手写 DOM 结构。
