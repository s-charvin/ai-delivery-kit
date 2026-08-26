# 框架适配

编排器是**框架无关**的：它拥有状态、门禁、阻塞器与交接，并输出**抽象阶段动作**而非第三方技能名。动作如何执行取决于用户已安装哪个 AI 开发框架。绝不要求用户安装任何东西；适配现状即可。

## 产物边界协议（必须）

即使外部框架提供了执行方法，产物位置仍由编排器负责。**外部 skill 只提供方法与执行纪律；其默认持久化位置一律失效。**

- 流程/治理产物包括设计文档、spec、plan、tasks、todo、状态、决策、进度、评审 finding 与修复简报、验证证据、报告、检查清单、代理/会话元数据和框架状态。它们只能写入 `.ai-delivery/meta/project-binding.json` 解析出的 canonical 路径，通常位于 `.ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/`；需求级 status、todo、progress 与交付报告仍写各自在需求目录下声明的 canonical 路径。
- `.ai-delivery/` 之外只允许写生产源码、项目原生测试、golden 或官方预览，以及该生产表面所需的运行时资源。可读取已存在的框架配置用于检测或遵循约定，但不得把它改成动作产物。
- 调用任何外部 skill、命令、代理或 hook 前，必须为其可能持久化的每个产物解析并传入明确的输出路径映射。调用方映射覆盖 `docs/superpowers/**`、`.superpowers/**`、`.specify/**`、`openspec/**` 等默认路径。
- 若框架步骤无法遵守 canonical 输出映射，不调用该持久化步骤；在当前会话中应用其方法，并把等价产物直接写到 canonical `.ai-delivery` 路径。禁止先在其他位置生成再搬运。
- 分发前捕获状态/内容指纹账本，动作后对比。账本覆盖 `git status --porcelain=v1 --untracked-files=all` 报告的每个 staged、unstaged、untracked 与 deleted 路径，记录 porcelain 状态及工作树 SHA-256 或删除哨兵。此外，还要为外部 skill 声明的每个默认输出根捕获独立文件系统指纹，并包含 ignored 文件；至少覆盖 `docs/superpowers/`、`.superpowers/`、`.specify/` 与 `openspec/`。逐项记录相对路径、类型与 SHA-256（或符号链接目标/删除哨兵），不得只依赖 Git status 审计这些目录。即使路径进入动作前已 dirty 或 ignored，只要路径、状态、类型、链接目标或内容 hash 变化且不属于允许类别，也属于边界失败：记录精确路径、设置 `blocked_verification_failure`，并且不推进门禁。两份入口账本都只保留在会话内，不另建仓库产物；审计时不得删除或重写用户既有文件。

这些规则覆盖外部 skill 中冲突的持久化指令。编排动作期间，既有 `.specify/`、`openspec/`、`.superpowers/` 或 `docs/superpowers/` 树只能作为只读输入，绝不是派生输出视图。

## Workspace 选择（必须）

[Workspace 与 Worktree 策略](workspace-policy.md) 是所有框架档位的唯一权威。默认使用当前 checkout。创建或复用 worktree 必须取得当前子需求的明确确认，准确路径必须为 `<project-root>/.worktrees/<req-id>-<sr-id>`。checkpoint 与旧的强制隔离字段都不构成用户同意。

调用外部 skill 前，必须同时传入 canonical 产物输出映射与准确的用户已批准 workspace。自动创建、自动复用或把 worktree 放到项目外的框架指令一律失效。如果会话已处于外部 worktree，停止生产编辑并按该策略进入用户决策门禁。

## 抽象动作词表

reconcile 为每个子需求输出以下动作之一：

| 动作 | 含义 | 典型触发状态 |
|------|------|--------------|
| `requirement-breakdown` | kit 自有技能：拆分需求 | `draft` |
| `ui-truth-mapping` | kit 自有能力：在用户已批准 workspace 中执行受控视觉实现 | `ui_truth_mode=figma` 或 `runtime-baseline` 的 `split_ready`，且 CP-UI 之后 |
| `solution-design` | 探索并提出方案设计；是否审批由 `design_mode` 决定 | `design_mode` 非 `none` 的 `split_ready` / `acceptance_frozen` |
| `spec` | 产出子需求规格 | `design_mode` 门禁满足后 |
| `plan` | 产出技术方案 | `spec_ready` |
| `tasks` | 产出任务拆分 | `plan_ready` |
| `implement` | 实现剩余任务（UI 复用 Stage 2 已批准 workspace；TDD + 评审纪律） | CP-001 之后的 `tasks_ready` / `in_dev` |
| `finish` | 变基合并并关闭切片 | `visual_acceptance_passed` |

`requirement-breakdown` 与 `ui-truth-mapping` 是 kit 技能，能力启用时直接调用；`ui-truth-mapping` 会写生产代码，仍受 CP-UI 门禁。`solution-design` 是由 `design_mode` 决定审批行为的编排器动作；其余动作一律通过下文选定的框架档位分发。

## 第 0 步 — 环境自查（每次 run 执行一次）

每次 run 开始时，检查已安装哪些框架，并将结果记入子需求 `decisions.md`（尚无子需求时记入需求级 notes）：

| 框架 | 检测标志 |
|------|----------|
| spec-kit | 仓库根存在 `.specify/` 目录，或 PATH 上有 `specify` CLI |
| OpenSpec | 仓库根存在 `openspec/` 目录，或 PATH 上有 `openspec` CLI |
| superpowers | 用户技能目录（`~/.claude/skills`、`~/.agents/skills` 或仓库技能树）含 superpowers 技能 |
| ECC | ECC 插件/命令标志（如 IDE 中注册了 `/ecc:*` 命令） |

**不要**安装任何东西。检测是只读的；检测不明确时询问用户一次并记录答案。

## 档位选择规则

多框架并存时各取所长：

1. 规格类动作（`spec`、`plan`、`tasks`）：优先 **spec-kit**，其次 **OpenSpec**，再次原生档。
2. 执行纪律类动作（`implement`、`finish`）：优先 **superpowers**，其次 **ECC**，再次原生档。
3. `solution-design` 动作：使用已安装框架中提供设计/头脑风暴流程者（superpowers brainstorming、ECC 设计代理）；否则走原生方案设计流程。
4. 什么都没装：所有动作一律使用**原生档**。
5. 同一子需求绝不混用两个规格类框架。子需求的档位选定后在 `decisions.md` 记录一次，跨 resume 保持稳定。

## 动作分发表

| 动作 | spec-kit | OpenSpec | superpowers | ECC | 原生档 |
|------|----------|----------|-------------|-----|--------|
| `solution-design` | — | — | brainstorming 流程 | 设计/评审代理 | 原生方案设计流程 |
| `spec` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `plan` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `tasks` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `implement` | — | — | [frameworks/superpowers.md](frameworks/superpowers.md) | [frameworks/ecc.md](frameworks/ecc.md) | [frameworks/native.md](frameworks/native.md) |
| `finish` | — | — | [frameworks/superpowers.md](frameworks/superpowers.md) | [frameworks/ecc.md](frameworks/ecc.md) | [frameworks/native.md](frameworks/native.md) |

`—` 表示该框架不覆盖此动作；顺延到下一优先档位或原生档。

## loop 范式

每个阶段都是一个闭环：

```
进入条件（状态 + 门禁）→ 动作（框架档位）→ 验证门禁 → 推进状态 / 重试 / 阻塞器
```

reconcile 就是 evaluate 步骤：重读治理真值、检查门禁、输出下一动作。未过门禁的动作绝不推进状态机 —— 要么在 loop 内重试，要么开启最窄阻塞器。

## 可追溯性

无论哪个档位，所有产出物必须记入子需求 `traceability.json`。**canonical 产物始终使用当前 binding 在 `.ai-delivery/` 下解析出的路径**；默认布局才把子需求产物放在 `.ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/`。框架名只记录采用了哪种方法，不授权第二份持久化副本。

- `spec_refs.tier`：`spec-kit` | `openspec` | `superpowers` | `ecc` | `native`
- `spec_refs.artifacts[].kind`：`spec`、`plan`、`tasks` 各一条完整记录
- `spec_refs.artifacts[].canonical_path`：由对应 `sub_requirement_artifacts` layout key 解析出的仓库相对路径
- `spec_refs.artifacts[].derived_paths`：所有档位均为空；仅为 schema 兼容保留
- `spec_refs.artifacts[].content_sha256`：当前 canonical 内容 hash
- `spec_refs.artifacts[].sync_state`：canonical 路径与 hash 均为当前值后设为 `synced`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`：仅兼容读取旧数据；新产物不得写入，也不得与 `artifacts[]` 混用
- `source_index.spec`：每个产物一条记录，`ref_type` 为 `spec` / `plan` / `tasks`

治理真值和全部流程产物都留在 `.ai-delivery`；宿主树只允许生产源码、项目原生测试、golden/预览和运行时资源。
