---
name: ui-truth-mapping
description: 当需要从设计源（Figma）提取结构化 UI 真值并冻结为单一规范化 HTML UI 契约（schema v2）以实现 1:1 映射时使用。自动检测并拆分单个设计源中的多个单元（页面、弹窗、共享组件）。
---

# UI 真值映射

从设计源（Figma）提取结构化 UI 真值，并将其冻结为每个单元一份的规范化 `ui-contract.html` 文件（schema v2）。HTML 文件是唯一输出 — 没有单独的映射文档，也没有与之并存的 YAML 或 JSON 伴生文件。

单个设计源可能包含多个独立单元：不同的页面、弹窗覆盖层、共享组件（导航外壳、标签栏），或**需求范围内的组件子树**。每个单元恰好对应一份 `ui-contract.html`。同一单元的多个状态（加载中、空、错误、已选择/未选择）都存放在这一个文件内，以 `<template data-ui-state>` 区块表达 — 它们永远不是独立契约。

**多状态契约必须可在浏览器中预览。** 每个状态（含默认态）都放在 `<template data-ui-state>` 中。原生 `<template>` 不会被浏览器渲染 — 模板内固定的 `script[data-ui-state-preview]` 会在加载时 hydrate `[data-ui-state-host]`，并由 `[data-ui-state-switcher]` 切换状态。不要在未 hydrate 的空 host 上宣称布局保真。

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

## 硬边界

- **按需求局部抽取：** 先读需求切片的 **In Scope**。列出必须出现的视觉产物（如拒信 tip、Appeal CTA、举报 sheet）。契约 root 取**覆盖全部 in-scope 产物的最小祖先子树** — 禁止默认整屏拷贝。未进范围的整页 chrome 仅作定位上下文（`data-ui-scope="context"` / `ignore`），不得当作验收真值。
- 不要发明视觉真值 — 不添加超出 Figma 证据支持范围的单元、状态、组件或字段。
- 不要发明布局 — DOM 结构、尺寸、定位、间距、层级必须从 TemPad `get_code` **机械转移**。只允许添加 `data-ui-*` / `data-figma-node` / `data-evidence` 标注。用手写语义化 flex/grid 重写并丢掉 get_code 几何是流程失败。
- 不要仅将截图或节点名称视为充分证据。需要结构化的 `get_code`/`get_structure` 载荷。
- 不要在 `ui-contract.html` 之外创建第二个 UI 真值源 — 不允许有并存的 YAML、JSON 或 markdown 映射/笔记文件。
- 不要将系统 UI 建模为契约内容：状态栏、系统导航、软键盘和设备外壳绝不能作为 `data-ui-kind` 值出现。改用受影响单元上的 CSS 安全区处理。
- 不要给空容器赋予功能性 `data-ui-kind`；每个 `data-ui-id` 元素都需要可见文字、图标、图片或明确的结构证据。
- 不要让 `data-ui-id` 元素缺少 `data-figma-node` 或 `data-ui-kind` 中的任意一个 — 每份真值单元都必须可溯源。
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

契约的 `unit.source_node` / `source.root_node` 必须是覆盖 must-freeze 产物的**最小祖先** — 当切片只命中子树时，禁止默认取整屏 page frame。

### 2. 枚举帧并对单元分类

**先枚举所有帧：** 在父级/选区层级（而非特定节点）查询设计源，列出顶层同级帧的完整清单 — id、名称、类型、位置。跳过此步骤会导致状态变体被遗漏。

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
- 共享相同外壳/布局、仅内容状态不同的帧 → 归为同一单元的状态变体。
- 布局不同、导航上下文不同或入口点独立的帧 → 拆分为独立单元。
- 模态覆盖层、底部弹出层和对话框 → 始终是独立单元。它们有自己的生命周期、入口触发器和关闭逻辑 — 绝不是某个页面契约内的子模板。
- 在 `page` 与状态之间犹豫时：检查这些帧是否通过同一路由/URL 到达。相同路由 → 状态。不同路由或由用户动作触发 → 独立单元（按情况选 `page` / `modal` / `component`）。

**验证：** 确认每个枚举的帧都已分配到单元、状态、context 或 ignore。没有帧被遗漏。确认 §1 的每个 must-freeze 产物都出现在某个单元的 DOM 中。

**派发：** 对于多于一个的独立单元，派发逐单元子代理，使证据收集与 DOM 编写保持隔离 — 不产生跨单元污染。仅当用户明确要求不使用子代理，或恰好只有一个单元且 ≤2 个状态时，才跳过子代理派发。

### 3. 收集最小 TemPad 证据 *（派发时在逐单元子代理内运行）*

对于该单元中的每一帧，一次处理一个：

1. 先调用 `get_code(frame_source_node)` — 它返回 markup、**布局样式**、token 和资源引用。这是结构、定位、间距和内容的主要证据来源。当 In Scope 是局部时，优先使用 §1 的**范围 root**，而非整页。
2. 仅当 `get_code` 之后层级、几何或重叠仍存在歧义时，才调用 `get_structure(frame_source_node)`。不要默认调用它 — 它是消歧工具，不是首选查询。
3. 在编写 DOM 之前，记录你打算引用的每个 `data-figma-node` — 不得凭空捏造节点 ID。

### 4. 逐字复制模板（新建）或打开已匹配文件（修补）

**新建：** 找到 `templates/ui-contract-template.html`，将其逐字复制到 `<output-dir>/<unit-id>/ui-contract.html`。四个区域（`#ui-contract-meta`、`<style>`、`<main data-ui-contract>`、`[data-ui-review-panel]`）保持完整；保留模板中的 `[data-ui-state-switcher]`、`[data-ui-state-host]`、`script[data-ui-state-preview]`；绝不新增第五个自由区域。

**增量修补：** 直接打开定位到的文件。不要在已有契约上重新复制模板。若已匹配文件缺少预览基础设施，从当前模板补齐 switcher / host / preview script，不要重写无关真值 DOM。

### 5. 填充或修补单元 HTML

- `#ui-contract-meta` — 填充 `schema_version: 2`、`contract_id`、`source`、`unit`、`states`（每帧一条，恰好一条 `default: true`）、`revision`、`delivery.status`。`unit.type` 为 `page` | `modal` | `shared-component` | `component`。`unit.source_node` 为 §1 的范围 root。
- `<style>` — 从 `get_code` **机械转移**有证据的 CSS（含几何：宽高、定位、inset、gap、padding、margin、display、flex/grid、z-index、排版、颜色）。TemPad 返回规范 token 绑定时优先 `var(--token)`；否则保留字面值。禁止用重写的语义化样式表替代 get_code 布局。
- `<main data-ui-contract>` —
  - 保留 `[data-ui-state-switcher]` 与空的 `[data-ui-state-host]`。
  - **每一个**已声明状态（含默认态）都放入 `<template data-ui-state="<id>">`。将 get_code DOM 转入 template；只加标注属性。
  - 仅当共享 chrome 在范围内且各状态完全相同时，才可放在 host 外；否则按状态模板复制，或标 `data-ui-scope="context"`。
  - `<main>` 上的 `data-ui-unit-id`/`data-ui-unit-type`/`data-ui-state-default` 必须与 meta 一致。
  - 每个真值元素携带唯一 `data-ui-id`、`data-ui-kind`、`data-figma-node`。
  - 原样保留 `script[data-ui-state-preview]`，以便打开浏览器即 hydrate 默认态并可切换。
- `[data-ui-review-panel]` — 必须包含：
  - `dt[data-ui-scope="in_scope"]` / `dd` 列出 must-freeze 产物（节点 id + 标签）；
  - `dt[data-ui-scope="out_of_scope"]` / `dd` 列出上下文 chrome 或 `"none"`；
  - 推断说明：每个 `data-evidence="inferred"` 都要有匹配的 `dt[data-ui-evidence-for]`/`dd`。
- 增量修补：只触碰此次需求实际变更的子树、状态和元数据字段。

一次处理一个帧 — 绝不将所有帧批量塞入单次查询或单次编辑。

### 6. 浏览器审查

在浏览器（或 IDE 渲染预览）中打开契约 HTML。预览脚本必须在不展开审查面板的情况下，将默认态 hydrate 进 `[data-ui-state-host]`：

- 确认 **hydrate 后的默认态**布局匹配 Figma 范围 root（几何 + 内容），而不是空 host 或手写近似。
- 用 `[data-ui-state-switcher]` 逐一切换**每个**已声明状态；每次激活后的 host 内容必须匹配其源帧。
- 展开 `[data-ui-review-panel]`，确认范围清单、每个 `data-figma-node` 与推断说明清晰准确。
- 绝不假设「校验器 OK ⇒ 看起来像 Figma」。

### 7. 运行校验器

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

仅当输出 `OK` 时才继续。失败则修复契约并重新运行 — 绝不在失败的契约上声称 `acceptance_frozen`。校验器 `OK` 是必要非充分条件：冻结前仍需 §1/§6 的 hydrate 预览与需求范围对齐。

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
- 跳过 §1 范围清单，把无关的导航 / 列表 / composer chrome 冻成验收真值。
- 用手写语义化 flex/grid 布局替代 `get_code` 几何的机械转移。
- 把默认态（或任意状态）只放进 `<template>` 并删除/省略 `script[data-ui-state-preview]`，导致浏览器显示空 host。
- 在 hydrate / switcher 未工作时声称已完成浏览器默认态审查。
- 将状态栏、导航栏、键盘或设备外壳建模为 `data-ui-kind` 内容，而不是使用 CSS 安全区处理。
- 使用 `data-evidence="inferred"` 却没有匹配的审查面板说明。
- 扫描每一份历史契约文件来"寻找"某个单元，而不是使用需求 ID、语义或用户显式指定的路径。
- 为一个很小的需求变更重写整份已匹配的契约，而不是做增量修补。
- 未做 hydrate 预览与 scope 对齐，仅凭校验器 `OK` 声称 `acceptance_frozen`/`frozen`/`implemented`/`merged`。
- 不先复制模板就手写 DOM 结构。
