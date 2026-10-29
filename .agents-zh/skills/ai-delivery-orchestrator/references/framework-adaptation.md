# 框架适配

编排器拥有状态、gate、blocker、handoff 和持久化产物形态。已安装框架只
贡献推理方法或执行纪律，不新增阶段和必需文档。

## 产物边界协议（必须）

- 流程/治理产物只能写入 `.ai-delivery/meta/project-binding.json` 解析出的
  canonical 路径。Stage 3 唯一契约是 `design.md`；可选恢复状态写
  `progress.md`。
- 宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。
- 调用外部 skill、命令、agent 或 hook 前，传入准确 canonical 输出映射和
  已批准 workspace。`docs/superpowers/**`、`.superpowers/**`、`.specify/**`
  与 `openspec/**` 默认路径全部禁用。
- 若步骤无法遵守映射，不调用该持久化步骤；在会话内应用方法并直接写
  canonical 产物。禁止先在其他位置生成再搬运。
- 在完整批次入口/出口及推进门禁前，比较 Git 状态/内容与每个外部默认输出根的独立文件系统指纹，包括 ignored 文件、类型、symlink target 与 SHA-256。仅当能覆盖批次中所有写入方及输出根时，才合并受控调用的审计；期间持续限制输出映射。未知写入方、输出根变化或覆盖不明时单独完整审计，不仅凭 mtime 或 tracked 路径复用。越界写入设置 `blocked_verification_failure`，不得删除或改写用户既有文件。

## Workspace

[workspace-policy.md](workspace-policy.md) 是唯一权威。默认当前 checkout；
创建或复用 worktree 必须针对当前切片明确批准准确路径
`<project-root>/.worktrees/<req-id>-<sr-id>`。任何 checkpoint 或框架默认值
都不构成同意。

## 抽象动作

| Action | 含义 | 触发 |
|--------|------|------|
| `requirement-breakdown` | kit 自有需求拆分 | `draft` |
| `ui-truth-mapping` | kit 自有受控视觉实现 | CP-UI 后的 eligible `split_ready` |
| `solution-design` | 产出并评审唯一 `design.md` | `split_ready` / `acceptance_frozen` |
| `implement` | 按当前契约执行 TDD 与评审 | 依赖就绪的 `design_ready` / `in_dev` |
| `finish` | 验证、集成并关闭切片 | 实现/验收完成 |
| `archive` | 原位收敛完成状态 | 所有适用切片 `merged` |

不得输出 `spec`、`plan`、`tasks` 动作。只有 `user_decision_required=true`
触发 CP-DESIGN，批准同时授权对应范围内的实现。

## 环境自检与选择

每次运行只读检测并在 `decisions.md` 记录所选方法：

| 框架 | 检测 | 作用 |
|------|------|------|
| spec-kit | `.specify/` 或 CLI | 可选需求/设计推理 |
| OpenSpec | `openspec/` 或 CLI | 可选棕地增量推理 |
| superpowers | skill 目录 | 设计、TDD、评审、finish 纪律 |
| ECC | 已注册命令/agent | 设计、执行与评审纪律 |
| native | 始终可用 | 完整兜底 |

`solution-design` 优先采用可用的 superpowers/ECC 设计方法；Spec Kit 和
OpenSpec 只可补充同一 `design.md` 的分析。它们不得运行会写 feature/change
目录或 spec/plan/task 文件的持久化管道。`implement` / `finish` 优先
superpowers，其次 ECC，最后 native。

## 闭环与追踪

```text
入口 guard → 框架方法 → 契约/验证 gate → 推进、重试或阻塞
```

在 `traceability.json` `source_index.design` 记录 canonical `design.md`
路径、当前 SHA-256、来源关系和推理方法。schema 2.0 不生成 `spec_refs` 或
`kind=spec|plan|tasks`；旧终态记录只读兼容。
