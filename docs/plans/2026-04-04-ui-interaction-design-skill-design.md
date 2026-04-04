# UI Interaction Design Skill Design

## Skill Name

- `ui-interaction-design`

## Goal

将 Figma 注释、视觉状态、原型线索与 Requirement 结合，转换为开发可直接消费的交互契约，减少后续实现阶段的脑补风险。

## Position In The Workflow

该 skill 位于：

- `ui-requirement-mapping` 之后
- `Spec Kit Phase` 之前

## Inputs

必需输入：

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`

可选输入：

- Figma 注释
- 原型连线
- 历史交互规范
- 现有组件行为约束

## Responsibilities

- 提取已有交互注释、状态切换与动效线索
- 将 Requirement 与视觉证据结合成可执行交互契约
- 输出 `interaction-design.md`
- 对缺失交互做受限补全
- 识别必须人工确认的问题并阻塞或升级

## Non-Responsibilities

- 不发明新业务流程
- 不新增未被 Requirement 或 Figma 支撑的状态机
- 不重做页面结构
- 不为了“更友好”而改变原有产品语义

## Output Files

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── interaction-design.md
├── decisions.md
└── status.json
```

## Suggested Structure Of `interaction-design.md`

- 交互目标
- 入口条件
- 用户动作
- 系统反馈
- 成功态
- 空态
- 加载态
- 错误态
- 禁用态
- 权限与可见性影响
- 页面间跳转或局部状态切换
- 动效与过渡
- 未决问题与升级项

## Restricted Completion Boundary

### Allowed

允许补全：

- 按钮 loading 表现
- hover / active / focus 规则
- toast 与 inline error 的优先级
- 空列表基础反馈
- 表单校验触发时机
- 禁用态不可点击
- 提交中避免重复提交
- 基础键盘可达性

### Not Allowed

不允许补全：

- 新增业务分支
- 新增字段、步骤、弹窗、确认流程
- 新增权限规则
- 新增页面切换关系
- 新增 Requirement 未提及的异常业务语义

## Blocking Rules

- Requirement 有业务动作，但 Figma 无法承载且不能从现有模式继承：`blocked_missing_design`
- Figma 有显式交互状态，但 Requirement 冲突：`blocked_requirement_figma_conflict`
- 关键交互需要决定业务语义但现有材料无法支持：`blocked_missing_requirement`
- 仅缺少微交互细节：不阻塞，记录为 `assumed_micro_interaction`

## Documentation Rules

所有补全项都必须显式标记，不能伪装为原始事实。

建议记录格式：

- `Source: Figma`
- `Source: Requirement`
- `Source: Existing Pattern`
- `Assumption: Micro Interaction`

## References And Dependencies

依赖：

- `ui-requirement-mapping`

参考：

- Figma 相关 skill 的结构化取证方式
- `brainstorming` 的“先澄清再定稿”原则

但本 skill 不重新进入产品探索阶段，只做最小必要的交互契约收敛。

## Completion Criteria

完成时必须满足：

- 开发者仅凭 `interaction-design.md` 即可明确主要交互行为
- 所有关键状态都有定义
- 所有补全项都被显式记录
- 所有超出允许边界的问题都已阻塞或升级
- 子需求状态可推进到 `interaction_ready`
