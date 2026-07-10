# AI Delivery Kit

将受治理的 `ai-delivery` 工作流引导进任意业务仓库，之后通过 `ai-delivery-orchestrator` 推进新需求，而不是手工按阶段逐个调度。

英文版：[README.md](README.md)

## 快速开始

安装 CLI：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo
```

或不安装、直接引导：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- /path/to/repo
```

引导脚本会下载临时 release 二进制，并执行与正式 `ai-delivery init` 相同的逻辑。

## 升级

重新运行安装脚本即可升级已安装的 CLI：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
```

若仓库由旧版 `ai-delivery init` 初始化，先升级 CLI，再刷新受管项目资产：

```bash
ai-delivery init --upgrade /path/to/repo
```

或一步完成：

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash -s -- --upgrade-init /path/to/repo
```

`init --upgrade` 会刷新目标仓库中受管的 `ai-delivery` 资产，并保留需求与运行时数据。

## `ai-delivery init` 做什么

`ai-delivery init` 只负责仓库入驻。它会：

- 发现 git 根目录
- 从仓库名推导 `project_id`
- 检测主分支并写入 `.ai-delivery/runtime/main-branch.json`
- 检查 `specify-cli` 与 `superpowers`
- 在通过官方路径安装缺失前置条件前征求确认
- 仅当 `specify-cli` 已可用或在入驻过程中已安装时，才运行 `specify init`
- 写入受治理的 `.ai-delivery` 契约、项目本地技能、校验器与配套文件

公开路径不再要求用户提供 `project_id` 或 `main-branch`。

## 默认需求入口

入驻完成后，通过 `ai-delivery-orchestrator` 开始新工作。

用户输入应保持自然语言、以素材驱动，例如：

- “这是需求文档，这是 Figma，这是接口，开始推进”
- “继续这个需求”
- “这个 blocker 我处理好了，继续”

编排器负责决定是继续已有需求还是创建新需求：给出一条建议，暂停等待人工确认，再驱动受治理的工作流链路。

## 人工介入点

人只在需要判断的地方介入：

- 确认编排器关于「继续已有需求」或「创建新需求」的建议
- 确认显式检查点，例如 `tasks_ready_user_confirmation`
- 在治理真值缺失或冲突时解决 blocker

其余默认由 AI 沿编排链路推进。

## 例外路径

底层技能如 `requirement-breakdown`、`ui-truth-mapping`，在前置条件已满足时仍可直接使用。新需求的默认入口仍是 `ai-delivery-orchestrator`。

该路径用于定点恢复或专家操作，不是新需求的常规入口。

## 前置条件

`ai-delivery init` 期间，CLI 会检查 `specify-cli` 与 `superpowers`。

- 若已存在，跳过重装。
- 若缺失，会在走官方安装路径前征求确认。
- 若拒绝安装，CLI 仍会初始化受治理的 `ai-delivery` 资产，并打印官方安装链接供手工跟进。

## IDE UI 契约门禁

`ai-delivery init` 会为 Cursor、Claude Code、Codex 安装项目级 UI 契约门禁：

| IDE | 配置 | 软性指引 |
|-----|------|----------|
| Cursor | `.cursor/hooks.json`（`afterFileEdit`，`Write\|TabWrite`） | `.cursor/rules/ui-contract-gate.mdc` |
| Claude Code | `.claude/settings.json`（`PostToolUse`，`Edit\|Write`） | `.claude/rules/ui-contract-gate.md` |
| Codex | `.codex/hooks.json` + `.codex/config.toml` | 仓库根目录 `AGENTS.md`（不是 `.codex/rules`） |

**Codex 必须开启 hooks。** 入驻会写入 `.codex/config.toml`：

```toml
[features]
hooks = true
```

若你使用用户级 `~/.codex/config.toml`，也需设置 `[features] hooks = true`（或确保项目层配置受信任）。未开启时 `.codex/hooks.json` 不会执行。参见 [Codex hooks](https://developers.openai.com/codex/hooks)。

被 amend 的 IDE JSON / `AGENTS.md` / Codex 配置会备份到 `.ai-delivery/backups/ide-gates/`。恢复：

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
