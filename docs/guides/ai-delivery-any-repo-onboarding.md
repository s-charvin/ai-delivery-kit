# AI Delivery 任意仓库接入指南

## 适用范围

只要你的目标仓库满足下面两点，就可以接入这套架构：

1. 该仓库是实际业务仓库，后续会承载 `.ai-delivery/`、`.specify/` 和 project-local skills。
2. 你手里有一个“参考仓库”，里面已经维护好这套 project AI delivery skill 源码与 helper script。

当前参考仓库就是本仓库，它提供：

- `requirement-breakdown`
- `ui-requirement-mapping`
- `ui-interaction-design`
- helper script
- onboarding guide

## 这套架构的职责边界

固定边界如下：

- `Requirement` 是功能真相
- `Figma` 是视觉真相
- `Spec Kit` 只负责 `constitution / spec / plan / tasks`
- `Superpowers` 只负责 agent 执行纪律
- `.ai-delivery/` 负责需求拆分、映射、交互、状态、日志、依赖和追踪
- `ai-delivery-admin` 负责控制面、展示、治理写入、MCP 和 admin support skill

推荐主链路：

`Requirement Intake -> Requirement Breakdown -> UI Mapping -> Interaction Design -> Spec Kit -> Superpowers Execution`

## 一次性接入任意仓库

### Step 1: 从参考仓库 bootstrap 目标仓库

在参考仓库里执行：

```bash
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh \
  --target-repo <target-repo-root> \
  --project-id <project-id> \
  --main-branch main-dev
```

例子：

```bash
cd /Users/charvin/Projects/spec-dev/Codex
zsh scripts/bootstrap-ai-delivery-project.sh \
  --target-repo /Users/charvin/Projects/my-app \
  --project-id my-app \
  --main-branch main-dev
```

这一步会把下面这些内容落进目标仓库：

- `.codex/skills/ai-delivery/`
- `.codex/skills/README.md`
- `scripts/bootstrap-ai-delivery-project.sh`
- `scripts/sync-ai-delivery-project-assets.sh`
- `scripts/install-project-ai-delivery-skills.sh`
- `scripts/validate-project-ai-delivery-skills.sh`
- `tests/ai-delivery-skills/validate-sources.test.sh`
- `tests/ai-delivery-skills/bootstrap-project.test.sh`
- `docs/guides/ai-delivery-any-repo-onboarding.md`
- 最小 `.ai-delivery/` 目录契约与基础 meta/runtime 文件

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

推荐先安装稳定版本：

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v0.0.90
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

### Step 3: 在目标仓库里安装 project-local skills 到当前 Codex 环境

```bash
cd <target-repo-root>
zsh scripts/install-project-ai-delivery-skills.sh
zsh scripts/validate-project-ai-delivery-skills.sh
```

完成后，当前 Codex 环境应该能识别：

- `$requirement-breakdown`
- `$ui-requirement-mapping`
- `$ui-interaction-design`

### Step 4: 可选安装 admin support skill

如果你还要接入控制面治理，从 `ai-delivery-admin` 仓库执行：

```bash
cd <ai-delivery-admin-root>
zsh scripts/install-admin-support-skill.sh
```

这样就能在 Codex 里使用：

- `$ai-delivery-admin-support`

## 后续升级任意目标仓库

当参考仓库里的 project-local skills 或 helper script 更新后，在参考仓库执行：

```bash
cd <reference-repo-root>
zsh scripts/sync-ai-delivery-project-assets.sh --target-repo <target-repo-root>
```

`sync` 会刷新这些 managed assets：

- `.codex/skills/ai-delivery/`
- `.codex/skills/README.md`
- helper script
- onboarding guide
- script test

但它不会覆盖这些真实业务数据：

- `.ai-delivery/requirements/`
- 已存在的 `.ai-delivery/meta/*.json`
- 已存在的 `.ai-delivery/runtime/*.json`

## 目标仓库最小目录契约

bootstrap 完成后，目标仓库至少具备：

```text
<target-repo>/
├── .codex/
│   └── skills/
│       ├── README.md
│       └── ai-delivery/
├── .ai-delivery/
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
│   └── runtime/
│       ├── main-branch.json
│       ├── worktrees.json
│       ├── merge-queue.json
│       ├── dependency-graph.json
│       ├── blockers.json
│       └── task-board.json
├── scripts/
└── docs/guides/
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
- 只做需求拆分，不做 Figma 映射，不做交互设计，不做 Spec Kit spec/plan/tasks
- 不允许脑补缺失业务规则
```

### 第 2 步：UI Requirement Mapping

```text
使用 $ui-requirement-mapping 处理子需求 SR-001。

输入：
- requirement root: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001
- requirement-slice: .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
- figma file: https://www.figma.com/file/abc123/Project-Settings
- target node: 120:88

要求：
- 基于结构化 node payload 完成映射
- 生成 figma-mapping.md
- 更新 traceability.json
- 不允许根据截图或记忆脑补 UI
- 如果设计缺失或与 requirement 冲突，就明确阻塞
```

### 第 3 步：UI Interaction Design

```text
使用 $ui-interaction-design 处理子需求 SR-001。

输入：
- requirement-slice.md
- figma-mapping.md
- traceability.json

要求：
- 输出 interaction-design.md
- 明确 success / loading / error / disabled / focus / a11y
- 只允许 bounded micro-interaction assumptions
- 不允许新增业务步骤、字段、弹窗或页面跳转
```

### 第 4 步：Spec Kit Phase

先生成 spec：

```text
使用 $speckit-specify 为 feature 001-project-rename 生成 Spec Kit spec。

上游输入必须以这些文件为准：
- .ai-delivery/requirements/req-project-rename/sub-requirements/SR-001/requirement-slice.md
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

### 第 5 步：Superpowers Execution

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
cd <reference-repo-root>
zsh scripts/bootstrap-ai-delivery-project.sh --target-repo <target-repo-root> --project-id <project-id> --main-branch main-dev
cd <target-repo-root>
specify init --here --ai codex --ai-skills --script sh
zsh scripts/install-project-ai-delivery-skills.sh
zsh scripts/validate-project-ai-delivery-skills.sh
```

后续升级：

```bash
cd <reference-repo-root>
zsh scripts/sync-ai-delivery-project-assets.sh --target-repo <target-repo-root>
```

## 验证命令

在已接入的目标仓库里：

```bash
cd <target-repo-root>
zsh scripts/validate-project-ai-delivery-skills.sh
zsh tests/ai-delivery-skills/validate-sources.test.sh
zsh tests/ai-delivery-skills/bootstrap-project.test.sh
specify check
```

## 参考资料

- 官方安装文档：[https://github.github.com/spec-kit/installation.html](https://github.github.com/spec-kit/installation.html)
- 官方升级文档：[https://github.github.com/spec-kit/upgrade.html](https://github.github.com/spec-kit/upgrade.html)
- 官方仓库 README：[https://github.com/github/spec-kit](https://github.com/github/spec-kit)
