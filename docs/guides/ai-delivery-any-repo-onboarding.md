# AI Delivery 任意仓库接入指南

## 适用范围

只要你的目标仓库满足下面两点，就可以接入这套架构：

1. 该仓库是实际业务仓库，后续会承载 `.ai-delivery/` 和 project-local skills。
2. 你手里有一个"参考仓库"，里面已经维护好这套 project AI delivery skill 源码与 helper script。

当前参考仓库就是本仓库，它提供：

- `requirement-breakdown`
- `ui-truth-mapping`
- `ai-delivery-orchestrator`
- helper script
- onboarding guide

注意：

- 参考仓库里的 source helper script 仍位于仓库根目录，方便作为 bootstrap 来源使用。
- 参考仓库里的 source skill 则位于 `.agents/skills/`（扁平三 skill 结构）。
- 一旦 bootstrap 到目标仓库，这些 workflow skills 会直接落在 `.agents/skills/`，而验证脚本、测试和 onboarding guide 会落在 `.ai-delivery/` 下面，避免污染目标仓库根目录。

## 这套架构的职责边界

固定边界如下：

- `Requirement` 是功能真相
- `Figma` 是视觉真相
- 规格类产物（spec / plan / tasks）由已安装的 spec 框架产出；未安装时走内置原生档
- 执行纪律（worktree / TDD / review / verification）由已安装的执行框架承担；未安装时用内置纪律
- `.ai-delivery/` 负责需求拆分、UI 真相映射、状态、依赖和追踪等重要产物存放

编排器本身**框架无关**：它只输出抽象阶段动作（`design` / `spec` / `plan` / `tasks` / `implement` / `finish`），并在运行时适配你已安装的框架。绝不要求你安装任何东西。

推荐主链路：

`Requirement Intake → Requirement Breakdown → UI Truth Mapping → Design → Spec 管道 → Implementation → Merge`

说明：

- API 文档直接传递给实现阶段作为参考，不做独立的 API contract mapping 阶段。
- 缺 Swagger / OpenAPI、缺字段、字段未定、接口晚到，默认记录为 `integration_deferred`。
- 只有当 API 已知事实会让当前需求或 UI 结论失真时，才应该 blocker 或触发重校验。

## 一次性接入任意仓库

### Step 1: 从参考仓库 bootstrap 目标仓库

在参考仓库里执行：

```bash
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh <target-repo-root>
```

例子：

```bash
cd /Users/xxx/Projects/delivery-dev
zsh scripts/bootstrap-ai-delivery-project.sh /Users/xxx/Projects/my-app
```

这一步会把下面这些内容落进目标仓库：

- `.agents/skills/requirement-breakdown/`
- `.agents/skills/ui-truth-mapping/`
- `.agents/skills/ai-delivery-orchestrator/`（含 `references/framework-adaptation.md` 与 `references/frameworks/` 框架指南）
- `.ai-delivery/scripts/validate-project-ai-delivery-skills.sh`
- `.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh`
- `.ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
- `.ai-delivery/tests/ai-delivery-skills/ui-composition-guardrails.test.sh`
- 最小 `.ai-delivery/` 目录契约与基础 meta 文件

也就是说，`project-local skills` 的初始化已经并入 bootstrap 本身，目标仓库不再需要额外执行单独的 skill 安装步骤。

它不会做这些事情：

- 不会安装任何第三方框架（spec-kit / OpenSpec / superpowers / ECC）
- 不会自动执行任何框架的 init 命令
- 不会创建真实 requirement package
- 不会绑定 Figma

### Step 2: 框架自查与适配（可选安装，装了更好，不装也行）

bootstrap 之后**不需要安装任何东西**即可跑完整条链路 —— 未安装任何框架时，编排器使用内置原生档（子需求目录内的轻量 `spec.md` / `tasks.md` + 内置纪律指引）。

如果你已经安装了以下主流 AI 开发框架，编排器会在每次 run 开始时自查环境并自动适配（自查与选档规则见 `.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md`）：

| 框架 | 主要承担 | 安装识别标志 |
|------|----------|--------------|
| [spec-kit](https://github.com/github/spec-kit) | `spec` / `plan` / `tasks`（constitution 治理最完整） | 仓库根 `.specify/` 或 `specify` CLI |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) | `spec` / `plan` / `tasks`（轻量 delta-spec，棕地友好） | 仓库根 `openspec/` 或 `openspec` CLI |
| [superpowers](https://github.com/obra/superpowers) | `design` / `implement` / `finish`（执行纪律技能包） | 用户技能目录含 superpowers 技能 |
| [ECC (Everything Claude Code)](https://github.com/everythingcc/everything-claude-code) | `design` / `implement` / `finish`（完整 harness 套件） | IDE 中注册 `/ecc:*` 命令 |

每个框架的具体使用意见、命令细节与产物落位见对应指南：`.agents/skills/ai-delivery-orchestrator/references/frameworks/<name>.md`。

原则：

- 编排器**只检测、不安装**；需要安装时由用户自行决定。
- 多框架并存时各取所长：规格类动作优先 spec-kit / OpenSpec，执行纪律类动作优先 superpowers / ECC。
- 同一子需求不混用两个规格类框架；选定档位记录在该子需求 `decisions.md`。

bootstrap 完成后，当前仓库内应该已经具备并可识别：

- `$requirement-breakdown`
- `$ui-truth-mapping`

如需确认 bootstrap 结果，可以额外执行：

```bash
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```

## 目标仓库最小目录契约

bootstrap 完成后，目标仓库至少具备：

```text
<target-repo>/
├── .agents/
│   └── skills/
│       ├── requirement-breakdown/
│       ├── ui-truth-mapping/
│       └── ai-delivery-orchestrator/
├── .ai-delivery/
│   ├── requirements/
│   ├── meta/
│   │   ├── project-binding.json
│   │   ├── workflow-policy.json
│   │   └── naming-rules.json
│   ├── scripts/
│   │   ├── validate-project-ai-delivery-skills.sh
│   │   └── hooks/
│   └── tests/
│       └── ai-delivery-skills/
│           ├── validate-sources.test.sh
│           ├── api-nonblocking-policy.test.sh
│           └── ui-composition-guardrails.test.sh
```

接入指南与阶段清单维护在 **kit 参考仓库** 的 `docs/guides/`（不会复制到目标仓库的 `.ai-delivery/`）。

框架自有目录（如 `.specify/`、`openspec/`）由框架自身初始化，不属于本架构的目录契约。

## 新需求怎么走完整条链路

假设：

- 总需求文档：`docs/requirements/project-rename.md`
- `requirement_id`: `req-project-rename`
- `subreq_id`: `SR-001`
- Figma file: `https://www.figma.com/file/abc123/Project-Settings`
- Figma node: `120:88`

最佳实践是直接调用编排器：告诉它需求文档位置，它会自查框架环境、运行 reconcile 并按 handoff 表逐步推进。以下是各阶段的手工说明。

### 第 1 步：Requirement Breakdown

```text
使用 $requirement-breakdown 处理 docs/requirements/project-rename.md。

要求：
- requirement_id 使用 req-project-rename
- 如果 .ai-delivery/requirements/req-project-rename 不存在，就按当前 governed contract bootstrap
- 生成 breakdown-summary.md、global-rules.md、dependency-graph.json 和 sub-requirements
- 初始化 traceability.json 和 source_index
- 只做需求拆分，不做 Figma 映射，不做 spec/plan/tasks
- 不允许脑补缺失业务规则
```

### 第 2 步：UI Truth Mapping

如果需求包含 UI 且 Figma 设计可用：

```text
使用 $ui-truth-mapping 处理子需求 SR-001。

输入：
- requirement root: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001
- requirement-slice: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- figma file: https://www.figma.com/file/abc123/Project-Settings
- target node: 120:88

要求：
- 基于结构化 node payload 完成映射
- 每个独立 unit 生成一份 ui-contract.html（schema v2），无配套 YAML/JSON 文件
- 更新 traceability.json
- 不允许根据截图或记忆脑补 UI
- 如果设计缺失或与 requirement 冲突，就明确阻塞
```

如果当前没有 Figma 设计，或需求不含 UI，可以跳过这一步。非 UI 子需求直接进入设计阶段。

### 第 3 步：Design + Spec 管道（框架无关）

设计阶段（`design` 动作）：基于 `requirement-slice.md`、冻结的 `ui-contract.html`（如有）与 API 文档做设计探索，产出架构、组件分解、数据模型与关键取舍，摘要记入子需求 `notes`，**用户明确批准后**才进入 spec 阶段（检查点 CP-DESIGN）。

spec 管道（`spec` → `plan` → `tasks`）按已安装的框架执行：

- 已装 spec-kit：`$speckit-specify` → `$speckit-plan` → `$speckit-tasks`（详见 frameworks/spec-kit.md）
- 已装 OpenSpec：一个子需求对应一个 change，产出 proposal.md / design.md / tasks.md（详见 frameworks/openspec.md）
- 都没装：走原生档，在子需求目录写轻量 `spec.md`（问题/目标/范围/验收四段式）与 `tasks.md`（详见 frameworks/native.md）

上游输入必须以这些文件为准：

- `.ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md`
- `.ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/<unit-id>/ui-contract.html`（如有 UI，每个 unit 一份）
- `.ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/traceability.json`

要求：

- 不要重新发明需求
- 产物要保留 requirement_id=req-project-rename 和 subreq_id=SR-001 的反向追踪信息
- 产物路径记入 `traceability.json` 的 `spec_refs`
- 这一阶段只产出规格，不直接开始实现

### 第 4 步：Implementation

所有可执行子需求达到 `tasks_ready` 后，经 CP-001 用户确认进入实现（`implement` 动作）。执行方式按已安装框架：

- 已装 superpowers：worktree 隔离 + 子代理驱动 + TDD + 评审（详见 frameworks/superpowers.md）
- 已装 ECC：ECC 任务执行代理 + 其 rules/hooks（详见 frameworks/ecc.md）
- 都没装：原生纪律 — 分支隔离、TDD 先行、小步提交、完成前自验（详见 frameworks/native.md）

执行约束（与框架无关）：

- 基于主开发分支创建独立 worktree/分支
- 严格按 tasks 与上游 .ai-delivery 产物实现
- 不允许跳过测试、review 和完成前验证
- 切片完成并验收后走 `finish` 动作：rebase 合并（无 merge commit），设置 `merged`

## API Policy

API 文档直接传递给实现阶段作为参考，不做独立的 API contract mapping 阶段。

- API 缺口记录为 `integration_deferred` — 不阻塞 UI mapping 或 page-state 实现。
- 只有当缺少 API 真相会导致无法确定 visual carrier 本身时，才阻塞。
- 如果 API 结论会影响 UI 或交互，在实现阶段处理。

## 最少要记住的命令

第一次接入：

```bash
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh <target-repo-root>
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```

## 验证命令

在已接入的目标仓库里：

```bash
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
zsh .ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh
zsh .ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh
```

## 参考资料

- spec-kit：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
- OpenSpec：[https://github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)
- superpowers：[https://github.com/obra/superpowers](https://github.com/obra/superpowers)
- Everything Claude Code (ECC)：[https://github.com/everythingcc/everything-claude-code](https://github.com/everythingcc/everything-claude-code)
- 框架适配总表：`.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md`
