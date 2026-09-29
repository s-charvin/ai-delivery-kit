# 阶段 1：需求拆分

Android View 切片分类前读取 [Android View 适配](framework-adapters/android-view.md)：检查模块/variant、SDK/JDK、语言、架构、资源和测试设施；按功能所有权分类，不以新建文件判断新功能。

## 何时运行

- 自动决策为「拆分」，或任一子需求处于 `draft` 且范围未确定。

## 准备输入

用户提供 Figma 来源时，读取设计证据前执行[提供方选择与配置](../../ui-truth-mapping/references/figma-provider-routing.md)。明确指定优先，否则使用可用者，两者可用默认 TemPad；两者均未安装需询问安装同意，拒绝后停止受影响流程，不能猜测基线。

- 阅读需求文档以及每一份明确提供的补充资料。先检查内容再赋予语义角色；文件名、扩展名、文件夹以及 `draft` / `pending` / `待确认` 这类标签并不能证明来源只是文案、本地化、参考资料，或可以安全省略。
- 输出目录：`.ai-delivery/requirements/<req-id>/`。

## 运行 `requirement-breakdown`

传入需求文档路径和补充来源路径。产出子需求、`requirement-slice.md`、`dependency.json` 及完整产物集。

## 完成后

- 每个子需求：若 source_ref 覆盖完整、有 normalized statements、依赖清晰 → 设 `split_ready`；不确定 → 保持 `draft`。
- 在能力审计中为每个子需求设置 `ui_truth_mode`：使用 `none`、`existing`、`runtime-baseline` 或 `figma`。
- 仅当切片引入或实质改变复杂 guard、并发、过期结果处理、重试/取消/幂等、持久化/恢复或跨组件/页面状态所有权时，设置 `state_flow_required=true`。架构名称和普通 loading/success/failure 阶段本身不触发。
- 当前设计版本包含治理证据无法解决、且决策权属于用户的实质产品、行为、资源或体验选择时，设置 `user_decision_required=true`。用稳定 `D-###` 在 `design.md` 中记录每项决策。当前版本获批后该字段仍保持 `true`，有效的 hash-bound `design_review.review_mode=human` 表示决策已解决。只有当前版本不再包含用户授权决策时才设为 `false`。技术复杂度、框架选择和状态流深度不触发人工门禁。
- 保留 `ui_bearing` 作为一致性字段：仅 `ui_truth_mode=none` 时为 `false`，其他 UI truth 模式为 `true`。
- 初始化 `status.json`：复制 `templates/status-template.json` 的结构，填充 `requirement_id`、子需求条目与状态。保留所有 `_` 前缀元数据键和机器值；其中人类可读的描述值改为用户当前对话语言。
- 依赖图写入 `.ai-delivery/requirements/<req-id>/dependency-graph.json`。

## 轻量审计清单（inline — 不要执行 `solution-design` 动作）

对每个 `split_ready` 子需求，主会话输出四项检查：

1. **缺口** — 是否缺少关键业务事实？
2. **冲突** — 是否与 `global-rules.md` 或其他切片矛盾？
3. **状态** — 各来源是否就可达状态、事件驱动转移、顺序、分支/汇合、loading/error/empty/权限边界、持久化和副作用达成一致？视觉证据尚未提供，并不推迟非视觉流程规则。
4. **权限** — 鉴权边界是否清晰？

审计必须拒绝 `split_ready`：若某份已提供来源包含实质行为，却只按文档标题归类，而没有追溯到切片、全局规则、待解决问题或带理由的明确排除。权威未决的 `pending` 证据记为 `unknown`，不得静默忽略。

结果：

- 严重缺口 → `blocked_missing_requirement`
- 严重冲突 → `blocked_requirement_conflict`
- 无严重问题 → 审计结论写入 `notes`，继续

## 需求冲突与询问

审计、设计、实现和验收都要将技术解释与原始需求及用户决定核对。现有代码
只能说明当前行为，不能覆盖需求要求。涉及可观察行为、业务事实、权限、
数据保留或验收标准的选择，只要来源有歧义或冲突，就属于用户决策。

实现受影响行为前先询问：引用来源位置与需求原文，说明技术限制和不一致点，
列出可行选项及其影响，明确需要用户决定什么。不得静默降低要求、自创默认
行为，或修改测试预期迎合代码。技术事实先调查；业务答案仍不明确就询问。
可安全推进的独立工作继续。

非阻塞问题集中提问；阻塞冲突发现时及时提出。将答复以 D-### 记入 design.md
（设计尚未创建时使用现有决策记录），注明来源与影响范围，同步行为、验收、
状态流及受影响测试。保留原始需求，显式记录批准的偏离。已有答复持续有效，
直到用户修改。批准契约或绑定证据变化时，重新打开适用的评审。

## 跳过路径

跳过拆分时，创建最小单切片包：

```
.ai-delivery/requirements/<req-id>/
├── requirement.md
├── status.json
└── sub-requirements/<subreq-id>/
    └── requirement-slice.md
```

不要创建子需求级 `status.json`。

## 决策边界

来源证据能唯一支持拆分或跳过结果时自动推进。只有不同边界会实质改变范围、
所有权、顺序或验收时才询问用户，并把选择记录为真实用户决策；不得为机械
明确的拆分创建例行审批。
