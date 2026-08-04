# PRD 压力测试:异常与人工介入场景走查与设计缺陷修正

> **文档性质**:对《coordination-platform-prd.md》v2.0 及其深化文档(fr2-orchestration.md / fr1-fr6-artifact-review.md / fr7-fr8-monitoring-visual.md)的真实开发场景压力测试报告
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:待评审
> **方法**:选取 4 个"异常流程 + 人工介入"的真实场景,逐步走查 PRD 当前设计能否处理,定位设计缺陷并提出修正方案
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)
> **关联深化**:[fr2-orchestration.md](../deep-dive/fr2-orchestration.md) | [fr1-fr6-artifact-review.md](../deep-dive/fr1-fr6-artifact-review.md) | [fr7-fr8-monitoring-visual.md](../deep-dive/fr7-fr8-monitoring-visual.md)

---

## 0. 测试方法说明

本文不验证 HappyPath(TC-01 已覆盖),而是用 4 个"异常但高频"的真实场景压力测试 PRD 的**优先级模型、审批韧性、降级路径、产物消费闭环**:

| 场景 | 核心挑战 | 压测的 PRD 设计点 |
|---|---|---|
| 场景 3 | 紧急 hotfix 插队,需抢占资源 + 加速审核 | 管线优先级 + agent 资源调度 + 审核快速通道 |
| 场景 7 | 审批人休假/离职,approval 节点与 PR reviewer 双重缺席 | 升级链 + 代理人机制 + 批量转交 |
| 场景 11 | agent LLM 故障,"协调提交"本身失效,流程卡死 | 降级方案语义 + 人工 fallback + 卡死检测 |
| 场景 13 | 产物 done 后下游消费发现问题,需逆向打回 | consume_ack 机制 + 逆向 changed 流程 |

每个场景按 **场景描述 → PRD 走查 → 设计缺陷 → 修正方案 → 设计图** 组织,所有缺陷均可定位到 PRD 具体章节。

---

## 1. 场景 3:紧急 hotfix 插队

### 1.1 场景描述

**业务背景**:
- 管线 A(Feature A,登录功能优化)正在进行中:product_spec(n1)已 done,api_contract(n2)pending_review,server_impl(n3)in_progress,design_asset(n6)pending_review,client_ui(n7)blocked
- 线上 Feature B(支付功能)突发 bug:用户支付后偶发扣款成功但订单状态未更新
- 需要紧急修复:定位问题 → 修改 server_impl → 提交 hotfix

**资源约束**:
- 4 个角色 agent(server_agent / client_agent / design_agent / product_agent)全部在忙 Feature A
- server_agent 正在处理 n3(in_progress),max_concurrent=3 已满
- hotfix 管线 B 需要 server_agent 协调提交

**关键矛盾**:
1. hotfix 管线 B 与 Feature A 管线平等竞争 agent 资源,但 hotfix 紧急程度高 10 倍
2. hotfix 的 server_impl 产物要不要走 PR 审核?如果要,SLA-Human-3 最快 2 工作小时,线上 bug 等不了
3. 如果给 hotfix 开"跳过审核"通道,破坏"所有提交都审核"原则(FR1.2 分支保护)
4. server_agent 在忙 n3,hotfix 的 n_b2 怎么抢资源?

### 1.2 PRD 走查

**走查点 1:管线有无优先级概念**

PRD §2.1《核心概念与术语》定义 Pipeline 为"一个功能需求的全链路 DAG",§5.1 数据模型 `Pipeline` 结构含 `id / name / nodes / edges`,**无 priority 字段**。

fr2-orchestration.md §2.3《PipelineState 数据结构》扩展字段含 `node_states / artifact_refs / events / pending_approvals / role_assignments / pending_prs / node_versions / idempotency_seen / last_checkpoint_ts`,**无 priority 字段**。

→ **PRD 无管线/节点优先级概念,所有管线平等。**

**走查点 2:agent 资源调度有无抢占**

PRD §3.2 NFR6:"支持多 agent 并行提交不同节点产物"——仅声明并发能力,无调度策略。

fr7-fr8-monitoring-visual.md §8《容量规划》:"agent 并发任务配额:AgentRegistry `max_concurrent` 字段(默认 3),超限任务排队,ready 节点等待"——**超限后只能排队,无抢占**。

fr3-fr5-crew-skills.md(主 PRD §3.2 引用)的 `build_crew_for_ready_nodes` 按 `ready_nodes` 列表顺序创建 Task,**无优先级排序**:

```python
def build_crew_for_ready_nodes(ready_nodes: list, state: PipelineState) -> Crew:
    tasks = []
    for node_id in ready_nodes:  # ← 按 ready 顺序,无 priority 排序
        ...
```

→ **agent 调度无优先级,hotfix 节点与普通节点平等排队。**

**走查点 3:审核有无快速通道**

PRD §6.4《审核策略矩阵》按**产物类型**分级(product_spec 自动 / api_contract 首次人工 / design_asset 人工 / ...),**无按紧急程度分级**。

fr1-fr6-artifact-review.md §6.1《SLA 分级》:
- SLA-Auto:30 秒(自动审核)
- SLA-Human-1:8 工作小时(常规)
- SLA-Human-2:4 工作小时(关键)
- SLA-Human-3:2 工作小时(交付级)

**最快人工审核 2 工作小时**,线上 hotfix 通常要求分钟级。SLA 级别由 skill 的 `sla_level` 配置,**无 hotfix 专用 SLA**。

**走查点 4:能否跳过审核**

PRD §1.2 产品定位第 4 条:"审核准入门:所有产物提交经 PR 审核(skill 约束校验 + 依赖检查)才能合并生效"。

fr1-fr6-artifact-review.md §6.3.4:"关键原则:超时可升级、可告警,但不可自动 approve。审核的本质是准入,自动放行违背需求 7"。

→ **审核不可跳过,hotfix 必须走 PR 审核。**

**走查点 5:多管线并行有无跨管线协调**

PRD §5.1 数据模型每个 Pipeline 独立,fr2 §3.4 异节点并发模型:"多个 agent 同时调 submit_artifact 不同 node_id → 不同 advisory lock → 真并行"——这是**单管线内**的异节点并发,未涉及**跨管线**资源协调。

fr2 §6.1 `thread_id = pipeline_id`(一管线一 thread),管线的 state 隔离,**无全局资源视图**。

### 1.3 设计缺陷

| # | 缺陷 | PRD 位置 | 影响 |
|---|---|---|---|
| D3-1 | **管线/节点无优先级字段** | §5.1 Pipeline 结构 / fr2 §2.3 PipelineState | hotfix 管线与普通管线平等,无法区分紧急程度 |
| D3-2 | **agent 调度无优先级排序** | §3.2 build_crew_for_ready_nodes / fr7 §8 容量规划 | hotfix 节点 ready 后与普通节点一起排队,无法优先分配 agent |
| D3-3 | **无 agent 资源抢占机制** | fr7 §8 max_concurrent 超限排队 | agent 满载时 hotfix 只能等,无法抢占低优先级节点的 agent |
| D3-4 | **审核 SLA 无紧急通道** | fr1-fr6 §6.1 SLA 分级 | 最快 2 工作小时,hotfix 等不了;无"分钟级快审"通道 |
| D3-5 | **无跨管线资源视图** | fr2 §3.4 单管线并发 / §6.1 thread_id 隔离 | 多管线并行时无法全局调度 agent,hotfix 无法跨管线抢资源 |
| D3-6 | **hotfix 与正常 feature 审核策略无差异** | §6.4 审核策略矩阵仅按产物类型分 | hotfix 的 server_impl 与普通 server_impl 走相同审核,无紧急差异化 |

### 1.4 修正方案

**修正 1:PipelineState 新增 `priority` 字段**

```python
class PipelineState(TypedDict):
    # ... 原有字段 ...
    priority: str  # "p0" | "p1" | "p2" | "p3"(对齐告警级别 ALR)
    priority_reason: str  # 优先级理由(如 "线上 hotfix:支付扣款异常")
```

管线 DSL 新增 priority 字段,admin 可动态调整:
```yaml
pipeline:
  id: "pay-hotfix-001"
  priority: "p0"          # 新增
  priority_reason: "线上支付扣款异常,P0 紧急"
```

**修正 2:CrewAI 调度按优先级排序 + 资源抢占**

`dispatch_router_fn` 改造为跨管线全局调度(新增 GlobalDispatchState 聚合所有 active pipeline 的 ready 节点):

```python
def dispatch_router_fn_global(all_pipelines_state: list[PipelineState]) -> list[Send]:
    """跨管线全局调度:按 priority 排序 ready 节点"""
    all_ready = []
    for ps in all_pipelines_state:
        for nid, s in ps["node_states"].items():
            if s == NodeStatus.READY:
                all_ready.append((ps["priority"], ps["pipeline_id"], nid))
    # 按 priority 排序:p0 > p1 > p2 > p3
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
    all_ready.sort(key=lambda x: priority_order[x[0]])
    # 高优先级先分配 agent
    return [Send("crewai_assign", {"pipeline_id": pid, "target_node": nid})
            for _, pid, nid in all_ready]
```

**资源抢占机制**:当 p0 节点 ready 但 agent 满载时,可抢占 p2/p3 节点的 agent:
- 被抢占节点 suspend(状态回 ready,释放 agent)
-抢占节点立即获得 agent
- 被抢占节点记录 `PREEMPTED` event,待 p0 完成后恢复
- p0 节点不可被抢占(最高优先级)

**修正 3:hotfix 快速审核通道(不跳过审核,但加速)**

新增 `sla_level: SLA-Critical`,配置于 hotfix skill:
```yaml
sla:
  level: SLA-Critical
  timeout_minutes: 15            # 15 分钟 SLA(替代小时制)
  review_mode: dual_fast_review  # 双人快审模式
  escalate_to: admin
```

**双人快审模式(dual_fast_review)**:
- 自动审核优先处理(review_artifact_pr 优先队列,p0 PR 插队)
- 自动审核通过后,**并行**通知 1 个 reviewer + 1 个 admin,任一 approve 即合并(替代串行 SLA 升级)
- 15 分钟无决策 → 自动升级到 admin + 飞书电话加急

**关键:不跳过审核,保留"所有提交都审核"原则,但用并行快审 + 极短 SLA 把时间压到分钟级。**

**修正 4:hotfix skill 标记**

新增 `hotfix-server-impl-skill`(或现有 skill 增加 `hotfix_variant` 配置):
```yaml
# skill.yaml
hotfix_variant:
  enabled: true
  sla_level: SLA-Critical
  skip_gates: [lint]           # hotfix 可跳过 lint 门禁(保留 test/security)
  require_post_merge_review: true  # 合并后 24h 内补完整 review(hotfix 先合后审)
```

`require_post_merge_review`:hotfix 先合并止血,24h 内补完整 review,若 review 不通过则触发 changed 重新修复。这是"先上车后补票"模式,平衡紧急性与审核原则。

### 1.5 设计图:hotfix 快速通道流程

```mermaid
flowchart TD
    BUG["线上 bug 触发<br/>admin 创建 hotfix 管线(priority=p0)"]
    BUG --> BOOT["bootstrap_node<br/>hotfix 节点 ready"]

    BOOT --> SCHED{"全局调度器<br/>按 priority 排序"}
    SCHED -->|p0 优先| PREEMPT{"agent 满载?"}
    PREEMPT -->|是| SUSP["抢占 p2/p3 节点 agent<br/>被抢占节点 suspend(回 ready)"]
    PREEMPT -->|否| ASSIGN["直接分配 agent"]
    SUSP --> ASSIGN

    ASSIGN --> DEV["开发方产出 hotfix 产物<br/>agent 协调提交"]
    DEV --> SUBMIT["submit_artifact<br/>PR 标记 priority=p0"]

    SUBMIT --> AUTO["自动审核(优先队列)<br/>review_artifact_pr 插队"]
    AUTO -->|reject| FIX["修复后重提"]
    FIX --> AUTO
    AUTO -->|pass| DUAL{"双人快审模式<br/>SLA-Critical 15min"}

    DUAL --> PAR["并行通知<br/>reviewer + admin"]
    PAR --> R1["reviewer 审核"]
    PAR --> R2["admin 审核"]

    R1 -->|approve| MERGE["bot 合并(任一 approve 即合并)"]
    R2 -->|approve| MERGE
    R1 -->|reject| REJ["reject → 重提"]
    R2 -->|reject| REJ
    REJ --> FIX

    DUAL -->|15min 超时| ESC["升级 admin + 飞书电话加急"]
    ESC --> R2

    MERGE --> STAB["线上止血完成"]
    STAB --> POST["合并后 24h 内补完整 review<br/>(require_post_merge_review)"]
    POST -->|review 通过| DONE["hotfix 管线 done"]
    POST -->|review 不通过| CHG["触发 changed<br/>重新修复"]

    style BUG fill:#b3261e,color:#fff
    style DUAL fill:#e3b341,color:#fff
    style MERGE fill:#3fb950,color:#fff
    style STAB fill:#3fb950,color:#fff
    style POST fill:#a371f7,color:#fff
```

---

## 2. 场景 7:审批人不在(休假/离职)

### 2.1 场景描述

**业务背景**:
- 管线进行中,approval 节点 n10(approver = reviewer_zhang)处于 `review` 状态,等待张三审批
- 张三休假 3 天,无法操作
- 同时,产物 PR #42(reviewer = reviewer_zhang)也在 pending_review,等待张三审核
- 第 4 天张三回来,但发现其实张三已离职,不会再回来

**关键矛盾**:
1. PRD 的 SLA 升级是"超时后升级到 backup→admin",但要等 4h/8h 才触发,张三休假 3 天会触发多次超时升级,效率极低
2. backup_reviewer 怎么确定?PRD 没说怎么配置、谁来当 backup
3. 张三离职,他名下所有 approval 节点和 PR 怎么办?要逐个等超时?还是能批量转交?
4. 升级到 admin 后,admin 不懂设计稿审批细节,approve 质量怎么保证?
5. 真实组织是"代理人制度"(事先指定),不是"超时升级"(事后兜底)

### 2.2 PRD 走查

**走查点 1:approval 节点的 approver 配置**

PRD §5.1 Pipeline 数据结构:
```yaml
- id: "n10"
  type: "approval"
  approver: "reviewer_agent"   # 单一 approver
```

fr2-orchestration.md §7.4 控制节点配置校验:"approval 节点 `approver` 必填,非空字符串"——**单一 approver,无 delegate 字段**。

fr2 §8.2 approval 边界条件:"approver 离线:不影响 approval 节点状态,超时机制兜底;admin 可重新指定 approver"——**离线靠超时兜底,admin 手动改 approver,无自动代理人**。

**走查点 2:SLA 升级链**

fr1-fr6-artifact-review.md §6.3.1 升级链配置:
```yaml
escalation:
  - tier: 1
    approver: reviewer_agent
    sla_hours: 4
  - tier: 2
    approver: backup_reviewer   # ← backup 怎么来?
    sla_hours: 4
  - tier: 3
    approver: admin
    sla_hours: 2
```

§6.3.2 升级触发:"定时任务(每 5 分钟扫描)检查 pending 人工审核,elapsed > tier.sla_hours 则升级"——**被动超时升级,无主动委托**。

**走查点 3:backup_reviewer 的确定方式**

PRD 全文搜索 "backup_reviewer":仅出现在 escalation 配置示例中,**未定义 backup_reviewer 的来源、配置方式、维护机制**。是 admin 手动配?是角色池自动选?PRD 空白。

**走查点 4:批量转交机制**

fr2 §7.5 热重载:"修改 approval approver:admin 手动,仅对未 approve 的 approval 生效"——**逐个手动改,无批量转交工具**。

MCP 工具清单(§6)无 `transfer_approvals` 工具,reviewer 离职后 admin 只能逐个节点改 approver。

**走查点 5:admin 不懂业务细节**

fr1-fr6 §6.3.4 全局超时兜底:"admin 手动处理(approve/reject/驳回重做)"——**未解决 admin 不懂业务的问题**。

PRD §3.1 角色定义:admin 职责是"管理员",可产出的节点类型为"—"(不产出),可用工具为"全部工具"。admin 是平台管理员,不是业务专家(如设计稿审批需 UI 专业知识)。

**走查点 6:PR reviewer 与 approval approver 是两套人**

PRD §3.1 reviewer 角色:可用工具 `approve_pr, reject_pr, get_audit_log`——审核**产物 PR**。
PRD §5.1 approval 控制节点:approver 配置——审核**审批门**。

两者是独立的审核机制,场景中张三是 reviewer(审 PR)又是 approver(审 approval 节点),两套都缺席,PRD 没有统一覆盖。

### 2.3 设计缺陷

| # | 缺陷 | PRD 位置 | 影响 |
|---|---|---|---|
| D7-1 | **无代理人(delegate)机制** | §5.1 approver 单一 / fr2 §7.4 无 delegate 字段 | reviewer 休假无法主动委托,只能等超时升级 |
| D7-2 | **backup_reviewer 来源未定义** | fr1-fr6 §6.3.1 escalation 配 backup_reviewer 但无来源 | backup 是空配置,实施时不知道填谁 |
| D7-3 | **无批量转交工具** | §6 MCP 工具清单 / fr2 §7.5 逐个手动改 | reviewer 离职后名下 N 个 approval 要逐个改,效率极低 |
| D7-4 | **超时升级是被动机制,不符合真实组织** | fr1-fr6 §6.3.2 定时扫描超时升级 | 真实组织是"事先指定代理人",PRD 是"事后超时兜底",3 天休假要触发多次 4h 超时 |
| D7-5 | **升级到 admin 后业务质量无保障** | fr1-fr6 §6.3.4 admin 手动处理 | admin 不懂设计稿/UI 业务,approve 质量存疑 |
| D7-6 | **PR reviewer 与 approval approver 缺席未统一覆盖** | §3.1 reviewer 审 PR / §5.1 approver 审 approval | 两套审核机制独立,reviewer 缺席时两套都卡,PRD 无统一代理人覆盖 |
| D7-7 | **reviewer 无"休假/在职"状态** | fr7 ALR-03 agent 心跳 / 无 reviewer 状态 | approver 离线靠 approval 超时(4h)才发现,无主动"休假设置" |

### 2.4 修正方案

**修正 1:approval 节点新增 `delegate` 字段(代理人)**

```yaml
- id: "n10"
  type: "approval"
  approver: "reviewer_zhang"
  delegate: "reviewer_li"        # 新增:代理人,approver 缺席时自动转
  delegate_active_when: "approver_offline"  # 触发条件
```

`delegate` 与 approver 有同等 approve 权限,但 audit_log 记录实际审批人身份(delegate_reviewer_li)。

**修正 2:reviewer 休假/在职状态管理**

新增 `reviewer_status` 表 + Dashboard 入口:
```sql
CREATE TABLE reviewer_status (
    reviewer_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,           -- active | on_leave | left
    delegate_id TEXT,               -- 代理人(reviewer_id)
    leave_start TIMESTAMPTZ,
    leave_end TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

reviewer 可在 Dashboard 设置休假时段,系统自动在该时段将 approval/PR 转给 delegate。

**修正 3:升级链补充代理人优先级**

```yaml
escalation:
  - tier: 1
    approver: reviewer_zhang
    sla_hours: 4
  - tier: 1'                      # 新增:代理人(同级,非超时升级)
    approver: reviewer_li         # 来自 delegate / reviewer_status
    trigger: approver_offline     # 主动触发,不等超时
    sla_hours: 4
  - tier: 2
    approver: backup_reviewer_pool  # 角色池(同 role 的其他 reviewer)
    sla_hours: 4
  - tier: 3
    approver: admin
    sla_hours: 2
    fallback_expert: true         # 新增:admin 可转专家审
```

**升级优先级**:代理人(tier 1') > 超时升级(tier 2/3)。代理人在线时直接转,不等 SLA 超时。

**修正 4:批量转交 MCP 工具**

新增 `transfer_approvals` 工具:
```json
{
  "name": "transfer_approvals",
  "description": "批量转交 reviewer 名下所有 pending approval/PR",
  "inputSchema": {
    "type": "object",
    "properties": {
      "from_reviewer": {"type": "string"},
      "to_reviewer": {"type": "string"},
      "scope": {"type": "string", "enum": ["all", "by_pipeline", "by_node"]},
      "pipeline_id": {"type": "string", "description": "scope=by_pipeline 时填"},
      "node_ids": {"type": "array", "items": {"type": "string"}, "description": "scope=by_node 时填"}
    },
    "required": ["from_reviewer", "to_reviewer", "scope"]
  }
}
```

张三离职,admin 一键转交:`transfer_approvals(from=reviewer_zhang, to=reviewer_li, scope=all)`。

**修正 5:admin "转专家审"机制**

升级到 admin 后,admin 可指定领域专家临时 reviewer:
```json
{
  "name": "delegate_to_expert",
  "description": "admin 将 approval 转给领域专家临时审核",
  "inputSchema": {
    "properties": {
      "node_id": {"type": "string"},
      "expert_id": {"type": "string", "description": "专家用户 ID"},
      "expertise": {"type": "string", "description": "如 UI/design/server"}
    }
  }
}
```

系统附带"业务上下文摘要"辅助决策:上游产物预览 + skill guide + 历史 review 记录 + 相似节点的历史审批结论。

**修正 6:PR reviewer 与 approval approver 统一代理人**

`reviewer_status.delegate_id` 同时覆盖 PR 审核(approve_pr)和 approval 节点(approve),确保 reviewer 缺席时两套机制都有代理人。

### 2.5 设计图:审批代理人机制

```mermaid
flowchart TD
    START["approval 节点进入 review<br/>approver=reviewer_zhang"]
    START --> CHECK{"检查 reviewer_status"}

    CHECK -->|active 在职| NORMAL["通知 reviewer_zhang 审批<br/>SLA 计时开始"]
    CHECK -->|on_leave 休假| DELEGATE1["自动转代理人 delegate=reviewer_li<br/>tier 1'(同级,不等超时)"]
    CHECK -->|left 离职| TRANSFER["admin 批量转交<br/>transfer_approvals(all → reviewer_li)"]

    DELEGATE1 --> NORMAL2["通知 reviewer_li 审批<br/>SLA 计时开始"]
    TRANSFER --> NORMAL2

    NORMAL --> SLA1{"tier 1 SLA<br/>4h 内决策?"}
    NORMAL2 --> SLA1

    SLA1 -->|approve| DONE["approval → done<br/>cascade 下游"]
    SLA1 -->|reject| CHG["上游产物 changed<br/>递归失效"]
    SLA1 -->|超时 4h| ESC2["升级 tier 2<br/>backup_reviewer_pool"]

    ESC2 --> SLA2{"tier 2 SLA<br/>4h 内决策?"}
    SLA2 -->|approve| DONE
    SLA2 -->|reject| CHG
    SLA2 -->|超时| ESC3["升级 tier 3<br/>admin + 加急通知"]

    ESC3 --> ADMIN{"admin 决策"}
    ADMIN -->|懂业务| APPROVE_A["admin approve/reject"]
    ADMIN -->|不懂业务| EXPERT["delegate_to_expert<br/>转领域专家临时审"]
    EXPERT --> EXPERT_REVIEW["专家审 + 业务上下文摘要<br/>(产物预览+guide+历史)"]
    EXPERT_REVIEW --> APPROVE_A

    APPROVE_A -->|approve| DONE
    APPROVE_A -->|reject| CHG
    ESC3 -->|全局超时| STUCK["needs_admin_attention<br/>不自动 approve"]

    DONE --> AUDIT["audit_log 记录实际审批人<br/>(reviewer_zhang / reviewer_li_delegate / admin / expert)"]

    style DELEGATE1 fill:#3fb950,color:#fff
    style TRANSFER fill:#3fb950,color:#fff
    style EXPERT fill:#a371f7,color:#fff
    style STUCK fill:#b3261e,color:#fff
    style DONE fill:#3fb950,color:#fff
```

---

## 3. 场景 11:agent LLM 失败导致流程卡死

### 3.1 场景描述

**业务背景**:
- 管线正常推进,n2(api_contract)已 done,n3(server_impl)处于 ready,等待 server_agent 协调提交
- LLM 服务商(如 OpenAI / 自部署模型)突发故障,所有 LLM 调用返回 500 或超时
- server_agent 在线(心跳正常),但调 LLM 失败,无法理解 n2 的 deps 内容,无法写 PR 说明,无法调 MCP submit_artifact
- 开发方人员已产出 server_impl 产物(代码已提交到代码仓库),等 agent 协调提交到管理方
- 人工不知道流程卡住了(Dashboard 显示 n3 ready,看似正常)

**关键矛盾**:
1. PRD 说降级方案是"规则引擎直提(绕过 LLM)",但"规则引擎直提"是什么意思?谁来调 MCP?
2. agent 是"协调提交员",LLM 挂了,开发方人员能不能直接调 MCP submit_artifact 绕过 agent?
3. agent 在线(心跳正常)但 LLM 失败,ALR-03(agent 离线告警)不会触发,卡死无人知
4. ALR-04(管线停滞 30min)太粗,n3 卡住但其他节点在动,管线不算停滞

### 3.2 PRD 走查

**走查点 1:"规则引擎直提"的定义**

主 PRD 附录 B 引用 fr3-fr5-crew-skills.md 提到"失败重试降级:规则引擎直提(绕过 LLM)",但主 PRD 本身未定义。fr3-fr5-crew-skills.md(本次未读,但主 PRD 附录 B 摘要)说"CrewAI agent LLM 配置 + cost 控制、失败重试降级"。

问题:agent 的职责是"理解 deps 内容、写 PR 说明、调 MCP submit_artifact"(§3.1)。"规则引擎直提"意味着绕过 LLM,但:
- 谁来调 MCP submit_artifact?规则引擎本身不能调 MCP(规则引擎是审核用的,§4.4)
- 谁来写 PR 说明?PR 模板(§1.3)有"说明: 用户登录接口契约 v1"自由文本,LLM 挂了谁来写?
- 谁来填 deps_decl?agent 需要读 deps 内容理解上下文,规则引擎不能理解

→ **"规则引擎直提"语义模糊,无法落地。规则引擎是审核组件,不能替代 agent 协调。**

**走查点 2:开发方人员能否直接调 MCP**

PRD §3.2 权限矩阵:`submit_artifact` 调用方是"各角色 agent"(product/server/design/client),**人员(人类用户)不在调用方列表**。

§4.1 MCP 工具清单:`submit_artifact` 调用方="各角色 agent"。

fr7-fr8 §10.1 MCP 认证:JWT token 含 `role` / `agent_id` claim——**token 绑定 agent_id,人员无独立 token**。

→ **开发方人员无法直接调 MCP submit_artifact,必须经 agent。LLM 挂了 = 流程卡死。**

**走查点 3:agent LLM 失败的告警覆盖**

fr7-fr8 §2.1 告警规则:
- ALR-03:agent 离线(心跳 > 90s 未上报)——**agent 进程级,LLM 失败时 agent 心跳正常,不触发**
- ALR-04:管线停滞(无状态变更 > 30min)——**管线级,n3 卡住但其他节点在动则不触发**
- ALR-07:MCP 错误率飙升(5min 窗口 > 10%)——**MCP 调用级,但 LLM 失败时 agent 不调 MCP,无 MCP 错误**

→ **无"agent 在线但 LLM 调用失败"的专用告警,卡死无人知。**

**走查点 4:节点级卡死检测**

fr2 §8.2 approval 超时有节点级检测(节点进 review 后 SLA 超时)。但产物节点 ready 后"无进展"的检测:
- ALR-04 管线级停滞 30min,非节点级
- 无"节点 ready 后 N 小时无 update_progress 或 submit_artifact"的告警

→ **节点级卡死检测缺失。**

**走查点 5:CrewAI 分配失败 ≠ LLM 失败**

fr2 §5.1 错误分类:"CrewAI 分配失败:agent 离线,重新选 agent → 退避重试 → 标记 NO_AGENT"——这是 **agent 进程离线**的处理。

LLM 失败是 **agent 在线但内部调 LLM 失败**,两者不同:
- agent 离线:CrewAI 分配失败,可重新选 agent
- LLM 失败:agent 在线,CrewAI 分配成功,但 agent 执行 Task 时调 LLM 失败,Task 卡住

PRD 未区分这两种失败,错误处理矩阵无"LLM 调用失败"类别。

### 3.3 设计缺陷

| # | 缺陷 | PRD 位置 | 影响 |
|---|---|---|---|
| D11-1 | **"规则引擎直提"语义模糊,无法落地** | 附录 B 引用 fr3-fr5 | 规则引擎是审核组件,不能调 MCP / 写 PR 说明 / 填 deps_decl,无法替代 agent |
| D11-2 | **开发方人员无法直接调 MCP** | §3.2 权限矩阵 / §4.1 调用方=agent / fr7 §10.1 token 绑 agent_id | LLM 挂了 = 流程卡死,无人工绕过路径 |
| D11-3 | **无"agent 在线但 LLM 失败"专用告警** | fr7 §2.1 ALR-03 仅 agent 离线 | LLM 失败时 agent 心跳正常,ALR-03 不触发,卡死无人知 |
| D11-4 | **节点级卡死检测缺失** | fr7 ALR-04 管线级 30min | 单节点卡住但管线在动则不告警 |
| D11-5 | **LLM 失败与 agent 离线未区分** | fr2 §5.1 错误分类 | LLM 失败按 agent 离线处理(重新选 agent)无效,根因不同 |
| D11-6 | **无人工 fallback 模式** | 全文无 | LLM 不可用时无降级到"人工通过 Dashboard 提交"的机制 |

### 3.4 修正方案

**修正 1:明确"人工 fallback 模式"替代"规则引擎直提"**

废弃"规则引擎直提"表述,改为**人工 fallback 模式**:LLM 不可用时,开发方人员通过 Dashboard 直接提交产物,绕过 agent 协调。

**修正 2:权限矩阵扩展——人员可调 submit_artifact(降级模式)**

§3.2 权限矩阵新增"开发方人员(降级模式)"列:

| 操作 | product 人员 | server 人员 | design 人员 | client 人员 | 触发条件 |
|---|---|---|---|---|---|
| submit_artifact(降级) | ✅(product_spec) | ✅(server 类) | ✅(design 类) | ✅(client 类) | LLM 降级模式开启 |

MCP JWT token 新增 `user_id` claim(人员身份),降级模式下人员用 user token 调 MCP,audit_log 记录 `submitter=user:zhangsan`(而非 agent_id)。

**修正 3:LLM 降级模式触发与切换**

新增 `llm_health` 监控 + 降级开关:

```python
# LLM 健康度监控(嵌入 agent 心跳上报)
class AgentHeartbeat(TypedDict):
    agent_id: str
    ts: str
    llm_error_rate: float       # 新增:5min 窗口 LLM 调用失败率
    llm_avg_latency_ms: float   # 新增:LLM 调用平均延迟
    pending_tasks: int
```

降级触发规则:
- agent 心跳 `llm_error_rate > 50%`(5min 窗口)→ 该 agent 进入降级模式
- 全局 LLM 错误率 > 30% → 全平台降级模式
- 降级模式开启 → SSE 推送 `llm_degraded` 事件 → Dashboard banner 提示

降级模式行为:
- ready 节点不分配 agent,改为 Dashboard "待人工提交"任务列表
- 开发方人员收到飞书/邮件通知"节点 n3 待人工提交"
- 人员在 Dashboard 填写 PR 说明 + 选择 deps + 上传产物引用 → 调 MCP submit_artifact
- LLM 恢复后,admin 手动关闭降级模式,恢复 agent 协调

**修正 4:LLM 失败专用告警(ALR-13)**

fr7 §2.1 告警规则新增:

| 编号 | 事件 | 触发条件 | 级别 | 渠道 |
|---|---|---|---|---|
| ALR-13 | agent LLM 失败率飙升 | agent 心跳 `llm_error_rate > 50%`(5min 窗口) | P1 | 飞书群 + Dashboard banner |
| ALR-14 | 节点卡死 | 产物节点 ready 后 > 2h 无 update_progress/submit_artifact | P1 | 飞书 @对应 role on-call |

ALR-14 是节点级卡死检测,补充 ALR-04(管线级)的盲区:
```python
# 节点级卡死检测定时任务
for nid, s in state["node_states"].items():
    if s == NodeStatus.READY:
        ready_since = get_ready_ts(nid)
        if now - ready_since > 2 * 3600:  # 2h
            emit_alert(ALR_14, node_id=nid, role=node["role"])
```

**修正 5:错误分类区分 LLM 失败**

fr2 §5.1 错误分类矩阵新增:

| 错误类别 | 典型错误 | 影响范围 | 处理策略 | 重试上限 |
|---|---|---|---|---|
| **LLM 调用失败** | OpenAI 500 / 模型超时 / 配额耗尽 | agent Task 卡住 | 退避重试 → 切备用 LLM → 进入降级模式 | 3 次 |

### 3.5 设计图:LLM 失败人工 fallback 流程

```mermaid
flowchart TD
    NODE["节点 n3 ready<br/>等待 server_agent 协调提交"]
    NODE --> ASSIGN["CrewAI 分配 Task 给 server_agent"]
    ASSIGN --> LLM_CALL["agent 调 LLM<br/>(理解 deps + 写 PR 说明)"]

    LLM_CALL --> LLM_OK{LLM 调用}
    LLM_CALL -->|成功| AGENT_SUBMIT["agent 调 submit_artifact<br/>→ pending_review"]
    AGENT_SUBMIT --> NORMAL_FLOW["正常审核流程"]

    LLM_CALL -->|失败| RETRY["退避重试 3 次"]
    RETRY -->|重试成功| AGENT_SUBMIT
    RETRY -->|3 次失败| FALLBACK_LLM["切备用 LLM(如本地模型)"]

    FALLBACK_LLM -->|成功| AGENT_SUBMIT
    FALLBACK_LLM -->|失败/无备用| HEALTH["上报 llm_error_rate > 50%<br/>触发 ALR-13 告警"]

    HEALTH --> DEGRADE{"降级模式判断"}
    DEGRADE -->|单 agent 降级| SINGLE["该 agent 进入降级模式<br/>其 ready 节点转人工"]
    DEGRADE -->|全局 error_rate > 30%| GLOBAL["全平台降级模式<br/>SSE 推送 llm_degraded"]

    SINGLE --> DASHBOARD
    GLOBAL --> DASHBOARD

    DASHBOARD["Dashboard:待人工提交任务列表<br/>SSE 通知开发方人员"]
    DASHBOARD --> NOTIFY["飞书/邮件通知 server 角色 on-call<br/>'节点 n3 待人工提交'"]

    NOTIFY --> HUMAN["开发方人员登录 Dashboard"]
    HUMAN --> FILL["填写 PR 说明 + 选择 deps<br/>+ 上传产物引用(代码 commit)"]
    FILL --> HUMAN_SUBMIT["人员用 user token 调<br/>submit_artifact(降级模式)"]

    HUMAN_SUBMIT --> REVIEW["→ pending_review<br/>审核流程不变"]
    REVIEW --> MERGE["approve → done"]

    MERGE --> RECOVER{"LLM 恢复?"}
    RECOVER -->|否| KEEP["保持降级模式<br/>下一节点继续人工"]
    RECOVER -->|是| ADMIN_CLOSE["admin 关闭降级模式<br/>恢复 agent 协调"]
    ADMIN_CLOSE --> NORMAL["恢复正常 agent 流程"]

    style LLM_CALL fill:#e3b341,color:#fff
    style RETRY fill:#e3b341,color:#fff
    style DEGRADE fill:#b3261e,color:#fff
    style DASHBOARD fill:#a371f7,color:#fff
    style HUMAN_SUBMIT fill:#3fb950,color:#fff
    style ADMIN_CLOSE fill:#3fb950,color:#fff
```

---

## 4. 场景 13:产物消费者反馈(设计稿评审打回)

### 4.1 场景描述

**业务背景**:
- 管线推进中,design_proto(n5)已提交,requires_human_review=false(FR6.4 设计原型主观性强不强审),自动审核通过 → done
- 产品方(product 角色)和客户端方(client 角色)在 downstream 开发时 review 设计稿,认为信息架构错误(导航层级混乱,核心入口埋得太深)
- 客户端方基于这个设计稿做的 client_ui 会有问题,需要设计稿重新设计

**关键矛盾**:
1. PRD 审核只发生在"产物提交时"(submit→review→approve/reject),产物 done 后无审核入口
2. design_proto 自动审核通过(元数据合规),但"是否符合需求"不在自动审核范围(§1.4 不校验内容)
3. changed 状态是"上游主动重提"(T10),下游不能替上游触发 changed
4. 下游发现问题只能飞书通知上游"改一下",上游手动重提 PR——纯人工,失去平台价值
5. 产物 done 不代表"被下游接受",缺少"消费确认"环节

### 4.2 PRD 走查

**走查点 1:审核只发生在提交时**

PRD §6.1 审核流程:"PR 提交 → webhook 通知管理方 → 解析 → 校验 → 决策(approve/reject)"——**审核入口仅 PR 提交**。

fr1-fr6 §9.1 审核决策树:从 PR 提交开始,到合并/驳回结束——**无"产物 done 后的反馈"路径**。

**走查点 2:changed 状态的触发权**

fr2 §2.1 状态转移表:
- T10:`done → changed`,触发事件=`submit_artifact 重提已 done 节点的 PR`,触发者是**上游(产物所有者)**
- T15:`review → changed`(approval reject),触发者是**审批人**

下游(消费者)无触发 changed 的路径。下游发现问题,只能通知上游,由上游主动 submit_artifact 重提。

**走查点 3:级联失效是单向的**

fr2 §2.2 DAG 规则:"级联失效:节点 changed → 所有下游产物引用清除 + 置 blocked(递归)"——**上游 changed → 下游 blocked,单向**。

无"下游打回 → 上游 changed"的逆向流程。

**走查点 4:产物 done 后下游无确认环节**

PRD §2.1 状态机:`done` 是终态(产物已合并生效),无"消费确认"中间态。

fr2 §2.1 T7:`pending_review → done`,合并即 done,无"待消费确认"环节。

§2.2 DAG 规则:"节点 done → 检查所有下游,依赖全满足的下游置 ready"——**done 即解锁下游,无下游确认步骤**。

**走查点 5:design_proto 的审核策略**

PRD §6.4 审核策略矩阵:`design_proto | 自动校验 ✅ | 人工审核 ❌ | 设计原型,主观性强不强审`——**自动审核仅校验元数据,不校验内容是否符合需求**。

§1.4 范围边界:"不校验产物内容格式(YAML/JSON/Figma 均可)" + "管理方不解析内容"——**内容是否符合需求,不在管理方审核范围**。

但真实场景中,设计稿"是否符合需求"需要下游(产品方/客户端方)人工判断,PRD 无此环节。

**走查点 6:下游依赖锁定机制**

fr1-fr6 §5.3.3 依赖失效:PR pending_review 期间依赖变 changed → PR reject。但这是**审核期间**的依赖失效保护,不是**产物 done 后**的消费确认。

产物 done 后,下游直接基于该产物开发,无"先确认接受再锁定依赖"的机制。

### 4.3 设计缺陷

| # | 缺陷 | PRD 位置 | 影响 |
|---|---|---|---|
| D13-1 | **审核仅发生在提交时,无 done 后反馈机制** | §6.1 / fr1-fr6 §9.1 | 产物 done 后下游发现问题,无平台内打回路径 |
| D13-2 | **changed 仅上游主动触发,下游无触发权** | fr2 §2.1 T10 / §2.2 级联单向 | 下游不能打回上游,只能人工通知 |
| D13-3 | **无 consume_ack 消费确认机制** | §2.1 状态机 / §2.2 DAG | 产物 done 即解锁下游,无"下游确认接受"环节 |
| D13-4 | **自动审核不校验内容符合度,且无下游验收补充** | §6.4 / §1.4 不校验内容 | design_proto 自动通过但不符合需求,下游被动接受 |
| D13-5 | **产物 done 即终态,缺"待消费确认"中间态** | fr2 §2.1 done 是终态 | done 不等于"被下游接受",但状态机无区分 |
| D13-6 | **下游反馈纯靠人工(飞书/Slack)** | 无平台内逆向流程 | 失去平台价值,打回靠口头通知,无追溯 |

### 4.4 修正方案

**修正 1:新增 `consume_ack` 消费确认机制**

产物 done 后,下游节点在 ready 或 in_progress 阶段,可对上游产物做"接受/打回"操作:

新增 MCP 工具:
```json
{
  "name": "consume_ack",
  "description": "下游确认接受/打回上游产物",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "string", "description": "下游节点 ID(调用方)"},
      "dep_node_id": {"type": "string", "description": "上游产物节点 ID(被确认的)"},
      "verdict": {"type": "string", "enum": ["accept", "reject"]},
      "reason": {"type": "string", "description": "reject 时必填,结构化理由"}
    },
    "required": ["node_id", "dep_node_id", "verdict"]
  }
}
```

- `verdict=accept`:锁定依赖,下游正常推进,上游产物进入"已消费确认"态
- `verdict=reject`:触发上游节点 changed(下游触发的 changed),级联失效该上游的其他下游

**修正 2:状态机新增"待消费确认"中间态**

fr2 §2.1 状态机新增 `done_pending_ack` 态(扩展 7 态为 8 态):

| 状态 | 含义 | 进入条件 | 退出条件 |
|---|---|---|---|
| `done_pending_ack` | 产物已合并,待下游消费确认 | approve_pr 合并 + skill.requires_consumer_ack=true | 全下游 ack accept / ack SLA 超时默认 accept / 任一下游 ack reject |

状态转移新增:
- T19:`pending_review → done_pending_ack`(requires_consumer_ack=true 时,合并后进待确认)
- T20:`done_pending_ack → done`(全下游 ack accept 或 SLA 超时默认 accept)
- T21:`done_pending_ack → changed`(下游 consume_ack reject 触发,逆向打回)
- T22:`done → changed`(下游 consume_ack reject 触发,已 done 但未过 ack SLA 的产物)

**T21/T22 与 T10 的区别**:T10 是上游主动重提,T21/T22 是下游 reject 触发,audit_log 记录 `trigger=consumer_reject`。

**修正 3:skill 新增 `requires_consumer_ack` 配置**

```yaml
# skill.yaml
consumer_ack:
  requires_consumer_ack: true       # 是否需下游消费确认
  ack_sla_hours: 48                 # 确认 SLA:48h 内下游未 ack 视为默认 accept
  ack_roles: [product, client]      # 哪些下游角色需确认(design_proto 需产品+客户端确认)
  reject_triggers_changed: true     # reject 是否触发上游 changed
```

按产物类型分级(补充 §6.4 审核策略矩阵):

| 产物类型 | requires_consumer_ack | ack_roles | 理由 |
|---|---|---|---|
| product_spec | true | [server, design, client] | 需求文档需下游认可 |
| api_contract | true | [client, server_impl] | 契约需消费方确认 |
| design_proto | true | [product, client] | 设计稿需产品+客户端验收(本场景核心) |
| design_asset | true | [client] | 标注/切图需客户端确认 |
| server_impl | false | — | 代码引用,由代码仓库 review |
| client_ui | false | — | 代码引用,由代码仓库 review |
| client_delivery | true | [product] | 交付物需产品验收 |

**修正 4:逆向 changed 流程(下游打回上游)**

`consume_ack(reject)` 触发的 changed 与上游主动 changed 的级联行为一致(§2.2 级联失效),但触发链路不同:

```
下游 consume_ack(node_id=n7, dep_node_id=n5, verdict=reject, reason="信息架构错误")
  → n5 状态 done → changed(T21,trigger=consumer_reject)
  → n5 下游全部 blocked(递归失效,包括 n7 自身)
  → n5 上游通知"下游 n7 打回,原因:信息架构错误"
  → n5 上游重新 submit_artifact → pending_review → 审核合并 → done_pending_ack
  → 下游重新 ready → 重新 consume_ack
```

**修正 5:consume_ack SLA 与默认接受**

为避免下游无限期不 ack 导致流程卡死,设 SLA(默认 48h):
- 产物进入 `done_pending_ack` 后,SLA 计时开始
- SLA 内全下游 ack accept → done
- SLA 内任一下游 ack reject → changed(逆向打回)
- SLA 超时未 ack → 默认 accept(锁定依赖,下游不能再打回)

SLA 超时默认 accept 是保守策略:下游不主动确认视为接受,避免流程停滞。但若下游后续发现问题,仍可通过"人工 notify + 上游主动 changed"路径处理(T10)。

**修正 6:consume_ack 与依赖锁定的关系**

产物 done_pending_ack 期间,下游可正常开始开发(基于该产物),但**依赖未锁定**:
- 下游 in_progress 时,若上游被 ack reject → 下游 blocked(产物引用清除)
- 下游 in_progress 时,若上游 ack accept → 依赖锁定,下游继续
- 下游 submit_artifact 时,Guard 检查上游是否已 ack accept,未 accept 则拒绝提交(`DEP_NOT_ACKED` 错误)

### 4.5 设计图:产物消费确认机制

```mermaid
flowchart TD
    SUBMIT["上游提交 design_proto(n5)<br/>submit_artifact"]
    SUBMIT --> REVIEW["pending_review<br/>自动审核(元数据)"]
    REVIEW -->|approve| MERGE["bot 合并"]

    MERGE --> ACK_CHECK{"skill.requires_consumer_ack?"}
    ACK_CHECK -->|false| DONE_DIRECT["→ done<br/>直接生效"]
    ACK_CHECK -->|true| PENDING_ACK["→ done_pending_ack<br/>待下游消费确认<br/>SLA 48h 开始计时"]

    PENDING_ACK --> NOTIFY_DOWN["通知下游 ack_roles<br/>(product + client)"]
    NOTIFY_DOWN --> DOWN_REVIEW["下游 review 产物内容"]

    DOWN_REVIEW --> ACK_DECIDE{"下游 consume_ack"}

    ACK_DECIDE -->|accept| ACK_ACCEPT["锁定依赖<br/>下游可 submit"]
    ACK_ACCEPT --> ALL_ACCEPT{"全下游 accept?"}
    ALL_ACCEPT -->|是| DONE["→ done<br/>产物正式生效"]
    ALL_ACCEPT -->|否| WAIT_ACK["等待其他下游 ack"]

    ACK_DECIDE -->|reject| ACK_REJECT["consume_ack(reject)<br/>reason=信息架构错误"]
    ACK_REJECT --> REVERSE_CHG["上游 n5: done_pending_ack → changed<br/>(T21, trigger=consumer_reject)"]
    REVERSE_CHG --> CASCADE["级联失效:n5 下游全部 blocked<br/>(递归清除产物引用)"]
    CASCADE --> UPSTREAM_NOTIFY["通知上游:n7 打回,原因:信息架构错误"]
    UPSTREAM_NOTIFY --> UPSTREAM_FIX["上游重新设计 → submit_artifact"]
    UPSTREAM_FIX --> REVIEW

    PENDING_ACK -->|SLA 48h 超时| DEFAULT_ACCEPT["默认 accept<br/>(下游不确认视为接受)"]
    DEFAULT_ACCEPT --> DONE

    DONE --> DOWN_READY["下游 ready<br/>依赖已锁定"]
    DOWN_READY --> DOWN_DEV["下游正常开发"]

    DOWN_DEV --> DOWN_SUBMIT{"下游 submit_artifact"}
    DOWN_SUBMIT --> GUARD{"Guard: 上游已 ack accept?"}
    GUARD -->|是| DOWN_PR["→ 下游 pending_review"]
    GUARD -->|否| DOWN_REJ["拒绝:DEP_NOT_ACKED<br/>上游未确认接受"]

    style PENDING_ACK fill:#e3b341,color:#fff
    style ACK_DECIDE fill:#a371f7,color:#fff
    style ACK_REJECT fill:#b3261e,color:#fff
    style REVERSE_CHG fill:#b3261e,color:#fff
    style DONE fill:#3fb950,color:#fff
    style DEFAULT_ACCEPT fill:#3fb950,color:#fff
```

---

## 5. 缺陷汇总表

### 5.1 缺陷全量清单

| 场景 | 缺陷 ID | 缺陷描述 | PRD 位置 | 严重度 | 修正方案 |
|---|---|---|---|---|---|
| 场景 3 | D3-1 | 管线/节点无优先级字段 | §5.1 / fr2 §2.3 | 高 | PipelineState 新增 priority 字段 |
| 场景 3 | D3-2 | agent 调度无优先级排序 | §3.2 / fr7 §8 | 高 | dispatch_router 按 priority 排序 |
| 场景 3 | D3-3 | 无 agent 资源抢占机制 | fr7 §8 | 高 | p0 可抢占 p2/p3 的 agent |
| 场景 3 | D3-4 | 审核 SLA 无紧急通道 | fr1-fr6 §6.1 | 高 | 新增 SLA-Critical + 双人快审 |
| 场景 3 | D3-5 | 无跨管线资源视图 | fr2 §3.4 / §6.1 | 中 | GlobalDispatchState 聚合多管线 |
| 场景 3 | D3-6 | hotfix 与正常审核无差异 | §6.4 | 中 | hotfix skill + 合并后补审 |
| 场景 7 | D7-1 | 无代理人(delegate)机制 | §5.1 / fr2 §7.4 | 高 | approval 新增 delegate 字段 |
| 场景 7 | D7-2 | backup_reviewer 来源未定义 | fr1-fr6 §6.3.1 | 高 | reviewer_status 表 + 角色池 |
| 场景 7 | D7-3 | 无批量转交工具 | §6 / fr2 §7.5 | 高 | transfer_approvals MCP 工具 |
| 场景 7 | D7-4 | 超时升级是被动,不符真实组织 | fr1-fr6 §6.3.2 | 高 | 代理人优先于超时升级 |
| 场景 7 | D7-5 | 升级到 admin 业务质量无保障 | fr1-fr6 §6.3.4 | 中 | delegate_to_expert + 上下文摘要 |
| 场景 7 | D7-6 | PR reviewer 与 approval approver 未统一覆盖 | §3.1 / §5.1 | 中 | reviewer_status.delegate 统一覆盖 |
| 场景 7 | D7-7 | reviewer 无休假/在职状态 | fr7 ALR-03 | 中 | reviewer_status 表 + Dashboard 入口 |
| 场景 11 | D11-1 | "规则引擎直提"语义模糊 | 附录 B / fr3-fr5 | 高 | 改为人工 fallback 模式 |
| 场景 11 | D11-2 | 开发方人员无法直接调 MCP | §3.2 / §4.1 / fr7 §10.1 | 高 | 降级模式下人员可调 submit_artifact |
| 场景 11 | D11-3 | 无"agent 在线但 LLM 失败"告警 | fr7 §2.1 ALR-03 | 高 | 新增 ALR-13(LLM 失败率) |
| 场景 11 | D11-4 | 节点级卡死检测缺失 | fr7 ALR-04 | 高 | 新增 ALR-14(节点 ready 后 2h 无进展) |
| 场景 11 | D11-5 | LLM 失败与 agent 离线未区分 | fr2 §5.1 | 中 | 错误分类新增 LLM 失败类别 |
| 场景 11 | D11-6 | 无人工 fallback 模式 | 全文 | 高 | 降级模式 + Dashboard 人工提交 |
| 场景 13 | D13-1 | 审核仅提交时,无 done 后反馈 | §6.1 / fr1-fr6 §9.1 | 高 | consume_ack 机制 |
| 场景 13 | D13-2 | changed 仅上游触发,下游无权 | fr2 §2.1 T10 / §2.2 | 高 | T21/T22 下游 reject 触发 changed |
| 场景 13 | D13-3 | 无 consume_ack 消费确认 | §2.1 / §2.2 | 高 | 新增 consume_ack MCP 工具 |
| 场景 13 | D13-4 | 自动审核不校验内容,无下游验收 | §6.4 / §1.4 | 中 | requires_consumer_ack + 下游 ack |
| 场景 13 | D13-5 | done 即终态,缺待确认中间态 | fr2 §2.1 | 中 | 新增 done_pending_ack 态 |
| 场景 13 | D13-6 | 下游反馈纯靠人工 | 无 | 高 | 平台内逆向打回流程 + 追溯 |

### 5.2 缺陷按严重度统计

| 严重度 | 数量 | 典型缺陷 |
|---|---|---|
| 高 | 17 | D3-1/2/3/4、D7-1/2/3/4、D11-1/2/3/4/6、D13-1/2/3/6 |
| 中 | 9 | D3-5/6、D7-5/6/7、D11-5、D13-4/5 |

### 5.3 修正方案按实施阶段分布

| 阶段 | 修正项 | 优先级 |
|---|---|---|
| Phase 1 MVP | D3-1 priority 字段 + D11-2 人员降级提交 + D11-4 节点卡死告警 + D13-3 consume_ack 基础 | P0 |
| Phase 2 生产化 | D3-2/3/4 优先级调度+抢占+快审 + D7-1/2/3/4 代理人+转交 + D11-1/3/6 人工 fallback + D13-1/2/5 逆向打回 | P1 |
| Phase 3 规模化 | D3-5/6 跨管线协调 + D7-5/6/7 专家审+统一覆盖 + D11-5 LLM 错误分类 + D13-4/5 消费确认分级 | P2 |

### 5.4 对 PRD 主文档的修正建议

| PRD 位置 | 现状 | 修正 |
|---|---|---|
| §2.1 状态机 7 态 | 7 态 | 扩展为 8 态,新增 `done_pending_ack` |
| §2.2 DAG 规则 | 级联单向(上游→下游) | 补充逆向级联(下游 ack reject → 上游 changed) |
| §3.2 权限矩阵 | 仅 agent 可调 submit_artifact | 新增"人员(降级模式)"列 |
| §5.1 Pipeline 数据结构 | 无 priority | 新增 priority + priority_reason |
| §6.1 审核流程 | 仅 submit 时审核 | 补充 consume_ack 反馈环节 |
| §6.4 审核策略矩阵 | 按产物类型分 | 补充 requires_consumer_ack 列 + hotfix 快速通道 |
| §6 MCP 工具 | 14 个 | 新增 consume_ack / transfer_approvals / delegate_to_expert(共 17 个) |
| fr1-fr6 §6.1 SLA | 4 级(最快 2h) | 新增 SLA-Critical(15min,双人快审) |
| fr1-fr6 §6.3 升级链 | 超时升级 | 补充代理人(tier 1')优先于超时升级 |
| fr2 §2.1 状态转移 | T1-T18 | 新增 T19-T22(done_pending_ack 相关) |
| fr2 §5.1 错误分类 | 无 LLM 失败 | 新增"LLM 调用失败"类别 |
| fr7 §2.1 告警规则 | ALR-01~12 | 新增 ALR-13(LLM 失败)+ ALR-14(节点卡死) |
| fr7 §8 容量规划 | max_concurrent 排队 | 补充优先级抢占语义 |

---

## 附录:Mermaid 设计图索引

| 图名 | 位置 | 说明 |
|---|---|---|
| hotfix 快速通道流程 | §1.5 | bug 触发 → 优先级调度 → 资源抢占 → 双人快审 → 合并止血 → 补审 |
| 审批代理人机制 | §2.5 | reviewer 状态检查 → 代理人转交 → 升级链 → 专家审 → 全局兜底 |
| LLM 失败人工 fallback 流程 | §3.5 | LLM 调用 → 重试 → 降级模式 → Dashboard 人工提交 → 恢复 |
| 产物消费确认机制 | §4.5 | 合并 → done_pending_ack → 下游 ack → accept/reject → 逆向 changed |

---

**本文档共发现 26 项设计缺陷(17 高 / 9 中),提出 24 项修正方案,涵盖优先级模型、审批韧性、降级路径、产物消费闭环四大主题。所有缺陷均可定位到 PRD 具体章节,修正方案均给出可落地的字段/工具/状态扩展。建议按 Phase 1/2/3 分阶段实施,P0 项优先落地。**

---

## 第三部分:基于需求 9(产物自由)+ 单一 hub 仓模型的重新走查(第三轮)

> **重新走查背景**:PRD v2.1 将产物仓库从"多产物仓库 + RepoRegistry"修正为**单一 hub 仓**(管理方管辖,各端共同提交),`ArtifactRef` 增加 `artifact_kind`(content/reference)、`external_repo`、`external_commit` 字段,引用型产物指向代码仓 commit 仅做 `git ls-remote` 存在性校验,并引入 `GitProvider` 抽象层屏蔽 GitHub/GitLab/Bitbucket 差异(详见主 PRD 附录 D7 和 §5.1)。同时需求 9 明确"产物完全自由,管理方只做管理约束"。
>
> 此轮重新走查针对第一部分 4 个场景,评估"单一 hub 仓 + 需求 9"下异常流程与人工介入的权限/审核/回退机制是否产生新设计缺陷。缺陷编号格式 `D{场景号}-R3.{序号}`,修正方案给到可落地字段/工具/接口扩展。

### 3.1 场景 3 重新走查:hotfix 在单一 hub 仓中的快速通道与并发冲突

#### 3.1.1 旧结论回顾

第一部分针对多产物仓库模型发现 6 项缺陷(D3-1~D3-6):管线/节点无优先级、agent 调度无抢占、审核 SLA 无紧急通道、无跨管线资源视图、hotfix 与正常审核无差异。修正方案引入 `priority` 字段、全局调度器、SLA-Critical 双人快审、合并后补审(`require_post_merge_review`)。

#### 3.1.2 新设计影响

**影响 1:hotfix PR 与常规 PR 共享单一 hub 仓 main 分支,合并串行化成瓶颈**

附录 D7 明确"产物仓库 1 个 hub 仓,管理方管辖,各端共同提交"。所有端的产物 PR(含 hotfix)都指向同一 main 分支。fr1-fr6 §4.3 已设计 rebase 冲突处理,但**合并本身是串行的**(git merge 不可并行)。hotfix PR 即使走快速通道审核,合并阶段仍需排队等前置 PR 合并完成。

具体地:`approve_pr` 在 fr2 §3.2 锁矩阵中持有 `node_id + 下游节点集` 的 advisory lock,但**hub 仓 main 分支的合并锁**未在 PRD 中定义。多个 PR 同时 approve 时,git merge 竞争 main 分支引用,需管理方进程内串行化。

**影响 2:hub 仓 CI 对所有 PR 跑相同检查,hotfix 的 `skip_gates` 无法落地**

第一部分修正 4 提出 hotfix skill 配置 `skip_gates: [lint]`,但 hub 仓 CI(GitHub Actions / GitLab CI)由 `.github/workflows/artifact-ci.yml` 或 `.gitlab-ci.yml` 定义,对**所有 PR** 跑相同 job。CI 引擎不支持"按 PR label 跳过特定 job"(GitHub Actions 的 `if` 条件需硬编码 job 内,无法由外部 PR label 动态控制完整 job 跳过)。

结果:hotfix PR 若 lint 失败,CI fail,分支保护阻止合并,"先合后审"模式无法落地。

**影响 3:hub 仓单点故障下 hotfix 完全卡死**

附录 D7 的"单一 hub 仓"模型将所有产物提交集中到一个仓库。fr7-fr8 §9.1 给出"产物仓库 git mirror 到备库"的灾备方案,但**mirror 是只读副本**,无法在 mirror 上开 PR/合并。当 hub 仓(GitHub/GitLab)宕机时:
- hotfix 无法提交 PR(write 不可用)
- 已提交的 hotfix PR 无法 approve_pr 合并
- 线上 bug 持续,完全卡死

原多产物仓库模型下,hotfix 可提交到独立产物仓库,部分能力可用。

**影响 4:引用型 hotfix 产物的代码质量无保障**

附录 D7 明确引用型产物(`artifact_kind=reference`)指向代码仓 commit,管理方仅做 `git ls-remote` 存在性校验,不 clone 代码仓。hotfix 的 `server_impl` 引用型产物:
- `git ls-remote` 校验 commit 存在,但不校验 commit 内容
- 代码仓的 hotfix PR 由业务方在代码仓审,管理方无感知
- 第一部分修正 4 的 `require_post_merge_review` 只审 hub 仓引用文件,不审代码

若业务方代码仓 hotfix 跳过审核(紧急直推 main),管理方无法发现,代码质量无保障。

#### 3.1.3 需求 9 张力

**张力 1:hotfix 跳过审核 vs 管理方只做管理约束**

需求 9:"产物怎么定义,由各端自己定义和演进"——管理方不约束产物内容,只做管理约束(分支保护、CI、审核)。hotfix 紧急情况下,管理约束需放宽,但单一 hub 仓的分支保护是"硬约束"(main 禁止直接 push),hotfix 也得走 PR。

第一部分修正 4 的"先合后审"(`require_post_merge_review`)试图平衡,但 hub 仓 CI 仍需通过才能合并,"先合"无法实现。

**张力 2:hotfix priority 标记与产物自由冲突**

hotfix 需在产物中标记 priority=p0 供管理方识别,但需求 9 说"产物格式自由"。priority 应放在 manifest(管理元数据)还是产物内容?

若放 manifest:manifest 是管理方 schema,可加 `priority` 字段,不限制产物内容格式,符合需求 9。

若放产物内容:违反需求 9(管理方不解析内容)。

PRD §3.3 manifest schema 未定义 `priority` 字段,需补充。

#### 3.1.4 新发现的设计缺陷

| # | 缺陷 | PRD 位置 | 影响 | 严重度 |
|---|---|---|---|---|
| D3-R3.1 | **hub 仓 main 分支合并串行化无显式锁,hotfix PR 合并排队** | 附录 D7 单一 hub 仓 / fr1-fr6 §4.3 仅 rebase / fr2 §3.2 锁矩阵无 main 分支锁 | hotfix 快速通道审核通过后,合并阶段仍排队等前置 PR,无法分钟级合并 | 高 |
| D3-R3.2 | **hub 仓 CI 不支持按 PR 标记跳过 job,hotfix 的 skip_gates 无法落地** | fr1-fr6 §8.1 CI 检查项 / 第一部分修正 4 skip_gates | hotfix PR 因 CI fail(lint)无法合并,"先合后审"模式失效 | 高 |
| D3-R3.3 | **hub 仓单点故障下 hotfix 完全卡死,无降级路径** | 附录 D7 单一 hub 仓 / fr7-fr8 §9.1 mirror 只读 | hub 仓宕机时 hotfix 无法提交/合并,线上 bug 持续,无 fallback | 高 |
| D3-R3.4 | **引用型 hotfix 产物的代码质量无保障,git ls-remote 只校验存在性** | 附录 D7 引用型产物 / §5.1 ArtifactRef external_commit | hotfix 代码 commit 在代码仓,管理方不审,业务方代码仓可能跳过审核,代码质量无保障 | 中 |
| D3-R3.5 | **manifest schema 无 priority 字段,hotfix 无法从自由格式产物中识别** | §3.3 manifest schema / 需求 9 产物自由 | 管理方无法从产物内容识别 hotfix(需求 9 不解析内容),priority 需进 manifest 但 schema 未定义 | 中 |

#### 3.1.5 修正方案

**修正 1:hub 仓 main 分支合并锁 + 优先级队列**

fr2 §3.2 锁矩阵新增 main 分支合并锁:

```python
HUB_MERGE_LOCK_KEY = 0x7FFFFFFF  # 固定 key,全局唯一

async def with_hub_merge_lock(fn):
    """hub 仓 main 分支合并锁,串行化所有 approve_pr 的 git merge"""
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock($1)", HUB_MERGE_LOCK_KEY)
            return await fn(conn)
```

`approve_pr` 在合并前抢 HUB_MERGE_LOCK,按 PR priority 排队:
- p0 PR 优先合并(p0 队列内 FIFO)
- p2/p3 PR 在 p0 队列空时合并
- 单次合并持锁 < 10s(git squash merge 耗时),超时释放并告警

**修正 2:CI 跳过机制(PR label 驱动)**

hub 仓 CI 配置支持按 PR label 跳过 job:

```yaml
# .github/workflows/artifact-ci.yml
jobs:
  lint:
    if: ${{ !contains(github.event.pull_request.labels.*.name, 'hotfix-skip-lint') }}
    runs-on: ubuntu-latest
    steps:
      - run: coord-ci lint
  test:
    # test 不可跳过(无 if 条件)
    runs-on: ubuntu-latest
    steps:
      - run: coord-ci test
```

管理方 bot 在 hotfix PR 上自动打 `hotfix-skip-lint` label(依据 manifest.priority=p0),CI 读取 label 跳过 lint job,保留 test/security 门禁。

**修正 3:hub 仓单点降级(紧急直提模式)**

新增 `emergency_local_commit` 模式:hub 仓不可达时,admin 在管理方本地暂存 hotfix 产物。

```python
class EmergencyArtifact(TypedDict):
    node_id: str
    manifest: dict
    content_path: str  # 管理方本地暂存路径
    priority: str
    pending_hub_sync: bool  # True=待 hub 仓恢复后补提
    created_at: str
```

降级行为:
- admin 调 `emergency_submit_artifact` 在管理方本地暂存产物
- 节点 state 推进到 `done`(标记 `pending_hub_sync=True`),hotfix 生效
- 管理方 audit_log 记录 `submit_mode=emergency_local`
- hub 仓恢复后,admin 调 `sync_pending_artifacts` 批量补提 PR + 自动合并

**修正 4:引用型 hotfix 代码质量追溯**

manifest 引用型产物子 schema 新增 `code_review_attribution` 字段:

```json
{
  "code_review_attribution": {
    "code_repo_pr_url": "https://github.com/org/backend/pull/123",
    "code_reviewer": "server-lead",
    "code_review_status": "merged",
    "hotfix_justification": "线上支付扣款异常,紧急修复"
  }
}
```

管理方不审代码,但:
- `review_artifact_pr` 校验 `code_repo_pr_url` 可达 + `code_review_status=merged`
- 合并后补审(`require_post_merge_review`)时校验代码仓 PR 已 merge
- 若 `code_review_attribution` 缺失 → reject(`R_CODE_REVIEW_ATTR_MISSING`)

**修正 5:manifest schema 新增 priority 字段**

§3.3 manifest JSON Schema 的 `required` 加 `priority`,`properties` 加:

```json
{
  "priority": {
    "type": "string",
    "description": "管理元数据,管理方据此排序审核/合并,不解析产物内容",
    "enum": ["p0", "p1", "p2", "p3"],
    "default": "p3"
  }
}
```

`priority` 是管理元数据(非产物内容),符合需求 9。管理方从 manifest 读取 priority,不解析产物内容格式。

#### 3.1.6 设计图:hotfix 在单一 hub 仓中的快速通道流程

```mermaid
flowchart TD
    BUG["线上 bug 触发<br/>admin 创建 hotfix 管线(priority=p0)"]
    BUG --> DEV["开发方产出 hotfix 产物<br/>代码 commit 在代码仓"]
    DEV --> ATTR["manifest 填 code_review_attribution<br/>指向代码仓 PR"]
    ATTR --> SUBMIT["submit_artifact<br/>manifest.priority=p0"]

    SUBMIT --> HOOK["hub 仓 webhook<br/>触发 CI"]
    HOOK --> LABEL["管理方 bot 打 hotfix-skip-lint label"]
    LABEL --> CI{"hub 仓 CI"}
    CI -->|lint 跳过| TEST["test/security 门禁<br/>不可跳过"]
    CI -->|test fail| FIX["修复后重提"]
    TEST -->|pass| REVIEW["review_artifact_pr<br/>优先队列(p0 插队)"]

    REVIEW -->|reject| FIX
    REVIEW -->|pass| DUAL{"双人快审<br/>SLA-Critical 15min"}
    DUAL -->|approve| MERGE_Q["进入合并优先级队列<br/>p0 优先"]

    MERGE_Q --> HUB_LOCK{"抢 HUB_MERGE_LOCK"}
    HUB_LOCK -->|获锁| MERGE["git squash merge<br/>持锁 < 10s"]
    HUB_LOCK -->|等锁| WAIT["排队等前置 PR 合并"]
    WAIT --> HUB_LOCK

    MERGE --> STAB["线上止血完成"]
    STAB --> POST["合并后 24h 内补完整 review<br/>含 code_review_attribution 校验"]
    POST -->|review 通过| DONE["hotfix 管线 done"]
    POST -->|review 不通过| CHG["触发 changed 重新修复"]

    BUG -.hub 仓宕机.-> EMERG["emergency_local_commit 模式<br/>admin 本地暂存"]
    EMERG --> LOCAL_DONE["节点 done(pending_hub_sync=True)<br/>hotfix 生效"]
    LOCAL_DONE --> RECOVER{"hub 仓恢复?"}
    RECOVER -->|是| SYNC["sync_pending_artifacts<br/>批量补提 PR + 自动合并"]

    style BUG fill:#b3261e,color:#fff
    style DUAL fill:#e3b341,color:#fff
    style MERGE fill:#3fb950,color:#fff
    style STAB fill:#3fb950,color:#fff
    style EMERG fill:#b3261e,color:#fff
    style LOCAL_DONE fill:#e3b341,color:#fff
    style SYNC fill:#3fb950,color:#fff
```

---

### 3.2 场景 7 重新走查:审批人缺席下的 hub 仓 PR 审核转交

#### 3.2.1 旧结论回顾

第一部分发现 7 项缺陷(D7-1~D7-7):无代理人机制、backup_reviewer 来源未定义、无批量转交工具、超时升级被动、admin 不懂业务、PR reviewer 与 approval approver 未统一覆盖、reviewer 无休假状态。修正方案引入 `delegate` 字段、`reviewer_status` 表、`transfer_approvals` MCP 工具、`delegate_to_expert`、统一代理人覆盖。

#### 3.2.2 新设计影响

**影响 1:单一 hub 仓 CODEOWNERS 与管理方 reviewer_status 不同步**

单一 hub 仓模型下,hub 仓的 CODEOWNERS(GitHub)/ APPROVALS(GitLab)是**单文件**,按 path 分配 reviewer:

```
# CODEOWNERS
product_spec/    @reviewer_zhang
api_contract/    @reviewer_wang
design_asset/    @reviewer_li
client_delivery/ @reviewer_zhao
```

第一部分修正 2 的 `reviewer_status` 表在管理方维护,但 hub 仓 CODEOWNERS 不感知。reviewer_zhang 休假,管理方 `reviewer_status` 设 `delegate=reviewer_li`,但 hub 仓 CODEOWNERS 仍指向 reviewer_zhang,GitHub native PR 审核请求仍发给 reviewer_zhang。

**影响 2:GitProvider 抽象未定义 reviewer 转交接口**

附录 D7 提及 `GitProvider` 抽象层屏蔽 GitHub/GitLab/Bitbucket 差异,但主 PRD 和 fr1-fr6 未列出 GitProvider 的完整接口清单。第一部分修正 4 的 `transfer_approvals` MCP 工具在管理方进程内做转交,但 hub 仓 native 的 PR reviewer 指派(GitHub `POST /repos/{owner}/{repo}/pulls/{pr}/requested_reviewers`)需通过 GitProvider 调用。

PRD 未定义 `GitProvider.update_pr_reviewers` 接口,批量转交无法跨 provider 落地。

**影响 3:代理人审 PR 的审计链断裂**

代理人 reviewer_li 代休假的 reviewer_zhang 审 hub 仓 PR 时:
- 管理方 `approve_pr` 由 bot 调用(因 hub 仓 bot token 才有 merge 权限)
- hub 仓 native 审计日志显示 reviewer 是 bot,而非实际代理人 reviewer_li
- 管理方 audit_log 可记录 `reviewer=delegate:reviewer_li`,但 hub 仓 PR 评论/review 记录无法体现代理人身份

结果:hub 仓 native 审计与管理方审计不一致,追溯困难。

**影响 4:产物格式自由下代理人无法判断元数据合理性**

需求 9 下产物格式自由(YAML/JSON/Markdown/Figma 链接 JSON 均可)。代理人审 PR 时,规则引擎校验元数据(字段存在性、版本格式),但**不校验内容合理性**。例如:
- `design_asset` 的 figma 链接,代理人如何判断链接是否指向正确的设计稿?
- `api_contract` 的 schema,代理人若非该业务领域,如何判断字段是否合理?

第一部分修正 5 的 `delegate_to_expert` 可解决,但代理人是"事先指定"的常规代理人,非专家,产物格式自由加剧代理人审核难度。

**影响 5:hub 仓单点 + reviewer 缺席双重叠加**

reviewer 休假时若 hub 仓不可达,代理人无法审 PR(PR 在 hub 仓上,write 不可用)。第一部分修正的 `transfer_approvals` 依赖 hub 仓 PR API,单点故障下失效。

#### 3.2.3 需求 9 张力

**张力 1:产物自由 + 代理人审核质量**

需求 9 下产物格式自由,代理人审核只能依赖规则引擎 + 产物预览。但规则引擎不校验内容,预览对自由格式产物(如非标 JSON)可读性差。代理人若不懂该产物类型,审核质量下降。

管理方是否应提供"产物内容辅助校验"工具(如 figma 链接可达性校验)?这又接近"解析内容",与需求 9 张力。

**张力 2:管理约束放宽**

reviewer 长期缺席下,管理约束是否允许"自审"(submitter 自行 approve)?需求 9 说"管理方只做管理约束",自审破坏约束。但紧急情况下(reviewer 长期缺席 + 业务受阻),约束需放宽。

#### 3.2.4 新发现的设计缺陷

| # | 缺陷 | PRD 位置 | 影响 | 严重度 |
|---|---|---|---|---|
| D7-R3.1 | **hub 仓 CODEOWNERS 与管理方 reviewer_status 不同步,delegate 转交后 native reviewer 未更新** | 附录 D7 单一 hub 仓 / 第一部分修正 2 reviewer_status | reviewer 休假后 hub 仓 native PR 审核请求仍发原 reviewer,代理人收不到通知 | 高 |
| D7-R3.2 | **GitProvider 抽象未定义 update_pr_reviewers / get_codeowners / update_codeowners 接口** | 附录 D7 GitProvider / §6 MCP 工具 | transfer_approvals 无法跨 provider(GitHub/GitLab/Bitbucket)落地,批量转交失效 | 高 |
| D7-R3.3 | **代理人审 PR 时 hub 仓 native 审计显示 bot 而非代理人,审计链断裂** | fr1-fr6 §6.5 审计日志 / 附录 D7 hub 仓 bot token | hub 仓 native 审计与管理方 audit_log 不一致,合规追溯困难 | 中 |
| D7-R3.4 | **产物格式自由下代理人无法判断元数据合理性,审核质量下降** | 需求 9 / §1.4 不校验内容 / 第一部分修正 5 delegate_to_expert | 代理人非专家,figma 链接有效性、schema 合理性难以判断,approve 质量存疑 | 中 |
| D7-R3.5 | **hub 仓单点故障 + reviewer 缺席双重叠加,代理人无法审 PR** | 附录 D7 单一 hub 仓 / fr7-fr8 §9.1 mirror 只读 | hub 仓宕机时 transfer_approvals 失效,代理人无法审 PR,流程完全卡死 | 高 |

#### 3.2.5 修正方案

**修正 1:reviewer_routing 表与 hub 仓 CODEOWNERS 双向同步**

管理方维护 `reviewer_routing` 表,与 hub 仓 CODEOWNERS 双向同步:

```sql
CREATE TABLE reviewer_routing (
    path_pattern TEXT PRIMARY KEY,      -- 如 "api_contract/*"
    reviewer_id TEXT NOT NULL,           -- 当前 reviewer
    delegate_id TEXT,                    -- 代理人(reviewer_status 同步)
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

`reviewer_status` 变更(delegate/transfer)时,管理方 bot 通过 GitProvider API 自动更新 hub 仓 CODEOWNERS:

```python
async def sync_codeowners_to_hub():
    routing = await db.fetch_all("SELECT * FROM reviewer_routing")
    content = render_codeowners(routing)  # 生成 CODEOWNERS 文件内容
    await git_provider.update_codeowners(content)  # GitProvider API
    await git_provider.commit_direct("main", ".github/CODEOWNERS", content,
                                      author="mgmt-bot", message="sync reviewer_routing")
```

**修正 2:GitProvider 接口扩展**

附录 D7 GitProvider 抽象层新增接口:

| 接口 | 作用 | GitHub 实现 | GitLab 实现 |
|---|---|---|---|
| `update_pr_reviewers(pr_id, new_reviewers)` | 更新 PR 指派 reviewer | `POST /repos/.../pulls/{pr}/requested_reviewers` | `PUT /projects/.../merge_requests/{mr}` |
| `get_codeowners()` | 读取 CODEOWNERS 文件 | `GET /repos/.../contents/.github/CODEOWNERS` | `GET /projects/.../repository/files/.gitlab/CODEOWNERS` |
| `update_codeowners(content)` | 更新 CODEOWNERS 文件 | `PUT /repos/.../contents/.github/CODEOWNERS` | `PUT /projects/.../repository/files/.gitlab/CODEOWNERS` |
| `add_pr_comment(pr_id, comment)` | PR 评论(注明代理人身份) | `POST /repos/.../issues/{pr}/comments` | `POST /projects/.../merge_requests/{mr}/notes` |
| `submit_pr_review(pr_id, verdict, body)` | 提交 PR review | `POST /repos/.../pulls/{pr}/reviews` | `POST /projects/.../merge_requests/{mr}/approve` |

`transfer_approvals` MCP 工具调用 `update_pr_reviewers` 同步 hub 仓 native reviewer。

**修正 3:代理人审 PR 的审计链修复**

代理人调 `approve_pr` 时,MCP 携带 `actual_reviewer_id`:

```json
{
  "name": "approve_pr",
  "inputSchema": {
    "properties": {
      "pr_id": {"type": "integer"},
      "note": {"type": "string"},
      "actual_reviewer_id": {"type": "string", "description": "实际审核人(代理人审时填)"}
    }
  }
}
```

- 管理方 audit_log 记录 `reviewer=delegate:reviewer_li`(`actual_reviewer_id`)
- 管理方 bot 调 `git_provider.add_pr_comment(pr_id, "代 reviewer_zhang 审,实际审核人 reviewer_li")` 在 hub 仓 PR 注明
- 管理方 bot 调 `git_provider.submit_pr_review(pr_id, "approve", body)` 提交 review,body 含代理人身份

**修正 4:代理人辅助校验工具**

新增 `validate_artifact_metadata` MCP 工具,辅助代理人审核:

```json
{
  "name": "validate_artifact_metadata",
  "description": "辅助代理人校验产物元数据合理性(不解析内容)",
  "inputSchema": {
    "properties": {
      "pr_id": {"type": "integer"}
    }
  }
}
```

返回:
- 规则引擎结果(`ReviewVerdict`)
- 外部链接可达性校验(figma URL HTTP HEAD)
- 历史相似产物对比(同 node_type 历史 approve 记录)
- skill guide 摘要

**修正 5:hub 仓单点降级下的审批**

hub 仓不可达时,admin 在管理方本地审 PR(读取 PR 缓存):

```python
class LocalApprovalRecord(TypedDict):
    pr_id: int
    node_id: str
    actual_reviewer_id: str
    verdict: str  # approve | reject
    reason: str
    pending_hub_sync: bool
    ts: str
```

- admin 调 `emergency_approve_pr` 在管理方本地记录审批
- 节点 state 推进(若 approve)
- hub 仓恢复后,bot 补充在 hub 仓 PR 上评论审核结果 + 合并

#### 3.2.6 设计图:代理人审 PR 与 hub 仓 CODEOWNERS 同步流程

```mermaid
sequenceDiagram
    participant RZ as reviewer_zhang(休假)
    participant RS as reviewer_status 表
    participant BOT as 管理方 bot
    participant GP as GitProvider
    participant HUB as hub 仓(GitHub)
    participant RL as reviewer_li(代理人)
    participant MCP as MCP Server
    participant AUDIT as audit_log

    Note over RZ,RS: reviewer_zhang 设置休假
    RZ->>RS: 设置 status=on_leave, delegate=reviewer_li

    Note over RS,BOT: 触发 CODEOWNERS 同步
    RS->>BOT: 同步事件
    BOT->>GP: update_codeowners(api_contract/* → reviewer_li)
    GP->>HUB: PUT .github/CODEOWNERS
    HUB-->>GP: committed

    Note over RL,HUB: 代理人审 PR
    HUB->>RL: PR #42 审核请求(api_contract/)
    RL->>MCP: approve_pr(pr_id=42, actual_reviewer_id=reviewer_li)
    MCP->>AUDIT: 记录 reviewer=delegate:reviewer_li
    MCP->>GP: add_pr_comment(42, "代 reviewer_zhang 审,实际 reviewer_li")
    GP->>HUB: POST /pulls/42/comments
    MCP->>GP: submit_pr_review(42, approve, body)
    GP->>HUB: POST /pulls/42/reviews
    MCP->>GP: merge_pr(42)
    GP->>HUB: PUT /pulls/42/merge
    HUB-->>GP: merged
    MCP->>AUDIT: 记录 merge_commit

    Note over HUB,AUDIT: hub 仓宕机降级
    HUB--xRL: PR 审核请求失败
    RL->>MCP: emergency_approve_pr(pr_id=42, actual_reviewer_id=reviewer_li)
    MCP->>AUDIT: 记录 submit_mode=emergency_local, pending_hub_sync=True
    Note over MCP: hub 仓恢复后 bot 补提评论+合并
```

---

### 3.3 场景 11 重新走查:agent 故障下的人工 fallback 直提 hub 仓

#### 3.3.1 旧结论回顾

第一部分发现 6 项缺陷(D11-1~D11-6):"规则引擎直提"语义模糊、开发方人员无法直接调 MCP、无 LLM 失败告警、节点级卡死检测缺失、LLM 失败与 agent 离线未区分、无人工 fallback 模式。修正方案引入人工 fallback 模式、人员降级提交(user token)、ALR-13/14 告警、LLM 错误分类。

#### 3.3.2 新设计影响

**影响 1:人员降级提交借 MCP 间接用 bot token,越权风险**

第一部分修正 2 提出人员用 user token 调 MCP submit_artifact。但单一 hub 仓模型下,hub 仓的 write 权限集中在 bot token(管理方 bot 才能推 feat 分支 + 开 PR + 合并)。人员 user token 无 hub 仓 write 权限。

人员调 MCP submit_artifact,MCP 内部用 bot token 代为推 feat 分支 + 开 PR。bot token 权限过大(可写整个 hub 仓),人员借 MCP 间接使用 bot token,存在越权风险(如人员故意/误操作推非本角色产物)。

fr7-fr8 §10.1 的"工具级 RBAC"在 MCP 层校验 role,但 hub 仓层 bot token 无 role 限制。

**影响 2:引用型产物 external_commit 归属校验缺失**

附录 D7 引用型产物指向代码仓 commit,`git ls-remote` 校验存在性。但人员降级提交时填 `external_repo` / `external_commit`:
- `git ls-remote external_repo` 校验 commit 存在
- 但不校验 commit 是否属于声明的 `external_repo`(commit hash 可能属于其他 repo,git ls-remote 只查 refs)
- 人员可能填错(复制粘贴错误)或恶意填其他 repo 的 commit

fr1-fr6 §4.1.4 的 `git_ls_file_exists` op 只校验 hub 仓内文件,未校验 `external_commit` 归属。

**影响 3:降级模式下 hub 仓 CI 严格校验阻塞人员提交**

fr1-fr6 §8.1 的 CI 检查项(CI-1~CI-11)对所有 PR 严格校验:目录白名单、文件命名规范(三段式 `<seq>_<slug>.<ext>`)、manifest schema、seq 唯一性等。

降级模式下人员不熟悉命名规范,CI fail 频发:
- 文件名含中文/空格 → CI-2 fail
- seq 跳号 → CI-9 warn(不阻断,但 CI-8 seq 重复 fail)
- manifest 字段缺失 → CI-4 fail

人员反复重提,阻塞降级流程。第一部分修正 3 的"降级模式行为"未涉及 CI 宽松。

**影响 4:GitProvider 未定义轻量提交接口**

人员 Dashboard 提交界面需适配 provider 差异(GitHub PR 模板 vs GitLab MR 模板)。附录 D7 的 GitProvider 抽象未定义"轻量提交"接口,人员 Dashboard 需直接调 provider API,差异由前端处理,耦合度高。

**影响 5:LLM + hub 仓双重故障无降级**

第一部分修正 3 的降级模式假设 hub 仓可用(人员通过 Dashboard 调 MCP 提交 PR)。若 LLM 故障 + hub 仓故障双重叠加,人工 fallback 也无法提交,MCP 调用失败,完全卡死。

#### 3.3.3 需求 9 张力

**张力 1:产物自由 + 人工提交质量**

需求 9 下产物格式自由,人员可提交任意格式。但人工提交的产物质量参差:
- 人员可能填错 manifest(如 external_commit 填错)
- 规则引擎校验元数据,但人员不懂规则,反复重提
- 管理方如何审核人工提交的"自由格式"产物?

规则引擎是"管理约束"(需求 9 允许),但降级模式下约束是否放宽?

**张力 2:管理约束放宽**

LLM 故障下,管理约束(CI、规则引擎)是否放宽?需求 9 说"管理方只做管理约束",降级模式下约束放宽但不可取消。但人员降级提交若 CI fail 频发,约束反而阻塞流程。

#### 3.3.4 新发现的设计缺陷

| # | 缺陷 | PRD 位置 | 影响 | 严重度 |
|---|---|---|---|---|
| D11-R3.1 | **人员降级提交借 MCP 间接用 bot token,bot token 权限过大(可写整个 hub 仓),越权风险** | 附录 D7 单一 hub 仓 / fr7-fr8 §10.1 bot token / 第一部分修正 2 user token | 人员故意/误操作可推非本角色产物,bot token 无 role 限制 | 高 |
| D11-R3.2 | **引用型产物 external_commit 归属校验缺失,git ls-remote 只校验存在性不校验归属** | 附录 D7 引用型产物 / fr1-fr6 §4.1.4 git_ls_file_exists | 人员填错/恶意填其他 repo 的 commit,管理方无法发现 | 高 |
| D11-R3.3 | **降级模式下 hub 仓 CI 对人员提交严格校验,人员不熟悉规范导致 CI fail 频发,阻塞降级流程** | fr1-fr6 §8.1 CI 检查项 / 第一部分修正 3 降级模式 | 降级模式下 CI fail 阻塞人员提交,LLM 故障叠加 CI 故障 | 高 |
| D11-R3.4 | **GitProvider 抽象未定义轻量提交接口,人员 Dashboard 需适配 provider 差异** | 附录 D7 GitProvider / 第一部分修正 3 Dashboard 提交 | 前端耦合 provider,GitHub/GitLab 切换需改前端 | 中 |
| D11-R3.5 | **LLM + hub 仓双重故障无降级,人工 fallback 也无法提交,完全卡死** | 附录 D7 单一 hub 仓 / 第一部分修正 3 降级模式假设 hub 仓可用 | 双重故障下无降级路径,流程完全卡死 | 高 |

#### 3.3.5 修正方案

**修正 1:人员降级提交的权限隔离(human_submit_token)**

引入 `human_submit_token`(per-user scoped),仅允许推 feat 分支 + 开 PR,无 merge 权限:

```python
class HumanSubmitToken(TypedDict):
    user_id: str
    role: str  # product | server | design | client
    allowed_paths: list[str]  # 如 ["api_contract/*"] 按 role 限制
    can_merge: bool  # False,无合并权限
    expires_at: str
```

MCP 用 human_submit_token 而非 bot token 代提:
- `submit_artifact` 校验 `allowed_paths` 包含产物 path(按 role 限制)
- 推 feat 分支用 human_submit_token(若 hub 仓支持 per-user scoped token,GitHub fine-grained token)
- 开 PR 用 human_submit_token
- 合并仍用 bot token(approve_pr 时)

hub 仓若不支持 per-user scoped token(GitLab),MCP 用 bot token 但记录 `submitter=user:zhangsan`,audit_log 可追溯。

**修正 2:引用型产物 external_commit 归属校验**

fr1-fr6 §4.1.4 新增 op `verify_external_ref_ownership`:

```yaml
- id: R_EXTERNAL_REF_OWNERSHIP
  name: 引用型产物代码 commit 归属校验
  priority: 78
  combinators: AND
  on_fail: reject
  checks:
    - field: external_repo
      op: git_ls_remote_commit_exists
      value_field: external_commit
    - field: external_commit
      op: commit_belongs_to_repo
      value_field: external_repo
```

`commit_belongs_to_repo` op 实现:
- `git ls-remote external_repo` 获取 refs
- `git cat-file -t external_commit`(需浅 clone 或 provider API `GET /repos/{owner}/{repo}/commits/{sha}`)
- 若 commit 不属于该 repo → reject(`R_EXTERNAL_REF_NOT_OWNED`)

GitProvider 新增 `verify_commit_belongs(repo, commit)` 接口,屏蔽 provider 差异(GitHub `GET /repos/.../commits/{sha}` / GitLab `GET /projects/.../repository/commits/{sha}`)。

**修正 3:降级模式 CI 宽松**

hub 仓 CI 配置支持"宽松模式"(由 PR label `degraded-mode` 触发):

```yaml
jobs:
  validate-strict:
    if: ${{ !contains(github.event.pull_request.labels.*.name, 'degraded-mode') }}
    runs-on: ubuntu-latest
    steps:
      - run: coord-ci check --strict  # CI-1~CI-11 全量
  validate-loose:
    if: ${{ contains(github.event.pull_request.labels.*.name, 'degraded-mode') }}
    runs-on: ubuntu-latest
    steps:
      - run: coord-ci check --loose  # 仅 CI-3 manifest 存在 + CI-4 manifest schema 必填字段
```

降级模式下:
- 管理方 bot 自动打 `degraded-mode` label
- CI 切换到宽松模式,仅校验 manifest schema 必填字段
- 跳过 CI-2 命名规范、CI-8 seq 唯一性、CI-9 seq 连续性
- 降级模式结束后,admin 触发 `ci_retrospective` 批量补审降级期间的 PR

**修正 4:GitProvider 轻量提交接口**

附录 D7 GitProvider 新增 `create_pr_lite` 接口:

```python
async def create_pr_lite(
    repo: str,
    branch: str,
    files: dict[str, str],  # path → content
    manifest: dict,
    pr_title: str,
    pr_body: str,
) -> PrId:
    """屏蔽 provider 差异的轻量提交,人员 Dashboard 调用"""
    # 内部:推 feat 分支 + 开 PR,适配 GitHub/GitLab/Bitbucket
```

人员 Dashboard 只填产物内容 + manifest,接口自动适配 GitHub PR / GitLab MR / Bitbucket PR。

**修正 5:LLM + hub 仓双重故障降级(本地暂存模式)**

双重故障时启用"本地暂存模式":

```python
class LocalStagedArtifact(TypedDict):
    node_id: str
    manifest: dict
    content_path: str  # 管理方本地暂存路径
    submitter: str  # user_id
    pending_hub_sync: bool
    pending_llm_recover: bool
    created_at: str
```

- 人员在 Dashboard 填产物,管理方本地暂存(不提 hub 仓)
- 节点 state 标记 `pending_hub_sync`,流程暂缓推进(不 done)
- hub 仓恢复后,admin 触发 `sync_pending_artifacts` 批量补提
- LLM 恢复后,agent 接管后续节点

#### 3.3.6 设计图:LLM 故障人工 fallback 直提 hub 仓流程(含双重故障降级)

```mermaid
flowchart TD
    NODE["节点 n3 ready<br/>等待 server_agent 协调提交"]
    NODE --> LLM_CALL["agent 调 LLM 失败<br/>ALR-13 告警"]
    LLM_CALL --> DEGRADE["进入降级模式<br/>SSE 推送 llm_degraded"]

    DEGRADE --> DASHBOARD["Dashboard:待人工提交任务列表<br/>通知 server 角色 on-call"]
    DASHBOARD --> HUMAN["开发方人员登录 Dashboard"]
    HUMAN --> FILL["填写产物内容 + manifest<br/>+ 引用型产物填 external_repo/external_commit"]

    FILL --> SUBMIT["人员用 human_submit_token<br/>调 submit_artifact(降级模式)"]

    SUBMIT --> PATH_CHECK{"MCP 校验 allowed_paths<br/>(role 限制)"}
    PATH_CHECK -->|越权| REJ_PATH["拒绝:ROLE_PATH_FORBIDDEN"]
    PATH_CHECK -->|通过| EXT_CHECK{"引用型产物?<br/>verify_external_ref_ownership"}

    EXT_CHECK -->|commit 不属于 repo| REJ_EXT["拒绝:R_EXTERNAL_REF_NOT_OWNED"]
    EXT_CHECK -->|通过或非引用型| LABEL["管理方 bot 打 degraded-mode label"]
    LABEL --> CI{"hub 仓 CI 宽松模式<br/>仅 manifest schema"}

    CI -->|fail| FIX["人员修复后重提"]
    CI -->|pass| REVIEW["review_artifact_pr<br/>(降级模式宽松审核)"]
    REVIEW --> MERGE["approve_pr → bot 合并<br/>(用 bot token)"]
    MERGE --> RECOVER{"LLM 恢复?"}
    RECOVER -->|否| KEEP["保持降级模式<br/>下一节点继续人工"]
    RECOVER -->|是| ADMIN_CLOSE["admin 关闭降级模式<br/>恢复 agent 协调"]

    DEGRADE -.hub 仓也宕机.-> DOUBLE["双重故障<br/>本地暂存模式"]
    DOUBLE --> LOCAL["人员填产物,管理方本地暂存<br/>节点 pending_hub_sync"]
    LOCAL --> WAIT_BOTH["等 hub 仓 + LLM 恢复"]
    WAIT_BOTH --> RECOVER2{"hub 仓 + LLM 恢复?"}
    RECOVER2 -->|是| SYNC["sync_pending_artifacts<br/>批量补提 + agent 接管"]

    style LLM_CALL fill:#e3b341,color:#fff
    style DEGRADE fill:#b3261e,color:#fff
    style SUBMIT fill:#3fb950,color:#fff
    style MERGE fill:#3fb950,color:#fff
    style DOUBLE fill:#b3261e,color:#fff
    style LOCAL fill:#e3b341,color:#fff
    style SYNC fill:#3fb950,color:#fff
```

---

### 3.4 场景 13 重新走查:逆向打回与 hub 仓 revert 机制

#### 3.4.1 旧结论回顾

第一部分发现 6 项缺陷(D13-1~D13-6):审核仅提交时、changed 仅上游触发、无 consume_ack、自动审核不校验内容、done 即终态、下游反馈纯人工。修正方案引入 `consume_ack` MCP 工具、`done_pending_ack` 态(8 态)、T21/T22 逆向 changed、`requires_consumer_ack` 配置、SLA 默认接受。

#### 3.4.2 新设计影响

**影响 1:hub 仓 revert PR 需走完整审核流程,逆向打回周期长**

单一 hub 仓模型下,已合并的产物在 hub 仓 main 分支上。逆向打回(consume_ack reject)触发上游 changed,上游需重新提交新版本 PR。但旧版本已在 main 上,若需"回退"旧版本(而非仅重提新版本),需开 revert PR。

revert PR 也走分支保护 + CI + 审核流程,周期长。第一部分修正 4 的逆向 changed 流程未涉及 revert PR,假设"上游重新 submit_artifact"即可,但若上游产物已被下游消费,旧版本需 revert 而非仅重提。

**影响 2:引用型产物代码层 revert 管控缺失**

引用型产物(`artifact_kind=reference`)的 hub 仓文件是引用 JSON(`*_ref.json`),指向代码仓 commit。逆向打回引用型产物:
- hub 仓 revert 引用 JSON(管理方管辖)——可做
- 但代码仓的 commit 不可变,代码层 revert 需在代码仓开 revert PR——管理方管不了代码仓
- 代码仓 revert 由业务方做,管理方无管控

结果:hub 仓引用 revert 了,但代码仓 commit 仍在,下游若直接用代码 commit 仍有问题。

**影响 3:产物格式自由下 consume_ack reason 难以结构化**

需求 9 下产物格式自由,下游 consume_ack reject 需结构化 reason。但自由格式产物的"问题"难以结构化:
- 设计稿"信息架构错误"——主观判断
- API 契约"字段缺失"——相对客观,但自由格式(非 OpenAPI)难以自动判断
- 管理方不解析内容(需求 9),无法仲裁"问题归属"

第一部分修正 4 的 `consume_ack` reason 字段是自由文本,难以聚合统计。

**影响 4:逆向打回触发上游 changed,新版本产物路径冲突**

上游 changed 后重新提交新版本,新版本产物 path 可能与其他端正在审的 PR 冲突(hub 仓单仓路径冲突)。fr1-fr6 §5.3.1 的路径冲突检测可发现,但解决需人工协调,逆向打回周期变长。

**影响 5:hub 仓单点下 consume_ack 卡死**

consume_ack 依赖 MCP 工具,MCP 调 hub 仓 PR API。hub 仓不可达时,consume_ack 无法提交,产物卡在 `done_pending_ack`,下游无法继续。第一部分修正 5 的 SLA 默认接受超时机制依赖管理方定时任务,但 ack 本身需提交到 hub 仓(记录在 PR 评论或 audit)。

#### 3.4.3 需求 9 张力

**张力 1:产物自由 + 逆向打回归属判断**

产物格式自由,下游 consume_ack reject 的 reason 难以结构化,管理方无法仲裁"问题归属"。例如 A 端认为设计稿有问题,B 端认为没问题,管理方如何决策?

需求 9 说"管理方只做管理约束",不解析内容。但逆向打回需判断"问题归属",接近"解析内容"。

**张力 2:管理约束放宽**

逆向打回紧急情况下,revert PR 是否走快速通道?需求 9 说"管理方只做管理约束",revert PR 也需审核,不可绕过。但紧急回退需快速,审核周期长矛盾。

#### 3.4.4 新发现的设计缺陷

| # | 缺陷 | PRD 位置 | 影响 | 严重度 |
|---|---|---|---|---|
| D13-R3.1 | **hub 仓 revert PR 需走完整审核流程,逆向打回周期长,与"快速止血"矛盾** | 附录 D7 单一 hub 仓 / fr1-fr6 §6.1 SLA / 第一部分修正 4 逆向 changed | consume_ack reject 后,旧版本 revert PR 走 8h SLA,逆向打回周期长 | 高 |
| D13-R3.2 | **引用型产物代码层 revert 管控缺失,hub 仓 revert 引用但代码仓 commit 不可变** | 附录 D7 引用型产物 / §5.1 ArtifactRef external_commit | 代码仓 revert 由业务方做,管理方无管控,代码 commit 仍在 | 高 |
| D13-R3.3 | **产物格式自由下 consume_ack reject 的 reason 难以结构化,管理方无法仲裁问题归属** | 需求 9 / §1.4 不校验内容 / 第一部分修正 4 consume_ack reason | 多端 ack 冲突时管理方无法决策,逆向打回卡死 | 中 |
| D13-R3.4 | **逆向打回触发上游 changed,新版本产物路径可能与其他端正在审的 PR 冲突(hub 仓单仓路径冲突)** | 附录 D7 单一 hub 仓 / fr1-fr6 §5.3.1 路径冲突 | 逆向打回叠加路径冲突,需人工协调,周期变长 | 中 |
| D13-R3.5 | **hub 仓单点故障下 consume_ack 无法提交,产物卡在 done_pending_ack** | 附录 D7 单一 hub 仓 / 第一部分修正 5 SLA 默认接受 | hub 仓宕机时 consume_ack 失效,产物卡在待确认态,下游无法继续 | 高 |

#### 3.4.5 修正方案

**修正 1:revert PR 快速通道**

consume_ack reject 触发的 revert PR 标记 `priority=p1`(比 hotfix p0 低,比常规 p3 高):

```yaml
# skill.yaml 补充
revert_pr:
  sla_level: SLA-Human-2  # 4h,而非常规 8h
  priority: p1
  review_focus: metadata_only  # 仅审 revert 是否正确,不审产物内容
```

revert PR 的审核重点是"revert 是否正确"(revert 的 commit 是否对应旧版本),而非产物内容,加速审核。

**修正 2:引用型产物双层 revert**

hub 仓 revert 引用文件 + 通知代码仓 owner 开代码仓 revert PR:

```python
class CodeRevertTracking(TypedDict):
    hub_revert_pr_id: int
    hub_revert_pr_url: str
    code_repo_revert_pr_url: str | None  # 代码仓 revert PR,由业务方开
    code_repo_revert_status: str  # pending | opened | merged | skipped
    tracked_at: str
```

管理方流程:
- consume_ack reject 触发上游 changed
- 上游重新提交新版本引用型产物(新 external_commit)
- 管理方 bot 自动在代码仓 issue 区开 issue,通知代码仓 owner "commit {old} 需 revert,关联 hub 仓 PR {new}"
- 代码仓 owner 在代码仓开 revert PR,填入 `code_repo_revert_pr_url`
- 管理方校验 `code_repo_revert_pr_url` 已 merged 后,hub 仓新版本引用 PR 才 approve

**修正 3:consume_ack reason 模板化辅助**

提供 reason 模板(按产物类型),建议非强制(符合需求 9):

```yaml
# skill.yaml 补充
consumer_ack:
  reason_templates:
    design_proto:
      - "信息架构错误:导航层级混乱"
      - "视觉规范不符:色彩/字体不一致"
      - "交互问题:核心入口埋得太深"
    api_contract:
      - "字段缺失:缺少 {field}"
      - "类型错误:{field} 应为 {type}"
      - "兼容性:与 v{version} 不兼容"
```

模板是建议(非强制),管理方按模板分类聚合统计。多端 ack 冲突时,admin 调 `delegate_to_expert`(第一部分修正 5)指定领域专家仲裁。

**修正 4:逆向打回路径冲突防护**

上游 changed 后,管理方扫描 hub 仓 pending PRs:

```python
async def check_reverse_invalidate_conflicts(changed_node_id: str):
    """逆向打回后,扫描 pending PRs 路径冲突"""
    new_version_path = get_new_version_path(changed_node_id)
    pending_prs = await get_pending_prs()
    for pr in pending_prs:
        if pr.node_id == changed_node_id:
            continue  # 自身
        if path_conflict(pr.files, new_version_path):
            await mark_pr_needs_rebase(pr.pr_id, reason="上游逆向打回,路径冲突")
```

受影响 PR 标记 `needs_rebase`,上游新版本合并后自动 rebase 或 reject。

**修正 5:consume_ack 降级(hub 仓单点)**

hub 仓不可达时,consume_ack 在管理方本地记录:

```python
class LocalConsumeAck(TypedDict):
    node_id: str  # 下游节点
    dep_node_id: str  # 上游产物节点
    verdict: str  # accept | reject
    reason: str
    actual_reviewer_id: str
    pending_hub_sync: bool
    ts: str
```

- 人员调 `emergency_consume_ack` 在管理方本地记录
- 节点 state 推进(若 reject,上游 changed)
- hub 仓恢复后,bot 补提 ack 记录到 hub 仓 PR 评论 + audit_log

#### 3.4.6 设计图:逆向打回与 hub 仓 revert 机制(含引用型双层 revert)

```mermaid
flowchart TD
    DOWN["下游 n7 消费上游 n5(design_proto)<br/>发现问题"]
    DOWN --> ACK["consume_ack(node_id=n7, dep_node_id=n5, verdict=reject)"]

    ACK --> HUB_CHECK{"hub 仓可达?"}
    HUB_CHECK -->|是| NORMAL_ACK["正常提交 ack 到 hub 仓"]
    HUB_CHECK -->|否| EMERG_ACK["emergency_consume_ack<br/>管理方本地记录 pending_hub_sync"]

    NORMAL_ACK --> CHG["上游 n5: done_pending_ack → changed<br/>(T21, trigger=consumer_reject)"]
    EMERG_ACK --> CHG

    CHG --> KIND{"n5 产物类型?"}
    KIND -->|内容型| CONTENT_REVERT["hub 仓开 revert PR<br/>(旧版本) priority=p1"]
    KIND -->|引用型| REF_REVERT["双层 revert"]

    CONTENT_REVERT --> REVERT_REVIEW["revert PR 快速审核<br/>SLA-Human-2 4h<br/>review_focus=metadata_only"]
    REVERT_REVIEW -->|approve| REVERT_MERGE["bot 合并 revert PR"]

    REF_REVERT --> HUB_REF["hub 仓 revert 引用 JSON<br/>(管理方管辖)"]
    REF_REVERT --> CODE_NOTIFY["通知代码仓 owner<br/>开代码仓 revert PR"]
    CODE_NOTIFY --> CODE_PR["代码仓 revert PR<br/>(业务方管辖)"]
    CODE_PR --> CODE_TRACK["code_revert_tracking 关联<br/>hub_revert_pr ↔ code_repo_revert_pr"]
    CODE_TRACK --> CODE_MERGE{"代码仓 PR merged?"}
    CODE_MERGE -->|否| WAIT_CODE["等待代码仓 revert"]
    CODE_MERGE -->|是| HUB_REF

    HUB_REF --> NEW_SUBMIT["上游重新提交新版本<br/>新 external_commit"]
    NEW_SUBMIT --> CONFLICT_CHECK{"路径冲突检测"}
    CONFLICT_CHECK -->|与其他 PR 冲突| REBASE["标记 needs_rebase<br/>上游合并后 rebase"]
    CONFLICT_CHECK -->|无冲突| NEW_REVIEW["新版本 PR 审核"]

    REVERT_MERGE --> NEW_SUBMIT
    NEW_REVIEW --> NEW_MERGE["approve → 合并新版本"]
    NEW_MERGE --> CASCADE["级联失效:n5 下游重新 ready"]
    CASCADE --> DOWN_READY["下游重新消费<br/>consume_ack(accept)"]

    EMERG_ACK -.hub 仓恢复.-> SYNC["sync_pending_artifacts<br/>补提 ack + revert PR"]

    style ACK fill:#a371f7,color:#fff
    style CHG fill:#b3261e,color:#fff
    style REF_REVERT fill:#e3b341,color:#fff
    style CODE_TRACK fill:#a371f7,color:#fff
    style NEW_MERGE fill:#3fb950,color:#fff
    style DOWN_READY fill:#3fb950,color:#fff
    style EMERG_ACK fill:#b3261e,color:#fff
```

---

### 3.5 第三轮缺陷汇总表

#### 3.5.1 缺陷全量清单

| 场景 | 缺陷 ID | 缺陷描述 | PRD 位置 | 严重度 | 修正方案 |
|---|---|---|---|---|---|
| 场景 3 | D3-R3.1 | hub 仓 main 分支合并串行化无显式锁,hotfix PR 合并排队 | 附录 D7 / fr1-fr6 §4.3 / fr2 §3.2 | 高 | HUB_MERGE_LOCK + 优先级队列 |
| 场景 3 | D3-R3.2 | hub 仓 CI 不支持按 PR 标记跳过 job,hotfix skip_gates 无法落地 | fr1-fr6 §8.1 / 第一部分修正 4 | 高 | PR label 驱动 CI 跳过 |
| 场景 3 | D3-R3.3 | hub 仓单点故障下 hotfix 完全卡死,无降级路径 | 附录 D7 / fr7-fr8 §9.1 | 高 | emergency_local_commit 模式 |
| 场景 3 | D3-R3.4 | 引用型 hotfix 产物代码质量无保障,git ls-remote 只校验存在性 | 附录 D7 / §5.1 | 中 | code_review_attribution 字段 |
| 场景 3 | D3-R3.5 | manifest schema 无 priority 字段,hotfix 无法从自由格式产物识别 | §3.3 / 需求 9 | 中 | manifest 新增 priority 字段 |
| 场景 7 | D7-R3.1 | hub 仓 CODEOWNERS 与管理方 reviewer_status 不同步 | 附录 D7 / 第一部分修正 2 | 高 | reviewer_routing 表双向同步 |
| 场景 7 | D7-R3.2 | GitProvider 未定义 update_pr_reviewers 等接口 | 附录 D7 / §6 | 高 | GitProvider 接口扩展 5 项 |
| 场景 7 | D7-R3.3 | 代理人审 PR 时 hub 仓 native 审计显示 bot,审计链断裂 | fr1-fr6 §6.5 / 附录 D7 | 中 | actual_reviewer_id + PR 评论注明 |
| 场景 7 | D7-R3.4 | 产物格式自由下代理人无法判断元数据合理性 | 需求 9 / §1.4 | 中 | validate_artifact_metadata 工具 |
| 场景 7 | D7-R3.5 | hub 仓单点 + reviewer 缺席双重叠加,代理人无法审 PR | 附录 D7 / fr7-fr8 §9.1 | 高 | emergency_approve_pr 本地审 |
| 场景 11 | D11-R3.1 | 人员降级提交借 MCP 间接用 bot token,越权风险 | 附录 D7 / fr7-fr8 §10.1 | 高 | human_submit_token 权限隔离 |
| 场景 11 | D11-R3.2 | 引用型产物 external_commit 归属校验缺失 | 附录 D7 / fr1-fr6 §4.1.4 | 高 | verify_external_ref_ownership op |
| 场景 11 | D11-R3.3 | 降级模式下 hub 仓 CI 严格校验阻塞人员提交 | fr1-fr6 §8.1 / 第一部分修正 3 | 高 | degraded-mode label CI 宽松 |
| 场景 11 | D11-R3.4 | GitProvider 未定义轻量提交接口,Dashboard 需适配 provider 差异 | 附录 D7 / 第一部分修正 3 | 中 | create_pr_lite 接口 |
| 场景 11 | D11-R3.5 | LLM + hub 仓双重故障无降级,完全卡死 | 附录 D7 / 第一部分修正 3 | 高 | 本地暂存模式 + sync |
| 场景 13 | D13-R3.1 | hub 仓 revert PR 需走完整审核,逆向打回周期长 | 附录 D7 / fr1-fr6 §6.1 | 高 | revert PR 快速通道 p1 |
| 场景 13 | D13-R3.2 | 引用型产物代码层 revert 管控缺失 | 附录 D7 / §5.1 | 高 | 双层 revert + code_revert_tracking |
| 场景 13 | D13-R3.3 | 产物格式自由下 consume_ack reason 难以结构化,无法仲裁归属 | 需求 9 / §1.4 | 中 | reason 模板 + delegate_to_expert 仲裁 |
| 场景 13 | D13-R3.4 | 逆向打回触发上游 changed,新版本路径冲突 | 附录 D7 / fr1-fr6 §5.3.1 | 中 | check_reverse_invalidate_conflicts |
| 场景 13 | D13-R3.5 | hub 仓单点下 consume_ack 无法提交,产物卡在 done_pending_ack | 附录 D7 / 第一部分修正 5 | 高 | emergency_consume_ack 本地记录 |

#### 3.5.2 缺陷按严重度统计

| 严重度 | 数量 | 典型缺陷 |
|---|---|---|
| 高 | 13 | D3-R3.1/2/3、D7-R3.1/2/5、D11-R3.1/2/3/5、D13-R3.1/2/5 |
| 中 | 7 | D3-R3.4/5、D7-R3.3/4、D11-R3.4、D13-R3.3/4 |
| **合计** | **20** | — |

#### 3.5.3 修正方案按实施阶段分布

| 阶段 | 修正项 | 优先级 |
|---|---|---|
| Phase 1 MVP | D3-R3.5 manifest priority + D11-R3.2 external_commit 归属校验 + D11-R3.3 CI 宽松模式 + D13-R3.3 reason 模板 | P0 |
| Phase 2 生产化 | D3-R3.1 HUB_MERGE_LOCK + D3-R3.2 CI label 跳过 + D7-R3.1 reviewer_routing 同步 + D7-R3.2 GitProvider 接口 + D11-R3.1 human_submit_token + D13-R3.1 revert 快速通道 + D13-R3.2 双层 revert | P1 |
| Phase 3 规模化 | D3-R3.3 emergency_local_commit + D3-R3.4 code_review_attribution + D7-R3.3 审计链修复 + D7-R3.4 validate_artifact_metadata + D7-R3.5 emergency_approve_pr + D11-R3.4 create_pr_lite + D11-R3.5 双重故障降级 + D13-R3.4 路径冲突防护 + D13-R3.5 emergency_consume_ack | P2 |

#### 3.5.4 对 PRD 主文档的修正建议(第三轮)

| PRD 位置 | 现状 | 修正 |
|---|---|---|
| 附录 D7 单一 hub 仓 | 未定义 main 分支合并锁 | 补充 HUB_MERGE_LOCK 串行化机制 |
| 附录 D7 GitProvider | 抽象层未列接口清单 | 补充 update_pr_reviewers / get_codeowners / update_codeowners / add_pr_comment / submit_pr_review / create_pr_lite / verify_commit_belongs 共 7 项接口 |
| §3.3 manifest schema | 无 priority 字段 | 新增 priority 字段(管理元数据,符合需求 9) |
| §3.3 引用型产物子 schema | 无 code_review_attribution | 新增 code_review_attribution 字段(引用型产物必填) |
| fr1-fr6 §4.1.4 op 清单 | 无 verify_external_ref_ownership | 新增 op,校验 external_commit 归属 |
| fr1-fr6 §8.1 CI 检查项 | 全量严格校验 | 补充 degraded-mode label 宽松模式 |
| fr2 §3.2 锁矩阵 | 无 HUB_MERGE_LOCK | 新增 main 分支合并锁 |
| fr7-fr8 §9.1 灾备 | mirror 只读 | 补充 emergency_local_commit / emergency_approve_pr / emergency_consume_ack 降级模式 |
| §6 MCP 工具 | 14 个(第一部分扩展后 17 个) | 新增 emergency_submit_artifact / emergency_approve_pr / emergency_consume_ack / sync_pending_artifacts / validate_artifact_metadata(共 22 个) |
| fr1-fr6 §6.1 SLA | 4 级 + SLA-Critical(第一部分) | 补充 revert PR 快速通道 SLA-Human-2 p1 |
| 第一部分 consume_ack | reason 自由文本 | 补充 reason 模板(按产物类型,建议非强制) |

#### 3.5.5 第三轮关键认知

1. **单一 hub 仓放大单点故障影响**:原多仓设计下,单仓故障影响局部;单一 hub 仓下,故障影响全局。所有异常流程(hotfix/审批/fallback/逆向打回)都需补充 hub 仓降级模式(emergency_* 系列)。
2. **GitProvider 抽象需完整接口清单**:附录 D7 仅提及 GitProvider 抽象,未列接口。第三轮发现 reviewer 转交、轻量提交、commit 归属校验等场景需 GitProvider 提供 7 项新接口,否则无法跨 provider 落地。
3. **需求 9"产物自由"≠"管理元数据自由"**:priority、code_review_attribution 等是管理元数据(manifest 字段),不限制产物内容格式,符合需求 9。manifest schema 可扩展管理元数据字段,不违反"产物自由"。
4. **引用型产物的代码层管控盲区**:hub 仓管引用 JSON,代码仓管代码 commit,两层分离。逆向打回/hotfix 等场景需双层协作(hub 仓 revert + 代码仓 revert),管理方需追踪代码仓 PR(code_revert_tracking),不能只管 hub 仓。
5. **CI 是"硬约束",降级模式需显式宽松**:hub 仓 CI 对所有 PR 一视同仁,降级模式(hotfix/LLM 故障)需通过 PR label 显式触发宽松模式,否则 CI fail 阻塞异常流程。

---

**第三轮重新走查共发现 20 项新设计缺陷(13 高 / 7 中),提出 20 项修正方案,涵盖单一 hub 仓合并锁、CI 跳过机制、hub 仓单点降级、GitProvider 接口扩展、引用型产物归属校验/双层 revert、manifest 管理元数据扩展六大主题。所有缺陷均源于"单一 hub 仓 + 需求 9"新设计,修正方案均给出可落地的字段/工具/接口/状态扩展。建议按 Phase 1/2/3 分阶段实施,P0 项(manifest priority、external_commit 归属校验、CI 宽松模式、reason 模板)优先落地。**
