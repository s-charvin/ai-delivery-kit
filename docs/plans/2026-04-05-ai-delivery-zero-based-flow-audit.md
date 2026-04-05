# AI Delivery Zero-Based Flow Audit

## Goal

假设从零开始，不预设任何目录、缓存、后台绑定、skill 安装或运行态残留，重新审查整条 AI Delivery 链路是否真的可以从头走到尾，并确认：

- 3 个项目内 skill 生成的数据是否与 `.ai-delivery/` 契约一致
- `ai-delivery-admin` 的受控管理与治理面是否覆盖这些数据
- `.ai-delivery/`、`.specify/`、admin、skill 之间的数据流是否真正闭环

## Audit Method

本次审查按以下顺序进行：

1. 读取主设计与主计划
2. 读取 3 个项目内 skill 定义
3. 读取 `ai-delivery-admin` support skill 与当前治理实现
4. 按零起点链路逐阶段推演：
   - `Requirement Intake`
   - `Sub-Requirement Breakdown`
   - `Figma Mapping & Cache`
   - `Interaction Design`
   - `Spec Kit Phase`
   - `Development Dispatch`
   - `Merge Back To Main Dev`
   - `Done`
5. 对照“设计要求”与“当前治理能力”是否一致

## Findings

### Finding 1: Governed Artifact Coverage Does Not Fully Cover Skill Outputs

当前设计要求项目内 skill 生成并维护以下关键产物：

- requirement 级：
  - `requirement.md`
  - `breakdown-summary.md`
  - `global-rules.md`
  - `dependency-graph.json`
- sub-requirement 级：
  - `README.md`
  - `requirement-slice.md`
  - `dependency.json`
  - `status.json`
  - `traceability.json`
  - `decisions.md`
  - `figma-mapping.md`
  - `interaction-design.md`

但 admin 设计与治理面此前只把其中一部分当成受控 artifact。

影响：

- `requirement-breakdown` 生成的 requirement 级数据无法完整进入治理面
- `ui-requirement-mapping` 生成的 `traceability.json` 没有被明确当成一等治理对象
- skill 端与 admin 端虽然都围绕 `.ai-delivery/`，但“哪些文件受管”并不完全一致

结论：

- 主数据目录是一致的
- 但治理覆盖面不完整，导致“同一真相源，不同管理边界”的断点

### Finding 2: Zero-Based Bootstrap Is Underspecified

主链路以 `Requirement Intake` 起步，但此前缺少明确的零起点 bootstrap 契约。

具体缺口：

- 第一个 `requirement-id` 目录由谁创建不够明确
- `requirement.md` 的初始落位、版本、命名、创建方式没有被单独定义
- `requirement-breakdown` 默认假设输入材料和目标 requirement 包已经存在

影响：

- 从“空项目”启动时，第一步就存在责任边界模糊
- 后续 skill 很容易在本地随手创建首批文件，而不是按统一治理路径创建

结论：

- 当前链路从第二步开始相对清晰
- 但第一步的 bootstrap 真相还不够完整

### Finding 3: Blocked State Has No Explicit Recovery Path

设计中定义了大量 `blocked_*` 状态，但此前未明确“解除阻塞后如何返回正常状态机”。

影响：

- blocker 关闭后，子需求可能仍停留在 `blocked_*`
- 如果没有 `blocked_from_status` / `resume_target_status` 一类的恢复语义，agent 和后台都不知道应恢复到哪个活跃状态
- 这会让“冲突必须阻塞升级”变成“阻塞后很难恢复执行”

结论：

- 阻塞规则定义得很强
- 但恢复规则不完整，导致状态机只有“刹车”，没有“恢复驾驶”

### Finding 4: Merge Completion Does Not Yet Mean Full Runtime Convergence

设计要求：

- 合并回主开发分支
- 解决冲突
- 更新子需求状态
- 解锁后继依赖节点

但零起点推演后发现，`record_merge_result` 这类治理动作如果只记录 merge 结果，而不联动：

- `status.json`
- `worktrees.json`
- `merge-queue.json`
- `task-board.json`
- `dependency-graph.json`

那么“已合并”就只是日志事实，不是完整的运行态收敛事实。

影响：

- downstream sub-requirement 仍可能无法被系统自动解锁
- worktree 状态可能仍停留在旧状态
- 主链路看似完成，实际上 runtime truth 没有真正闭环

### Finding 5: Spec Kit Bridge Is Still Conceptual, Not Fully Contracted

主链路中已经有 `Spec Kit Phase`，但此前对下面这段桥接定义还不够落地：

- `.ai-delivery` 中的 `requirement_id / subreq_id`
- `.specify/` 中的 spec / plan / tasks

缺少明确问题包括：

- 谁负责把 `interaction_ready` 的子需求送进 Spec Kit
- `subreq_id` 与 Spec Kit feature identity 如何映射
- 反向追踪如何写回 `.ai-delivery`

影响：

- 前半段“需求拆分 / UI 映射 / 交互契约”是完整的
- 中段进入 Spec Kit 时还缺少一条正式桥梁

结论：

- 这不是方向错误
- 而是主链路里一个尚未完全合同化的关键跨层桥接点

### Finding 6: Runtime Control And Workflow Governance Boundaries Were Slightly Blurred

当前 `ai-delivery-admin` 已经有本地 runtime 控制能力，但 zero-based 审查后需要把边界写得更硬：

- MCP daemon 的启动/停止/日志查看是运行时运维能力
- 不属于 Requirement/Figma/traceability/worktree 这类 workflow truth

如果不把这条线写清楚：

- 容易让项目内 skill 误把 runtime 控制当成工作流主依赖
- 也容易让 admin support skill 过度承诺 agent 可以直接管理 runtime

结论：

- runtime control 是有效能力
- 但应明确属于 operator convenience / admin runtime 管理，而不是工作流真相层

### Finding 7: Figma Cache And Traceability Need Clearer Managed Boundaries

此前设计已经要求缓存 Figma 原始证据，但管理边界还需更明确：

- `traceability.json` 应视为一等结构化治理产物
- `figma-cache/` 中的截图、原始 nodes、comments、tokens 更适合由 skill 生成、admin 做索引与新鲜度展示

影响：

- 如果把 raw binary cache 也当通用编辑 artifact，会让 admin 复杂度无意义上升
- 如果完全不管 cache freshness，又会影响后续高保真映射判断

结论：

- `traceability.json` 应升格为核心治理对象
- `figma-cache/` 应主要走“可读、可索引、可判断 freshness”的边界

## End-To-End Verdict

### What Is Already Coherent

- 目录总边界是对的：
  - 业务真相留在 `.ai-delivery/`
  - Spec Kit 真相留在 `.specify/`
  - admin 是独立项目
  - 3 个 workflow skill 在业务项目内
  - admin support skill + MCP 在 `ai-delivery-admin`
- 双主源原则是清楚的
- worktree / dependency / merge 的治理目标是清楚的
- 3 个项目内 skill 的职责切分是清楚的

### What Was Not Fully Closed Yet

- 第一个 requirement 包如何创建
- 哪些 artifact 必须被 admin 统一治理
- blocked 状态如何恢复
- merge 完成后如何驱动 runtime truth 收敛
- `.ai-delivery` 与 `.specify` 如何正式桥接
- runtime 管理与 workflow truth 的边界

## Required Repair Directions

本次审查后的修复方向为：

1. 增补 `Requirement Intake` bootstrap 契约
2. 扩展 governed artifact coverage，使其覆盖 skill 真实产出
3. 为 blocked 状态补充恢复模型
4. 为 merge 完成补充联动收敛模型
5. 为 `.ai-delivery -> .specify` 补充正式 bridge 契约
6. 明确 runtime control 仅属于 admin runtime boundary
7. 明确 `traceability.json` 与 `figma-cache/` 的治理边界

## Output Of This Audit

本次审查不会直接改代码，而是先修复架构和计划文档，确保后续实现沿着一条真正能打通的链路前进。
