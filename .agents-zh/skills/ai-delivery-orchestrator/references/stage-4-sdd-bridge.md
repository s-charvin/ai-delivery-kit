# Stage 4：实现桥接

把 `implement` 映射为有边界的执行与 `.ai-delivery` 进度证据。

## 何时执行

当 reconcile 为依赖就绪的 `design_ready` 或 `in_dev` 切片输出
`NEXT_ACTION=implement` 时执行。当前 hash 绑定设计评审即为批准范围内的
开发授权，不存在第二个开发 checkpoint。

`figma` / `runtime-baseline` 复用 Stage 2 的准确 workspace；其他模式默认
使用当前 checkout。

## 从设计契约形成执行 brief

| 来源 | 执行用途 |
|------|----------|
| `design.md` 范围与 `B-###` | 行为边界和当前目标 |
| `AC-###` 与追踪 | TDD 与验收条件 |
| 依赖图和项目架构 | 安全顺序和编辑所有权 |
| 当前代码与测试 | 具体文件和验证命令 |
| UI truth scenario | 视觉、交互、动效、资源与运行时证据 |
| 可选 `progress.md` | 已完成、待完成、阻塞和最近验证结果 |

brief 是临时执行上下文，不是新治理产物。不得持久化 `spec.md`、`plan.md`
或 `tasks.md`，也不得把文件级步骤复制进 `design.md`。

每个最小执行单元都必须经过 TDD 和新鲜上下文评审。可复用问题先更新
`retrospective.md` 并报告 `RET-###`。

## 可选进度记录

仅在需要跨会话恢复时使用需求级 `progress.md`，简洁记录：

- 已完成工作及关联行为/验收 ID；
- 待完成工作；
- blocker 及范围；
- 验证命令、结果与评审结论。

它不是第二份计划，也不能提升 gate。

## 评审与验收

执行闭环：实现 → 新鲜上下文评审 → 修复 → 重新评审，直到 clean 或预算
耗尽。随后做完整切片评审、必要的视觉/动效验收和最终验证。

启用 UI truth 时，schema v2 `visual-acceptance.json` 必须绑定当前 v3 index，
并且每个索引 scenario 恰好有一条结果：

- `component-only` 使用冻结的真实组件预览和适用行为证据，不声称宿主组合；
- `host-static` / `host-runtime` 使用 hash 绑定 runtime capture、生产测试、
  几何/landmark 断言、命令、评审者和 host provenance；
- 每个 unit 独立验收动效；静态 golden 不能替代动效验收。

运行时截图保存在 `.ai-delivery/` 外、index 指定的项目原生证据根。waiver
必须含用户身份、时间和原因。

```text
design_ready → in_dev → [visual_acceptance_passed] → merged
```

`none` / `existing` 跳过 `visual_acceptance_passed`。
