# 阶段 1：需求拆分

## 何时运行

- 自动决策为「拆分」，或任一子需求处于 `draft` 且范围未确定。

## 准备输入

- 阅读需求文档以及每一份明确提供的补充资料。先检查内容再赋予语义角色；文件名、扩展名、文件夹以及 `draft` / `pending` / `待确认` 这类标签并不能证明来源只是文案、本地化、参考资料，或可以安全省略。
- 输出目录：`.ai-delivery/requirements/<req-id>/`。

## 运行 `requirement-breakdown`

传入需求文档路径和补充来源路径。产出子需求、`requirement-slice.md`、`dependency.json` 及完整产物集。

## 完成后

- 每个子需求：若 source_ref 覆盖完整、有 normalized statements、依赖清晰 → 设 `split_ready`；不确定 → 保持 `draft`。
- 在能力审计中为每个子需求设置 `ui_truth_mode` 与 `design_mode`：`ui_truth_mode` 使用 `none`、`existing`、`runtime-baseline` 或 `figma`；`design_mode` 使用 `none`、`light` 或 `full`。
- 当切片使用 MVI/UDF/Redux/Reducer/Store，跨组件或跨页面共享可变状态，呈现多阶段异步操作状态，需要重试/取消/并发/过期结果/幂等/恢复规则，或存在业务约束的导航与一次性 UI effect 时，设置 `state_flow_required=true`。这会自动要求 `design_mode=full` 和 CP-DESIGN。纯静态页面以及不承载业务规则的局部控件保持 `false`。
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

## 暂停

继续前与用户确认拆分方案（或跳过决策）。
