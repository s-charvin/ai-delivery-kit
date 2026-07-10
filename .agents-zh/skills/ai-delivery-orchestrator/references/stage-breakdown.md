# 阶段 1：需求拆分

## 何时运行

- 自动决策为「拆分」，或任一子需求处于 `draft` 且范围未确定。

## 准备输入

- 阅读需求文档。
- 输出目录：`.ai-delivery/requirements/<req-id>/`。

## 运行 `requirement-breakdown`

传入需求文档路径。产出子需求、`requirement-slice.md`、`dependency.json` 及完整产物集。

## 完成后

- 每个子需求：若 source_ref 覆盖完整、有 normalized statements、依赖清晰 → 设 `split_ready`；不确定 → 保持 `draft`。
- 为每个子需求设置 `ui_bearing`：拥有页面/屏幕状态 → `true`；纯基础设施或无 UI → `false`。
- 初始化 `status.json`：逐字复制 `templates/status-template.json`，填充 `requirement_id`、子需求条目与状态。保留所有 `_` 前缀元数据键。
- 依赖图写入 `.ai-delivery/requirements/<req-id>/dependency-graph.json`。

## 轻量审计清单（inline — 不要 invoke brainstorming）

对每个 `split_ready` 子需求，主会话输出四项检查：

1. **缺口** — 是否缺少关键业务事实？
2. **冲突** — 是否与 `global-rules.md` 或其他切片矛盾？
3. **状态** — 是否缺少 error/empty/loading/权限边界？
4. **权限** — 鉴权边界是否清晰？

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
