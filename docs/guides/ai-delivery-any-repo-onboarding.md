# AI Delivery 任意仓库接入指南

本指南说明如何安装发行程序、初始化项目并启动需求工作。阶段规则以项目安装的 `ai-delivery-orchestrator` 及其引用文档为准；命令判断由同一 `ai-delivery` 程序完成。

## 安装与初始化

从 [Releases](https://github.com/s-charvin/ai-delivery-kit/releases) 下载对应平台的压缩包，将其中的 `ai-delivery` 程序放入 PATH。安装便利脚本见 [README 快速开始](../../README.zh-CN.md#快速开始)。日常 kit 不需要 Go SDK、Python、Node 或 zsh；宿主项目声明的构建、测试工具仍由项目提供。

初始化目标项目：

```bash
ai-delivery init /path/to/repo
ai-delivery info --project /path/to/repo
ai-delivery validate --project /path/to/repo --kind skills
ai-delivery validate --project /path/to/repo --kind sources
ai-delivery validate --project /path/to/repo --kind api-policy
ai-delivery validate --project /path/to/repo --kind layout
```

`init` 安装项目本地技能、人读模板和基础治理配置，并维护根 `AGENTS.md` 的受管区块。它从项目目录推导 `project_id`；有 Git 时定位仓库根，无 Git 时使用显式目标目录。项目内不安装 kit 可执行核心、旧 Python/shell 校验器或旧测试链。

初始化后可见的主要位置：

| 位置 | 用途 |
| --- | --- |
| `.agents/skills/ai-delivery-orchestrator/` | 默认需求入口及阶段说明 |
| `.agents/skills/requirement-breakdown/` | 需求拆分方法与模板 |
| `.agents/skills/ui-truth-mapping/` | 按能力启用的 UI 真值流程 |
| `.agents-zh/skills/` | 随发行提供的中文技能资料 |
| `.ai-delivery/meta/project-binding.json` | 项目绑定与正式产物路径 |
| `.ai-delivery/meta/workflow-policy.json` | 当前治理配置 |
| `.ai-delivery/meta/kit-assets.json` | 当前安装资源身份 |
| `.ai-delivery/requirements/` | 后续需求与切片材料 |

这些静态校验检查安装资源或项目布局，不证明某个切片已获批准、已完成实现或可以推进。`init` 也不创建真实需求，不安装或初始化第三方框架。

维护者从源码 checkout 开发时，可使用 `go run ./cmd/ai-delivery init /path/to/repo`；`scripts/bootstrap-ai-delivery-project.sh` 只是委托该命令的源码便利 wrapper，需要 Go SDK。业务项目使用发行程序即可。

## 开始或继续需求

将需求文档和已有资料交给编排器，例如：

```text
使用 $ai-delivery-orchestrator 推进 docs/requirements/project-rename.md。
已有 Figma 和接口资料随本次输入提供；缺失或冲突之处按当前项目规则处理。
```

继续已有需求时，提供需求 ID 或材料路径。编排器会根据现有状态选择下一步，并读取已安装技能中的阶段说明；无需手动逐个调度底层技能。

每个活跃切片使用唯一的 `design.md` 行为与方案设计契约，正式路径从 `project-binding.json` 解析。外部框架只提供推理、实现或验证方法，不另建一套 spec/plan/tasks 或 decisions 治理文档。跨会话需要恢复时才维护 `progress.md`。

`ui_truth_mode` 决定是否启用 UI 真值流程；`figma` 与 `runtime-baseline` 通过编排器进入需 CP-UI 授权的 Stage 2。适用的生产组件、预览、动效、资源与确认要求见安装技能的 `references/stage-ui-truth.md`。Figma 只对其实际提供证据的场景承担视觉真值；其他行为需要需求、项目规范或明确用户决策。

当前 `design.md` 有效的 hash-bound review 决定设计是否就绪。需要用户决策时，CP-DESIGN 批准当前设计范围，也授权该范围内的实现；不再重复请求同一开发批准。设计变化后按当前证据重新判断，不能沿用失效批准。

默认在当前 checkout 工作。分支、worktree 或子代理不是接入前提，也不因框架默认值自动启用；工作区选择遵循用户授权与项目规则。启用 UI 真值的实现沿用 Stage 2 已批准的工作区。具体实现、验证、评审与合并条件统一读取安装技能，不在本指南复制第二份规则表。

## 区分读取、检查和推进

| 命令 | 职责 |
| --- | --- |
| `context` | 按需求、切片和角色提供所需正文；上下文完整不授予动作权限。 |
| `check` | 只读检查指定动作与当前证据，返回是否允许及 `snapshot_id`；不会推进状态。 |
| `advance` | 使用同一动作检查得到的快照，重新判断门禁并受控推进状态；不能用旧快照绕过变化。 |
| `validate` | 校验指定资源、布局或状态字段；阶段动作就绪由 `check` 判断。 |

例如，已经存在的 `req-project-rename` / `SR-001` 切片可这样读取实现上下文并检查进入实现的条件：

```bash
ai-delivery context --project /path/to/repo --req req-project-rename --subreq SR-001 --role implement
ai-delivery check --project /path/to/repo --req req-project-rename --subreq SR-001 --intent implement --to in_dev
```

仅在当前范围已有必要授权、检查允许且证据仍有效时，使用该次 `check` 返回的 `snapshot_id`：

```bash
ai-delivery advance --project /path/to/repo --req req-project-rename --subreq SR-001 --to in_dev --expected-snapshot SNAPSHOT_ID_FROM_CHECK
```

`SNAPSHOT_ID_FROM_CHECK` 必须替换为真实返回值。`advance` 自身仍会重评门禁；失败时按诊断处理。需要执行设计绑定的宿主验证时使用 `run`，合并与归档遵循编排器当前动作及相应授权要求，不能通过直接改状态字段代替。

仅检查现有切片的状态格式时：

```bash
ai-delivery validate --project /path/to/repo --kind status --req req-project-rename --subreq SR-001
```

该校验不证明阶段或交付就绪。

## 可选 hook 与用户配置

无 hook 时，上述显式 CLI 流程仍可用。初始化、刷新与重建不会创建或要求 `.codex/hooks.json`、`.claude/settings.json`、`.cursor/hooks.json` 或 `.codex/config.toml`，已有文件按原字节保留。

用户自行选择并维护可选 hook 配置；协议与宿主信任边界见 [原生 hook 说明](../../.agents/skills/ai-delivery-orchestrator/references/native-hooks.md)，安装后对应 `references/native-hooks.md`。配置示例不代表本机宿主已启用或实际调用 hook。

受管 `AGENTS.md` 的更新备份与历史 IDE 配置备份仍可通过 `ai-delivery ide-gates list` / `restore` 显式查看或恢复；不要依赖升级自动改写用户 hook。

## 资源不匹配与旧数据

程序升级与项目资源刷新分开进行。更换发行程序后，或收到资源身份不匹配诊断时，先核对 `info` 返回的程序路径和版本，再显式刷新对应项目：

```bash
ai-delivery info --project /path/to/repo
ai-delivery init --upgrade /path/to/repo
```

`info` 可能同时报告资源不匹配；这不会自动修复。`init --upgrade` 使用当前程序内嵌资源刷新受管 skills、模板和资源身份，不自动迁移需求数据。资源刷新成功也不表示需求已经验收。

不兼容、缺失或损坏的治理数据会被拒绝。根据诊断明确选择以下一种处理方式：

- 自行备份后，用自己的 AI 或工具按当前模板迁移所需数据；保持原始业务含义，不伪造批准或验证证据。
- 显式备份重建：`ai-delivery init --upgrade --reset-data /path/to/repo`。旧数据根是自定义路径时，使用诊断中对应的 `--reset-data=相对旧根路径`。这是重建选择，不是普通资源刷新。

即使项目本地升级指南缺失，也可读取发行程序内嵌的当前说明：

```bash
ai-delivery info --resource kit://ai-delivery-orchestrator/references/version-upgrade.md
```

备份位置、恢复方式与嵌套治理根用法见 [README 升级说明](../../README.zh-CN.md#升级)。普通命令不替用户选择迁移或重建，也不会回退旧校验器。

## 维护者测试入口

业务项目的安装验收使用本指南的 `ai-delivery validate` 命令。kit 维护者使用 README 中的 Go 测试与发行彩排入口。旧 shell 开发测试仅适用于明确的完整固定基线，不作为当前 Go 候选的验收入口；边界见 [固定开发基线说明](../../tests/migration-oracle/README.md)。
