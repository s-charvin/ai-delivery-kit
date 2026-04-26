# AI Delivery 任意仓库接入指南

## 适用范围

只要你的目标仓库满足下面两点，就可以接入这套架构：

1. 该仓库是实际业务仓库，后续会承载 `.ai-delivery/`、`.specify/` 和 project-local skills。
2. 你可以使用 `ai-delivery` CLI，或者直接运行发布出来的 bootstrap 脚本。

当前 source repo 仍然是这些 governed 资产的维护来源，它提供：

- `requirement-breakdown`
- `api-contract-mapping`
- `ui-requirement-mapping`
- `ui-acceptance-contract`
- `ui-interaction-design`
- `ai-delivery-orchestrator`
- helper script
- onboarding guide

注意：

- 对外推荐入口已经不是“先进入参考仓库再 bootstrap”，而是 `ai-delivery init` 或发布脚本。
- source repo 里的 helper script 仍位于仓库根目录，主要用于兼容包装、本地开发和 contract test。
- 参考仓库里的 source skill 则位于 `.agents/skills/ai-delivery/`。
- 一旦 bootstrap 到目标仓库，这些 workflow skills 会直接落在 `.agents/skills/`，而验证脚本、测试和 onboarding guide 会落在 `.ai-delivery/` 下面，避免污染目标仓库根目录。

## 这套架构的职责边界

固定边界如下：

- `Requirement` 是功能真相
- `Figma` 是视觉真相
- `Spec Kit` 只负责 `constitution / spec / plan / tasks`
- `Superpowers` 只负责 agent 执行纪律
- `.ai-delivery/` 负责需求拆分、映射、交互、状态、日志、依赖和追踪
- `ai-delivery-admin` 负责控制面、展示、治理写入、MCP 和 admin support skill

推荐主链路：

`Requirement Intake -> Requirement Breakdown -> API Contract Mapping (optional but governed) -> UI Mapping -> UI Acceptance Contract -> Interaction Design -> Spec Kit -> Superpowers Execution -> Slice Closure`

说明：

- API contract mapping 是受治理的，但不是前期前端工作的默认门禁。
- 缺 Swagger / OpenAPI、缺字段、字段未定、接口晚到，在这套链路里都默认记录为 `missing_nonblocking` 或后续集成上下文。
- 只有当 API 已知事实会让当前需求、UI 或交互结论失真时，才应该 blocker 或触发重校验。

## 一次性接入任意仓库

### Step 1: 安装 `ai-delivery` CLI，或直接使用 bootstrap 脚本

推荐主路径是直接安装 CLI：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init <target> --project-id <project-id> --main-branch main
```

例子：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /Users/xxx/Projects/my-app --project-id my-app --main-branch main
```

如果你不想先安装 CLI，可以直接走 no-install bootstrap：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- <target> --project-id <project-id> --main-branch main
```

例子：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- /Users/xxx/Projects/my-app --project-id my-app --main-branch main
```

这一步会把下面这些内容落进目标仓库：

- `.agents/skills/requirement-breakdown/`
- `.agents/skills/api-contract-mapping/`
- `.agents/skills/ui-requirement-mapping/`
- `.agents/skills/ui-acceptance-contract/`
- `.agents/skills/ui-interaction-design/`
- `.agents/skills/ai-delivery-orchestrator/`
- `.ai-delivery/scripts/validate-project-ai-delivery-skills.sh`
- `.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh`
- `.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md`
- 最小 `.ai-delivery/` 目录契约与基础 meta/runtime 文件

也就是说，`project-local skills` 的初始化已经并入 `ai-delivery init` / bootstrap 本身，目标仓库不再需要额外执行单独的 skill 安装步骤。

如果 CLI 检测到缺失的 `specify-cli` 或 `superpowers`，会先提示你是否按官方路径安装：

- 你选择安装：CLI 会按支持环境里的官方路径继续处理。
- 你选择不安装：CLI 仍会完成 `.ai-delivery` 与 governed skill 的初始化，但会打印官方安装链接，方便你后续手动处理。

它不会做这些事情：

- 不会创建真实 requirement package
- 不会绑定 Figma
- 不会启动 `ai-delivery-admin`

兼容说明：

- 如果你正在 `ai-delivery-kit` source repo 内做本地验证，仍然可以执行 `zsh scripts/bootstrap-ai-delivery-project.sh --target-repo <target-repo-root> --project-id <project-id> --main-branch main`。
- 这个 wrapper 仍然有效，但它是兼容入口，不是对外推荐入口。

### Step 2: 确认 `specify-cli` / `superpowers` 就绪

先确保机器具备：

```bash
uv --version
python3 --version
git --version
```

`Python` 需要 `3.11+`。

如果你在 Step 1 里已经允许 CLI 代装，可以直接跳到验证步骤。

如果你在 Step 1 里选择稍后处理，可以按官方路径自行安装 `specify-cli`，并确认 `superpowers` 已经在当前 agent 环境可用。

`specify-cli` 示例安装：

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify check
```

`superpowers` 请按你当前 coding agent 支持的官方路径安装；如果 CLI 没有直接代装，它会打印对应官方链接。

然后进入目标仓库确认 `Spec Kit` 可用：

```bash
cd <target-repo-root>
specify init --here --force --ai codex --script sh
```

如果仓库已经有旧的 `Spec Kit` 模板，需要升级：

```bash
cd <target-repo-root>
cp .specify/memory/constitution.md .specify/memory/constitution.backup.md 2>/dev/null || true
specify init --here --force --ai codex --script sh
```

说明：

- 在 `Codex` 里，`Spec Kit` 的调用方式是 `$speckit-*`
- 例如 `$speckit-constitution`、`$speckit-specify`、`$speckit-plan`
- 升级时先备份 `.specify/memory/constitution.md`
- `ai-delivery init` 自动接管 `specify init` 时，会先检测你本地 `specify` 是否支持 `--ai-skills`；如果当前版本不支持，会自动退回兼容命令。
- `superpowers` 在这套链路里负责执行纪律，不负责替代 `.ai-delivery` 或 `Spec Kit` 的制品边界

bootstrap 完成后，当前仓库内应该已经具备并可识别：

- `$requirement-breakdown`
- `$api-contract-mapping`
- `$ui-requirement-mapping`
- `$ui-interaction-design`

如需确认 bootstrap 结果，可以额外执行：

```bash
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```

### Step 3: 可选安装 admin support skill

如果你还要接入控制面治理，从 `ai-delivery-admin` 仓库执行：

```bash
cd <ai-delivery-admin-root>
zsh scripts/install-admin-support-skill.sh
```

这样就能在 Codex 里使用：

- `$ai-delivery-admin-support`

## 目标仓库最小目录契约

bootstrap 完成后，目标仓库至少具备：

```text
<target-repo>/
├── .agents/
│   └── skills/
│       ├── requirement-breakdown/
│       ├── api-contract-mapping/
│       ├── ui-requirement-mapping/
│       ├── ui-acceptance-contract/
│       ├── ui-interaction-design/
│       └── ai-delivery-orchestrator/
├── .ai-delivery/
│   ├── docs/
│   │   └── guides/
│   │       └── ai-delivery-any-repo-onboarding.md
│   ├── requirements/
│   ├── figma-cache/
│   ├── logs/
│   │   ├── events.ndjson
│   │   ├── sessions/
│   │   └── subagents/
│   ├── meta/
│   │   ├── project-binding.json
│   │   ├── workflow-policy.json
│   │   └── naming-rules.json
│   ├── scripts/
│   │   └── validate-project-ai-delivery-skills.sh
│   ├── tests/
│   │   └── ai-delivery-skills/
│   │       └── validate-sources.test.sh
│   └── runtime/
│       ├── main-branch.json
│       ├── worktrees.json
│       ├── merge-queue.json
│       ├── dependency-graph.json
│       ├── blockers.json
│       ├── task-board.json
│       ├── slice-closures.json
│       └── agent-sessions.json
```

`.specify/` 则由 `Spec Kit` 负责初始化。

## 新需求怎么走完整条链路

假设：

- 总需求文档：`docs/requirements/project-rename.md`
- `requirement_id`: `req-project-rename`
- `subreq_id`: `SR-001`
- `Spec Kit feature id`: `001-project-rename`
- Figma file: `https://www.figma.com/file/abc123/Project-Settings`
- Figma node: `120:88`

### 第 0 步：初始化仓库级 Spec Kit constitution

直接对 Codex 说：

```text
使用 $speckit-constitution 为当前仓库建立开发原则：
1. Requirement 是功能真相，Figma 是视觉真相，冲突必须阻塞；
2. Spec Kit 只负责 spec、plan、tasks，不负责运行态和日志态；
3. 实现执行必须走独立 worktree、TDD、review、verification；
4. 所有需求都要保留从 .ai-delivery 到 Spec Kit 产物的反向追踪；
5. Requirement 与 Figma 冲突时，agent 不允许私自补需求或补 UI。
```

### 第 1 步：Requirement Breakdown

```text
使用 $requirement-breakdown 处理 docs/requirements/project-rename.md。

要求：
- requirement_id 使用 req-project-rename
- 如果 .ai-delivery/requirements/req-project-rename 不存在，就按当前 governed contract bootstrap
- 生成 breakdown-summary.md、global-rules.md、dependency-graph.json 和 sub-requirements
- 初始化 api-contract-mapping.md、traceability.json.api_contract_mapping 和 traceability.json.source_index
- 只做需求拆分和 API stage 初始化，不做详细 API 映射，不做 Figma 映射，不做交互设计，不做 Spec Kit spec/plan/tasks
- 不允许脑补缺失业务规则
```

### 第 2 步：API Contract Mapping（可选但受治理）

如果已经提供 Swagger / OpenAPI / 接口协议：

```text
使用 $api-contract-mapping 处理子需求 SR-001。

输入：
- requirement root: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001
- requirement-slice: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- api contract: contracts/project-rename.openapi.yaml

要求：
- 生成 api-contract-mapping.md
- 只更新 traceability.json.api_contract_mapping
- 如果接口协议晚到，可以在 UI mapping 前补跑，或者与 UI mapping 并行补跑
- 如果接口结论会影响 UI 或 interaction，则写入 downstream_revalidation
- 普通缺字段、缺错误码、缺接口、字段未定，只记录 known gaps / integration risks / reservation points，不阻塞前几个 frontend pre-dev 阶段
- 不允许根据服务端内部实现细节脑补 client-facing contract
```

如果当前没有 API contract，可以跳过这一步，后续在协议补充后单独补跑。

### 第 3 步：UI Requirement Mapping

```text
使用 $ui-requirement-mapping 处理子需求 SR-001。

输入：
- requirement root: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001
- requirement-slice: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- api contract mapping: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/api-contract-mapping.md
- figma file: https://www.figma.com/file/abc123/Project-Settings
- target node: 120:88

要求：
- 基于结构化 node payload 完成映射
- 生成 figma-mapping.md
- 更新 traceability.json
- 保留现有 traceability.json.api_contract_mapping 子树
- 不允许根据截图或记忆脑补 UI
- 如果设计缺失或与 requirement 冲突，就明确阻塞
```

### 第 4 步：UI Interaction Design

```text
使用 $ui-interaction-design 处理子需求 SR-001。

输入：
- requirement-slice.md
- api-contract-mapping.md（如果已存在）
- figma-mapping.md
- traceability.json

要求：
- 输出 interaction-design.md
- 明确 success / loading / error / disabled / focus / a11y
- 只允许 bounded micro-interaction assumptions
- 不允许新增业务步骤、字段、弹窗或页面跳转
```

### 第 5 步：Spec Kit Phase

先生成 spec：

```text
使用 $speckit-specify 为 feature 001-project-rename 生成 Spec Kit spec。

上游输入必须以这些文件为准：
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/api-contract-mapping.md
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/figma-mapping.md
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/interaction-design.md
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/traceability.json

要求：
- 不要重新发明需求
- spec 要保留 requirement_id=req-project-rename 和 subreq_id=SR-001 的反向追踪信息
- 这一阶段只生成 spec，不直接开始实现
```

如果有歧义，再跑 clarify：

```text
使用 $speckit-clarify，只澄清会影响方案与验收的未定点，不要重新设计产品。
```

然后生成 plan 和 tasks：

```text
使用 $speckit-plan 为 feature 001-project-rename 生成实现计划。
```

```text
使用 $speckit-tasks 为 feature 001-project-rename 生成可执行任务列表。
```

### 第 6 步：Superpowers Execution

这套架构里，执行层默认交给 `Superpowers`，不是 `Spec Kit`。

直接对 Codex 说：

```text
请按顺序使用 $using-git-worktrees、$test-driven-development、$requesting-code-review、$verification-before-completion 来执行 feature 001-project-rename 的任务。

执行约束：
- 基于主开发分支创建独立 worktree
- 严格按 Spec Kit tasks 和上游 .ai-delivery 产物实现
- 如果 ai-delivery-admin 可用，使用 $ai-delivery-admin-support 记录开始、阻塞、恢复和完成日志
- 不允许跳过测试、review 和完成前验证
```

## Spec Kit bridge 的处理方式

bootstrap 脚本不会替目标仓库强行规定 `traceability.json.spec_kit_refs` 的最终路径策略。

原因很直接：

- 有的仓库会先用 stub bridge
- 有的仓库会直接接 live `Spec Kit`
- 不同仓库对 `spec_path / plan_path / tasks_path` 的约束可能不同

推荐做法：

1. 先把 `Requirement -> Mapping -> Interaction -> Spec Kit -> Execution` 主链路接起来。
2. 再在目标仓库里正式定义 `spec_kit_refs` 契约。
3. 如果仓库已经有 `traceability.json.spec_kit_refs` 规则，就按仓库自己的 bridge contract 继续，不要让 bootstrap 脚本擅自改写。

## 最少要记住的命令

第一次接入：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init <target> --project-id <project-id> --main-branch main
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```

## 验证命令

在已接入的目标仓库里：

```bash
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
zsh .ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh
specify check
```

## 参考资料

- 官方安装文档：[https://github.github.com/spec-kit/installation.html](https://github.github.com/spec-kit/installation.html)
- 官方升级文档：[https://github.github.com/spec-kit/upgrade.html](https://github.github.com/spec-kit/upgrade.html)
- 官方仓库 README：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
