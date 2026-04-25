# AI Native One-Stop Development Workflow Research

Date: 2026-04-25
Status: research-report
Retrieval date: 2026-04-25

## Executive Conclusion

当前最优路线不是押注某一个“一站式”产品，而是把一站式能力拆成可治理的栈：

```text
Requirement truth + Design truth
        |
        v
.ai-delivery governed fact layer
        |
        v
Orchestrator / stage gate decision layer
        |
        v
Spec Kit bridge and task generation
        |
        v
Worktree-isolated coding agents
        |
        v
Review, visual acceptance, verification, merge
        |
        v
Runtime observability and feedback loop
```

推荐组合是：

- `Requirement + Figma` 继续作为功能与视觉双真相源。
- `.ai-delivery` 继续作为 `spec-dev` 的本地事实层，保存需求、映射、追踪、状态、blocker、worktree、merge 与日志。
- `Spec Kit` 继续作为规格到 plan/tasks 的标准桥，但不要让 `.specify` 反向成为业务真相源。
- `Codex` 与 `Claude Code` 作为主力编码 agent：前者更适合多 agent、cloud/local、review/automation 组合；后者更适合本地强交互、hooks、MCP、subagents 与 worktree 化深水任务。
- `GitHub Copilot coding agent` 适合接入 GitHub issue/PR 的低到中复杂度后台任务，尤其适合已有 GitHub governance 的团队。
- `Cursor` 适合设计/代码之间的高频交互、快速补丁、背景 agent 与 PR Bugbot，但其 background agent 自动运行命令和联网能力要放进更严格的安全边界。
- `GSD` 的价值在执行态：上下文工程、状态文件、wave/parallel execution、pause/resume、verification。`spec-dev` 应吸收这些运行节奏，而不是复制一整套 `.planning` 真相。
- `OpenSpec` 的价值在 change folder 与 archive 思路。它适合轻量棕地变化，但与 `Spec Kit` 在 spec/task 层重叠，不能再引入为第二套规格源。
- `BMad` 的价值在角色化 agents、PRD/Architecture/Epic/Story 到 Dev loop。它适合学习多角色拆分，但对 `spec-dev` 当前目标偏重。
- `Lovable / Replit / v0 / Figma Make` 适合探索、MVP、设计验证、demo、营销页与早期全栈原型；不建议让它们直接成为复杂棕地项目的长期真相源。

一句话判断：**“放心交给 AI 干活”的关键不是更强 prompt，而是源头真相、阶段门禁、隔离执行、可观测、可恢复，以及人类只在高价值决策点介入。**

对 `spec-dev` 的核心建议：

- 保留：`.ai-delivery` 事实层、traceability、Spec Kit bridge、governed MCP、worktree isolation、blocker recovery、visual acceptance gate。
- 吸收：Codex/Claude 的多 agent 与 review 经验、Copilot 的 PR-native 审计边界、GSD 的 pause/resume 与 wave execution、OpenSpec 的 archive/change delta、Figma Make 的 design-system-backed prototype。
- 避免：再增加一套并列 status 真相、让 cloud app builder 直接改核心棕地代码、让 background agent 拿到无限制 MCP/网络/secret 权限、把所有阶段都做成硬阻塞。
- 重构重点：压缩重复状态词，统一 `todo.md / status.json / traceability.json / spec-kit-binding.json` 的职责；把 API 阶段改成“影响分析和缺口记录优先，硬阻塞只针对不可实现或高风险冲突”；把 admin 从展示面升级为可观测控制面。

## Tool And Methodology Deep Dives

### OpenAI Codex

**定位**

Codex 是 OpenAI 的 coding agent 产品线，覆盖 ChatGPT/Codex app、cloud task、CLI、IDE 与 SDK。官方 Codex 页面强调多 agent workflow、built-in worktrees、cloud environments、Skills、Automations、review 与测试质量提升。Codex GA 公告还加入 Slack integration、Codex SDK、admin controls、monitoring 与 analytics。

**核心机制**

Codex cloud task 在隔离 cloud sandbox 中执行，预载仓库，可以读写文件、运行 test/lint/typecheck，并在任务完成后提供日志、测试输出、diff 与 PR 路径。Codex CLI 本地运行，可检查仓库、编辑文件、运行命令，并支持 subagents、local code review、web search、cloud tasks、MCP 和 approval modes。`AGENTS.md` 是其项目级指令入口。

**端到端覆盖**

覆盖 requirement clarification、code implementation、tests、review、PR、CI/CD automation。对 UI 设计真相、产品需求拆分和部署反馈的支持需要通过外部文件、Skills、MCP、Figma/Vercel/Cloudflare 等集成补齐。

**自动化能力**

强。适合并行 cloud tasks、local CLI execution、SDK embedding、Slack delegation、Automations、review automation。多 agent 并发和 worktree/cloud environment 是当前 coding-agent 栈里最接近 `spec-dev` 目标的执行能力。

**治理与可观测**

较强。官方资料强调 terminal logs、test outputs、citations、admin controls、environment controls、monitoring、analytics dashboard。仍然需要团队侧保持人工 review、branch protection、secret policy 与 MCP allowlist。

**风险与限制**

cloud task 对环境配置、依赖安装、私有服务访问、secret policy 依赖高；background automation 若接入 issue/alert/CI，需要防 prompt injection、数据外泄和误触发。Codex 不能替代产品验收与业务决策。

**适用场景**

复杂重构、批量测试补齐、低到中风险功能切片、多仓库重复任务、代码 review、CI/alert routine work、需要本地和云端联动的团队。

**对 spec-dev 的启发**

`spec-dev` 应把 Codex 作为“执行 worker + review worker + background routine worker”，但所有输入必须来自 `.ai-delivery` 与 Spec Kit bridge；所有写操作通过 worktree、测试、review、visual acceptance 与 governed merge 收敛。

Sources:

- https://openai.com/codex/
- https://openai.com/index/introducing-codex/
- https://openai.com/index/codex-now-generally-available/
- https://developers.openai.com/codex/cli
- https://github.com/openai/codex

### Claude Code

**定位**

Claude Code 是 Anthropic 的 agentic coding tool，可在 terminal、IDE、desktop app、browser 中工作，能读代码、改文件、跑命令、接入开发工具。它更偏本地工程师 pair/agent 环境，但也通过 GitHub Actions 进入 PR/issue 自动化。

**核心机制**

核心机制包括 `CLAUDE.md`/project memory、subagents、hooks、fine-grained permissions、MCP、worktrees、SDK 与 GitHub Actions。Subagents 有独立上下文、定制 prompt 与工具权限；hooks 可在工具调用、任务完成、subagent stop 等事件上接入 command/http/MCP/prompt/agent checks；permissions 可用 allow/ask/deny 与 mode 控制读写执行边界。

**端到端覆盖**

覆盖需求澄清、代码探索、实现、测试、review、PR automation。对设计/UI 真相、视觉验收和部署反馈没有内置一站式闭环，需要通过 Figma/Playwright/Sentry/GitHub/MCP 等连接。

**自动化能力**

强。适合本地深度改动、长上下文诊断、subagent 并行探索、worktree 隔离、hooks gated automation。GitHub Action 可通过 `@claude` 在 issue/PR 中触发实现或 PR creation。

**治理与可观测**

很强。Claude Code 的 permissions、hooks、managed settings、MCP scopes 和 worktree workflow 给团队提供了细粒度治理点。它比单纯 IDE chat 更适合放进 `spec-dev` 的 gate decision 和 verification loop。

**风险与限制**

本地 agent 权限如果开启过宽，能访问文件、shell、MCP、secret 或外部系统；hooks 和 MCP 自身也会带来供应链与 prompt injection 风险。Claude Code 适合被治理，不适合裸奔式 `bypassPermissions`。

**适用场景**

复杂棕地修复、跨模块重构、需要强工具控制的本地执行、需要 subagent 分工和 hooks 检查的流程、需要和 JIRA/Sentry/GitHub/DB 等系统协作的任务。

**对 spec-dev 的启发**

`spec-dev` 可吸收 Claude Code 的三个点：subagent context isolation、hooks as gates、permission modes as policy。现有 `ai-delivery-admin` MCP 应增加 allowlist、capability class、event hook 与 replayable trace，让 Claude/Codex 都能在同一治理面下执行。

Sources:

- https://code.claude.com/docs
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/common-workflows
- https://docs.anthropic.com/en/docs/claude-code/github-actions

### GitHub Copilot coding agent

**定位**

GitHub Copilot coding agent 是 PR-native background coding agent。它从 GitHub issue、GitHub UI、VS Code、Copilot Chat、MCP-compatible tools 等入口接任务，在 GitHub Actions-powered ephemeral environment 中工作，并创建或更新 pull request。

**核心机制**

Copilot coding agent 会根据 issue/chat prompt 制定改动、运行测试和 linter、提交分支、打开 PR、请求人类 review，并接受 PR comment 迭代。它自动处理 branch creation、commit message、push、PR body。MCP 可扩展其工具和上下文，默认 GitHub MCP 以当前 repo read-only token 连接。

**端到端覆盖**

覆盖 backlog issue -> code -> tests -> PR -> review iteration。需求、设计、UI acceptance、部署反馈不属于其核心，适合挂在 GitHub workflow 后段。

**自动化能力**

中高。它特别适合 low-to-medium complexity issues、documentation、test coverage、technical debt、security alert fixes。优势不是“最强 coding”，而是天然落在 GitHub audit trail、PR review 和 branch protection 里。

**治理与可观测**

强。官方文档描述 sandbox environment、firewall-controlled internet、`copilot/` branch 限制、PR workflow approval、不能 approve/merge 自己 PR、提交 co-author attribution、组织和企业 policy 约束、secret scanning、CodeQL/Advisory DB 等安全保护。

**风险与限制**

适合 GitHub-first 团队；复杂多阶段产品决策、Figma/UI 真相、跨 repo orchestration 需要外部系统补齐。MCP 扩权要谨慎，避免把 read-only GitHub agent 变成过宽外部系统写入者。

**适用场景**

GitHub issue backlog、PR follow-up、CI failure fix、test coverage、security campaign、documentation、small refactor。

**对 spec-dev 的启发**

`spec-dev` 可把 Copilot coding agent 作为“GitHub-native execution backend”。未来 `.ai-delivery` 中的 ready slice 可以生成 GitHub issue，Copilot 完成 PR 后由 `ai-delivery-admin` 读取 PR status、review comments、checks，并回写 traceability。

Sources:

- https://docs.github.com/en/copilot/using-github-copilot/coding-agent/about-assigning-tasks-to-copilot
- https://docs.github.com/en/copilot/using-github-copilot/coding-agent/extending-copilot-coding-agent-with-mcp
- https://docs.github.com/copilot/concepts/agents/openai-codex

### Cursor

**定位**

Cursor 是 AI-first IDE，核心强项是本地交互式编辑、Agent、rules、MCP、background agents 和 PR Bugbot。它非常适合开发者在代码和设计之间快速迭代，也能把部分任务交给 remote background agents。

**核心机制**

Cursor Project Rules 存在 `.cursor/rules`，可 version-controlled、path-scoped、manual/auto/agent-requested。MCP 连接外部工具和数据源，默认工具调用需要 approval，也可 auto-run。Background Agents 在隔离 Ubuntu VM 中异步运行，clone GitHub repo 并可自动运行 terminal commands。Bugbot 通过 GitHub PR diff 进行自动 review。

**端到端覆盖**

覆盖设计参考到代码、代码探索、实现、测试、PR review。需求治理、正式 spec、merge/deploy/ops loop 需要外部系统。

**自动化能力**

中高。Foreground Agent 强在高频人机协作；Background Agents 强在离线异步改动；Bugbot 补 review。它不天然提供 `spec-dev` 这种需求/状态事实层。

**治理与可观测**

中等。Rules 和 MCP approvals 可治理；Bugbot 有 PR comment trace；Background Agents 的 GitHub app、internet access、auto-run terminal commands 是高风险区域，需要额外 gate。

**风险与限制**

Cursor background agents 文档明确指出 code 运行在云端 isolated VMs，agent 有 internet access 且 auto-runs terminal commands。这意味着 prompt injection、dependency/script exfiltration、secret exposure 需要团队侧严格控制。

**适用场景**

快速 UI/UX iteration、局部 refactor、组件级实现、设计稿落地、人类持续 steering 的代码工作、PR 质量补充检查。

**对 spec-dev 的启发**

Cursor 的 `.cursor/rules` 模型适合启发 `spec-dev` 的 project-local rule scoping；Bugbot 启发自动 review lane；Background Agents 可作为候选执行 backend，但必须通过 `.ai-delivery` 生成 task package 并在受限 repo/secret/network 环境运行。

Sources:

- https://docs.cursor.com/background-agents
- https://docs.cursor.com/en/context/rules
- https://docs.cursor.com/en/context/mcp
- https://docs.cursor.com/bugbot

### GSD

**定位**

GSD, get-shit-done, 是面向 AI coding assistants 的 meta-prompting、context engineering 和 execution system。它强调解决 context rot，并把项目执行变成 `.planning` 文件、phase、plan、state、summary、parallel agents 和 verification 的循环。

**核心机制**

GSD 使用 `PROJECT.md`、`REQUIREMENTS.md`、`ROADMAP.md`、`STATE.md`、`PLAN.md`、`SUMMARY.md`、`todos/`、`threads/` 等文件承载上下文。典型流程是 `new-project -> discuss-phase -> plan-phase -> execute-phase -> verify-work -> ship`。它支持 codebase mapping、research agents、planner/checker/verifier、parallel execution waves、workstreams、pause/resume、threat model、security hardening 与 prompt injection scanning。

**端到端覆盖**

覆盖需求澄清、roadmap、phase planning、执行、验证、ship/PR。UI/Figma、API 合同、traceability 等需要项目自定义。

**自动化能力**

强。尤其适合长周期项目、跨会话恢复、并行执行和自动推进。它的优势在“把 agent 当工程执行系统管理”，不是在某个模型本身。

**治理与可观测**

较强。状态文件、summary、verification、security scanning、threat model、plan checking 都有审计价值。但 `.planning` 如果与 `.ai-delivery` 并存，会变成第二事实层。

**风险与限制**

流程侵入性较高；如果直接引入，会与 `spec-dev` 的 `.ai-delivery`、`todo.md`、Spec Kit bridge 和 admin runtime 重叠。GSD 的默认世界观是 `.planning`，而 `spec-dev` 已经选择 `.ai-delivery`。

**适用场景**

个人或小团队希望 AI 长周期推进项目、需要上下文工程和自动执行节奏、尚未建立自有 control plane 的项目。

**对 spec-dev 的启发**

不要引入 `.planning` 作为第二真相。应该吸收 GSD 的执行节奏：phase discussion、research before planning、plan checker、execution waves、verification, pause/resume handoff、thread memory、security scan。

Sources:

- https://github.com/gsd-build/get-shit-done
- Local reference: `/Users/charvin/Projects/spec-dev/gsd-vs-spec-kit-调研总结.md`
- Local reference: `/Users/charvin/Projects/spec-dev/get-shit-done-and-spec-kit-联合实施指南.md`

### Spec Kit

**定位**

Spec Kit 是 GitHub 开源的 Spec-Driven Development toolkit，目标是让团队关注 product scenarios 与 predictable outcomes，而不是从零 vibe coding。它把规格变成主要事实源，再生成计划和任务。

**核心机制**

核心命令链是 constitution、specify、plan、tasks、implement，并提供 clarify、analyze、checklist、taskstoissues 等增强命令。产物包括 `constitution.md`、`spec.md`、`plan.md`、`tasks.md`、contracts、data-model、quickstart、research 等。`tasks.md` 按 user story、依赖和可并行标记组织，可直接供 agent 执行。

**端到端覆盖**

强在需求、规格、计划、任务和实现入口。它对 UI 设计证据、运行态状态、blocker recovery、merge queue、admin observability 不负责。

**自动化能力**

中等到强。`/speckit.implement` 可以执行任务，但 Spec Kit 最核心价值仍是结构化 definition pipeline，而不是项目级 runtime control plane。

**治理与可观测**

中等。constitution、spec、plan、tasks、checklist 和 analyze 都能减少歧义。但缺少受控写入、状态机、跨 agent 日志、worktree/merge governance。

**风险与限制**

容易停留在文档层；如果没有执行层和观测层，`spec.md/plan.md/tasks.md` 会与代码和运行态漂移。对于 `spec-dev`，Spec Kit 应是桥，不是唯一事实源。

**适用场景**

跨端复杂功能、需要先统一需求和验收的功能、绿地 feature、需要把任务拆到可执行单元的项目。

**对 spec-dev 的启发**

当前 `spec-dev` 选择 Spec Kit 作为 bridge 是正确的。下一步应强化 bind：`spec-kit-input.md` 必须从 `.ai-delivery` 生成，`spec-kit-binding.json` 回写 traceability，并明确 `.specify` 是 derived planning artifact。

Sources:

- https://github.com/github/spec-kit
- Local reference: `/Users/charvin/Projects/spec-dev/skills/spec-kit/spec-driven.md`

### OpenSpec

**定位**

OpenSpec 是轻量、迭代、棕地友好的 spec-driven framework。它强调 change folder、proposal/spec/design/tasks、implementation 和 archive，减少重型阶段门禁。

**核心机制**

典型流程是 `proposal -> planning -> implementation -> archive`，命令可表达为 `/opsx:new`、`/opsx:ff`、`/opsx:apply`、`/opsx:archive`。每个 change 生成 proposal、specs、design、tasks；完成后 archive 到 permanent specs。

**端到端覆盖**

覆盖需求对齐、变更设计、任务、实现和知识沉淀。它不像 `spec-dev` 一样内置 Figma/API/traceability/worktree/merge/admin runtime。

**自动化能力**

中等。更偏轻量 change management 和 context persistence，而不是强执行编排。

**治理与可观测**

中等。reviewable proposal、spec delta 和 archive 有利于审计；但没有完整 gate/state/worktree/MCP governance。

**风险与限制**

与 Spec Kit 重叠。如果在 `spec-dev` 中直接并列引入，会出现 `OpenSpec changes/`、`.specify/specs/`、`.ai-delivery/requirements/` 三套需求与状态。

**适用场景**

棕地小变更、个人项目、团队希望用轻量 change proposal 管理 AI 代码改动，但不想引入完整控制面。

**对 spec-dev 的启发**

吸收 archive 和 change delta，不引入第二 spec framework。`spec-dev` 可在 `.ai-delivery` 中增加“完成后归档摘要”，把每个 slice 的决策、diff、验证、视觉验收、PR 链接沉淀为 future context。

Sources:

- https://openspec.pro/
- https://openspec.pro/workflow/
- Local reference: `/Users/charvin/Projects/spec-dev/skills/OpenSpec/README.md`

### BMad

**定位**

BMad Method 是 AI-driven development framework，提供 specialized AI agents、guided workflows 和 planning tracks，覆盖 ideation/planning 到 agentic implementation。它更像多角色软件交付方法论包。

**核心机制**

BMad 的基础过程包含 Analysis、Planning、Solutioning、Implementation 四阶段。按复杂度提供 Quick Flow、BMad Method、Enterprise 三种 planning tracks。Implementation 阶段以 sprint/status、epic/story、developer agent、create-story、dev-story、code-review 等循环推进。

**端到端覆盖**

覆盖产品分析、PRD/spec、architecture、UX、epic/story、implementation、code review。对具体代码执行、安全沙箱、MCP 写入、CI/deploy/ops feedback 的约束需要外部系统。

**自动化能力**

中高。它的 agent role 和 workflow map 很完整，适合把产品/架构/UX/开发拆给不同 agent。

**治理与可观测**

中等。BMad 的 artifact 和 workflow 有管理价值，但不等同于 `.ai-delivery` 这种 runtime fact layer。

**风险与限制**

对 `spec-dev` 当前目标可能偏重。若全量引入，会把已有 requirement breakdown、ui mapping、interaction design、Spec Kit bridge 又包一层角色流程。

**适用场景**

从零到一产品、多角色 AI planning、企业级需求/架构/安全/DevOps 文档都需要纳入 agent workflow 的团队。

**对 spec-dev 的启发**

吸收角色分工和 track selection：简单任务走 Quick Flow，复杂 UI/API/跨端任务走完整 pre-dev；enterprise/high-risk 任务增加 security/devops gates。不要复制其全部 artifact 层。

Sources:

- https://docs.bmad-method.org/
- https://docs.bmad-method.org/tutorials/getting-started/
- https://docs.bmad-method.org/reference/modules/

### Lovable

**定位**

Lovable 是 full-stack AI development platform，面向自然语言构建、迭代和部署 web applications，强调真实可编辑代码、frontend/backend/database/auth/integrations、GitHub sync、enterprise governance。

**核心机制**

用户用自然语言描述 app，Lovable 生成 working application；可接 Lovable Cloud 或 Supabase，支持 Stripe/Resend 等集成，项目可 sync to GitHub 并纳入现有工程流程。发布后可使用 Lovable URL/custom domain，并在 Business/Enterprise 控制访问。

**端到端覆盖**

覆盖需求 prompt、UI、backend、database、auth、integrations、deploy/publish。对复杂棕地 repo 的模块边界、测试策略、review/merge governance 和生产观测，需要转入 GitHub/工程系统后补齐。

**自动化能力**

强，尤其是 MVP 和 SaaS/internal tool 0->1。它不是代码库内细粒度工程变更 agent，而是平台化 app generator。

**治理与可观测**

中高。官方文档提到 workspace、roles、security/privacy/compliance、SOC 2 Type II、ISO 27001、GDPR、SSO/SCIM 等。但这些治理是平台治理，不是项目内 traceability。

**风险与限制**

生成速度快但容易绕开既有架构、设计系统、API 合同和测试深度。对复杂 brownfield，不应让 Lovable 直接成为核心代码入口。

**适用场景**

MVP、internal tools、营销页、早期产品验证、非核心业务原型、产品/设计/市场团队快速验证。

**对 spec-dev 的启发**

Lovable 可作为 prototype source。`spec-dev` 应允许把 Lovable 结果作为需求和交互参考导入 `.ai-delivery`，但正式开发仍走 requirement/Figma/API/Spec Kit/worktree/review。

Sources:

- https://docs.lovable.dev/introduction/welcome
- https://docs.lovable.dev/introduction/getting-started
- https://docs.lovable.dev/features/deploy
- https://docs.lovable.dev/features/custom-domain

### Replit Agent

**定位**

Replit Agent 是 browser-native AI app creation platform 的核心 agent，可从自然语言生成、设置、调试和发布应用。Replit 更像“浏览器里的开发环境 + hosting + AI agent + collaboration”。

**核心机制**

Replit 提供单浏览器 tab 中的 code editor、preview、deployment、database、collaboration、version control。Agent/Assistant 可生成完整 app、补全代码、自动检测错误、生成文档。Canvas 允许把设计 mockup、live app preview、截图、标注、多个方向并排比较，并把设计变成 full app。

**端到端覆盖**

覆盖 idea -> design mockup -> full app -> database/backend -> publish。对企业级 brownfield 的 repo governance、PR review、traceability 和复杂 CI/CD 不如 GitHub-native 或自建控制面。

**自动化能力**

强。特别适合从空白到可运行 demo、教育/学习、轻量 full-stack app、团队协作原型。

**治理与可观测**

中等。Replit 有平台运行、publish、database、collaboration 和 preview，但不是以企业 PR gate 和 `.ai-delivery` traceability 为中心。

**风险与限制**

平台环境与生产环境可能不一致；复杂多仓库、私有服务、既有设计系统和安全策略迁入成本较高。Agent 做出的架构选择需要人工审查。

**适用场景**

快速原型、教学、hackathon、简单 full-stack 工具、需要零本地环境的协作。

**对 spec-dev 的启发**

Replit 的 Canvas 很适合启发 `spec-dev` 的“设计验证沙盘”：多个 UI 方案、交互流、设备尺寸预览、从 design frame 转 full app。但正式落地仍应回到 repo + tests + PR。

Sources:

- https://docs.replit.com/getting-started/intro-replit
- https://docs.replit.com/replitai/canvas

### v0

**定位**

v0 是 Vercel 的 AI agent，用 prompt 创建 real code、full-stack apps、agents 和 high-fidelity UI，并可直接部署到 Vercel 或打开 PR。

**核心机制**

v0 从 text prompt、screenshots、files、Figma 等输入生成 UI/code，默认 Next.js，对 full-stack app 支持 RSC、App Router API routes、Supabase/Neon/Upstash 等数据库集成。可一键部署到 Vercel，使用 production URL、preview deployment、analytics、monitoring 和 Fix with v0。

**端到端覆盖**

强在 UI、React/Next.js app、backend API routes、database integration、deployment。需求治理、跨端客户端、复杂后端服务、企业工作流、视觉验收和长期维护需要外部流程。

**自动化能力**

强。尤其适合 landing page、dashboard、SaaS prototype、Next.js full-stack app、设计到可运行 demo。

**治理与可观测**

中等到高。Vercel deployment、preview、monitoring、analytics 是强项；但 spec traceability 和业务 gate 需要团队补。

**风险与限制**

框架倾向明显，Next.js/Vercel 路径最顺。对非 Web、非 Next、复杂移动端或已有后端架构不应强行迁就。

**适用场景**

Web prototype、React components、Next.js MVP、设计稿快速转实现、营销/内容/数据 dashboard。

**对 spec-dev 的启发**

v0 是很好的 UI prototype backend。`spec-dev` 可以把 v0 输出作为视觉/交互候选，再由 `.ai-delivery` 绑定 Figma、API 和验收标准，避免让 v0 直接定义产品真相。

Sources:

- https://v0.app/docs
- https://v0.app/docs/full-stack-apps
- https://v0.app/docs/deployments

### Figma Make

**定位**

Figma Make 是 Figma 的 AI-driven prompt-to-code / prompt-to-app 工具，用于把 ideas 和 existing Figma designs 变成 functional prototypes、web apps 和 interactive UI。

**核心机制**

核心是 AI chat + preview + code editor。用户可以导入 Figma design、图片或组件，用 prompt 生成 web app/prototype，也能手动编辑代码。Figma Make 支持下载 zip、push to GitHub、发布到 live web、使用 design system packages 和 Make kits。Make kits 可把生产级 React design system 引入 Figma Make，使 prototype 使用与生产一致的组件。

**端到端覆盖**

强在设计到可交互原型、设计系统验证、UI 代码、简单 web app。后端、复杂业务、测试、review、merge/deploy governance 需要外部工具。

**自动化能力**

中高。它是设计组织内最自然的 AI app/prototype generator，尤其适合设计师和 PM 从 Figma 上下文进入代码。

**治理与可观测**

中等。GitHub push、download code、design system packages、MCP Server 提供工程衔接点。但它不是完整软件交付控制面。

**风险与限制**

Make kits 当前主要面向 React design systems。Figma Make 输出如果绕开真实 repo、API 合同和测试，会产生 prototype 与生产实现漂移。

**适用场景**

高保真 prototype、设计系统验证、设计评审前的 functional mock、把 Figma frame 变成可点击 web app。

**对 spec-dev 的启发**

Figma Make 最值得吸收的是“设计系统作为可执行真相”。`spec-dev` 应把 Figma evidence、Make prototype、design-system package 和 visual acceptance 纳入同一 traceability，而不是只保存截图或节点描述。

Sources:

- https://developers.figma.com/docs/code/intro-to-figma-make/
- https://help.figma.com/hc/en-us/articles/35710574222487-Beyond-the-basics-Using-Figma-Make
- https://help.figma.com/hc/en-us/articles/35946832653975-Use-your-design-system-package-in-Make-kits

### Cross-Tool Comparison

| Tool | Best Role | Requirement | UI | Backend/API | Client | Test/Review | Governance | Recommended `spec-dev` Use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex | 主力执行 agent | 中 | 中 | 强 | 强 | 强 | 强 | worktree/cloud worker + review + automation |
| Claude Code | 本地深水执行与治理 agent | 中 | 中 | 强 | 强 | 强 | 很强 | hooks/permissions/subagents/worktree 模型 |
| GitHub Copilot coding agent | GitHub PR-native worker | 弱到中 | 弱 | 中 | 中 | 强 | 强 | issue/PR backend worker |
| Cursor | IDE + background agent + PR review | 弱到中 | 强 | 中 | 强 | 中 | 中 | 快速 UI/code iteration + Bugbot |
| GSD | 执行编排方法论 | 强 | 中 | 中 | 中 | 强 | 中高 | 吸收 execution rhythm，不复制 `.planning` |
| Spec Kit | 规格驱动框架 | 强 | 中 | 中 | 中 | 中 | 中 | 继续作为 derived spec/plan/tasks bridge |
| OpenSpec | 轻量 change/spec framework | 中高 | 中 | 中 | 中 | 中 | 中 | 吸收 archive/change delta |
| BMad | 多角色规划与交付方法论 | 强 | 中高 | 中 | 中 | 中 | 中 | 吸收 role/track 分层 |
| Lovable | full-stack app generator | 中 | 强 | 强 | 弱 | 弱到中 | 中高 | prototype/MVP source |
| Replit Agent | browser full-stack builder | 中 | 强 | 强 | 中 | 中 | 中 | sandbox prototype and design exploration |
| v0 | Web/Next.js prototype and app builder | 中 | 很强 | 中高 | 弱到中 | 中 | 中 | UI/Next.js candidate implementation |
| Figma Make | design-to-functional prototype | 中 | 很强 | 弱到中 | 弱到中 | 弱 | 中 | design truth/prototype evidence |

## Layered Taxonomy

### Coding Agents

代表：Codex、Claude Code、GitHub Copilot coding agent、Cursor。

这一层负责“拿到清晰 task 后，把代码改出来并验证”。它们不应该直接拥有需求真相。最佳输入是：冻结后的 requirement slice、API mapping、UI acceptance contract、Spec Kit tasks、repo rules、测试命令、允许写入范围和验收 gate。

`spec-dev` 应吸收：

- Codex 的 multi-agent/cloud/local/Skills/Automations。
- Claude Code 的 subagent、hooks、permissions、worktree。
- Copilot 的 PR-native audit trail 和 branch protection。
- Cursor 的 high-frequency UX iteration 与 PR Bugbot。

### Workflow Orchestration Frameworks

代表：GSD、BMad、`ai-delivery-orchestrator`。

这一层负责“什么时候该问人、什么时候该生成 plan、什么时候该派工、什么时候该暂停”。它不是 spec 内容本身，也不是代码 agent 本身，而是 stage decision layer。

`spec-dev` 现有 `ai-delivery-orchestrator` 已经具备良好方向：`.ai-delivery` fact layer、`todo.md` execution panel、stage guards、checkpoints、blocker recovery、worktree/merge governance。需要补强的是：状态词压缩、自动 resume、CI/PR/deploy feedback 接入。

### Spec-Driven Frameworks

代表：Spec Kit、OpenSpec。

这一层负责把意图转成可 review 的 spec/plan/tasks/change proposal。Spec Kit 更完整、阶段更强，适合当前 `spec-dev`；OpenSpec 更轻、更适合棕地小变更和 archive。

`spec-dev` 应继续使用 Spec Kit，但保持 derived bridge 角色：

```text
.ai-delivery facts
-> spec-kit-input.md
-> official speckit-specify/plan/tasks
-> spec-kit-binding.json
-> traceability.json.spec_kit_refs
```

### Design-To-Code Platforms

代表：Figma Make、v0、Cursor、Replit Canvas。

这一层负责“把设计变成可交互候选实现”。它的输出应视为 prototype evidence，而不是最终业务事实。对 UI-heavy feature，推荐从 Figma truth 开始，必要时用 Figma Make/v0 生成候选，然后把视觉/交互决策写回 `.ai-delivery`。

`spec-dev` 应新增：视觉验收自动化、设计系统 package 引用、Figma node/code evidence freshness、prototype-to-production delta review。

### Cloud Full-Stack Generation Platforms

代表：Lovable、Replit Agent、v0。

这一层负责快速生成 full-stack app，包括 UI、backend、database、auth、deployment。它适合探索和 MVP，不适合直接作为复杂棕地交付主链路。

`spec-dev` 可以接收它们的输出作为：

- 产品 demo。
- 交互原型。
- API/数据模型灵感。
- 用户验收讨论材料。

但正式实现仍应由 `.ai-delivery + Spec Kit + coding agent + tests/review` 接管。

### Governance And Observability Layers

代表：GitHub branch protection/Actions、Codex admin controls、Claude permissions/hooks、Cursor rules/MCP approvals、`ai-delivery-admin`、MCP server、traceability。

这一层决定 AI 能不能被放心使用。治理不是“多写几个文档”，而是：

- agent 可读什么、可写什么、可执行什么。
- 每次状态流转有没有证据。
- 每个 blocker 有没有恢复条件。
- 每个 PR 是否能追溯到 requirement/design/API/test。
- 每次失败是否能 resume，而不是重新聊天。

`spec-dev` 的目标架构应该让这一层成为 control plane，而不是把控制散在 prompt、Markdown 和口头约定里。

## End-To-End One-Stop Workflow

### Recommended Integrated Chain

```text
Product requirement
-> requirement breakdown
-> API context capture
-> Figma evidence and UI acceptance
-> interaction and delivery slices
-> Spec Kit spec/plan/tasks
-> worktree-isolated Codex or Claude Code implementation
-> automated tests and code review
-> visual acceptance
-> governed merge
-> deployed feedback and follow-up tasks
```

### 1. Requirements

推荐工具组合：`requirement-breakdown` + `ai-delivery-admin` bootstrap + optional Spec Kit clarify。

输入：产品需求、业务规则、非目标、优先级、约束。

输出：`.ai-delivery/requirements/<id>/requirement.md`、`breakdown-summary.md`、`global-rules.md`、sub-requirements、dependency graph。

门禁：需求包存在；子需求可追踪；冲突进入 blocker。

AI 自动范围：拆分、命名、依赖初判、缺口列举。

人类必须介入：产品语义冲突、范围取舍、优先级、合规/安全决策。

### 2. Design And UI

推荐工具组合：Figma MCP/Figma evidence + `ui-requirement-mapping` + `ui-acceptance-contract` + optional Figma Make/v0 prototype。

输入：Figma node/frame、design tokens、组件约束、目标状态、交互说明。

输出：`figma-mapping.md`、`ui-acceptance-contract.md`、visual acceptance checklist、prototype evidence。

门禁：UI-bearing sub-requirement 必须达到 `acceptance_frozen` 后才能进入 Spec Kit。

AI 自动范围：节点提取、状态映射、视觉差异列举、候选交互推断。

人类必须介入：Requirement 与 Figma 冲突、缺失关键状态、设计系统偏离、品牌/体验取舍。

### 3. API And Backend

推荐工具组合：`api-contract-mapping` + OpenAPI/Swagger/GraphQL sources + backend coding agent。

输入：API contract、服务端源码、数据模型、权限规则、错误码、mock/fixture。

输出：`api-contract-mapping.md`、operation refs、field gaps、downstream revalidation targets。

门禁：缺少 API 不应默认硬阻塞；只有无法实现、需求冲突、安全/数据风险时阻塞。

AI 自动范围：接口匹配、字段缺口、兼容策略、mock 建议、测试契约草案。

人类必须介入：新增/变更 API 合同、权限模型、数据迁移、第三方集成风险。

### 4. Client Implementation

推荐工具组合：Spec Kit tasks + Codex/Claude Code + worktree + project rules。

输入：slice contract、Spec Kit tasks、traceability refs、UI acceptance、API mapping、repo instructions。

输出：实现代码、测试、migration、docs、agent summary。

门禁：依赖 slice 已 merged；worktree 已隔离；写入范围清楚。

AI 自动范围：组件实现、业务逻辑、适配层、测试补齐、文档更新。

人类必须介入：跨架构边界重构、产品行为变更、高风险迁移、不可恢复数据变更。

### 5. Testing

推荐工具组合：repo test runner + Codex/Claude verification + Playwright/visual checks + CI。

输入：tasks.md、acceptance criteria、API contract、visual acceptance contract。

输出：unit/integration/e2e/visual test results、terminal logs、failure analysis。

门禁：失败必须进入 auto-fix retry；重复失败进入 blocker。

AI 自动范围：补测试、运行测试、修复确定性失败、生成 failure summary。

人类必须介入：测试目标与产品目标冲突、flaky infra、无法复现的问题。

### 6. Review

推荐工具组合：Codex review、Claude review、Cursor Bugbot、GitHub Copilot code review、human reviewer。

输入：diff、traceability、test outputs、risk notes。

输出：review findings、auto-fix patches、approved/unapproved state。

门禁：高优先级 findings 必须修复或记录 accepted risk；AI 自己生成的 PR 不能自己批准。

AI 自动范围：bug/security/code quality review、PR body、traceability check、simple fix。

人类必须介入：风险接受、架构方向、业务语义、final approval。

### 7. Merge And Deploy

推荐工具组合：GitHub PR/branch protection + `ai-delivery-admin` merge finalization + deployment provider。

输入：approved PR、passing checks、visual acceptance、merge queue status。

输出：merged state、runtime convergence files、deployment URL、release notes。

门禁：UI-bearing slice 必须 `visual_acceptance_passed`；dependency unlock 只在 merge finalization 后发生。

AI 自动范围：merge readiness summary、release note draft、post-merge traceability update。

人类必须介入：production deploy approval、feature flag rollout、incident-sensitive release。

### 8. Operations Feedback

推荐工具组合：Sentry/Datadog/Cloud logs + MCP + Codex Automations/GitHub Issues + `ai-delivery-admin`。

输入：error events、performance metrics、user feedback、support tickets、CI/deploy signals。

输出：follow-up requirement、bug slice、rollback/forward-fix recommendation、traceability update。

门禁：agent 可 triage 和 draft，但不能自动处理高风险 production action。

AI 自动范围：告警归类、复现线索收集、issue 创建、低风险修复草案。

人类必须介入：事故等级、用户影响判断、回滚/数据修复/合规通知。

## Current spec-dev Workflow Assessment

### Local Baseline

本报告以本地仓库为准：

- `/Users/charvin/Projects/spec-dev/ai-delivery-kit`
- `/Users/charvin/Projects/spec-dev/ai-delivery-admin`

关键事实：

- `ai-delivery-kit` 将业务项目侧 workflow skills 放在 `.agents/skills/ai-delivery/`。
- `.ai-delivery` 包含 `requirements/`、`figma-cache/`、`runtime/`、`logs/`、`meta/`。
- `ai-delivery-orchestrator` 明确三层模型：`.ai-delivery/*` fact layer、`todo.md` execution panel、orchestrator decision layer。
- Spec Kit bridge 是 `.ai-delivery facts -> spec-kit-input.md -> official speckit-* -> spec-kit-binding.json -> traceability.json`。
- `ai-delivery-admin` 是独立 control-plane 项目，只拥有 admin-local bindings、schemas、adapters、server/web、support skill、MCP server，不迁移业务真相。
- `ai-delivery-admin` MCP server 提供 binding、read tools、governed writes，包括 bootstrap、logs、status transitions、blocker resume、dependency checks、worktree/merge tracking、artifact writes。

### Current Strengths

1. `.ai-delivery` 作为事实层的方向正确。
   它比单纯 `.specify` 或聊天历史更适合作为 AI delivery runtime：需求、Figma、API、状态、日志、blocker、worktree 和 merge 都能集中追踪。

2. 双真相源边界清晰。
   Requirement 管功能，Figma 管视觉；冲突阻塞，而不是让 agent 自行补需求或补 UI。这是高保真 AI 交付的关键。

3. Orchestrator 明确区分 fact、execution panel、decision layer。
   这是避免 `todo.md` 漂移成第二真相源的好设计。

4. Spec Kit bridge 选择正确。
   Official Spec Kit 保持 upstream-style，repo-specific rules 放在 orchestrator，不 fork 官方技能体，降低维护成本。

5. Admin/MCP 控制面方向正确。
   `ai-delivery-admin` 不拥有业务真相，只提供治理、展示、状态流转、blocker、artifact 和 runtime daemon 管理。这正是“AI 可执行，但写入受控”的形态。

6. Traceability 是核心治理对象。
   本地 `traceability.json` 已同时承载 requirement refs、Figma nodes、API mapping 和 `spec_kit_refs`，这比普通任务清单更接近可审计 delivery graph。

7. Worktree 和 merge governance 已进入主链路。
   当前 orchestrator 明确 development stage 包含 worktree、TDD、review、visual acceptance、verification、merge；这是并行 agent 的基本安全条件。

### Current Risks

1. 状态词和阶段词仍偏多。
   本地 `workflow-policy.json` 有 `workflow_gates`、`status_sequence`、`governance_events`；orchestrator 又有 stage mapping、checkpoint、runtime modes。语义强，但 agent 执行时容易把 gate、status、event、phase 混用。

2. Markdown artifact 数量偏多。
   Requirement、breakdown、global rules、slice、api mapping、figma mapping、acceptance、interaction、Spec Kit input/spec/plan/tasks/binding、todo、decisions、traceability、status 都有价值，但同步成本高。

3. `todo.md / status.json / traceability.json / spec-kit-binding.json` 有漂移风险。
   Orchestrator 已声明 `todo.md` 不是事实源，但如果没有自动 reconcile 和 diff check，长会话后仍可能漂移。

4. API 阶段有过度门禁风险。
   当前已经有 non-blocking policy 的方向，但实际执行时 agent 容易把 API contract 缺失当成阻塞，而不是记录缺口并继续 UI/client 可验证部分。

5. Visual acceptance 自动化仍不足。
   现有门禁要求 UI-bearing slice 合并前 `visual_acceptance_passed`，但缺少统一 screenshot diff、viewport matrix、Figma evidence freshness、design-system code reference 的自动检查面。

6. CI/cloud agent feedback loop 还没闭环。
   `ai-delivery-admin` 有 runtime 和 logs，但还没完全接入 GitHub PR、CI checks、deployment URL、error monitoring、post-release feedback。

7. Admin 支持面可能仍偏“读写 API”，还不是完整 operations cockpit。
   下一步要从 artifact viewer 升级到 queue、risk、agent sessions、CI/deploy feedback、recovery action 的控制面。

## spec-dev Optimization Recommendations

### Keep

- Keep `.ai-delivery` as the only workflow fact layer.
- Keep Requirement/Figma dual truth and conflict-blocking rule.
- Keep project-local skills under `.agents/skills/ai-delivery/`.
- Keep Spec Kit as official derived bridge.
- Keep `traceability.json` as first-class governed artifact.
- Keep worktree isolation, review, visual acceptance and verification before merge.
- Keep `ai-delivery-admin` as external control plane, not business truth owner.

### Absorb

- From Codex: cloud/local unified tasks, multi-agent worktrees, Skills, Automations, review agent and admin analytics.
- From Claude Code: subagent isolation, hooks, permission rules, MCP scopes, worktree lifecycle.
- From GitHub Copilot coding agent: PR-native execution, branch protection, independent review rule, ephemeral GitHub Actions environment.
- From Cursor: scoped rules, background agent UX, Bugbot style PR comments.
- From GSD: execution waves, pause/resume handoff, plan checker, verifier, security prompt scanning.
- From OpenSpec: change archive and compact spec delta review.
- From BMad: track selection by complexity and role-specific agents.
- From Figma Make/v0/Replit/Lovable: prototype import path and design-system-backed UI exploration.

### Avoid

- Avoid adding `.planning` or `openspec/changes` as equal truth stores.
- Avoid treating cloud full-stack generators as production source of truth for complex brownfield work.
- Avoid giving background agents broad MCP write access, unbounded internet, or secrets.
- Avoid making missing API docs a universal blocker.
- Avoid requiring human confirmation at every low-risk transition; reserve human gates for product, risk, merge and production decisions.

### Split

- Split fact layer from execution panel more visibly:
  - `.ai-delivery`: only governed facts.
  - `todo.md`: queue/recovery panel.
  - `.specify`: derived spec/plan/tasks.
  - admin DB: local binding/cache only.
- Split “gate status” from “event log”:
  - status answers where a sub-requirement is.
  - event answers what happened.
  - traceability answers why this state is justified.

### Merge

- Merge duplicated stage vocabulary into one canonical state map.
- Merge `api_contract`, `ui_evidence`, `ui_acceptance_freeze`, `interaction` descriptions into reusable gate contracts.
- Merge end-of-slice summary, PR link, test log, visual acceptance and deploy feedback into a single slice closure record.

### Refactor

- Refactor orchestrator reconcile into an explicit command/check:
  - read `.ai-delivery`;
  - verify todo guards;
  - verify Spec Kit binding freshness;
  - verify traceability refs;
  - output next safe action.
- Refactor admin MCP tool classes:
  - read-only inspection;
  - low-risk append/log;
  - guarded transition;
  - versioned artifact write;
  - merge/finalization;
  - external feedback ingestion.
- Refactor API stage to impact analysis:
  - `mapped`;
  - `missing_nonblocking`;
  - `blocked_contract_conflict`;
  - `blocked_security_or_data_risk`.
- Refactor visual acceptance into automated contract:
  - required viewports;
  - Figma node refs;
  - screenshots;
  - allowed deltas;
  - design-system component evidence;
  - Playwright/browser logs.

### Add

- Add source index per requirement: requirement, Figma, API, Spec Kit, PR, CI, visual, deploy, monitoring.
- Add automatic PR/CI ingestion from GitHub.
- Add code review agent lane with severity mapping and accepted-risk workflow.
- Add deployment feedback ingestion: URL, environment, release time, health signal.
- Add operations feedback loop: Sentry/logs/support -> `.ai-delivery` follow-up slice.
- Add agent session registry: who ran, environment, branch/worktree, tools, commands, outputs.
- Add recovery dashboard: blocked items, stale worktrees, failed gates, retry candidates.

## Phased Adoption Roadmap

### Near Term: Low-Risk Workflow And Documentation Cleanup

1. Create canonical state vocabulary.
   Reduce stage/status/event overlap and document one state map used by skills, admin and MCP.

2. Add source index to each requirement package.
   One place lists requirement, Figma, API, Spec Kit artifacts, PRs, CI runs, screenshots and deployment URLs.

3. Make API mapping explicitly non-blocking by default.
   Block only on true conflict, data/security risk, or impossible implementation.

4. Add reconcile check command.
   A script or MCP read tool should compare `todo.md`, `status.json`, `traceability.json`, `spec-kit-binding.json` and report drift.

5. Add slice closure template.
   Each merged slice records diff summary, tests, review, visual acceptance, PR and follow-up risks.

### Mid Term: Orchestrator And Admin Control Plane Upgrade

1. Upgrade `ai-delivery-admin` from artifact explorer to execution cockpit.
   Show queue, next safe action, blockers, agent sessions, worktrees, PRs, CI and visual checks together.

2. Add governed CI/PR ingestion.
   Read GitHub PR/check status and map it back to `.ai-delivery` slices.

3. Add visual acceptance automation.
   Store screenshot evidence, viewport matrix, Figma freshness and diff summary.

4. Add review agent integration.
   Codex/Claude/Cursor Bugbot/Copilot review outputs should normalize to a common finding schema.

5. Add policy-based agent backend selection.
   Simple GitHub issue -> Copilot; deep local task -> Claude/Codex; UI prototype -> v0/Figma Make; full-stack MVP -> Lovable/Replit; production slice -> `spec-dev` chain.

### Long Term: Multi-Agent Scheduling And Feedback-Driven Delivery

1. Multi-agent dispatcher.
   Use dependency graph and risk class to schedule independent slices into worktrees/cloud tasks.

2. Background routine agents.
   Codex Automations or equivalent agents monitor CI failures, stale blockers, dependency alerts and production errors.

3. Deployment feedback loop.
   Production metrics and incidents generate follow-up requirements, not just bug tickets.

4. Agent replay and audit.
   Every meaningful agent action is replayable from source refs, tool calls, logs and artifacts.

5. Self-healing queue.
   Failed review/visual/test gates enter bounded auto-fix loops before escalation; unrecoverable blockers wake humans with exact missing decision.

## Source Index

| Area | Source |
| --- | --- |
| OpenAI Codex product | https://openai.com/codex/ |
| OpenAI Codex launch mechanics | https://openai.com/index/introducing-codex/ |
| OpenAI Codex GA, SDK, Slack, admin controls | https://openai.com/index/codex-now-generally-available/ |
| OpenAI Codex CLI docs | https://developers.openai.com/codex/cli |
| OpenAI Codex CLI repository | https://github.com/openai/codex |
| Claude Code overview | https://code.claude.com/docs |
| Claude Code subagents | https://code.claude.com/docs/en/sub-agents |
| Claude Code hooks | https://code.claude.com/docs/en/hooks |
| Claude Code permissions | https://code.claude.com/docs/en/permissions |
| Claude Code MCP | https://code.claude.com/docs/en/mcp |
| Claude Code worktrees/common workflows | https://code.claude.com/docs/en/common-workflows |
| Claude Code GitHub Actions | https://docs.anthropic.com/en/docs/claude-code/github-actions |
| GitHub Copilot coding agent | https://docs.github.com/en/copilot/using-github-copilot/coding-agent/about-assigning-tasks-to-copilot |
| Copilot coding agent MCP | https://docs.github.com/en/copilot/using-github-copilot/coding-agent/extending-copilot-coding-agent-with-mcp |
| GitHub OpenAI Codex agent integration | https://docs.github.com/copilot/concepts/agents/openai-codex |
| Cursor background agents | https://docs.cursor.com/background-agents |
| Cursor rules | https://docs.cursor.com/en/context/rules |
| Cursor MCP | https://docs.cursor.com/en/context/mcp |
| Cursor Bugbot | https://docs.cursor.com/bugbot |
| GSD | https://github.com/gsd-build/get-shit-done |
| Spec Kit | https://github.com/github/spec-kit |
| OpenSpec | https://openspec.pro/ |
| OpenSpec workflow | https://openspec.pro/workflow/ |
| BMad Method | https://docs.bmad-method.org/ |
| BMad getting started | https://docs.bmad-method.org/tutorials/getting-started/ |
| BMad modules | https://docs.bmad-method.org/reference/modules/ |
| Lovable docs | https://docs.lovable.dev/introduction/welcome |
| Lovable getting started | https://docs.lovable.dev/introduction/getting-started |
| Lovable deploy | https://docs.lovable.dev/features/deploy |
| Lovable custom domain | https://docs.lovable.dev/features/custom-domain |
| Replit introduction | https://docs.replit.com/getting-started/intro-replit |
| Replit Canvas | https://docs.replit.com/replitai/canvas |
| v0 docs | https://v0.app/docs |
| v0 full-stack apps | https://v0.app/docs/full-stack-apps |
| v0 deployments | https://v0.app/docs/deployments |
| Figma Make developer intro | https://developers.figma.com/docs/code/intro-to-figma-make/ |
| Figma Make advanced usage | https://help.figma.com/hc/en-us/articles/35710574222487-Beyond-the-basics-Using-Figma-Make |
| Figma Make design system packages | https://help.figma.com/hc/en-us/articles/35946832653975-Use-your-design-system-package-in-Make-kits |
| Local spec-dev design | `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/superpowers/specs/2026-04-25-ai-native-one-stop-development-workflow-research-design.md` |
| Local orchestrator | `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md` |
| Local stage mapping | `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/references/stage-mapping.md` |
| Local workflow policy | `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.ai-delivery/meta/workflow-policy.json` |
| Local admin README | `/Users/charvin/Projects/spec-dev/ai-delivery-admin/README.md` |
| Local admin MCP README | `/Users/charvin/Projects/spec-dev/ai-delivery-admin/mcp-server/README.md` |
