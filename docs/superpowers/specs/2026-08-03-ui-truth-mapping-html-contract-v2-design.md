# UI Truth Mapping：HTML Contract v2

**状态：** 已确认设计，待实施  
**日期：** 2026-08-03  
**范围：** `.agents/skills/ui-truth-mapping` 及其契约门禁、编排消费链路  

## 1. 背景与问题

TemPad Dev 提供的是面向 Agent 的结构化设计事实：`get_code` 输出语义化 markup、布局样式、token 和 asset；`get_structure` 只在层级、几何或重叠存在歧义时补充结构事实。设计师不遵循组件/实例约定时，原始节点树不等于可开发页面结构，仍需要 Agent 在可追溯证据范围内推理出正确的页面、弹窗和共享组件边界。

现有 UI 契约由 `section-map.json` 和 `ui-acceptance-contract.yaml` 组成。YAML 将组件树、四向锚点、布局、样式、内容、状态、交互和实现说明塞入同一递归结构；同时，section-map 与契约重复保存设计源、帧与单元身份。它难以直接审阅布局，也让 Agent 与开发者承担过多格式转换成本。

当前三 pass 的逐帧构建过程能降低 Figma 大树导致的遗漏，但它只是构建过程的增量化，不支持已验收页面的契约复用和局部更新。

## 2. 决策

直接切换到 **HTML Contract v2**：

- 一份 `ui-contract.html` 是唯一、版本化、可编辑的 UI 契约。
- 一份契约只承载一个独立单元：`page`、`modal` 或 `shared-component`。多单元需求在各自目录下创建契约文件。
- 不再产生、读取、迁移或兼容 `ui-acceptance-contract.yaml` 和 `section-map.json`。
- HTML 同时承担可视审阅、结构化实现输入和单元反查，但以受限 schema 管控；它不是自由手写的网页实现。
- 单元信息、需求关系和“已开发后的实现反查”嵌入各自 HTML 的元数据中，不创建独立契约索引。
- 后续开发按需求、组件语义、已有页面关系或用户显式指定定位已有 HTML；不扫描并匹配全部历史契约。

这与 TemPad 的主证据链保持一致：结构化 Figma 事实决定数值，截图只用于项目级后验视觉回归，不能反推 CSS、token 或布局数值。

## 3. 单文件契约结构

每个 `ui-contract.html` 包含四个受限区域：

1. **版本与交付元数据**
   - 使用固定的 `<script type="application/json" id="ui-contract-meta">`。
   - 记录 `schema_version: 2`、契约 ID、来源设计文件、需求/子需求、单元类型、路由或触发条件、Figma 根节点、修订版本和交付状态。
   - 记录唯一的 `page`、`modal` 或 `shared-component` 单元的稳定语义 ID、依赖、关联需求和来源节点。
   - 页面或组件开发完成后，必须记录其实现反查：已交付 UI 类型、代码目标、关联需求、完成版本和状态。这是硬门禁必需元数据。

2. **设计 token 与事实样式**
   - 使用 `<style>` 记录由 TemPad 证实的布局、间距、字体、颜色、边框、效果和资产展示规则。
   - 保留 TemPad 的 canonical CSS custom properties，例如 `var(--token)`；没有安全 token 映射时保留证实的字面值。
   - 不从截图、节点名称或未返回的后代推导样式值。

3. **可渲染语义 DOM**
   - 使用 `<main data-ui-contract>` 作为契约根。
   - 根单元具有 `data-ui-unit-id`、`data-ui-unit-type`；元素具有稳定 `data-ui-id`、组件语义类型、`data-figma-node` 与证据状态。
   - 状态通过受限的状态容器或模板表达；避免旧 YAML 中 `states[]`、`visible_when` 与组件 style diff 三套状态机制并存。
   - 不把系统状态栏、系统导航、软键盘或设备外壳建模为组件。

4. **审查细节层**
   - 默认展示可直接对照 Figma 的布局。
   - 来源节点、状态、推理说明和实现映射置于同一 HTML 的可折叠审查面板中。
   - 此分层让设计/开发先审页面布局，按需查看细节，不形成第二份可编辑真相。

## 4. 发现与增量更新流程

### 4.1 新契约

1. 读取需求切片，明确 UI 范围。
2. 用 TemPad 在父/选区层级枚举候选帧并分类页面、弹窗和共享组件。
3. 对每个独立单元逐帧获取最小必要证据：以 `get_code` 为主，只有层级、几何或重叠歧义时调用 `get_structure`。
4. Agent 在证据范围内归一化不规范 Figma 结构，生成受限 HTML DOM、样式、状态和元数据。
5. 运行 HTML v2 validator；只有输出 `OK` 才能声明 `acceptance_frozen`。

### 4.2 已交付页面的后续需求

1. 从需求拆解、组件语义、已有页面关联或用户直接指定中确定候选单元。
2. 通过 HTML 内嵌元数据检索并只读取命中的契约。Figma node ID 是命中后局部证据和 patch 锚点，而不是跨历史文件的发现主键。
3. 对当前需求涉及的节点和必要子树获取 TemPad 事实。
4. 生成最小 DOM/CSS/状态/元数据 patch，并保留无关单元与无关子树。
5. 对 Figma 结构不规范造成的语义推理，记录来源节点和简短推理说明；不能静默创造视觉事实。
6. 单元边界、路由或共享依赖发生根本变化时才重构该单元。未命中时新建单元；命中歧义时阻塞并要求用户指定。
7. 开发完成后，在同一 HTML 的元数据中写入或更新实现反查信息，再运行门禁。

## 5. Validator 与状态门禁

新增 HTML v2 validator，解析 DOM 和 `ui-contract-meta`，至少校验：

- 文档 schema 版本和唯一契约 ID；
- 每个页面、弹窗、共享组件单元都有类型、稳定 ID、需求关系和来源；
- 每份契约恰有一个独立单元，且声明的依赖可解析；
- `data-ui-id` 唯一且关联的来源节点有效；
- 状态、资产、token、交互和可见性符合受限 schema；
- 不含系统 UI、未声明的设计推理或不受控的自由结构；
- 交付完成时存在实现反查元数据；
- 跨契约依赖能解析，并可导出实现顺序：`shared-component → page → modal`。

`acceptance_frozen` 与后续 merged 状态只能在 validator 打印 `OK` 后成立。视觉回归如启用，应从同一 HTML 元数据读取 Figma node、路由/story、viewport、阈值与 mask，并只输出差异报告。视觉差异不能自动修改契约或代码。

## 6. 技能改造

`ui-truth-mapping` 的工作流改为：

1. 识别新建还是增量更新，并定位目标单元；
2. 收集 TemPad 最小设计证据；
3. 生成新 HTML 或对命中 HTML 应用最小 patch；
4. 在浏览器中审查布局和可折叠证据层；
5. 运行 validator，冻结或报告阻塞；
6. 开发完成后强制回填实现反查。

旧的 YAML 三 pass 字段所有权不再沿用为格式规则，但保留其有效原则：先结构、再布局、后样式/内容；逐帧处理；不跨单元污染；只根据结构化证据填充。

## 7. 实施影响

实施时需要同步更新：

- `.agents/skills/ui-truth-mapping` 及 `.agents-zh` 的中文镜像、模板和 fixtures；
- HTML v2 validator、编辑 hook、交付状态校验与 reconcile 脚本；
- UI Contract Gate（`AGENTS.md`、`.cursor/rules` 等）：从 YAML 文件迁移为 `ui-contract.html`；
- `ai-delivery-orchestrator` Stage 2、Spec Kit 输入和实现阶段的单元依赖消费逻辑；
- bootstrap managed assets；
- 正反 fixture、技能结构测试、交付门禁测试和增量 patch 测试。

## 8. 测试与验收

- HTML schema/DOM validator 的正反 fixture；
- 单元发现、依赖排序和嵌入式元数据检索测试；
- 局部 patch 仅影响命中子树，且保留无关单元；
- 匹配歧义必须阻塞；
- 开发完成但没有实现反查元数据必须失败；
- TemPad shell、depth-cap、token、asset、来源节点与系统 UI 排除回归测试；
- 可选视觉回归的报告字段、确定性与“不得回流为设计数值”测试。

## 9. 非目标

- 不支持 YAML v1 的读取或迁移；
- 不维护 HTML 与任何 YAML/JSON UI 真相源的双写；
- 不从截图、OCR 或像素差推断契约数值；
- 不自动猜测未返回 Figma 节点的结构、状态、响应式行为或交互；
- 不将“实现反查”扩展为第二份实现规范；它仅是同一 HTML 内的已交付关系记录。
