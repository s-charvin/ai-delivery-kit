# 框架适配

编排器是**框架无关**的：它拥有状态、门禁、阻塞器与交接，并输出**抽象阶段动作**而非第三方技能名。动作如何执行取决于用户已安装哪个 AI 开发框架。绝不要求用户安装任何东西；适配现状即可。

## 抽象动作词表

reconcile 为每个子需求输出以下动作之一：

| 动作 | 含义 | 典型触发状态 |
|------|------|--------------|
| `requirement-breakdown` | kit 自有技能：拆分需求 | `draft` |
| `ui-truth-mapping` | kit 自有技能：冻结 UI 契约 | `split_ready`（含 UI） |
| `design` | 探索并提出设计方案；需用户批准（CP-DESIGN） | `split_ready`（非 UI）/ `acceptance_frozen` 且 `design_approved: false` |
| `spec` | 产出子需求规格 | `design_approved` 之后 |
| `plan` | 产出技术方案 | `spec_ready` |
| `tasks` | 产出任务拆分 | `plan_ready` |
| `implement` | 实现任务（工作树 + TDD + 评审纪律） | CP-001 之后的 `tasks_ready` / `in_dev` |
| `finish` | 变基合并并关闭切片 | `visual_acceptance_passed` |

`requirement-breakdown` 与 `ui-truth-mapping` 是 kit 技能，直接调用。其余动作一律通过下文选定的框架档位分发。

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
3. `design` 动作：使用已安装框架中提供设计/头脑风暴流程者（superpowers brainstorming、ECC 设计代理）；否则走原生设计流程。
4. 什么都没装：所有动作一律使用**原生档**。
5. 同一子需求绝不混用两个规格类框架。子需求的档位选定后在 `decisions.md` 记录一次，跨 resume 保持稳定。

## 动作分发表

| 动作 | spec-kit | OpenSpec | superpowers | ECC | 原生档 |
|------|----------|----------|-------------|-----|--------|
| `design` | — | — | brainstorming 流程 | 设计/评审代理 | 原生设计流程 |
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

无论哪个档位，所有产出物必须记入子需求 `traceability.json`：

- `spec_refs.tier`：`spec-kit` | `openspec` | `superpowers` | `ecc` | `native`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`：具体产物路径
- `source_index.spec`：每个产物一条记录，`ref_type` 为 `spec` / `plan` / `tasks`

治理真值（状态、门禁、契约）永远留在 `.ai-delivery`；框架产物只被引用，绝不搬移。
