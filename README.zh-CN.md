# AI Delivery Kit

将受治理的 `ai-delivery` 工作流引导进任意业务仓库，之后通过 `ai-delivery-orchestrator` 推进新需求，而不是手工按阶段逐个调度。

英文版：[README.md](README.md)

## 快速开始

直接从 [Releases](https://github.com/s-charvin/ai-delivery-kit/releases) 下载对应平台压缩包，解压单一 `ai-delivery` 程序并放入 PATH，即可运行。日常 kit 不需要 Go SDK、Python、Node 或 zsh；宿主项目声明的工具独立安装。下列脚本只是可选安装便利入口，不拉取 Git 源码或拼接其他版本的技能。

安装 CLI：

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo
```

或不安装、直接引导：

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/bootstrap-ai-delivery.sh | bash -s -- /path/to/repo
```

引导脚本会下载临时 release 二进制，并执行与正式 `ai-delivery init` 相同的逻辑。

若需多方协同（可选），另行安装 [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) 并在业务仓运行 `coordination-cli init`；kit 本身不包含协同逻辑。

## 默认执行节奏

默认同一实现者连续完成完整批次，单元内保留定向测试反馈，完成后独立评审集成结果。单元数量不自动触发子代理；仅在所有权独立、产出有界且协调收益为正时委派。最终测试/分析范围与 UI/动效确认保持，核对输入和产物 hash 后复用有效证据。详见[实现与验证规则](.agents-zh/skills/ai-delivery-orchestrator/references/stage-implementation.md)。

## 升级

重新运行安装脚本即可升级已安装的 CLI：

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash
```

若仓库由旧版 `ai-delivery init` 初始化，先升级 CLI，再刷新受管项目资产：

```bash
ai-delivery init --upgrade /path/to/repo
```

或一步完成：

```bash
curl -fsSL https://github.com/s-charvin/ai-delivery-kit/releases/latest/download/install-ai-delivery.sh | bash -s -- --upgrade-init /path/to/repo
```

`init --upgrade` 从当前程序刷新人读 skills/模板与 `meta/kit-assets.json`，并保留需求数据；项目内不安装可执行核心。在已经初始化的宿主项目内也可用：

```bash
ai-delivery init --upgrade .
```

kit 只支持当前交付协议。普通 `init --upgrade` 会在更新受管资产前检查已有 binding/policy；不支持、缺失或损坏的元数据会使升级失败，并显示文件、字段、实际值、目标格式及两个处理方向。需求材料在实际消费时检查；资产更新成功不代表全部需求验收通过，也不代表数据迁移成功。

遇到不兼容时，由你自行选择：

- **用自己的 AI 或工具迁移：** 复制[升级指引](.agents-zh/skills/ai-delivery-orchestrator/references/version-upgrade.md)中的提示词，自行备份并整理需要继续使用的数据。仍须满足当前证据和批准要求。
- **备份后重新开始：** 显式运行 `ai-delivery init --upgrade --reset-data /path/to/repo`。这是确定性文件操作，不调用 AI。旧交付根为自定义路径时，可用 `--reset-data=tooling/delivery`；新工作区统一创建在 `.ai-delivery/`，若标准目标已存在则拒绝与自定义源混合。

重建先把旧树及本次受管资产原件备份到唯一的 `.ai-delivery-backups/<UTC时间>-<后缀>/`，核对字节、类型和链接关系后，才搬离旧数据并刷新资产。损坏的旧 JSON 也可按字节备份；备份失败不改活跃数据及受管资产。备份成功但初始化失败时，输出完整备份、原树位置及已触及范围。恢复时核对 `manifest.json`，将 `files/` 中各路径放回项目；`absent` 表示该路径原先不存在。整树备份不会自动轮换或删除。生产文件、无关技能和第三方配置保留。

项目根 `.ai-delivery.lock` 通过平台原生锁串行协调归档、初始化、升级和重建。不支持的平台在改数据前明确失败；Windows 重建及交付动作共用原生锁。请将 `.ai-delivery.lock` 和 `.ai-delivery-backups/` 加入项目忽略规则，妥善保管备份。

当前数据根嵌套超过一级时，可直接传该根升级：`ai-delivery init --upgrade /project/tooling/delivery`。`ide-gates list/restore` 也可传相同目标；项目根自动发现保持有界。备份重建仍传项目路径，并使用 `--reset-data=tooling/delivery`。

`--upgrade-policy` 和旧归档快照验证已移除。普通入口不替用户选方案、不转换旧记录、不要求迁移收据，也不回退旧校验器。

`.ai-delivery/backups/` 仍为 IDE gate amend 的临时备份，与 `.ai-delivery-backups/` 中的整树重建备份分开。

## `ai-delivery init` 做什么

`ai-delivery init` 只负责仓库入驻。它会：

- 有 Git 时定位 Git 根；无 Git 时使用显式目录，不要求安装 Git
- 从仓库名推导 `project_id`
- 写入受治理的 `.ai-delivery` 契约、项目本地技能、校验器与配套文件

它绝不安装任何第三方框架。工作流是框架无关的：运行时适配环境中已安装的 AI 开发框架，未安装任何框架时使用内置原生档兜底。

公开路径不再要求用户提供 `project_id`。

## 默认需求入口

入驻完成后，通过 `ai-delivery-orchestrator` 开始新工作。

用户输入应保持自然语言、以素材驱动，例如：

- “这是需求文档，这是 Figma，这是接口，开始推进”
- “继续这个需求”
- “这个 blocker 我处理好了，继续”

编排器负责决定是继续已有需求还是创建新需求。选择明确时自动推进；只有不同选择会实质改变治理范围或所有权时才询问用户。

## 人工介入点

人只在需要判断的地方介入：

- 解决会实质改变范围的需求边界歧义
- 在 CP-UI 授权启用的 UI truth 工作，并在 CP-DESIGN 解决明确命名的产品、行为、资源或体验决策
- 在治理真值缺失或冲突时解决 blocker

其余默认由 AI 沿编排链路推进。

## 例外路径

底层技能如 `requirement-breakdown`、`ui-truth-mapping`，在前置条件已满足时仍可直接使用；`ui-truth-mapping` 还要求受治理的 Stage 2 切片与已记录的 CP-UI 授权。新需求的默认入口仍是 `ai-delivery-orchestrator`。

该路径用于定点恢复或专家操作，不是新需求的常规入口。

## 框架适配

编排器输出抽象动作（`solution-design` / `implement` / `finish` / `archive`），并适配环境中已安装的框架。不要求安装任何东西。`design.md` 是唯一持久化的行为与方案设计契约。

推荐框架（只检测、不安装）：

| 框架 | 主要承担 | 识别标志 |
|------|----------|----------|
| spec-kit | 可选的需求与设计推理 | 仓库根 `.specify/` 或 `specify` CLI |
| OpenSpec | 可选的棕地增量推理 | 仓库根 `openspec/` 或 `openspec` CLI |
| superpowers | `solution-design` / `implement` / `finish` | 用户技能目录含 superpowers 技能 |
| ECC | `solution-design` / `implement` / `finish` | IDE 中注册 `/ecc:*` 命令 |

未安装任何框架时，原生档仍可使用同一份 `design.md`、TDD、评审和验证纪律端到端运行。

各框架的具体使用意见随编排器技能分发：`references/framework-adaptation.md` 与 `references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`。

## 按能力启用的 UI 真值（无 HTML 契约 hook）

每个子需求在 `status.json` 中声明独立的能力与决策字段：

- `ui_truth_mode`：`none`（没有可见 UI）、`existing`（既有视觉表面的行为或语义变化）、`runtime-baseline`（没有稳定 Figma 真值的新可见 UI）或 `figma`（有稳定 Figma 证据）。
- `state_flow_required`：是否因复杂状态所有权、守卫、并发、过期结果、持久化或恢复规则而需要完整状态流契约。
- `user_decision_required`：当前设计版本是否包含决策权属于用户的实质产品、行为、资源或体验选择。当前版本批准后仍保持 `true`；hash-bound `design_review` 记录该版本是否已有有效人工授权。

只有 `ui_truth_mode=figma` 或 `runtime-baseline` 才启用 CP-UI、Stage 2、`acceptance_frozen`、v3 UI truth index 与视觉验收。`none` 与 `existing` 进入统一设计契约和普通行为或语义验证。状态流深度不会触发 CP-DESIGN；只有 `user_decision_required=true` 且当前文件缺少有效 hash-bound human review 时才进入。`ui_bearing` 只是模式一致性字段。

CP-UI 授权后，Stage 2 在用户已批准 workspace 中用 TDD 与新鲜上下文评审实现并冻结 **真实宿主栈组件**，并为每个视觉场景生成官方栈预览（Flutter：Widget + golden PNG；有动效的 unit 在宿主能够生成时还需确定性 GIF）。GIF 是唯一治理的动效预览格式；无法生成时记录原因并延后运行时验证，不得新增 WebP/MP4 或伪造文件。默认使用当前 checkout。创建或复用 worktree 必须为当前子需求另行确认，并使用 `<project-root>/.worktrees/<req-id>-<sr-id>`；禁止外部或平台托管临时路径。编写组件代码前，每个 unit 都必须按适用性解决覆盖 `state`、`layout`、`content`、`interaction`、`motion`、`assets`、`theme`、`accessibility`、`platform`、`performance` 的 Runtime Coverage Plan，并记录独立的 `motion_decision`（动效需确认/豁免，无动效也需明确确认）。golden 只证明静态帧，不能替代动效验收；Stage 4 还必须为每个 unit 记录独立动效验收。可见 UI 必须使用真实控件和有依据的资源；缺失真实数据时呈现空/省略状态，未经批准的占位层、静态替身和静默 fallback 均禁止。资源缺失时必须由用户明确选择“为空、延后或阻塞”。`ai-delivery init` **不会** 安装 UI git hook。

对话里给用户每份预览的 **绝对路径**。v3 `contracts/ui-truth-index.json` 保存组件/测试/预览的 **仓内相对路径**、环境 profile、带来源的 state、具体 scenario、完整 coverage、证据范围、宿主能力判定、适用时的宿主绑定、SHA-256，以及绑定当前预览哈希的确认。只有 Figma 实际展示的场景才可称为 1:1 真值；未展示的运行时行为必须来自需求、项目规范或用户明确决策。Stage 4 复用同一个用户已批准 workspace，并写入 `visual-acceptance.json`，绑定当前 index 哈希、每个 scenario 对应模式的证据，以及每个索引 unit 一条独立动效验收记录。

仓库根 `AGENTS.md` 带有简短 UI 真值提醒（升级时 amend）。旧 IDE JSON 可从 `.ai-delivery/backups/ide-gates/` 恢复。

原生 hook 为可选功能。安装不创建或要求 `.codex/hooks.json`、`.claude/settings.json`、`.cursor/hooks.json` 或 `.codex/config.toml`。已有文件、`features.hooks` 值、大整数和第三方定义原位原字节保留，用户自行选择并维护 opt-in 配置。[Codex SessionStart/PreToolUse 可审查示例](.agents-zh/skills/ai-delivery-orchestrator/references/native-hooks.md)说明显式 scope 与宿主信任要求。真实二进制协议测试不认证本机 Codex 已启用、已信任或实际回调；Claude/Cursor 原生 transport 未实现。无 hook 时显式 CLI 流程仍完整可用。

受管 `AGENTS.md` 更新会备份到 `.ai-delivery/backups/ide-gates/`；历史 IDE JSON / Codex 配置备份仍可显式按原字节恢复。恢复：

```bash
ai-delivery ide-gates list
ai-delivery ide-gates restore --to <timestamp>
```

## 发布策略

- `main` 只做构建与预发布校验。
- `tag push` 发布正式 GitHub Release。

## 发布彩排

打 release tag 前先跑本地彩排：

```bash
bash scripts/rehearse-release.sh
```

默认会跑 Go 测试套件、校验器、bootstrap/install 冒烟测试，以及 `git diff --check`。
若本机有 `goreleaser` 或 `pwsh`，也会一并纳入。

## 当前产物布局

本重构后 `ai-delivery init` 的仓库使用唯一 canonical 目录 `.ai-delivery/requirements/<req-id>/sub-requirements/<SR>/`：

- `design.md`（必需的行为与方案设计契约）、`verification.md`、可选的跨会话 `progress.md`、`visual-acceptance.json`（仅 UI truth 模式）和 `contracts/ui-truth-index.json`（仅启用 UI truth 时）
- 路径常量在 `.ai-delivery/meta/project-binding.json` → `layout`
- 外部框架只提供方法；schema 2.0 不生成 `spec.md`、`plan.md` 或 `tasks.md`，框架自有派生视图保持只读

旧格式会明确拒绝；可自行迁移，或显式备份重建。普通升级不会自动转换。

### 生命周期语义（`merged` → `archived`）

- `merged` = 代码已集成到开发分支
- `archived` = 原位收敛状态，canonical 产物保留在原路径；所有可执行子需求 `archived` 后需求 `completed`
- 可选的 `retrospective.md` 是需求级活复盘台账。归档时原样保留，只将问题地图中明确标记为可复用、跨需求适用、已确认且高价值的问题登记到 `.ai-delivery/retrospectives/index.md`，供后续需求按场景渐进加载；临时决策仍保留在台账中但不进入索引。归档前 AI 会在保留详细记录的前提下，将旧问题地图升级为 `problem-index:v2`。
- CP-ARCHIVE 须先运行 `ai-delivery archive --confirm-archive --expected-snapshot <snapshot-id>` 再置 `archived`；该动作不得复制第二份产物
- 归档最后一个子需求时，先用用户当前对话语言实例化 `delivery-report-template.md`，删除语言指令注释，再通过 `--delivery-report-template <path>` 传入

若需多方协同，另行安装 [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) 并在业务仓运行 `coordination-cli init`；kit 本身不包含协同逻辑。

## 维护者工具链与支持证据

Go 源兼容基线为 `1.22.0`；发行/CI 编译器固定 `1.26.2`。新版 macOS 对部分 Go 1.22 产物报缺少 `LC_UUID`，不能把源兼容当成所有新系统可执行保证。默认 `go test ./...` 包含原生进程/锁、真实外部安装与无解释器完整 CLI 链，并审计候选进程启动点；Python 只用于显式运行的 `tests/migration-oracle/` 固定开发基线。CI 在 Linux/macOS/Windows 执行本机测试；交叉构建不能代替实机证据。

包括 `bootstrap-project.test.sh` 和 `current-protocol-reset.test.sh` 在内的旧 shell 开发测试仅适用于[完整固定开发基线](tests/migration-oracle/README.md)，不用于验收当前 Go 候选。当前发行彩排仍运行 `tests/ai-delivery-cli/bootstrap-script.test.sh` 和 `tests/ai-delivery-cli/install-script.test.sh`；对应 PowerShell 脚本也仍是现行安装烟测。
