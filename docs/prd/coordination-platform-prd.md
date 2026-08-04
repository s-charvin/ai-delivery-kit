# 产品需求文档 PRD:AI 多角色开发协同平台(Coordination Platform)

> **文档性质**:基于《AI 多 Agent 开发协同平台调研报告》第十六~二十七章(v2 自建设计)产出的可开发 PRD
> **版本**:v2.0 | **日期**:2026-08-04 | **状态**:待评审
> **设计文档**:[ai-multi-agent-dev-dashboard-research.md](file:///Users/zuiyou/develop/skills/.trae/documents/ai-multi-agent-dev-dashboard-research.md)

---

## 目录

- [1. 产品概述(总)](#1-产品概述总)
- [2. 核心概念与术语](#2-核心概念与术语)
- [3. 角色与权限模型](#3-角色与权限模型)
- [4. 功能需求详述(分)](#4-功能需求详述分)
  - [FR1 产物仓库管理](#fr1-产物仓库管理)
  - [FR2 管理编排引擎(LangGraph)](#fr2-管理编排引擎langgraph)
  - [FR3 角色协调(CrewAI)](#fr3-角色协调crewai)
  - [FR4 MCP 接口层](#fr4-mcp-接口层)
  - [FR5 约束技能(Constraint Skills)](#fr5-约束技能constraint-skills)
  - [FR6 产物审核机制](#fr6-产物审核机制)
  - [FR7 监控与可观测性](#fr7-监控与可观测性)
  - [FR8 可视化编排与 Dashboard](#fr8-可视化编排与-dashboard)
- [5. 数据模型](#5-数据模型)
- [6. 接口规范(MCP 工具)](#6-接口规范mcp-工具)
- [7. 非功能需求](#7-非功能需求)
- [8. 验收标准](#8-验收标准)
- [9. 实施阶段](#9-实施阶段)

---

## 1. 产品概述(总)

### 1.1 背景与问题

AI 驱动的软件开发中,产品、服务端、客户端、UI 设计多方并行工作,存在以下痛点:

| 痛点 | 描述 |
|---|---|
| 产物散落 | 各方产物(需求 spec、接口契约、设计稿、代码引用)分散在不同工具中,无统一管理 |
| 依赖不可见 | 客户端依赖服务端契约和设计稿,但依赖关系无显式声明和自动推进 |
| 信息不同步 | 一方变更(如接口契约修改),下游无法自动感知,导致联调冲突 |
| 无统一监控 | 多 agent 开发状态分散,无统一 dashboard 观察进度和阻塞 |
| 产物质量不可控 | 无审核机制,部分方产物有问题会级联影响下游 |

### 1.2 产品定位

**Coordination Platform 是一个"管理与编排层"平台**,不干预开发执行,只做:

1. **产物管理**:通过独立 git 仓库管理所有产物内容,管理方只持有引用
2. **状态编排**:用 LangGraph StateGraph 管理节点状态机 + 依赖 DAG,自动推进/阻塞/级联
3. **角色协调**:用 CrewAI 定义 4 角色,按 ready 节点动态分配任务
4. **审核准入门**:所有产物提交经 PR 审核(skill 约束校验 + 依赖检查)才能合并生效
5. **监控可观测**:用 Langfuse 旁路监听全链路,提供 trace + dashboard

### 1.3 核心价值

- **通用性**:覆盖服务端/客户端/UI 设计全流程,产物格式中立(不限开发方案)
- **自动化**:依赖推进、变更级联、状态流转全自动
- **质量可控**:PR 审核闭环,审核后才生效
- **可观测**:全链路 trace + 实时可视化依赖图

### 1.4 范围边界

| 做什么(范围内) | 不做什么(范围外) |
|---|---|
| 产物仓库的分支保护 + PR 审核 | 不限制开发方用什么工具产出内容 |
| 状态机 + 依赖 DAG 编排 | 不执行代码开发(无执行层) |
| MCP 工具接口(submit/review/approve) | 不生成代码、不生成设计稿 |
| Constraint Skills 元数据约束 | 不校验产物内容格式(YAML/JSON/Figma 均可) |
| Langfuse 监控 + 可视化 Dashboard | 不做多租户/RBAC(v3 规划) |
| 变更级联(下游自动 blocked) | 不做成本/配额/密钥管理(v3 规划) |

---

## 2. 核心概念与术语

| 术语 | 定义 |
|---|---|
| **管线(Pipeline)** | 一个功能需求的全链路 DAG,由节点和依赖边组成 |
| **节点(Node)** | 管线中的一个任务单元,分产物节点和控制节点 |
| **产物节点** | 产出交付物的节点(product_spec/api_contract/design_asset/client_ui 等) |
| **控制节点** | 编排控制节点(gate 门禁 / approval 审批 / fork 并行汇合 / switch 条件) |
| **产物(Artifact)** | 产物节点产出的交付物,内容存产物仓库,管理方只存引用 |
| **产物引用(ArtifactRef)** | 指向产物仓库的 `repo + path + commit`,不含内容 |
| **Constraint Skill** | 约束技能,定义某节点类型的元数据约束 + 产出引导(superpowers 风格) |
| **状态机** | 节点状态流转:blocked → ready → pending_review → done / changed |
| **审核** | 管理方对产物 PR 的准入审核(skill 校验 + 依赖检查 → 批准/驳回) |
| **级联(Cascade)** | 节点 done 后自动解锁下游;changed 后自动失效下游 |
| **MCP** | Model Context Protocol,管理方暴露给 agent 的标准工具接口 |

### 2.1 节点类型完整清单

**产物节点(9 种):**

| 节点类型 | 角色 | 说明 |
|---|---|---|
| `product_spec` | product | 产品需求文档 |
| `api_contract` | server | 接口契约(端点/schema/错误码) |
| `server_impl` | server | 服务端实现引用(指向代码仓库 commit) |
| `server_test` | server | 服务端测试结果引用 |
| `design_proto` | design | 设计原型 |
| `design_asset` | design | 设计标注/切图(含 figma 链接) |
| `client_ui` | client | 客户端 UI 实现 |
| `client_func` | client | 客户端功能联调 |
| `client_delivery` | client | 客户端交付物 |

**控制节点(5 种):**

| 节点类型 | 说明 |
|---|---|
| `gate` | 质量门禁:lint/test/coverage/安全扫描通过才放行 |
| `approval` | 审批门:需人工或 agent 审批通过 |
| `fork` | 并行汇合:多入边依赖全 done 后透传 |
| `switch` | 条件路由:按产物字段路由(如风险高走 review-agent) |
| `notify` | 通知节点:触发外部通知(飞书/Slack/GitHub) |

---

## 3. 角色与权限模型

### 3.1 角色定义

| 角色 | 职责 | 可产出的节点类型 | 可用 MCP 工具 |
|---|---|---|---|
| **product** | 产品需求 | product_spec | submit_artifact, update_progress, get_dependencies |
| **server** | 服务端开发 | api_contract, server_impl, server_test | submit_artifact, update_progress, get_dependencies, request_approval |
| **design** | UI 设计 | design_proto, design_asset | submit_artifact, update_progress, get_dependencies |
| **client** | 客户端开发 | client_ui, client_func, client_delivery | submit_artifact, update_progress, get_dependencies, request_approval |
| **reviewer** | 审批人 | — | approve_pr, reject_pr, get_audit_log |
| **admin** | 管理员 | — | set_gate_policy, get_audit_log, 全部工具 |

### 3.2 权限矩阵

| 操作 | product | server | design | client | reviewer | admin |
|---|---|---|---|---|---|---|
| 提交产物(submit_artifact) | ✅(仅 product_spec) | ✅(server 类) | ✅(design 类) | ✅(client 类) | ❌ | ✅ |
| 更新进度(update_progress) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| 查询依赖(get_dependencies) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 请求审批(request_approval) | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| 审核PR(approve_pr/reject_pr) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 设置门禁(set_gate_policy) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查询审计(get_audit_log) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 4. 功能需求详述(分)

### FR1 产物仓库管理

**目标**:独立 git 仓库管理所有产物内容,受分支保护,只接受审核合并的 PR。

#### FR1.1 仓库结构

```
artifact-repo/                        # 独立 git 仓库
├─ product_spec/                      # 按产物类型分目录
│  └─ 001.yaml                        # 产物文件(格式不限:yaml/json/md/figma.json)
├─ api_contract/
│  └─ 001.yaml
├─ design_proto/
│  └─ 001.json
├─ design_asset/
│  └─ 001_figma.json                  # 含 figma 链接
├─ server_impl/
│  └─ 001_ref.json                    # 引用代码仓库 commit
├─ client_ui/
│  └─ 001_ref.json
├─ client_func/
│  └─ 001_ref.json
├─ client_delivery/
│  └─ 001_ref.json
└─ .github/
   └─ pull_request_template.md        # PR 模板(强制声明 node_id/deps)
```

**规则:**
- 每种产物类型一个目录,目录名与节点 type 一致
- 产物文件名自由(建议序号前缀:001_xxx)
- 文件格式不限(YAML/JSON/Markdown/Figma 链接 JSON 均可)
- 管理方不解析内容,只校验文件存在性 + 扩展名/大小

#### FR1.2 分支保护规则

| 规则 | 配置 |
|---|---|
| main 分支 | 禁止直接 push,只接受 PR 合并 |
| PR 审核 | 至少 1 个管理方 bot approve |
| CI 校验 | manifest schema + skill 约束(详见 FR6) |
| 合并方式 | squash merge(每产物一个 commit,便于追溯) |
| feat 分支 | 命名规范 `feat/{role}/{node_type}-{seq}` |

#### FR1.3 PR 模板

```yaml
# .github/pull_request_template.md
## 关联节点
node_id: n2                        # 必填,对应管线节点
node_type: api_contract
role: server

## 产物引用
artifact:
  path: api_contract/001.yaml
  toolspec_framework: spec-kit     # 必填,生成工具(不限取值)

## 依赖声明
deps:
  - node_id: n1
    artifact_path: product_spec/001.yaml

## 产物说明(自由填写)
说明: 用户登录接口契约 v1
```

#### FR1.4 验收标准

- AC1.1: main 分支直接 push 被拒绝
- AC1.2: feat 分支提交后可开 PR
- AC1.3: PR 模板字段缺失时 CI 报错
- AC1.4: squash merge 后 main 上每产物一个 commit

---

### FR2 管理编排引擎(LangGraph)

**目标**:用 LangGraph StateGraph 实现节点状态机 + 依赖 DAG + 条件推进 + 变更级联。

#### FR2.1 状态机定义(7 态)

| 状态 | 含义 | 进入条件 | 退出条件 |
|---|---|---|---|
| `blocked` | 依赖未满足 | 初始态 / 上游变更失效 | 上游全 done |
| `ready` | 依赖满足,待产出 | cascade 解锁 / PR 驳回 | submit_artifact 提 PR |
| `pending_review` | PR 已提交,待审核 | submit_artifact | approve_pr 合并 / reject_pr 驳回 |
| `in_progress` | 开发中(进度更新) / 门禁失败打回 | update_progress / gate 失败 | 重新 submit |
| `review` | 审批门等待审批 | approval 节点依赖满足 | approve / reject |
| `done` | 产物已合并生效 | approve_pr 合并 / approval 通过 | 重新提 PR 变更 |
| `changed` | 已 done 产物被重新提交(变更) | 重提已 done 节点的 PR | 重新提交 commit |

**状态流转图:**
```
blocked →(依赖满足)→ ready →(提PR)→ pending_review →(审核合并)→ done
                       ↑                                    ↓
                       ←─────(驳回)───── pending_review    (重提PR)
                                                            ↓
                                                         changed →(提PR)→ pending_review
                                                            ↓
                                                      (级联)→ 下游 blocked
```

#### FR2.2 依赖 DAG 规则

| 规则 | 描述 |
|---|---|
| 依赖声明 | 节点 `deps` 数组声明上游依赖(边由 deps 推导,无需手写) |
| 单入边 | 节点依赖 1 个上游:上游 done → 本节点 ready |
| 多入边 | 节点依赖 N 个上游:全部 done → 本节点 ready(fork 节点同理) |
| 级联解锁 | 节点 done → 检查所有下游,依赖全满足的下游置 ready |
| 级联失效 | 节点 changed → 所有下游产物引用清除 + 置 blocked(递归) |
| 无环校验 | 管线加载时校验 DAG 无环(CI 校验) |

#### FR2.3 PipelineState 数据结构

```python
class PipelineState(TypedDict):
    node_states: dict[str, NodeStatus]              # node_id -> 状态
    artifact_refs: dict[str, ArtifactRef]           # node_id -> 产物引用
    events: Annotated[Sequence[dict], operator.add] # 事件流(累积追加)
    pending_approvals: dict[str, str]               # node_id -> approver
    role_assignments: dict[str, str]                # node_id -> agent_id
    pending_prs: dict[str, str]                     # node_id -> pr_id(pending_review 时)
```

#### FR2.4 StateGraph 节点

| 节点 | 作用 | 触发条件 |
|---|---|---|
| `bootstrap_node` | 初始化:无依赖根节点置 ready | 管线启动 |
| `dispatch_router` | 条件路由:按节点状态分发 | 每次状态变更后 |
| `crewai_assign` | 调 CrewAI 分配 ready 节点给角色 agent | 节点 ready |
| `cascade_node` | done 节点解锁下游 | 节点 done |
| `invalidate_node` | changed 节点失效下游(清引用 + blocked) | 节点 changed |
| `approval_node` | 审批门等待 | approval 节点依赖满足 |
| `wait_node` | 等待(无待处理节点) | 无 ready/review/done/changed |

#### FR2.5 控制节点行为

| 控制节点 | 行为 |
|---|---|
| `gate` | 上游 done → 评估 policy(lint/test/coverage/security);全过→done;失败→上游打回 in_progress |
| `approval` | 上游 done → review;approve→done 推进下游;reject→上游最近产物节点 changed |
| `fork` | 多入边全 done → done(透传);否则 blocked |
| `switch` | 按上游产物字段路由(如 risk_score>7 → 走 review-agent 分支) |
| `notify` | 上游 done → 触发外部通知(飞书/Slack)→ done |

#### FR2.6 验收标准

- AC2.1: 根节点(无依赖)启动时自动 ready
- AC2.2: 节点 done 后,下游依赖全满足时自动 ready
- AC2.3: 多入边节点,部分依赖 done 时仍 blocked
- AC2.4: changed 节点的下游递归 blocked + 产物引用清除
- AC2.5: gate 失败时上游产物打回 in_progress
- AC2.6: approval 驳回时上游最近产物节点 changed
- AC2.7: 管线全节点 done 时自动终止

---

### FR3 角色协调(CrewAI)

**目标**:用 CrewAI 定义 4 角色,监听 LangGraph ready 事件动态分配 Task。

#### FR3.1 角色 Agent 定义

| Agent | role | goal | backstory | tools |
|---|---|---|---|---|
| product_agent | 产品经理 | 产出 product_spec 并通过 MCP 提交 | 理解业务需求,用任意工具产出需求文档 | mcp_submit_artifact, mcp_update_progress, mcp_get_deps |
| server_agent | 服务端开发 | 产出 api_contract/server_impl/server_test 并提交 | 接口协议优先,用任意工具产出契约 | mcp_submit_artifact, mcp_update_progress, mcp_get_deps, mcp_request_approval |
| design_agent | UI 设计师 | 产出 design_proto/design_asset(含 figma 链接) | 用户体验驱动,用 Figma 或任意工具 | mcp_submit_artifact, mcp_update_progress, mcp_get_deps |
| client_agent | 客户端开发 | 产出 client_ui/client_func/client_delivery | 还原设计+联调服务,用任意 IDE | mcp_submit_artifact, mcp_update_progress, mcp_get_deps, mcp_request_approval |

**关键约束:Agent 不执行开发,只协调提交。** 真正开发由人员自由完成,Agent 是"提交协调员",调用 MCP 工具把人员产出的产物引用提交到管理方。

#### FR3.2 Task 动态生成

```python
def build_crew_for_ready_nodes(ready_nodes: list, state: PipelineState) -> Crew:
    """按 LangGraph ready 节点动态创建 CrewAI Task"""
    tasks = []
    for node_id in ready_nodes:
        node = get_node(node_id)
        agent = role_to_agent.get(node["role"])
        tasks.append(Task(
            description=f"为节点 {node_id}({node['type']})产出产物,通过 MCP 提交",
            agent=agent,
            expected_output="产物已提交 PR,等待审核",
            context={"node_id": node_id, "deps": get_deps_info(node_id, state)},
        ))
    return Crew(agents=[...], tasks=tasks, process=Process.sequential)
```

#### FR3.3 CrewAI ↔ LangGraph 协作

| 事件 | 触发 | 动作 |
|---|---|---|
| 节点 ready | LangGraph cascade | CrewAI build_crew → 分配 Task 给对应角色 agent |
| agent 调 submit_artifact | CrewAI Task 执行 | MCP 提 PR → 节点 pending_review |
| PR 合并 | MCP approve_pr | LangGraph set_done → cascade 下游 |
| 下游 ready | LangGraph cascade | CrewAI 再次 build_crew(循环) |

#### FR3.4 验收标准

- AC3.1: 节点 ready 时,CrewAI 自动分配 Task 给正确角色 agent
- AC3.2: 多个节点同时 ready 时,对应角色 agent 并行执行
- AC3.3: agent 调 submit_artifact 后,节点进入 pending_review

---

### FR4 MCP 接口层

**目标**:MCP 是执行层与管理层之间的唯一桥梁,暴露标准工具给 agent/人员调用。

#### FR4.1 基础工具清单(7 个)

| 工具名 | 调用方 | 作用 | 关键参数 | 返回 |
|---|---|---|---|---|
| `submit_artifact` | 各角色 agent | 提交产物(推 feat 分支 + 开 PR) | node_id, repo, branch, path, toolspec_framework, deps_decl | pr_id, status=pending_review |
| `update_progress` | 各角色 agent | 更新节点进度(不提产物) | node_id, status, note | ok |
| `get_dependencies` | 各角色 agent | 查上游产物内容(git show 拉取) | node_id | [{node_id, content}] |
| `get_pipeline_state` | 监控/可视化 | 查全局管线状态 | — | {node_states, artifact_refs} |
| `request_approval` | server/client agent | 请求审批 → 节点进 review | node_id, approver | ok |
| `approve` / `reject` | reviewer/admin | 审批操作 | node_id | ok, state |
| `set_gate_policy` | admin | 设置门禁策略 | node_id, policy | ok |

#### FR4.2 审核工具清单(6 个,详见 FR6)

| 工具名 | 调用方 | 作用 |
|---|---|---|
| `list_pending_prs` | 管理方/监控 | 列出待审核 PR |
| `get_pr_detail` | 管理方 | 获取 PR 详情(产物+manifest+diff) |
| `review_artifact_pr` | 管理方 agent | 自动审核:skill 校验 + 依赖检查 → 返回结论 |
| `approve_pr` | reviewer/admin | 批准 PR → 合并 → 触发状态推进 |
| `reject_pr` | reviewer/admin | 驳回 PR → 通知提交方 |
| `get_audit_log` | reviewer/admin | 查审核记录 |

#### FR4.3 Langfuse 旁路监听

所有 MCP 工具调用经 `@langfuse_trace` 装饰器,记录 span + 属性(node_id 等)。**旁路原则:Langfuse 失败时降级,不阻塞主流程。**

#### FR4.4 验收标准

- AC4.1: MCP 工具可被 agent 原生调用(MCP 协议标准)
- AC4.2: submit_artifact 后节点进入 pending_review(非直接 done)
- AC4.3: get_dependencies 返回上游产物内容(git show 拉取)
- AC4.4: Langfuse 挂掉时 MCP 工具仍正常工作(降级)

---

### FR5 约束技能(Constraint Skills)

**目标**:superpowers 风格的约束 skill,定义"交什么"(元数据约束)+ 引导"建议交什么"(guide),不限制"怎么交"。

#### FR5.1 Skill 目录结构

```
skills/
├─ product-spec-skill/
│  ├─ skill.yaml          # 元数据约束 + 触发条件 + MCP 工具绑定
│  └─ guide.md            # 产出引导(建议,非强制)
├─ api-contract-skill/
│  ├─ skill.yaml
│  └─ guide.md
├─ design-handoff-skill/       # design_proto + design_asset
├─ server-impl-skill/          # server_impl + server_test
├─ client-ui-skill/            # client_ui
└─ client-delivery-skill/      # client_func + client_delivery
```

#### FR5.2 skill.yaml 结构

```yaml
name: <skill-name>
description: <描述>
trigger:
  node_type: <产物节点类型>
  role: <角色>
artifact_constraints:
  required_fields:              # 元数据必填字段(管理方校验)
    - title
    - version                   # semver
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework        # 不限取值(中立)
  deps:                         # 必须依赖的节点类型
    - <dep_node_type>
  min_version:                  # 依赖最低版本
    <dep_node_type>: "1.0.0"
  file_constraints:             # 文件格式约束(不解析内容)
    allowed_extensions: [.yaml, .json, .md]
    max_size_kb: 512
  requires_human_review: false  # 是否需人工审核
guide_ref: guide.md
guide_summary: |
  <产出建议,非强制>
allowed_mcp_tools:              # 此 skill 激活时可调用的 MCP 工具
  - submit_artifact
  - update_progress
  - get_dependencies
```

#### FR5.3 Skill 匹配与加载

| 步骤 | 描述 |
|---|---|
| 1. 发现 | 节点 ready 时,按 `node_type` 匹配 skill |
| 2. 加载约束 | 读取 skill.yaml 的 artifact_constraints |
| 3. 加载引导 | 读取 guide.md(供 agent 参考,非强制) |
| 4. 绑定工具 | 按 allowed_mcp_tools 限制 agent 可用工具 |
| 5. 审核校验 | PR 审核时按 artifact_constraints 校验元数据 + 文件格式 |

#### FR5.4 6 个 Skill 的约束摘要

| Skill | node_type | deps 必须包含 | requires_human_review | 引导要点 |
|---|---|---|---|---|
| product-spec-skill | product_spec | 无 | false | 建议含需求背景、验收标准 |
| api-contract-skill | api_contract | product_spec | true(首次) | 建议含端点、schema、错误码 |
| design-handoff-skill | design_proto/design_asset | product_spec | true(design_asset) | 建议含 figma 链接、标注 |
| server-impl-skill | server_impl/server_test | api_contract | false | 建议含代码仓库 commit 引用 |
| client-ui-skill | client_ui | api_contract + design_asset | false | 建议含 UI 实现引用 |
| client-delivery-skill | client_func/client_delivery | client_ui + server_impl | true | 建议含联调结果、交付清单 |

#### FR5.5 验收标准

- AC5.1: 节点 ready 时自动匹配正确 skill
- AC5.2: PR 审核时按 skill.required_fields 校验,缺失字段被拒
- AC5.3: 依赖未 done 的 PR 被拒(skill.deps 校验)
- AC5.4: 文件扩展名不在 allowed_extensions 的 PR 被拒
- AC5.5: requires_human_review=true 的 PR 转人工审核
- AC5.6: guide.md 内容对 agent 可见但非强制

---

### FR6 产物审核机制

**目标**:所有产物 PR 经管理方审核(skill 校验 + 依赖检查)才能合并,合并后才触发状态推进。

#### FR6.1 审核流程

```
PR 提交 → webhook 通知管理方 → 解析 PR 模板(node_id/path/deps)
  → 匹配 Constraint Skill → 校验元数据 + 依赖完整性 + 文件格式
  → 决策:
    全过 + requires_human_review=false → 自动 approve → bot 合并
    全过 + requires_human_review=true  → 转人工 → 等待 approve → 合并
    任一失败 → reject → 通知提交方修改
  → 合并 → 记录审计日志 + Langfuse trace → 触发 LangGraph set_done + cascade
```

#### FR6.2 自动审核逻辑(review_artifact_pr)

| 校验项 | 逻辑 | 失败结果 |
|---|---|---|
| 元数据校验 | skill.required_fields 全部存在 | reject |
| 依赖完整性 | PR 声明的 deps 节点全 done | reject |
| 文件格式 | 扩展名在 allowed_extensions 内 + 大小 ≤ max_size | reject |
| 文件存在 | git ls-file 校验产物文件存在于 feat 分支 | reject |
| 人工审核 | skill.requires_human_review=true | needs_human(转人工) |

#### FR6.3 合并逻辑(approve_pr)

| 步骤 | 动作 |
|---|---|
| 1 | 管理方 bot approve PR |
| 2 | squash merge 到 main |
| 3 | 获取 merge commit hash |
| 4 | 构造 ArtifactRef(repo + path + commit + toolspec_framework + trace_id) |
| 5 | 记录审计日志 |
| 6 | Langfuse trace: approve_pr + merge_commit |
| 7 | langgraph_invoke(set_done + artifact_ref) |
| 8 | cascade 解锁下游 |

#### FR6.4 审核策略矩阵(按产物类型分级)

| 产物类型 | 自动校验 | 人工审核 | 理由 |
|---|---|---|---|
| product_spec | ✅ | ❌ | 需求文档,影响面可控 |
| api_contract | ✅ | ✅(首次) | 契约影响下游多端,首次人工把关 |
| server_impl 引用 | ✅ | ❌ | 仅引用 commit,代码在代码仓库审 |
| design_proto | ✅ | ❌ | 设计原型,主观性强不强审 |
| design_asset | ✅ | ✅ | 标注/切图影响客户端实现 |
| client_ui | ✅ | ❌ | UI 实现,代码在代码仓库审 |
| client_delivery | ✅ | ✅ | 交付物,最终把关 |

#### FR6.5 审计日志

每条审核记录(批准/驳回/转人工)入审计日志:

```json
{
  "audit_id": "aud_20260804_001",
  "action": "approve",
  "pr_id": 42,
  "pr_url": "https://github.com/org/artifact-repo/pull/42",
  "node_id": "n2",
  "node_type": "api_contract",
  "artifact_path": "api_contract/001.yaml",
  "merge_commit": "a1b2c3d4",
  "reviewer": "mgmt-bot",
  "submitter": "server-agent-01",
  "skill_used": "api-contract-skill",
  "skill_verdict": "approve",
  "deps_at_review": {"n1": "done"},
  "note": "自动审核通过",
  "trace_id": "lf_xxx",
  "ts": "2026-08-04T10:30:00Z"
}
```

#### FR6.6 验收标准

- AC6.1: PR 提交后自动触发 webhook → 管理方审核
- AC6.2: 元数据缺失的 PR 被自动 reject
- AC6.3: 依赖未 done 的 PR 被自动 reject
- AC6.4: requires_human_review=true 的 PR 等待人工 approve
- AC6.5: approve_pr 合并后节点 done + 下游 cascade
- AC6.6: reject_pr 后节点回 ready + 通知提交方
- AC6.7: 审计日志可按 node_id / reviewer / 时间 / action 查询

---

### FR7 监控与可观测性

**目标**:Langfuse 旁路监听 MCP + LangGraph,提供 trace/dashboard/告警。

#### FR7.1 埋点设计

| 埋点源 | span 名称 | 关键属性 |
|---|---|---|
| MCP 工具调用 | `mcp.<tool_name>` | node_id, agent_id, tool_args |
| LangGraph 节点 | `langgraph.<node_name>` | node_id, from_state, to_state |
| PR 审核 | `mcp.review_artifact_pr` | pr_id, node_id, verdict |
| PR 合并 | `mcp.approve_pr` | pr_id, node_id, merge_commit |

#### FR7.2 旁路监听原则

- **不阻塞主流程**:Langfuse 调用失败时降级,工具正常执行
- **trace 贯穿**:一次管线执行的 MCP 调用 + LangGraph 节点用同一 trace_id 串联
- **trace_id 关联产物**:ArtifactRef.trace_id 记录,可从产物反查执行 trace

#### FR7.3 Dashboard 视图

| 视图 | 数据源 | 内容 |
|---|---|---|
| 依赖图叠加 | Langfuse + 管理方 state | 依赖图上每节点显示状态颜色 + 耗时 |
| Trace 列表 | Langfuse | 每次 MCP 调用 + LangGraph 节点 trace |
| 节点耗时 | trace span | 节点从 ready→done 耗时分布 |
| 异常告警 | trace error | gate 失败、审批超时、agent 离线 |
| 角色负载 | trace 按 agent 聚合 | 各角色 agent 任务数/耗时 |
| 审计日志 | 管理方 audit_log | 审核记录列表(可过滤) |

#### FR7.4 验收标准

- AC7.1: MCP 工具调用产生 Langfuse span
- AC7.2: LangGraph 节点执行产生 Langfuse span
- AC7.3: 产物 ArtifactRef.trace_id 可关联 Langfuse trace
- AC7.4: Langfuse 挂掉时平台正常工作(降级)
- AC7.5: Dashboard 可按 node_id 查看完整执行链路

---

### FR8 可视化编排与 Dashboard

**目标**:可视化依赖图 + 实时状态 + 节点详情 + 交互式审批。

#### FR8.1 可视化视图

| 视图 | 内容 |
|---|---|
| 依赖图(主视图) | DAG 节点 + 边,节点颜色随状态实时变化 |
| 节点详情面板 | 选中节点:node_id/type/role/状态/deps/framework/trace_id/manifest |
| 审批操作 | approval 节点 review 状态时,可点击 approve/reject |
| 审计日志视图 | 审核记录列表(按时间/reviewer/action 过滤) |
| PR 列表视图 | 待审核 PR 列表 + 状态 |

#### FR8.2 节点状态颜色

| 状态 | 颜色 | 视觉 |
|---|---|---|
| blocked | 红 | 边框红 + 角标阻塞依赖 |
| ready | 灰蓝 | 虚线边框 + "待启动" |
| pending_review | 黄 | 边框流动动画 + "审核中" |
| in_progress | 橙 | 进度环 |
| review | 紫 | 角标"待审" + 审批人 |
| done | 绿 | 实线 + ✓ |
| changed | 橙红 | 闪烁 + 变更标记 |

#### FR8.3 实时更新

- SSE/WebSocket 推送状态变更
- 节点颜色随 state 变化实时更新
- 点击节点 → 详情面板 → 跳产物引用 → 跳 Langfuse trace

#### FR8.4 技术选型

- react-flow(DAG 渲染)+ SSE(实时推送)
- 复用 v1 原型的 SVG 分层布局逻辑

#### FR8.5 验收标准

- AC8.1: 依赖图正确渲染 DAG(节点+边+分层布局)
- AC8.2: 节点状态变更时颜色实时更新(SSE 推送)
- AC8.3: 点击节点显示详情(manifest + trace_id)
- AC8.4: approval 节点 review 状态时可交互 approve/reject
- AC8.5: 审计日志视图可按条件过滤

---

## 5. 数据模型

### 5.1 核心数据结构

#### Pipeline(管线)

```yaml
pipeline:
  id: "login-feature"
  name: "登录功能全链路"
  nodes:
    - id: "n1"
      type: "product_spec"
      role: "product"
      deps: []
      toolspec: { framework: "openspec" }
    - id: "n2"
      type: "api_contract"
      role: "server"
      deps: ["n1"]
    - id: "n7"
      type: "fork"
      role: "control"
      deps: ["n2", "n6"]
    - id: "n9"
      type: "gate"
      role: "control"
      deps: ["n8"]
      policy: { lint: true, test: true, coverage_min: 80 }
    - id: "n10"
      type: "approval"
      role: "control"
      deps: ["n9"]
      approver: "reviewer_agent"
  edges: []  # 由 deps 推导
```

#### ArtifactRef(产物引用,管理方持有)

```python
class ArtifactRef(TypedDict):
    node_id: str
    repo: str                    # 产物仓库地址
    path: str                    # 产物在仓库内路径
    commit: str                  # git commit hash(合并后的)
    toolspec_framework: str      # 生成工具(中立,不限取值)
    trace_id: str                # Langfuse trace 关联
```

#### AuditLogEntry(审计日志)

```python
class AuditLogEntry(TypedDict):
    audit_id: str
    action: str                  # approve | reject | needs_human
    pr_id: int
    pr_url: str
    node_id: str
    node_type: str
    artifact_path: str
    merge_commit: str | None     # 仅 approve 有
    reviewer: str                # mgmt-bot | reviewer_id
    submitter: str
    skill_used: str
    skill_verdict: str
    deps_at_review: dict         # {node_id: status}
    note: str
    trace_id: str
    ts: str                      # ISO 8601
```

### 5.2 存储方案

| 数据 | 存储 | 说明 |
|---|---|---|
| PipelineState | LangGraph checkpointer(Postgres/SQLite) | 状态持久化 + 中断恢复 |
| artifact_refs | PipelineState 内 | 随 state 持久化 |
| audit_log | 独立表(Postgres)或独立 audit git 仓库 | 审计可追溯 |
| 产物内容 | 产物仓库(git) | 管理方不存内容,只存引用 |
| Constraint Skills | 文件系统(skills/ 目录) | YAML + Markdown |
| Langfuse trace | Langfuse 自托管(Postgres) | 独立存储 |

---

## 6. 接口规范(MCP 工具)

### 6.1 submit_artifact(提交产物 → 开 PR)

```json
{
  "name": "submit_artifact",
  "description": "提交产物:推 feat 分支 + 开 PR,等待管理方审核",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "string", "description": "管线节点 ID"},
      "repo": {"type": "string", "description": "产物 git 仓库地址"},
      "branch": {"type": "string", "description": "feat 分支名"},
      "path": {"type": "string", "description": "产物在仓库内路径"},
      "toolspec_framework": {"type": "string", "description": "生成工具(中立,不限)"},
      "deps_decl": {"type": "array", "items": {"type": "object"}, "description": "依赖声明"}
    },
    "required": ["node_id", "repo", "branch", "path", "toolspec_framework"]
  }
}
```
**返回**: `{"ok": true, "pr_id": 42, "status": "pending_review"}`

### 6.2 review_artifact_pr(自动审核)

```json
{
  "name": "review_artifact_pr",
  "description": "自动审核 PR:skill 约束 + 依赖检查,返回结论",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pr_id": {"type": "integer"}
    },
    "required": ["pr_id"]
  }
}
```
**返回**: `{"verdict": "approve|reject|needs_human", "reason": "..."}`

### 6.3 approve_pr(批准合并 → 状态推进)

```json
{
  "name": "approve_pr",
  "description": "批准 PR → bot 合并 → 触发 LangGraph 状态推进",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pr_id": {"type": "integer"},
      "note": {"type": "string"}
    },
    "required": ["pr_id"]
  }
}
```
**返回**: `{"ok": true, "merged": true, "node_id": "n2", "state": "done"}`

### 6.4 reject_pr(驳回)

```json
{
  "name": "reject_pr",
  "description": "驳回 PR → 节点回 ready → 通知提交方",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pr_id": {"type": "integer"},
      "reason": {"type": "string"}
    },
    "required": ["pr_id", "reason"]
  }
}
```
**返回**: `{"ok": true, "node_id": "n2", "state": "ready"}`

### 6.5 get_dependencies(查上游产物内容)

```json
{
  "name": "get_dependencies",
  "description": "查上游产物内容(git show 拉取),供 agent 参考",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "string"}
    },
    "required": ["node_id"]
  }
}
```
**返回**: `[{"node_id": "n1", "content": "..."}]`

### 6.6 其他工具

| 工具 | 参数 | 返回 |
|---|---|---|
| `update_progress` | node_id, status, note | {ok} |
| `get_pipeline_state` | — | {node_states, artifact_refs, pending_prs} |
| `request_approval` | node_id, approver | {ok} |
| `approve` / `reject` | node_id | {ok, state} |
| `set_gate_policy` | node_id, policy | {ok} |
| `list_pending_prs` | status=pending | [{pr_id, node_id, submitter}] |
| `get_pr_detail` | pr_id | {pr_id, template, files, diff} |
| `get_audit_log` | filter(node_id/reviewer/action/ts) | [AuditLogEntry] |

---

## 7. 非功能需求

| 编号 | 类别 | 需求 |
|---|---|---|
| NFR1 | 可靠性 | Langfuse 挂掉时平台正常工作(降级) |
| NFR2 | 可靠性 | 产物仓库不可达时 MCP 返回明确错误,不崩溃 |
| NFR3 | 持久化 | LangGraph checkpointer 持久化 state,重启可恢复 |
| NFR4 | 性能 | MCP 工具调用响应 < 2s(不含 git 操作) |
| NFR5 | 性能 | git show 拉取产物内容 < 5s |
| NFR6 | 并发 | 支持多 agent 并行提交不同节点产物 |
| NFR7 | 安全 | MCP 工具按角色权限限制(agent 只能提交本角色产物) |
| NFR8 | 可观测 | 全链路 trace 可从产物反查执行链路 |
| NFR9 | 审计 | 审核日志不可篡改,保留 ≥ 1 年 |
| NFR10 | 部署 | Langfuse 自托管 docker compose;管理方 Python 进程 |

---

## 8. 验收标准

### 8.1 端到端验收用例

| 用例 | 场景 | 预期结果 |
|---|---|---|
| TC-01 | HappyPath:product→contract→design→client_ui→delivery | 全链路节点逐级 done |
| TC-02 | 并行:server 与 design 同时 ready | 两角色 agent 并行执行 |
| TC-03 | 多入边:client_ui 依赖 contract AND design_asset | 两者都 done 后才 ready |
| TC-04 | 变更级联:改 done 的 contract | 下游 client_ui 自动 blocked + 产物引用清除 |
| TC-05 | 门禁失败:gate test coverage<80% | 上游产物打回 in_progress |
| TC-06 | 审批驳回:reject approval | 上游最近产物节点 changed |
| TC-07 | 审核闭环:submit→review→approve→merge→done | PR 合并后才 done |
| TC-08 | 审核驳回:元数据缺失 | PR 自动 reject + 通知 |
| TC-09 | 中立性:ECC/OpenSpec/spec-kit/custom 产物 | 均可注册,管理方不解析内容 |
| TC-10 | 监控:产物 trace_id 跳转 Langfuse | 可查看完整执行 trace |
| TC-11 | 可视化:节点颜色随状态实时变化 | SSE 推送 < 1s 延迟 |
| TC-12 | 降级:Langfuse 挂掉 | 平台正常工作 |

### 8.2 验收检查清单

- [ ] 产物仓库 main 分支受保护,只接受 PR
- [ ] PR 模板强制声明 node_id/deps
- [ ] submit_artifact 后节点进入 pending_review(非直接 done)
- [ ] approve_pr 合并后节点 done + 下游 cascade
- [ ] reject_pr 后节点回 ready + 通知
- [ ] 依赖未 done 的 PR 被自动 reject
- [ ] 元数据缺失的 PR 被自动 reject
- [ ] requires_human_review=true 的 PR 转人工
- [ ] changed 节点下游递归 blocked + 产物引用清除
- [ ] gate 失败上游打回 in_progress
- [ ] approval 驳回上游 changed
- [ ] 审计日志可查 + 含 trace_id
- [ ] Langfuse trace 贯穿 MCP + LangGraph
- [ ] 可视化依赖图实时状态更新
- [ ] Langfuse 挂掉时降级正常

---

## 9. 实施阶段

### Phase 1:核心编排 + 产物仓库(MVP)

| 任务 | 产出 |
|---|---|
| 产物仓库初始化 + 分支保护 + PR 模板 | artifact-repo 可用 |
| LangGraph StateGraph(状态机 + DAG + cascade/invalidate) | orchestration/ |
| MCP Server(submit/review/approve/reject/get_deps) | mcp_server/ |
| 2 个 Constraint Skill(product-spec + api-contract) | skills/ |
| 审核流程(webhook → skill 校验 → approve/reject) | mcp_server/ |
| 基础可视化(依赖图 + 实时状态) | visual/ |

**验收**:跑通 TC-01 ~ TC-04, TC-07 ~ TC-09

### Phase 2:角色协调 + 监控

| 任务 | 产出 |
|---|---|
| CrewAI 4 角色 Agent + Task 动态生成 | crew/ |
| Langfuse 旁路监听装饰器 + 埋点 | monitoring/ |
| 全部 6 个 Constraint Skill | skills/ |
| 控制节点(gate/approval/fork) | orchestration/nodes.py |
| 审计日志 + get_audit_log 工具 | mcp_server/ |

**验收**:跑通 TC-05, TC-06, TC-10, TC-12

### Phase 3:可视化增强 + 生产化准备

| 任务 | 产出 |
|---|---|
| react-flow 可视化(替代 SVG) | visual/ |
| 审批交互 + 审计日志视图 | visual/ |
| LangGraph Postgres checkpointer | 持久化 |
| Langfuse Dashboard 集成 | monitoring/ |
| 控制节点(switch/notify) | orchestration/ |

**验收**:跑通 TC-11,全部验收检查清单通过

---

## 附录 A:技术栈

| 层 | 技术 | 版本要求 |
|---|---|---|
| 编排 | LangGraph | ≥ 0.2 |
| 角色 | CrewAI | ≥ 0.4 |
| 接口 | MCP Python SDK | ≥ 1.0 |
| 监控 | Langfuse(自托管) | ≥ 3.0 |
| 产物 | 独立 git 仓库 | — |
| 可视化 | react-flow + SSE | — |
| 语言 | Python 3.11+ | — |
| 持久化 | Postgres(checkpointer + audit) | ≥ 15 |
| 部署 | docker compose | — |

---

## 附录 B:深化文档索引

主 PRD 各功能需求均有配套深化文档,位于 `docs/prd/deep-dive/` 目录,共 5 份约 6950 行 + 24 张 Mermaid 设计图:

| 深化文档 | 覆盖章节 | 行数 | 设计图 | 核心深化内容 |
|---|---|---|---|---|
| [fr1-fr6-artifact-review.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr1-fr6-artifact-review.md) | FR1 + FR6 | 1522 | 3 | manifest JSON Schema、审核规则引擎(YAML 配置+优先级+组合逻辑)、并发冲突处理(6类+锁)、SLA 与超时升级、驳回重试流程、CI 校验 |
| [fr2-orchestration.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr2-orchestration.md) | FR2 | 1368 | 6 | 18 条合法转移 + 14 条非法防护、并发 advisory lock、PR 冲突、错误恢复 DLQ、Postgres checkpointer、管线校验、控制节点边界、事件溯源 |
| [fr3-fr5-crew-skills.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr3-fr5-crew-skills.md) | FR3 + FR5 | 1263 | 5 | 4 agent LLM 配置 + cost 控制、失败重试降级、事件队列桥接、**6 个完整 skill.yaml**、版本化演进、SkillRegistry 热重载 |
| [fr4-data-api.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr4-data-api.md) | FR4 + 第5章 + 第6章 | 2021 | 4 | 37 个错误码、JWT 认证、ER 关系图(15 实体)、Postgres 13 表 + 20 索引、**14 个 MCP 工具完整规范**、限流配额、langgraph_invoke 协议 |
| [fr7-fr8-monitoring-visual.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr7-fr8-monitoring-visual.md) | FR7 + FR8 + 第7章 | 779 | 6 | 12 条告警规则、12 项 SLO、评估飞轮、Dashboard 交互规格、SSE 协议、容量规划、灾备 RTO/RPO、安全加固 |

**阅读顺序建议**:先读主 PRD 建立全局认知 → 按实施阶段读对应深化文档(Phase 1 读 fr1/fr2/fr4,Phase 2 读 fr3/fr5/fr7,Phase 3 读 fr8)。

---

## 附录 C:深化修正记录

多 agent 深化过程中发现主 PRD 需修正的 3 项内容:

### C1. MCP 工具数量:13 → 14

**修正**:`approve` / `reject`(作用于 approval 控制节点)与 `approve_pr` / `reject_pr`(作用于产物 PR)是两对独立工具,主 PRD 第 6 章工具总数应为 **14 个**(原误为 13)。详见 [fr4-data-api.md §9](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr4-data-api.md)。

### C2. 密钥管理:v3 → 本期落地

**修正**:主 PRD 第 1.4 节将"密钥管理"划为 v3 范围外,但密钥管理是安全基线,应本期落地(新增 NFR18)。MCP JWT 签名密钥、产物仓库 webhook HMAC、agent API Key 均需 Vault 管理,永不硬编码。详见 [fr7-fr8-monitoring-visual.md §10](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr7-fr8-monitoring-visual.md)。

### C3. skill.yaml 双结构:artifact_constraints + review_rules

**修正**:FR1/FR6 深化建议将 `artifact_constraints` 重构为规则引擎配置 `review_rules`;FR3/FR5 深化的 6 个 skill.yaml 仍用 `artifact_constraints`。**主 agent 仲裁**:两者共存,不冲突——`artifact_constraints` 是声明式简写(简单场景),`review_rules` 是规则引擎配置(复杂场景,可选)。运行时 `artifact_constraints` 自动编译为 `review_rules` 的等价子集。详见 [fr1-fr6-artifact-review.md §4](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr1-fr6-artifact-review.md) 与 [fr3-fr5-crew-skills.md §6](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr3-fr5-crew-skills.md)。

### C4. 新增验收标准

深化文档补充了以下验收标准,实施时一并验证:
- AC2.8 ~ AC2.23(16 项,状态机边界 + 并发 + 错误恢复,见 fr2-orchestration.md §12)
- AC7.6 / AC7.7(告警 + SLO,见 fr7-fr8-monitoring-visual.md §11)
- AC8.6 ~ AC8.8(Dashboard 交互 + SSE,见 fr7-fr8-monitoring-visual.md §11)

### C5. 新增非功能需求

深化文档补充 NFR11 ~ NFR20(共 10 条),涵盖:容量规划、灾备 RTO/RPO、密钥管理、限流配额、审计防篡改等。详见 [fr7-fr8-monitoring-visual.md §9](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr7-fr8-monitoring-visual.md)。

---

## 附录 D:真实场景压力测试汇总(2 轮 32 场景,196 缺陷)

> 通过 2 轮共 32 个真实开发场景对 PRD 进行压力测试,共发现 196 个设计缺陷。场景报告位于 `docs/prd/scenarios/` 目录。本附录为汇总索引,详细走查与修正方案见各场景报告。

### D1. 测试场景总览

#### 第一轮:16 场景(基础流程 + 异常 + 多团队)

| 场景 | 名称 | 核心挑战 | 缺陷数 | 报告 |
|---|---|---|---|---|
| 1 | 契约中途变更 | changed 级联全量失效,无兼容期 | — | [scenario-contract-versioning.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-contract-versioning.md) |
| 2 | 设计稿延迟并行 | client_ui 节点粒度太粗,无灵活并行 | 4 | [scenario-parallel-dependency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-parallel-dependency.md) |
| 3 | 紧急 hotfix 插队 | 无优先级/抢占机制 | 6 | [scenario-exception-human.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-exception-human.md) |
| 4 | 跨团队接口协调 | 4 角色太粗,无角色实例化 | 7 | [scenario-multi-team-rollback.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-multi-team-rollback.md) |
| 5 | 大产物(50MB zip) | max_size 512KB + 无 LFS | 8 | [scenario-artifact-trust.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-artifact-trust.md) |
| 6 | 同契约多格式 | 中立性 vs 格式转换能力 | — | [scenario-contract-versioning.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-contract-versioning.md) |
| 7 | 审批人不在 | 无代理人机制,超时升级不符合组织结构 | 7 | [scenario-exception-human.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-exception-human.md) |
| 8 | 错误产物引用 | 不解析内容=引用正确性无保障 | 7 | [scenario-artifact-trust.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-artifact-trust.md) |
| 9 | 管线中途修改 | 无热重载 + 无管线版本 | 7 | [scenario-artifact-trust.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-artifact-trust.md) |
| 10 | 跨管线共享产物 | Pipeline 隔离,无产物注册表 | 3 | [scenario-parallel-dependency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-parallel-dependency.md) |
| 11 | LLM 失败卡死 | "规则引擎直提"语义模糊,无人工 fallback | 6 | [scenario-exception-human.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-exception-human.md) |
| 12 | Mock 先行开发 | 无 mock 节点类型,依赖模型过于线性 | 5 | [scenario-parallel-dependency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-parallel-dependency.md) |
| 13 | 产物消费者反馈 | 无下游逆向反馈机制 | 6 | [scenario-exception-human.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-exception-human.md) |
| 14 | 契约 v2 不兼容共存 | 无多版本共存,7 态不够 | — | [scenario-contract-versioning.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-contract-versioning.md) |
| 15 | 全链路回滚 | changed 级联全量失效,无增量失效 | 6 | [scenario-multi-team-rollback.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-multi-team-rollback.md) |
| 16 | 多 feature 分支冲突 | 无 feature 命名空间 | 5 | [scenario-multi-team-rollback.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/scenario-multi-team-rollback.md) |

#### 第二轮:16 场景(版本演进 + 多形态 + 运维边界,重点测需求 9)

| 场景 | 名称 | 核心挑战 | 缺陷数 | 报告 |
|---|---|---|---|---|
| A1 | 产物格式自主演进 | skill 约束死板,目录型产物被禁 | 5 | [round2-scenario-evolution.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-evolution.md) |
| A2 | 多语言客户端 | 1 节点 1 引用,无多平台支持 | 7 | [round2-scenario-evolution.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-evolution.md) |
| A3 | A/B 测试变体 | DAG 无法表达并存变体 | 6 | [round2-scenario-evolution.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-evolution.md) |
| A4 | 跨多代码仓库 | ArtifactRef 1:1,微服务多仓库无法表达 | 7 | [round2-scenario-crossrepo-link.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-crossrepo-link.md) |
| A5 | 纯链接产物 | 外部链接无校验,版本失真 | 8 | [round2-scenario-crossrepo-link.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-crossrepo-link.md) |
| A6 | 无依赖旁路产物 | 9 种封闭枚举,无自由产物类型 | 7 | [round2-scenario-crossrepo-link.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-crossrepo-link.md) |
| A7 | 同节点方案竞争 | 先到先得锁,无方案竞争机制 | 5 | [round2-scenario-concurrency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-concurrency.md) |
| A8 | 跨 feature 路径冲突 | 无 feature 命名空间,seq 非原子 | 6 | [round2-scenario-concurrency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-concurrency.md) |
| A9 | PR 合并冲突 | rebase 后重审规则不明确 | 7 | [round2-scenario-concurrency.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-concurrency.md) |
| A10 | 存量项目迁移 | 无批量导入/免审通道 | 8 | [round2-scenario-migration-ops.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-migration-ops.md) |
| A11 | 权限误操作 | 校验失败不入审计,无主动撤销 token | 8 | [round2-scenario-migration-ops.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-migration-ops.md) |
| A12 | 冷启动单节点管线 | 全节点 done 即终止,单节点语义错误 | 7 | [round2-scenario-migration-ops.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-migration-ops.md) |
| A13 | 草案产物共享 | 无 draft 状态,无软提交 | 7 | [round2-scenario-draft-multiworkflow.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-draft-multiworkflow.md) |
| A14 | 多产物仓库 | 跨 git 托管 webhook/CI 不统一 | 7 | [round2-scenario-draft-multiworkflow.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-draft-multiworkflow.md) |
| A15 | 代码产物合一 | 需求 6 vs 需求 9 冲突,审核边界模糊 | 7 | [round2-scenario-draft-multiworkflow.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-draft-multiworkflow.md) |
| A16 | 管线模板复用 | 无模板继承/参数化/版本化 | 8 | [round2-scenario-draft-multiworkflow.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/scenarios/round2-scenario-draft-multiworkflow.md) |

### D2. 缺陷分类统计(196 项)

| 严重度 | 第一轮 | 第二轮 | 合计 |
|---|---|---|---|
| Critical(阻断) | 3 | 5 | 8 |
| High | 45 | 43 | 88 |
| Medium | 35 | 41 | 76 |
| Low | 6 | 18 | 24 |
| **合计** | **89** | **107** | **196** |

### D3. 缺陷根因归类(8 大类)

| 根因类别 | 涉及场景 | 核心问题 | 影响范围 |
|---|---|---|---|
| **R1. 1 节点 1 产物 1 状态刚性** | A2/A3/A4/A6 | ArtifactRef 1:1,无法表达多平台/多变体/多仓库/旁路产物 | 数据模型 + 状态机 |
| **R2. 格式中立≠格式不可知** | A1/A2/A5 | 需求 9"不限制格式"被误解为"不记录格式",导致 guide 失效/审核退化/版本失真 | skill + 审核 |
| **R3. 级联失效粒度过粗** | 1/15/A13 | changed 全量递归 blocked+清引用,无兼容性判定/增量失效/草案隔离 | 状态机 + cascade |
| **R4. 角色与权限粒度过粗** | 4/A11/A14 | 4 角色无实例化,权限只校验 role 不校验团队/仓库归属 | CrewAI + MCP 认证 |
| **R5. 依赖模型过于线性** | 2/12/A6 | 严格 AND 依赖,无可选依赖/替代依赖/旁路依赖 | DAG + 状态机 |
| **R6. 产物仓库边界模糊** | 5/8/16/A4/A14/A15 | 单仓库假设,无 LFS/多仓库/代码合一/路径命名空间 | FR1 + ArtifactRef |
| **R7. 管线生命周期缺失** | 9/A10/A12/A16 | 无热重载/版本/模板/存量迁移/冷启动/派生 | FR2 + pipeline |
| **R8. 异常流程可观测性不足** | 3/7/11/13/A11 | 无优先级/代理人/fallback/逆向反馈/权限异常告警 | FR7 + 审批 + agent |

### D4. P0 修正项(Phase 1 必做,共 20 项)

以下缺陷若不在 Phase 1 修正,后续有数据后返工成本极高:

| 编号 | 场景 | 缺陷 | 修正方案 | 影响章节 |
|---|---|---|---|---|
| P0-1 | A2 | ArtifactRef 1:1 阻断多平台 | 升级为 1:N(引入 slot/variant 维度) | §5.1 + fr4 §8 |
| P0-2 | A4 | ArtifactRef 1:1 阻断多仓库 | 同 P0-1 | §5.1 + fr4 §8 |
| P0-3 | A1 | 目录型产物被 CI 拦截 | 放宽 file_constraints,允许目录型产物 | fr1-fr6 §2 |
| P0-4 | 16/A8 | 无 feature 命名空间,路径冲突 | 产物路径改 `features/{pipeline_id}/...` | FR1.1 + fr1-fr6 §2 |
| P0-5 | 4 | 无角色实例化,单 agent 瓶颈 | 引入 RoleInstance + instance_id | FR3 + fr3-fr5 §2 |
| P0-6 | 15 | 级联全量失效,无增量 | deps 增 coupling 字段,分级失效 | FR2 + fr2 §2 |
| P0-7 | 5 | max_size 512KB 阻断大产物 | 引入 L1/L2/L3 分层存储 | fr1-fr6 §3 + §5.1 |
| P0-8 | A10 | 无存量迁移通道 | 新增 import_legacy_artifacts + 免审标记 | FR6 + 新 MCP 工具 |
| P0-9 | 9 | 无管线版本/热重载 | pipeline_version + reload_pipeline | FR2 + fr2 §7 |
| P0-10 | A16 | 无管线模板 | 模板继承 + 参数化 + 版本化 | FR2 + 新机制 |
| P0-11 | 8 | 引用正确性无保障 | R_REF_EXISTS(git ls-remote) + implements 声明 | fr1-fr6 §4 |
| P0-12 | A13 | 无草案状态 | 新增 draft 状态 + soft_submit | 状态机 + MCP |
| P0-13 | A6 | 无旁路产物类型 | 新增 free_artifact + side_node 标记 | §2.1 + 状态机 |
| P0-14 | 11 | LLM 失败无 fallback | 人工 fallback 模式 + 人员 token | FR3 + FR4 权限 |
| P0-15 | 13 | 无消费者反馈 | consume_ack + done_pending_ack 状态 | 状态机 + MCP |
| P0-16 | 3 | 无优先级/抢占 | pipeline.priority + p0 抢占 | FR2 + 调度 |
| P0-17 | A11 | 权限误操作不入审计 | 校验失败入审计 + ALR-13 告警 | FR7 + MCP 中间件 |
| P0-18 | A5 | 纯链接无校验 | external_refs 字段 + url_reachable op | fr1-fr6 §3/§4 |
| P0-19 | A9 | PR 合并冲突无规则 | 内容指纹校验 + 仓库级 merge 锁 | fr1-fr6 §5 |
| P0-20 | 7 | 无代理人机制 | delegate 字段 + transfer_approvals 工具 | 审批 + MCP |

### D5. 设计图统计

| 来源 | Mermaid 图数 |
|---|---|
| 调研报告(27 章) | 7 |
| 5 份深化文档 | 24 |
| 第一轮场景走查(4 份) | 15 |
| 第二轮场景走查(5 份) | 29 |
| **合计** | **75** |

### D6. 迭代结论

经过 2 轮 32 场景压力测试,PRD 从 v2.0(8000 行)演进到 v2.1(+ 196 缺陷修正)。**主 agent 评估:第二轮新增的 107 个缺陷中,P0 级 20 项已明确修正方案,可作为 PRD v2.1 的输入进入实现阶段。** 剩余 P1/P2 项在 Phase 2/3 逐步落地。

关键认知升级:
1. **需求 9 的正确解读**:不**限制**格式,但应**记录** format_type 供下游感知——"中立"不等于"不可知"
2. **1 节点 1 产物模型必须打破**:引入 slot(平台)+ variant(变体)维度,ArtifactRef 从 1:1 演进为 1:N
3. **级联失效必须分级**:hard_invalidate(破坏性)/ soft_invalidate(兼容性待确认)/ cascade_skip(无影响)
4. **管线生命周期必须完整**:版本化 + 热重载 + 模板 + 存量迁移 + 派生 + 归档
