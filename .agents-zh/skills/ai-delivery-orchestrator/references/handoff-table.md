# 交接表

每个阶段只有一个合法下一动作；具体工具见
[framework-adaptation.md](framework-adaptation.md)。

| 当前完成状态 | 唯一下一动作 | 禁止 |
|--------------|--------------|------|
| 拆分边界存在实质歧义 | 解决命名的用户决策后拆分或创建单切片包 | 为明确拆分创建例行审批 |
| `split_ready` + `figma` / `runtime-baseline` | CP-UI → 受控视觉实现 | CP-UI 前写生产 UI |
| CP-UI 已确认 | 解析批准 workspace → `ui-truth-mapping` | 把 CP-UI 当 worktree 同意 |
| `split_ready` + `none` / `existing` | `solution-design` | 强制 UI gate |
| `acceptance_frozen` | `solution-design` | 绕过冻结视觉/动效证据 |
| 当前设计有实质用户决策 | CP-DESIGN | 把技术复杂度当用户决策 |
| 当前 `design.md` 有有效 hash 评审 | `design_ready` → 依赖就绪时 `implement` | 第二次开发授权 |
| 实现与验证完成 | `finish` → `merged` | 带过期设计或未清洁评审合并 |
| 所有切片 `merged` | CP-ARCHIVE → 原位 `archive` | 复制 canonical 产物 |

## 状态到动作

| 状态 | 能力条件 | 下一动作 |
|------|----------|----------|
| `draft` | 任意 | `requirement-breakdown` |
| `split_ready` | `figma` / `runtime-baseline` | CP-UI 后 `ui-truth-mapping` |
| `split_ready` | `none` / `existing` | `solution-design` |
| `acceptance_frozen` | 启用 UI truth | `solution-design` |
| `design_ready` | 依赖就绪 | `implement` |
| `in_dev` | 任意 | `implement` |
| `visual_acceptance_passed` | 启用 UI truth | `finish` |
| `merged` | 任意 | closing checkpoint 后原位 `archive` |
| `archived` | 任意 | 无 |
| `blocked_*` | 任意 | 解决 blocker，同时继续独立 runnable 切片 |

所有活跃 schema 2.0 切片都有一个 canonical `design.md`。无用户决策时
`review_mode=self`；有实质用户决策时通过 CP-DESIGN 记录
`review_mode=human`。两者都绑定文件精确 SHA-256。文件变化重新进入
`solution-design`，但只有实质用户决策仍存在时才再次暂停。
