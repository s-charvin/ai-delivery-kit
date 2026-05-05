---
name: ui-acceptance-contract
description: 当带有 UI 的子需求已拥有受治理的需求和设计映射工件，以及当 API 工件对冻结的屏幕合约产生实质性影响时的 API 工件时使用。必须在交互设计、Spec Kit 或实现之前冻结不可变的 YAML UI 验收真相。
---

# UI 验收合约

项目本地工作流技能，用于将屏幕、状态、组件、布局和视觉风格验收真相冻结到宿主仓库中受治理的 YAML 工件中。

## 概述

在 `ui-requirement-mapping` 之后，当带有 UI 的子需求已拥有需求真相、可信的结构化设计证据，以及当该 API 真相实质性改变可执行屏幕状态合约时的 API 合约真相时，使用此技能。此阶段写入 `ui-acceptance-contract.yaml`，原地更新 `traceability.json.ui_acceptance_contract`，并仅在 YAML UI 真相树真正就绪时将 `status.json` 推进到 `acceptance_frozen`。

`ui-acceptance-contract.yaml` 是唯一规范的 UI 验收真相。不要创建、更新或依赖 Markdown 验收合约工件。旧的 Markdown 验收合约已过时，应移除或替换为 YAML 合约，而不是保留为兼容性输入。

此技能分离两个关注点：

- `figma-mapping.md` 证明需求已绑定到结构化设计证据。
- `ui-acceptance-contract.yaml` 冻结不可变的屏幕状态 UI 真相树，下游的交互设计、Spec Kit、视觉验收和实现必须消费该真相树，且不得重新解释视觉真相。

## 硬边界

- 不得臆造视觉真相。
- 不得臆造业务流程、权限规则、导航或 API 语义。
- 不得将顶级 `SECTION` 用作冻结的可执行帧目标。
- 当 `get_code` 仍然缺失时，不得将 `get_structure` 视为足够的屏幕状态真相。
- 不得覆盖 `figma-mapping.md`、`api-contract-mapping.md` 或 `interaction-design.md`。
- 不得用 sidecar 笔记或第二个桥接工件替换 `traceability.json`。
- 不得在 `ui-acceptance-contract.yaml` 之外创建第二个 UI 验收源。
- 不得手动编辑阻止状态使其看起来已恢复。
- 不得在没有明确的壳组合真相的情况下，在更大的路由壳内冻结子载体。
- 当基于源的证据已证明该载体内部存在多个可见块、通道、簇、行、槽或 CTA 分组时，不得接受 `children: []`。
- 当存在可见的基于源的文本或资源时，不得将 `typography`、`icon` 或 `image` 留空。
- 如果所需的屏幕状态、可执行帧、组件树分支、布局、视觉样式、图标资源或其他 1:1 影响的 UI 真相无法得到可信证据支持，则停止并阻止，而不是将不确定的真相推向下游。

## 此技能适用于

- 为带有 UI 的子需求冻结不可变的屏幕状态验收真相。
- 写入 `ui-acceptance-contract.yaml`。
- 更新 `traceability.json.ui_acceptance_contract`。
- 当 YAML 合约有源可溯时，将带有 UI 的子需求移至 `acceptance_frozen`。
- 在交互设计、Spec Kit、TDD 或实现之前记录 1:1 视觉阻止器。
- 冻结组件树、布局、盒模型、组件类型、排版、图标、图像、状态和实现映射真相。

## 请勿将此技能用于

- 需求拆分。
- API 合约发现。
- Figma 证据发现。
- 交互设计。
- Spec Kit 生成。
- 通过猜测实现的代码或视觉调整。

## 必需参考

- [双重真相规则](references/dual-truth-rules.md)
- [阻止器目录](references/blocker-catalog.md)
- [日志检查清单](references/logging-checklist.md)
- [UI 验收合约模板](templates/ui-acceptance-contract-template.yaml)

同时匹配已在 `.ai-delivery/requirements/` 下建立的受治理工件形状，而不是臆造一个并行的验收存储。

## 输入

### 必需输入

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`
- 每个最终可执行屏幕状态的可信 `get_code` 证据

### 预期的辅助输入

- 当动作语义已存在且对冻结的屏幕合约产生实质性影响时的 `api-contract-mapping.md`
- 来自 Figma、Tempad 或兼容的结构化设计提供者的令牌工件
- 当设计需要特殊 UI 提供的资源时，已下载的图像或图标资源
- 当首选实现组件已被命名或已建立时的现有代码组件属性
- `traceability.json`
- `status.json`
- `decisions.md`

### 缺失输入处理

如果源或工件缺失：

- 如果 `requirement-slice.md` 缺失或不足以安全消费，则停止并将工作交回给 `requirement-breakdown`。
- 如果 `figma-mapping.md` 缺失或没有可信的结构化证据支持，则停止并将工作交回给 `ui-requirement-mapping`。
- 如果任何必需的最终屏幕状态缺少可信的 `get_code` 证据，则阻止在 `blocked_verification_failure`。
- 如果关键的 1:1 视觉真相缺口仍未解决，则阻止在 `blocked_missing_design`。
- 如果需求真相和 Figma 真相在可执行屏幕合约内冲突，则阻止在 `blocked_requirement_figma_conflict`。
- 如果 API 真相不完整但不会改变冻结的屏幕状态合约，则将该缺口保留供后续的交互或集成工作处理，而不是仅因 API 完整性而阻止验收。
- 如果证据或间距语义提到 2 个以上可见块/通道/簇/行，则禁止使用 `children: []`。获取后代或阻止验收。
- 如果存在 `parent_shell_node_id`，则需要 `parent_shell_contract_ref` 和 `mount_path`。
- 如果存在可见文本，则 `typography` 不能为空。如果存在可见图标/图像，则 `icon/image` 不能为空。否则阻止。
- 如果一个分区只是更大路由壳内的一个拥有的子树，则合约必须包含 `composed_screen_context`，而不仅仅是附属/共享说明文字。
- 如果源证明同一选择中其他地方存在完整页面壳，则当前子需求必须显式链接到该冻结的壳合约；仅标注 `governed by SR-xxx` 不够。
- 如果需要特殊的 UI 提供图标且该图标可从 MCP 或其他可信的结构化提供者下载，则下载并在 YAML 合约中引用该资源。
- 如果需要特殊的 UI 提供图标但无法下载或无法基于源支持，则阻止验收，直到用户提供该图标资源或可检索的设计源。
- 如果旧文件夹中缺少 `traceability.json`，则仅修复受治理的合约并在 `decisions.md` 中记录该修复。

## 输出目标

生成下游阶段可直接消费而无需重新解释视觉真相的验收包。输出必须保留：

- 有源可溯的 `ui-acceptance-contract.yaml`
- 更新后的 `traceability.json.ui_acceptance_contract` 子树，其路径指向 YAML 文件
- 现有的非验收可追溯性字段，如 `requirement_refs`、`api_contract_mapping`、`figma_nodes` 和 `spec_kit_refs`
- 显式的 `screen_states`、嵌套的 `component_tree`、`verification_targets`、`unresolved_ui_truth` 以及冻结的屏幕状态边界
- 当拥有的子树挂载到更大的路由壳内时的显式父壳链接和组合屏幕上下文

## 默认输出路径

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── ui-acceptance-contract.yaml
├── traceability.json
├── status.json
└── decisions.md
```

## 规范 YAML 形状

合约是以 `screen_states` 为根的树。每个屏幕状态拥有一个 `component_tree`，每个组件节点携带原地实现和验证所需的 UI 真相。

必需的顶级键：

- `version`
- `updated_at`
- `updated_by`
- `contract`
- `spacing_policy`
- `tree_extraction`
- `screen_states`
- `verification_targets`
- `unresolved_ui_truth`

必需的 `contract` 键：

- `id`
- `status`
- `source_requirements`
- `source_design`
- `api_dependency`

每个 `screen_states[*].component_tree` 节点应包含适用于该组件的字段：

- `component_id`
- `node_id`
- `component_type`
- `role`
- `required`
- `layout`
- `box_model`
- `size`
- `component_props`
- `visual_style`
- `content`
- `typography`
- `icon`
- `image`
- `states`
- `implementation_mapping`
- `source_refs`
- `blocking_unknowns`
- `extraction`
- `children`

将相关真相置于其所治理的节点旁边。不要将必需元素、布局约束、排版和组件属性拆分成下游读者必须在脑中合并的独立表格。

当屏幕状态挂载到更大的路由壳内时，`screen_states[*]` 还必须包含：

- `parent_shell_contract_ref`
- `mount_path`
- `composed_screen_context`

## 组件树提取工作流

复杂的 Figma、Tempad 或提供者节点必须使用源树优先的提取工作流进行转换。目标不是生成更漂亮的实现树；而是保留每一个影响 1:1 渲染、布局所有权、点击目标、状态样式或资源交付的节点边界。

### 1. 收集完整的结构证据

- 从 `figma-mapping.md` 命名的可执行帧节点开始。
- 读取可执行帧的最终状态 `get_code` 证据。
- 使用 `get_structure` 或等效的提供者结构输出来检查原始节点层级结构、几何形状、子节点顺序和自动布局提示。
- 如果提供者输出警告深度上限、壳省略、子节点省略、分离实例边界或缺失矢量资源，则在冻结验收之前获取省略的子节点。
- 如果所需的后代无法获取且其缺失可能影响 1:1 实现，则记录带有 `blocks: acceptance_frozen` 的 `unresolved_ui_truth`。

### 2. 在塑造合约之前对原始源节点进行分类

对于每个有意义的源节点，在决定其是否作为组件节点出现之前，将其分类为以下角色之一：

- `semantic-component`：屏幕、分区、表单、卡片、列表、行、按钮、输入、标签页、模态框或用户可识别的其他单元。
- `layout-wrapper`：拥有自动布局、堆叠方向、网格行为、绝对定位上下文、滚动区域、间距、换行、对齐或约束。
- `visual-wrapper`：拥有背景、边框、圆角、阴影、模糊、透明度、裁剪、遮罩、高度或状态样式。
- `hit-target-wrapper`：拥有可点击/可点击边界、聚焦环、悬停/按压区域、禁用行为或手势表面。
- `content-leaf`：文本、富文本跨度组、值标签、徽章标签或其他承载内容的节点。
- `asset-leaf`：图像、图标、头像、徽标、矢量、插图或提供者下载的资源。
- `decoration-only`：不拥有语义内容但仍可能需要保留（如果影响 1:1 像素）的视觉装饰。
- `implementation-noise`：不拥有任何视觉、布局、语义、点击目标、溢出、状态或资源真相的源包装器。

在分类完成之前，不要折叠节点。分类应记录在节点本地的 `extraction.wrapper_role` 或顶级 `tree_extraction.audit.notes` 中。

### 3. 除非证明折叠安全，否则保留包装器

使用 `tree_extraction.wrapper_retention_policy` 来治理该决定。

当源包装器拥有以下任何一项时，将其保留为组件节点：

- 自动布局或布局模式
- 轴、对齐、间距、换行或子节点排序
- 内边距、外边距、间距所有权或约束
- 裁剪、遮罩、溢出、滚动或视口行为
- 背景、填充、渐变、边框、圆角、阴影、模糊、透明度或高度
- 固定尺寸、最小/最大尺寸、宽高比、响应式行为或绝对定位
- z 顺序、叠加关系、固定/粘性行为或影响像素的图层堆叠
- 组件变体、状态样式、禁用/加载/错误/选中处理或令牌模式
- 点击目标、聚焦面、悬停/按压面、手势边界或无障碍角色
- 图像、图标、矢量、已下载资源或资源遮罩边界
- 列表、网格、信息流、菜单或分组行的重复项边界

仅在以下所有条件都满足时才折叠源节点：

- 它不拥有任何独立的视觉、布局、语义、交互、状态、溢出或资源真相。
- 移除它不会改变父/子间距、对齐、裁剪、尺寸或堆叠。
- 其子节点可在不丢失源支持的排序或角色的情况下重新挂载。
- 折叠决策记录在 `collapsed_source_node_ids` 中，并附有具体的 `collapse_reason`。

不要仅因为实现会更短、源树看起来很深或代码组件通常在内部隐藏该包装器就折叠包装器。便利性不是证据。

### 4. 有意识地构建验收组件树

- 保持树以可执行屏幕状态为根。
- 为自动布局和正常流保留源子节点顺序。
- 对于绝对或叠加布局，保留视觉堆叠并记录 `layout.positioning`、`layout.constraints` 和 z 顺序备注。
- 对于重复列表或网格，冻结列表/容器节点加上项组件模式；包括代表性源节点 ID 和列表特定属性，如分割线、项间距、空状态和滚动行为。
- 对于文本组，当排版、颜色、最大行数、溢出、运行时源或语义角色不同时，保留独立的文本节点。
- 对于图标或矢量，当它们影响布局、间距、颜色、语义角色或必须下载时，保留资源叶子节点。
- 对于纯装饰节点，当它们影响 1:1 像素时保留；如果折叠到 `visual_style` 中，记录折叠的源 ID 和原因。

### 5. 审计提取

YAML 必须包含顶级 `tree_extraction`：

```yaml
tree_extraction:
  source_node_id: "<executable-frame-node-id>"
  extraction_mode: "source-tree-first"
  evidence_artifacts: []
  wrapper_retention_policy:
    block_on_unfetched_descendants: true
    preserve_when: []
    collapse_allowed_when: []
  audit:
    source_nodes_reviewed: []
    preserved_source_node_ids: []
    collapsed_source_node_ids: []
    blocked_source_node_ids: []
    notes: []
```

每个组件节点应包含节点本地的 `extraction`：

```yaml
extraction:
  source_node_type: "<FRAME|INSTANCE|GROUP|TEXT|VECTOR|RECTANGLE|IMAGE|COMPONENT|unknown>"
  source_node_name: "<source node name>"
  wrapper_role: "<semantic-component|layout-wrapper|visual-wrapper|hit-target-wrapper|content-leaf|asset-leaf|decoration-only|implementation-noise>"
  retained_from_source_node_ids: []
  collapsed_source_node_ids: []
  retention_reason: "<why this boundary remains in the component tree>"
  collapse_reason: null
  extraction_confidence: "<high|medium|blocked>"
```

如果任何必需组件或后代的提取置信度为 `blocked`，则不要推进到 `acceptance_frozen`。

## 组件树合约

冻结每个最终屏幕状态的 UI 层级结构为嵌套树。

- 每个状态的根是 `screen_states[*].component_tree`。
- 每个组件节点必须指定其 `component_id`、`node_id`、`component_type`、`role`、`required` 和 `children`。
- `children` 必须保留基于源的视觉层级结构和顺序。
- 父、伴生和共享的 UI 关系可以使用节点本地的 `source_refs`、`role` 或 `implementation_mapping` 来表示，但验收真相仍必须从树本身可读。
- 使用稳定的、对实现友好的 `component_id` 值，但不要让编造的 ID 替换源的 `node_id`。
- 使用 `tree_extraction` 加上节点本地的 `extraction` 来证明复杂的源节点是如何保留、折叠或阻止的。
- 如果证据或间距语义提到 2 个以上可见块/通道/簇/行，则禁止使用 `children: []`。获取后代或阻止验收。
- 如果存在 `parent_shell_node_id`，则需要 `parent_shell_contract_ref` 和 `mount_path`。
- 如果一个分区只是更大路由壳内的一个拥有的子树，则合约必须包含 `composed_screen_context`，而不仅仅是附属/共享说明文字。
- 如果源证明同一选择中其他地方存在完整页面壳，则当前子需求必须显式链接到该冻结的壳合约；仅标注 `governed by SR-xxx` 不够。

组件类型词汇表应足够具体以指导实现：

- `screen`
- `container`
- `card`
- `list`
- `list-item`
- `form`
- `text`
- `text-input`
- `button`
- `image`
- `icon`
- `tab`
- `navigation`
- `divider`
- `badge`
- `modal`
- `sheet`
- `toast`
- `custom`

如果列出的类型都不合适，使用 `custom` 并在 `component_props.custom` 中解释基于源的原因。

## 布局合约

每个非平凡的组件必须冻结布局行为，而不仅仅是视觉顺序。

在 `layout` 下记录适用的字段：

- `mode`：`vertical-stack`、`horizontal-stack`、`grid`、`absolute`、`overlay`、`list`、`leaf` 或其他基于源的模式。
- `primary_axis`
- `cross_axis_alignment`
- `main_axis_alignment`
- `gap`
- `wrap`
- `positioning`
- `constraints`

在 `size` 下记录适用的字段：

- `width`
- `height`
- `width_behavior`
- `height_behavior`
- `min_width`
- `max_width`
- `min_height`
- `max_height`
- `aspect_ratio`

如果自动布局、弹性布局、网格或绝对定位可能产生视觉上相似的结果，选择最匹配源证据和组件职责的模式。在 `layout.notes` 或 `box_model.spacing_semantics` 中记录该决策。

## 盒模型与间距策略

YAML 必须包含顶级 `spacing_policy`：

```yaml
spacing_policy:
  padding: "用于容器内部呼吸空间。"
  gap: "用于父布局拥有的兄弟间距。"
  margin: "仅在父布局无法拥有间距时用于外部放置。"
  equivalent_visuals_rule: "如果 padding 和 margin 可产生相同的视觉结果，选择最能匹配组件职责的语义拥有者并记录该决策。"
```

每个影响布局的组件节点必须包含 `box_model`：

- `padding.top`
- `padding.right`
- `padding.bottom`
- `padding.left`
- `margin.top`
- `margin.right`
- `margin.bottom`
- `margin.left`
- `spacing_semantics`

间距所有权规则：

- 容器内部呼吸空间应为 `padding`。
- 兄弟间距应为父拥有的 `gap`。
- 仅在父布局无法拥有间距时，外部放置才使用 `margin`。
- 不要仅仅因为 padding、margin 和 gap 产生相同的像素就互换使用。
- 如果源证据仅提供视觉距离，合约必须选择并记录推荐的实现语义。

## 组件属性合约

在 `component_props` 下冻结组件特定属性。使用来自 `figma-mapping.md`、最终状态 `get_code`、设计令牌、已下载资源和现有代码组件属性的源证据。不要臆造缺失的组件行为。

按类型的常见字段：

- `button`：`variant`、`size`、`height`、`min_width`、`radius`、`state_coverage`、`background`、`content_complexity`。
- `text`：`font_family`、`font_size`、`font_weight`、`line_height`、`color_token`、`max_lines`、`overflow`、`text_source`。
- `list`：`item_component`、`item_spacing`、`divider`、`empty_state_component`、`scroll_behavior`。
- `image`：`aspect_ratio`、`fit`、`fallback`、`mask`、`loading_state`。
- `icon`：`size`、`stroke_width`、`color_token`、`semantic_role`、`asset_ref`、`download_status`。
- `card` 或 `container`：`background`、`radius`、`border`、`shadow`、`padding`、`layout_mode`。
- `text-input`：`variant`、`height`、`placeholder_source`、`value_source`、`disabled_state`、`validation_surface`。

当项目代码组件是首选实现目标时，在 `implementation_mapping` 下记录 `preferred_component`、`allowed_substitution` 和 `prop_mapping`。

## 文本、图标、图像和状态规则

使用节点本地字段，使每个组件的合约无需跨表查找即可阅读。

文本真相：

- 记录 `content.text_source`、`content.text_value`（当有源可溯时）、`content.max_lines` 和 `content.overflow`。
- 记录 `typography.font_family`、`font_size`、`font_weight`、`line_height` 和 `color_token`。
- 如果文本是运行时提供的，记录运行时源，并仍冻结最大行数和溢出行为。
- 如果存在可见文本，则 `typography` 不能为空。否则阻止。

图标真相：

- 尽可能使用已下载的 MCP 或结构化提供者资源作为特殊的 UI 提供图标。
- 记录 `icon.asset_ref`、`icon.asset_source`、`icon.download_status`、`icon.size`、`icon.color_token` 和 `icon.semantic_role`。
- 如果设计需要特殊图标且无法下载或验证任何资源，添加一个阻止项目 `unresolved_ui_truth`，带有 `blocks: acceptance_frozen`。
- 通用系统图标仅在源设计明确映射到该组件且不需要特殊资源时，才可使用现有设计系统组件。
- 如果存在可见图标/图像，则 `icon/image` 不能为空。否则阻止。

图像真相：

- 记录 `image.asset_ref`、`image.aspect_ratio`、`image.fit`、`image.mask`、`image.fallback` 和 `image.loading_state`（如适用）。
- 除非源显式将其定义为占位状态，否则不要用占位图像替换验收真相。

状态真相：

- 记录 `states.required_states` 用于可见组件状态，如 `default`、`disabled`、`loading`、`pressed`、`error`、`empty` 或 `selected`。
- 记录 `states.state_style_refs` 用于基于源的视觉状态证据。
- 如果必需状态缺少结构化视觉证据，则记录阻止未知项，而不是臆造样式。

## 视觉令牌和源合约

每个影响 1:1 的样式值应是可追溯的：

- Figma 或 Tempad 令牌
- 最终状态 `get_code`
- 已下载资源
- 设计系统令牌
- 现有代码组件属性
- 显式的未解决阻止器

在最小有用范围内使用 `source_refs`。对于组件级别的值，将引用放在组件上。对于属性级别的值，将引用放在 `visual_style`、`typography`、`icon`、`image` 或 `component_props` 下。

当源需要精确的 UI 真相时，不允许使用后备令牌，除非合约显式记录 `fallback_allowed: true` 以及该后备不影响 1:1 验收的原因。

## 未解决的 UI 真相

`unresolved_ui_truth` 用于阻止或明确限定的 UI 未知项。它不能成为软笔记桶。

每个未解决项应包括：

- `unknown`
- `affected_component`
- `impact`
- `resolution_path`
- `blocks`

当缺失的真相影响 1:1 实现或验证时，设置 `blocks: acceptance_frozen`。示例：

- 必需组件缺少最终状态 `get_code`。
- 组件层级结构或布局模式不明确。
- 内边距、外边距或间距所有权无法确定且影响实现语义。
- 必需的排版、令牌、视觉样式、图像或特殊图标资源缺失。
- 必需组件状态缺少结构化视觉证据。
- 需求和设计在冻结的屏幕合约内冲突。

如果 API 缺口不改变可见的屏幕状态合约，则不要仅因 API 完整性就阻止验收。在 `contract.api_dependency` 中记录 API 依赖，并将动作集成留待后续受治理的阶段。

## 工作流

### 1. 确认上游合约

- 在起草 YAML 验收合约之前，阅读 `requirement-slice.md`、`api-contract-mapping.md`（当存在且影响屏幕状态含义时）、`figma-mapping.md`、`traceability.json`、`status.json` 和 `decisions.md`。
- 优先从 `figma_mapped` 开始。
- 确认子需求是带有 UI 的，并且下游执行仍然依赖于 1:1 视觉真相。

### 2. 清点可执行屏幕状态

- 读取上游已建立的可执行状态证据。
- 每个最终屏幕状态需要可信的可执行帧节点。
- 在冻结合约之前，每个最终屏幕状态需要可信的 `get_code` 证据。
- 记录冻结的状态 ID、父壳、父壳合约引用、挂载路径、组合屏幕上下文、必需的层级结构、组件树根和验证目标。

### 3. 提取和审计组件树

- 在编写验收树之前遍历源设计层级结构。
- 将原始节点分类为语义组件、布局包装器、视觉包装器、点击目标包装器、内容叶子节点、资源叶子节点、纯装饰节点或实现噪音。
- 保留每个拥有 1:1 影响的布局、视觉、状态、点击目标、溢出、资源或响应式真相的包装器。
- 仅折叠经过证明安全的实现噪音节点，并在 `tree_extraction.audit.collapsed_source_node_ids` 和节点本地的 `extraction.collapsed_source_node_ids` 中记录每个折叠的源 ID。
- 将 `tree_extraction.wrapper_retention_policy.block_on_unfetched_descendants` 设置为 `true`；如果所需的后代被省略或受深度上限限制且无法获取，则阻止而不是近似组件树。
- 如果证据或间距语义提到 2 个以上可见块/通道/簇/行，则禁止使用 `children: []`。获取后代或阻止验收。

### 4. 冻结 YAML UI 真相树

- 使用 `templates/ui-acceptance-contract-template.yaml`。
- 将 `screen_states[*].component_tree` 写为主要工件形状。
- 冻结组件标识、层级结构、布局、盒模型、间距语义、尺寸行为、组件类型、组件属性、排版、视觉令牌、内容、图标、图像、状态、实现映射和源引用。
- 将每个影响 1:1 的未知项视为已解决或已阻止。
- 不要让视觉未知项退化为软笔记。

### 5. 保守更新可追溯性和状态

- 仅更新 `traceability.json.ui_acceptance_contract`。
- 将 `traceability.json.ui_acceptance_contract.path` 设置为 `ui-acceptance-contract.yaml`。
- 保留 `api_contract_mapping`、`figma_nodes`、`spec_kit_refs` 和其他非验收字段。
- 仅当每个冻结的页面状态合约有源可溯且剩余未知项不影响 1:1 交付时，才将 `status.json` 推进到 `acceptance_frozen`。
- 仅在可用时使用单独的管理支持界面进行受治理的日志记录、阻止器处理和状态转换。

### 6. 交接前重新审计

- 重新打开 `figma-mapping.md`、`ui-acceptance-contract.yaml`、`traceability.json` 和 `status.json`。
- 验证每个冻结的屏幕状态都有最终的可执行证据和 `verification_targets`。
- 验证每个组件节点在其职责级别拥有足够的基于源的 1:1 实现真相。
- 验证每个保留或折叠的源节点可通过 `tree_extraction` 或节点本地的 `extraction` 解释。
- 验证没有视觉真相被猜测或转移进交互设计。

## 状态和阻止器规则

- 如果必需的最终屏幕状态没有可信的可执行证据，则阻止在 `blocked_verification_failure`。
- 如果必需的视觉载体缺失，则阻止在 `blocked_missing_design`。
- 如果需求、API 和视觉真相以改变可执行屏幕合约的方式冲突，则阻止在最精确匹配的阻止器并止步于 `acceptance_frozen` 之前。
- 如果必需的特殊 UI 提供图标无法从 MCP 或其他可信提供者下载且用户未提供，则阻止在 `blocked_missing_design` 或最精确可用的视觉证据阻止器。
- 如果所需的后代因深度上限、壳截断或提供者获取失败而省略且可能影响 1:1 布局或样式，则阻止而不是近似组件树。
- 如果存在 `parent_shell_node_id` 但缺少 `parent_shell_contract_ref`、`mount_path` 或 `composed_screen_context`，则阻止在 `blocked_missing_visual_truth`。
- 如果存在可见文本但 `typography` 为空，或存在可见图标/图像但 `icon` 或 `image` 为空，则阻止在 `blocked_missing_visual_truth`。
- 不要仅因为后续的动作语义或服务器副作用仍未完成就阻止验收，如果这些缺口不改变冻结的屏幕状态合约的话。
- 仅当 YAML 合约完全有源可溯且对下游消费安全时，才将子需求移至 `acceptance_frozen`。

## 硬约束

- 在编写验收合约之前读取上游受治理工件。
- 将工作流真相保留在 `.ai-delivery/` 中。
- 不要替换 `traceability.json`。
- 不要生成 Markdown 验收合约。
- 不要将影响 1:1 的未知项软化为非阻止性说明文字。
- 在 `acceptance_frozen` 之前，不允许下游规范、计划、任务或实现继续进行。

## 输出标准

每个 YAML 验收合约必须定义：

- `contract` 元数据和源依赖关系
- 顶级 `spacing_policy`
- 带有包装器保留策略的顶级 `tree_extraction` 审计
- 冻结的 `screen_states`
- 每个最终屏幕状态的嵌套 `component_tree`
- 更大路由壳内子载体的显式 `parent_shell_contract_ref`、`mount_path` 和 `composed_screen_context`
- 保留或折叠的源节点的节点本地 `extraction` 证据
- 组件标识、类型、角色、层级结构和必要性
- 布局模式、轴、对齐、间距、定位、换行和约束
- 盒模型内边距、外边距、间距所有权和间距语义
- 尺寸行为和关键尺寸
- 组件特定属性
- 排版、内容、溢出、图标、图像和状态规则（如适用）
- 首选代码组件的实现映射（当有源可溯时）
- 影响 1:1 的值的源引用
- `verification_targets`
- `unresolved_ui_truth`

如果单独的管理支持界面不可用，则将工件真相保留在 `.ai-delivery/` 中并在本地记录缺失的受治理依赖，而不臆造另一个真相存储。

## 自查清单

在报告完成之前，确认所有以下内容：

- [ ] 起草前已阅读 `requirement-slice.md` 和 `figma-mapping.md`
- [ ] 每个冻结的屏幕状态都有可信的可执行证据
- [ ] 每个关键屏幕状态都有 `get_code` 证据
- [ ] 已写入 `ui-acceptance-contract.yaml`
- [ ] 没有 Markdown 验收合约作为并行验收真相保留
- [ ] `traceability.json.ui_acceptance_contract` 已更新且未覆盖其他字段
- [ ] 仅当 YAML 合约有源可溯时，`status.json` 才移至 `acceptance_frozen`
- [ ] `screen_states[*].component_tree` 携带层级结构、布局、盒模型、组件类型和关键样式真相
- [ ] 更大路由壳内的任何子载体包含 `parent_shell_contract_ref`、`mount_path` 和 `composed_screen_context`
- [ ] 没有具有源支持的多块结构的载体被冻结为 `children: []`
- [ ] `tree_extraction` 记录已审查、保留、折叠和阻止的源节点
- [ ] 每个折叠的包装器都有 `collapsed_source_node_ids` 和基于源的折叠原因
- [ ] 因深度上限或壳省略而隐藏的所需后代已被获取或阻止
- [ ] `spacing_policy` 和节点级别的 `box_model.spacing_semantics` 使内边距、外边距和间距所有权显式化
- [ ] 可见文本永远不会随空的 `typography` 提交，可见图标/图像永远不会随空的 `icon` 或 `image` 提交
- [ ] 特殊的 UI 提供图标已下载并引用，或阻止直至提供
- [ ] `verification_targets` 是显式的
- [ ] 没有影响 1:1 的未知项被静默地作为软笔记留下

## 交接

在生成 `ui-acceptance-contract.yaml`、更新 `traceability.json.ui_acceptance_contract` 并将子需求移至 `acceptance_frozen` 或阻止状态后停止。

如果用户想要继续，传递下游阶段 `requirement-slice.md`、`api-contract-mapping.md`（当存在时）、`figma-mapping.md`、`ui-acceptance-contract.yaml`、`traceability.json` 和 `decisions.md`。除非用户显式要求下一阶段，否则不要在此技能内执行交互设计、Spec Kit 生成或实现。
