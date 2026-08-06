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

## 硬边界

- **按需求局部抽取：** 先读需求切片的 **In Scope**。列出必须出现的视觉产物（如拒信 tip、Appeal CTA、举报 sheet）。契约 root 取**覆盖属于本单元的 in-scope 产物的最小祖先子树** — 禁止默认整屏拷贝。**当 in-scope 产物在 Figma 树中断连**（最小公共祖先是整页 — 如消息列表里的 tip *加* composer 里的 CTA），**拆成多个 `component` / `modal` 单元，每个产物簇一份**，各自取局部最小祖先 root。绝不要为了「一个 root 覆盖全部」把断连产物压成单份整页契约 — 那是整页 dump 反模式的变体。未进范围的整页 chrome 仅作定位上下文（`data-ui-scope="context"` / `ignore`），不得当作验收真值。
- **取证前必须有单元拆分计划：** 填完 §1b 计划（产物 → 单元 → 作用域 `source_node` → `get_code` 目标）之前，禁止调用 TemPad 或拷贝模板。跳过计划、直接从整页选区开写，是流程失败。
- **只对作用域调 `get_code`：** 对每个计划单元的 `source_node`（及其状态帧）调用。**禁止**对整屏 page `get_code` 再裁剪，也禁止整页 dump 后把多余部分标成 `context`。
- **微小变更的 create vs patch：** 若已有契约拥有该物理容器 → **增量修补**（只增改 in-scope 节点；更新 `unit.requirements` + review-panel `in_scope`；不要把整个 shell 扩进 `in_scope`）。若不存在匹配契约 → **新建 `component`**，root 取产物最小祖先 — **不要**仅为挂一个 badge 而发明整根新的 `shared-component` / `page` dump。
- 不要发明视觉真值 — 不添加超出 Figma 证据支持范围的单元、状态、组件或字段。
- 不要发明布局 — DOM 结构、尺寸、定位、间距、层级必须从 TemPad `get_code` **机械转移**。只允许添加 `data-ui-*` / `data-figma-node` / `data-evidence` 标注。用手写语义化 flex/grid 重写并丢掉 get_code 几何是流程失败。
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
| 产物 (node id + 标签) | 单元 id | 类型 (page\|component\|modal\|shared-component) | 动作 (create\|patch\|rebuild) | source_node (作用域 root) | 状态 (或 "element-patch") | get_code 目标 (= source_node) |
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
| `ignore` | 非 UI 内容（设计师备注、标注、辅助线）或范围外 chrome | 完全排除在契约之外 |

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

**派发：** 对于多于一个的独立单元，派发逐单元子代理，使证据收集与 DOM 编写保持隔离 — 不产生跨单元污染。仅当用户明确要求不使用子代理，或恰好只有一个单元且 ≤2 个状态时，才跳过子代理派发。

### 3. 收集最小 TemPad 证据 *（派发时在逐单元子代理内运行）*

对每个**已计划单元**（及其每个状态帧），一次处理一个：

1. 对单元拆分计划中的**作用域** `source_node` / 状态 `source_node` 调用 `get_code` — 绝不要对整屏 page「先取再剪」。整页 `get_code` 再裁剪是流程失败，即便把多余部分标成 `context`。
2. 只把该作用域节点返回的 markup 转入该单元的 `<template>`。不要粘贴整页 DOM dump 再删除/隐藏兄弟。
3. 仅当同一作用域节点在 `get_code` 后仍有层级/几何/重叠歧义时，才调用 `get_structure`。默认不要调用。
4. 在编写 DOM 之前，记录你打算引用的每个 `data-figma-node` — 不得凭空捏造节点 ID。

### 4. 逐字复制模板（新建）或打开已匹配文件（修补）

**新建：** 找到 `templates/ui-contract-template.html`，将其逐字复制到 `<output-dir>/<unit-id>/ui-contract.html`。四个区域（`#ui-contract-meta`、`<style>`、`<main data-ui-contract>`、`[data-ui-review-panel]`）保持完整；保留模板中的 `[data-ui-state-switcher]`、`[data-ui-state-host]`、`script[data-ui-state-preview]`；绝不新增第五个自由区域。

**增量修补：** 直接打开定位到的文件。不要在已有契约上重新复制模板。若已匹配文件缺少预览基础设施（较旧的 v2 文件或预览前草稿），按以下顺序补齐，不重写无关真值 DOM：
1. 将既有真值 DOM（每个 `data-ui-id` 子树）移入 `<main>` 内新建的 `<template data-ui-state="default">`。这是结构搬迁，不是重写 — 原样保留节点、属性和顺序。
2. 从当前模板补加空的 `[data-ui-state-host]` 与 `[data-ui-state-switcher]`，并逐字复制 `script[data-ui-state-preview]`。
3. 回填 `meta.states` 一条 `{ "id": "default", "source_node": <unit.source_node>, "default": true }`，并在 `<main>` 上设 `data-ui-state-default="default"`。
4. 保持四个区域完整；不引入第五个。

### 5. 填充或修补单元 HTML

- `#ui-contract-meta` — 填充 `schema_version: 2`、`contract_id`、`source`（`requirement`/`design_file`/`root_node`/`cache`）、`unit`（`id`/`type`/`title`/`route_or_trigger`/`requirements`/`source_node`/`dependencies`）、`states`（每帧一条，恰好一条 `default: true`）、`revision`、`delivery.status`。`unit.type` 为 `page` | `modal` | `shared-component` | `component`。`unit.source_node` 为 §1 的范围 root。**State id 必须是 kebab-case 小写 ASCII**（`^[a-z][a-z0-9-]*$`，如 `loading`、`empty-state`）— 预览脚本用 state id 拼接 CSS 选择器，遇到空格、引号或方括号会失效。**默认态** = 评审首次打开页面时看到的状态（通常是 `loaded`/`success`，而非瞬态 `loading`/`error`），这样 hydrate 后的预览匹配屏幕的主视觉，而非一闪而过的帧。
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
  - 推断说明：每个 `data-evidence="inferred"` 都要有匹配的 `dt[data-ui-evidence-for]`/`dd`。
- 增量修补：只触碰此次需求实际变更的子树、状态和元数据字段。不触碰无关 `data-ui-id` 子树、无关状态及其它单元的 `unit.dependencies`。

一次处理一个帧 — 绝不将所有帧批量塞入单次查询或单次编辑。

### 6. 浏览器审查

在浏览器（或 IDE 渲染预览）中打开契约 HTML。预览脚本必须在不展开审查面板的情况下，将默认态 hydrate 进 `[data-ui-state-host]`：

- 确认 **hydrate 后的默认态**布局匹配 Figma 范围 root（几何 + 内容），而不是空 host 或手写近似。
- 若 host 看起来空白：检查（1）预览脚本在场，（2）默认 template 非空，（3）`--color-text` / `--color-surface` 是合法 CSS 颜色（绝不能残留无效 token `#PLACEHOLDER` — IDE 暗色画布会把黑字藏掉）。模板因此为 `html, body` 强制浅色底 + `color-scheme: light`；用证据色覆盖，不要写占位字符串。
- 用 `[data-ui-state-switcher]` 逐一切换**每个**已声明状态；每次激活后的 host 内容必须匹配其源帧。
- 展开 `[data-ui-review-panel]`，确认范围清单、每个 `data-figma-node` 与推断说明清晰准确。
- 绝不假设「校验器 OK ⇒ 看起来像 Figma」。

### 7. 运行校验器

在交付项目 / kit 根目录（包含 `scripts/validate-ui-contract-html.py` 的目录）执行：

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

仅当输出 `OK` 时才继续。失败则修复契约并重新运行 — 绝不在失败的契约上声称 `acceptance_frozen`。校验器 `OK` 是必要非充分条件：冻结前仍需 §1/§1b/§6 的 hydrate 预览与需求范围对齐。

**校验器自动检查的内容：** schema/DOM 结构、单一单元 root、`data-ui-id` 唯一性 + `data-figma-node`/`data-ui-kind` 存在性（拒绝 placeholder figma 节点）、预览基础设施存在、**每个**状态模板非空且含可见文字/媒体、`in_scope`/`out_of_scope` 清单存在、**in_scope 节点 id 与 DOM 中冻结的 `data-figma-node` 值交叉校验**、context chrome 未携带真值标注、推断说明覆盖每个 `data-evidence="inferred"`、交付字段。

**校验器无法检查的内容（仍是 §6 流程检查）：** `unit.source_node` 的最小性（无法访问 Figma 树 — 你必须确认范围 root 是局部最小祖先，而非整页）、布局对 Figma 的保真度（机械转移 vs 手写重写）、浏览器 hydrate 的保真度（打开看）、state/default 选择的语义正确性。`OK` ≠ 「看起来像 Figma」且 ≠ 「scope 匹配切片」— 那些是人工/§6 门禁。

### 8. 开发完成后 — 回填交付信息并重新校验

单元实现完成后，编辑同一文件的 `#ui-contract-meta`：

- 将 `delivery.status` 设为 `"implemented"`（合并后设为 `"merged"`）；
- 填充 `delivery.implemented`：`type`、`target`（代码位置）、`requirement`、`version`、`status`。

重新运行校验器 — 它会强制要求当 `delivery.status` 为 `"implemented"` 或 `"merged"` 时，`delivery.implemented` 必须完整。不要创建单独的实现追踪文件；同一份 HTML 内的这次回填就是唯一的实现记录。

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
- 把默认态（或任意状态）只放进 `<template>` 并删除/省略 `script[data-ui-state-preview]`，导致浏览器显示空 host。
- 在 hydrate / switcher 未工作时声称已完成浏览器默认态审查，或未逐一切换**每个**已声明状态。
- 将状态栏、导航栏、键盘或设备外壳建模为 `data-ui-kind` 内容，而不是使用 CSS 安全区处理。
- 使用 `data-evidence="inferred"` 却没有匹配的审查面板说明。
- 在 `data-figma-node` 或 `unit.source_node` 中残留模板 `PLACEHOLDER-*` 值（校验器拒绝 placeholder figma 节点；source_node 最小性是 §6 流程检查）。
- 扫描每一份历史契约文件来"寻找"某个单元，而不是使用需求 ID、语义或用户显式指定的路径。
- 为一个很小的需求变更重写整份已匹配的契约，而不是做增量修补。
- 未做 hydrate 预览与 scope 对齐，仅凭校验器 `OK` 声称 `acceptance_frozen`/`frozen`/`implemented`/`merged`。
- 不先复制模板就手写 DOM 结构。
