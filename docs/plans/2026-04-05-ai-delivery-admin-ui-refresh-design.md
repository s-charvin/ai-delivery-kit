# AI Delivery Admin UI Refresh Design

## Goal

升级 `ai-delivery-admin` 的 Web 控制台，使其从“基础数据面板 + 原始 textarea 编辑器”提升为适合治理型文档工作的控制台：视觉层级清晰、交互反馈明确、Markdown 内容可直接阅读与预览、关键操作具备更好的 loading / feedback / accessibility 表现。

## Scope

本次改造覆盖：

- `ai-delivery-admin` 的 Web UI 外壳与主要信息架构
- `Artifact Editor` 的 Markdown / JSON 阅读与编辑体验
- 保存、切换、加载等关键交互反馈
- 项目内 `ui-interaction-design` skill 的增强，吸收 `interaction-design` 思路中擅长的微交互、动效、loading、feedback、timing、a11y 方法

本次不覆盖：

- 服务端 API 合约重构
- `.ai-delivery/` 数据结构变更
- 安装或依赖任何外部 skill
- 把业务真相迁移到 `ai-delivery-admin`

## Design Principles

### 1. Content First

控制台的核心工作对象是 Requirement、Figma mapping、interaction design、decisions、traceability 等文档型 artifact。界面设计应优先服务于“读清楚、比对清楚、改得稳”，而不是只服务于 CRUD 表单。

### 2. Feedback Should Be Local And Clear

保存、加载、JSON 解析失败、未保存变更、切换 artifact 等反馈应尽量在用户当前上下文内完成。优先采用局部状态提示、内联警告和非阻断通知，避免无意义的全局打断。

### 3. Loading Should Preserve Orientation

页面或面板加载应优先采用骨架屏、局部 loading、按钮 loading，而不是把整个界面锁死。用户需要知道“哪一块在忙、哪一块还能继续看”。

### 4. Markdown Is A First-Class Surface

绝大多数治理文件是 Markdown，因此编辑器必须支持：

- 源码编辑
- 渲染预览
- 在同一上下文中对照阅读

JSON 文件则保持结构化文本展示和格式化预览，避免误把 JSON 当成 Markdown 渲染。

### 5. Accessibility Is Part Of The Default

键盘可达、焦点可见、语义标签、状态提示、reduced motion 兼容不是附加项，而是默认约束。

## Recommended Stack

- `@mantine/core`
- `@mantine/hooks`
- `@mantine/notifications`
- `@tabler/icons-react`
- `react-markdown`
- `remark-gfm`

说明：

- Mantine 提供适合控制台的 `AppShell`、`Tabs`、`Notifications`、`Skeleton`、`ScrollArea`、表单与反馈组件。
- `react-markdown + remark-gfm` 负责 Markdown 内容渲染。
- 不引入外部 skill，不让 UI 改造依赖用户环境里是否安装第三方 `interaction-design` skill。

## UI Architecture

### Global Shell

采用 Mantine `AppShell` 重建控制台骨架：

- 固定顶部 Header：应用名称、用途说明、当前模式提示
- 固定侧边导航：Dashboard、Requirements、Logs、Blockers、Execution、Runtime、Traceability、Artifacts
- 主内容区：根据当前页面切换内容
- 移动端：侧栏折叠为 Burger + Drawer 交互

### Project Binding Surface

项目绑定区域保留在主内容上方，但从裸表单升级为：

- 更清晰的绑定上下文说明
- 当前已绑定项目的显式状态
- 明确的输入与操作反馈

### Page Presentation

各页面统一采用：

- 页面眉题 + 标题 + 辅助说明
- 卡片式信息分组
- 统一状态 Badge
- 更稳定的间距和排版层级

## Artifact Editor Experience

### Editing Modes

Artifact Editor 采用 Markdown-first 的三态模式：

- `Edit`: 专注编辑源码
- `Split`: 左侧编辑、右侧预览
- `Preview`: 专注阅读渲染结果

Markdown artifact：

- 使用 `react-markdown` 渲染
- 支持 GFM 列表、表格、代码块、引用

JSON artifact：

- 编辑区保持原始文本
- 预览区展示格式化后的 JSON
- 当 JSON 非法时，在预览区给出内联错误提示，并阻止保存

### Interaction Feedback

Artifact Editor 需要新增以下交互契约：

- 保存按钮具备按钮级 loading
- 成功保存后显示局部成功反馈与 toast
- 解析失败时显示内联错误，不只是在提交时报错
- 显示“未保存变更”状态
- 切换 artifact 或 sub-requirement 后重置 dirty state

### Markdown Reading Quality

预览区需要对以下元素做更好的视觉处理：

- 层级标题
- 列表与有序列表
- 引用块
- 表格
- 行内代码与代码块
- 分隔线

## Motion And Timing

动效使用“保守但有用”的原则：

- 页面载入以轻量骨架和短时淡入为主
- Tab、Alert、Notification、Drawer 等使用 Mantine 默认或轻量过渡
- 避免大幅装饰性动画
- 遵循 reduced motion 偏好

## Skill Integration

项目内的 `ui-interaction-design/SKILL.md` 需要显式强化以下内容：

- 交互质量能力内建于项目 skill，不依赖外部安装
- 允许在受限边界内补齐微交互、feedback、loading、timing、a11y
- 强调“轻量反馈优先、局部 loading 优先、功能性动效优先、可恢复优先”
- 将这些原则继续映射到 `Assumption: Micro Interaction` 的记录边界

必要时同步增强：

- `references/interaction-quality-guidelines.md`
- `references/allowed-assumptions.md`
- 项目内校验脚本，让这些要求成为可验证的契约

## Verification Strategy

### Web

- 为 Artifact Editor 增加 Markdown 预览测试
- 为 JSON 非法输入增加内联错误测试
- 为未保存变更提示增加测试
- 更新导航与关键页面测试，确保 Mantine 迁移后角色和文案仍可访问

### Skill

- 扩展项目 skill 校验脚本，要求 `ui-interaction-design` 明确覆盖：
  - `micro-interaction`
  - `loading`
  - `feedback`
  - `timing`
  - `a11y` / `accessibility`
- 再更新 skill 文档与引用文件通过校验

## Expected Outcome

完成后，`ai-delivery-admin` 应具备以下体验改进：

- 整体视觉从“临时工具”提升为“可持续使用的本地控制台”
- 大多数 Markdown artifact 可以直接读、直接预览，不再只能对着原始文本
- 保存、切换、加载、出错等关键动作反馈更清晰
- `ui-interaction-design` 的方法论在项目内自洽存在，不依赖外部 skill 安装状态
