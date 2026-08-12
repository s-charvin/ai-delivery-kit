# 框架指南：ECC

已安装 ECC（Everything Claude Code）时，`design` / `implement` / `finish` 动作使用本档位。ECC 是完整的 harness 套件 —— 代理、技能、规则、hooks 与斜杠命令 —— 主要强化设计评审与实现纪律。

## 检测标志

- IDE 中注册了 ECC 插件/命令标志（如 `/ecc:*` 命令可用），或
- 项目或用户代理配置下存在 ECC 提供的 agents/rules。

ECC 演进很快。一次 run 中首次使用前，先列出本地实际可用的 ECC 命令/代理，并把将要使用的映射记入子需求 `decisions.md`；不要假设未实际注册的命令名。

## 覆盖的动作

| 动作 | ECC 用法 |
|------|----------|
| `design` | ECC 规划/架构代理或 plan 命令 —— 以 `requirement-slice.md`、冻结的 `ui-contract.html`（含 UI 时）、API 文档为种子 |
| `implement` | ECC 任务执行代理，由其 rules/hooks 强制约定；把其评审代理作为每任务评审步骤 |
| `finish` | 变基合并前先跑 ECC 评审/验证命令 |

## 使用意见

- 保持编排器 loop 完整：每个 ECC 命令只服务一个抽象动作；状态推进、门禁、阻塞器留在主会话。
- 每任务[评审循环](../stage-implementation.md#评审循环任务级闭环)优先用 ECC 评审代理：实现 → ECC 评审代理 → finding 交回实现者 → 复审，直到干净或 `review_loop.max_rounds` 预算耗尽（然后升级给用户；绝不自动合并）。
- ECC hooks 强制格式/lint 规则时就让它跑；hook 失败即验证失败（经评审循环修复一轮后仍失败则 `blocked_verification_failure`），不是绕过 hook 的理由。
- ECC 与另一个框架同时安装时，ECC 通常与规格类档位（spec-kit/OpenSpec）搭配良好：ECC 负责 design/implement/finish，规格档位负责 `spec`/`plan`/`tasks`。
- 进入 `merged` 前须写 `verification.md`（须含小节：评审轮次记录 / 验证命令与结果 / 签署）。无此文件时状态验证器拒绝 `merged`。

## 可追溯性记录

ECC 本身不产出规格产物；`spec_refs.tier` 保持规格类档位不变。把实际使用的 ECC 命令/代理记入 `decisions.md`，方便后续会话按同一映射恢复。

## 边界

- 绝不自行安装或配置 ECC。
- 不让 ECC 代理决定门禁/状态/合并结果；它们只执行被派发的动作。
