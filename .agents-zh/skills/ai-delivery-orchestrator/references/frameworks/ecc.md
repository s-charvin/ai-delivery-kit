# 框架指南：ECC

已安装 ECC（Everything Claude Code）时，`solution-design` / `implement` / `finish` 动作使用本档位。ECC 是完整的 harness 套件 —— 代理、技能、规则、hooks 与斜杠命令 —— 主要强化方案设计评审与实现纪律。

## 检测标志

- IDE 中注册了 ECC 插件/命令标志（如 `/ecc:*` 命令可用），或
- 项目或用户代理配置下存在 ECC 提供的 agents/rules。

ECC 演进很快。一次 run 中首次使用前，先列出本地实际可用的 ECC 命令/代理，并把将要使用的映射记入子需求 `decisions.md`；不要假设未实际注册的命令名。

## 覆盖的动作

| 动作 | ECC 用法 |
|------|----------|
| `solution-design` | ECC 规划/架构代理或 plan 命令 —— 以 `requirement-slice.md`、启用 UI truth 的宿主组件 / v3 profile-state-scenario-scope `ui-truth-index.json`、API 文档为种子 |
| `implement` | ECC 任务执行代理，由其 rules/hooks 强制约定；把其评审代理作为每任务评审步骤 |
| `finish` | 变基合并前先跑 ECC 评审/验证命令 |

## 产物边界

- 调用 ECC 命令或代理前，传入当前需求/子需求 canonical 根目录和明确的输出映射。ECC 只提供设计、执行与评审方法。
- 从 binding 分别解析 layout key `solution_design`、layout key `decisions`、layout key `progress` 与 layout key `verification`。设计输出、评审 finding、修复简报、报告、检查清单和会话元数据写入适用的已解析路径；不得把它们持久化到 ECC 自有的项目或用户目录。
- 若 ECC 代理/hook 无法遵守 canonical 映射，则不调用其持久化步骤；在会话内运行等价方法并直接写入 `.ai-delivery`，禁止先在其他位置生成再搬运。
- 宿主树只允许写生产源码、项目原生测试、golden/官方预览和运行时资源。任何门禁推进前，执行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。

## 使用意见

- 保持编排器 loop 完整：每个 ECC 命令只服务一个抽象动作；状态推进、门禁、阻塞器留在主会话。
- 每任务[评审循环](../stage-implementation.md#评审循环任务级闭环)优先用 ECC 评审代理：实现 → ECC 评审代理 → finding 交回实现者 → 复审，直到干净或 `review_loop.max_rounds` 预算耗尽（然后升级给用户；绝不自动合并）。
- 对 UI truth 切片，ECC 执行/评审必须以模式对应的证据覆盖每个已索引 scenario，并写结构化 `visual-acceptance.json`；只检查 state 或截图文件存在不构成验收。
- ECC hooks 强制格式/lint 规则时就让它跑；hook 失败即验证失败（经评审循环修复一轮后仍失败则 `blocked_verification_failure`），不是绕过 hook 的理由。
- ECC 与另一个框架同时安装时，ECC 通常与规格类档位（spec-kit/OpenSpec）搭配良好：ECC 负责 solution-design/implement/finish，规格档位负责 `spec`/`plan`/`tasks`。
- 进入 `merged` 前须用用户当前对话语言写 `verification.md`。保留 `templates/verification-template.md` 中三个 `ai-delivery-verification:*` 标记；缺少这些标记时状态验证器拒绝 `merged`。

## 可追溯性记录

ECC 本身不产出规格产物；`spec_refs.tier` 保持规格类档位不变。把实际使用的 ECC 命令/代理记入 `decisions.md`，方便后续会话按同一映射恢复。

## 边界

- 绝不自行安装或配置 ECC。
- 不让 ECC 代理决定门禁/状态/合并结果；它们只执行被派发的动作。
- 不得让 ECC 在 `.ai-delivery/` 外持久化流程/治理产物。
