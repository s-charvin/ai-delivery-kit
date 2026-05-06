# AI Delivery 任意仓库接入指南

## 适用范围

只要你的目标仓库满足下面两点，就可以接入这套架构：

1. 该仓库是实际业务仓库，后续会承载 `.ai-delivery/`、`.specify/` 和 project-local skills。
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
- `Spec Kit` 只负责 `constitution / spec / plan / tasks`
- `Superpowers` 只负责 agent 执行纪律
- `.ai-delivery/` 负责需求拆分、UI 真相映射、状态、日志、依赖和追踪

推荐主链路：

`Requirement Intake → Requirement Breakdown → UI Truth Mapping → Spec Kit → Implementation → Merge`

说明：

- API 文档直接传递给实现阶段作为参考，不做独立的 API contract mapping 阶段。
- 缺 Swagger / OpenAPI、缺字段、字段未定、接口晚到，默认记录为 `integration_deferred`。
- 只有当 API 已知事实会让当前需求或 UI 结论失真时，才应该 blocker 或触发重校验。

## 一次性接入任意仓库

### Step 1: 从参考仓库 bootstrap 目标仓库

在参考仓库里执行：

```bash
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh \
  --target-repo <target-repo-root> \
  --project-id <project-id> \
  --main-branch main
```

例子：

```bash
cd /Users/xxx/Projects/delivery-dev
zsh scripts/bootstrap-ai-delivery-project.sh \
  --target-repo /Users/xxx/Projects/my-app \
  --project-id my-app \
  --main-branch main
```

这一步会把下面这些内容落进目标仓库：

- `.agents/skills/requirement-breakdown/`
- `.agents/skills/ui-truth-mapping/`
- `.agents/skills/ai-delivery-orchestrator/`
- `.ai-delivery/scripts/validate-project-ai-delivery-skills.sh`
- `.ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh`
- `.ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
- `.ai-delivery/tests/ai-delivery-skills/ui-composition-guardrails.test.sh`
- 最小 `.ai-delivery/` 目录契约与基础 meta/runtime 文件

也就是说，`project-local skills` 的初始化已经并入 bootstrap 本身，目标仓库不再需要额外执行单独的 skill 安装步骤。

它不会做这些事情：

- 不会安装全局 `Spec Kit` CLI
- 不会自动执行 `specify init`
- 不会创建真实 requirement package
- 不会绑定 Figma
- 不会启动 `ai-delivery-admin`

### Step 2: 在目标仓库里安装 Spec Kit

先确保机器具备：

```bash
uv --version
python3 --version
git --version
```

`Python` 需要 `3.11+`。

安装：

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify check
```

再进入目标仓库初始化 `Spec Kit`：

```bash
cd <target-repo-root>
specify init --here --ai codex --ai-skills --script sh
```

如果仓库已经有旧的 `Spec Kit` 模板，需要升级：

```bash
cd <target-repo-root>
cp .specify/memory/constitution.md .specify/memory/constitution.backup.md 2>/dev/null || true
specify init --here --force --ai codex --ai-skills --script sh
```

说明：

- 在 `Codex` 里，`Spec Kit` 的调用方式是 `$speckit-*`
- 例如 `$speckit-constitution`、`$speckit-specify`、`$speckit-plan`
- 升级时先备份 `.specify/memory/constitution.md`

bootstrap 完成后，当前仓库内应该已经具备并可识别：

- `$requirement-breakdown`
- `$ui-truth-mapping`

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
│       ├── ui-truth-mapping/
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
│   │       ├── validate-sources.test.sh
│   │       ├── api-nonblocking-policy.test.sh
│   │       └── ui-composition-guardrails.test.sh
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
- 初始化 traceability.json 和 source_index
- 只做需求拆分，不做 Figma 映射，不做 Spec Kit spec/plan/tasks
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
- 生成 ui-acceptance-contract.yaml 和 section-map.json
- 更新 traceability.json
- 不允许根据截图或记忆脑补 UI
- 如果设计缺失或与 requirement 冲突，就明确阻塞
```

如果当前没有 Figma 设计，或需求不含 UI，可以跳过这一步。非 UI 子需求直接进入 Spec Kit。

### 第 3 步：Spec Kit Phase

先生成 spec：

```text
使用 $speckit-specify 为 feature 001-project-rename 生成 Spec Kit spec。

上游输入必须以这些文件为准：
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/ui-acceptance-contract.yaml（如有 UI）
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/section-map.json（如有 UI）
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

### 第 4 步：Implementation

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

## API Policy

API 文档直接传递给实现阶段作为参考，不做独立的 API contract mapping 阶段。

- API 缺口记录为 `integration_deferred` — 不阻塞 UI mapping 或 page-state 实现。
- 只有当缺少 API 真相会导致无法确定 visual carrier 本身时，才阻塞。
- 如果 API 结论会影响 UI 或交互，在实现阶段处理。

## 最少要记住的命令

第一次接入：

```bash
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh --target-repo <target-repo-root> --project-id <project-id> --main-branch main-dev
cd <target-repo-root>
specify init --here --ai codex --ai-skills --script sh
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```

## 验证命令

在已接入的目标仓库里：

```bash
cd <target-repo-root>
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
zsh .ai-delivery/tests/ai-delivery-skills/validate-sources.test.sh
zsh .ai-delivery/tests/ai-delivery-skills/api-nonblocking-policy.test.sh
specify check
```

## 参考资料

- 官方安装文档：[https://github.github.com/spec-kit/installation.html](https://github.github.com/spec-kit/installation.html)
- 官方升级文档：[https://github.github.com/spec-kit/upgrade.html](https://github.github.com/spec-kit/upgrade.html)
- 官方仓库 README：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
