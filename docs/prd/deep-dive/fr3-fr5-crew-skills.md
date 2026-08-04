# FR3 角色协调(CrewAI)+ FR5 约束技能(Constraint Skills)深化设计

> **文档性质**:对《coordination-platform-prd.md》FR3 / FR5 的深化补充
> **版本**:v3.0 | **日期**:2026-08-04 | **状态**:待评审
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)(v3.0 权威源)
> **调研依据**:[ai-multi-agent-dev-dashboard-research.md](../../research/ai-multi-agent-dev-dashboard-research.md) 第18章 CrewAI、第20章 Skills
> **关联深化**:[fr4-data-api.md](./fr4-data-api.md)(MCP 工具参数与错误码)、[fr1-fr6-artifact-review.md](./fr1-fr6-artifact-review.md)(审核闭环)

## Changelog

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v2.0 | 2026-08-03 | 初版深化:8 个薄弱点(LLM 配置/重试降级/事件桥接/6 skill.yaml/版本化/发现加载/权限矩阵/Process 模式) |
| v2.1 | 2026-08-04 | 修正 AC 编号(AC3.6 起);附录 A llm.yaml 补 design 配置 |
| **v3.0** | 2026-08-04 | **与主 PRD v3.0 全面对齐**:<br/>① **S9 硬预算数值对齐**——Task 级 10k→20k(token)+ warning→硬中断;Agent 级 $5→$10;管线级 $50→$100;补平台级 $4000;补充三层硬预算完整定义/session 级 token/key_constraints 提取算法/agent 行为基线/Task 重入队上限 3 次/成本归因 Dashboard<br/>② **S6 skill.yaml 模型统一**——确认全部使用 `artifact_constraints`(无 `review_rules`);补 `classification`/`completeness_contract` 字段;deps 改用 `presence: required/optional/if_present` 条件依赖语法(对齐主 PRD §FR5.2)<br/>③ **新增 generator 角色**(管理方内置 bot,derived_artifact 生成)<br/>④ **新增 human_submit_token 降级机制**(LLM 故障时人员直提)<br/>⑤ **新增 competition mode**(allow_competition + 竞争锁 TTL 4h)<br/>⑥ **新增 4 个 skill**:client-logic-skill / server-delivery-skill / research-spike-skill / derived-artifact-skill |

> **对齐原则**:本文档与主 PRD v3.0 冲突时,以主 PRD §FR3.5 / §FR5.2 为准。审核报告 review-part2 P0-2/P0-8 已修正。

---

## 0. 文档范围与补全说明

本文针对 PRD v3.0 中 FR3(CrewAI 角色协调)与 FR5(Constraint Skills)的薄弱点进行深化:

| # | 薄弱点 | 深化章节 |
|---|---|---|
| 1 | CrewAI agent 的 LLM 配置(模型/temperature/max_tokens/cost) | §2.1 ~ §2.2 |
| 2 | agent 失败重试与降级策略 | §3(含 Mermaid 图) |
| 3 | CrewAI ↔ LangGraph 事件桥接(双向同步机制) | §4(含代码示例 + Mermaid 时序图) |
| 4 | 10 个完整 skill.yaml(原仅 api-contract-skill 示例) | §6.1 ~ §6.10 |
| 5 | skill 版本化与演进 | §7 |
| 6 | skill 发现与加载机制(运行时匹配/缓存/热重载) | §8(含 Mermaid 图) |
| 7 | agent 工具权限矩阵(细化到参数级) | §2.4 |
| 8 | CrewAI Process 模式选择(sequential vs hierarchical / 并行策略) | §5 |
| **9** | **硬预算数值对齐 + 行为护栏(session token / key_constraints / 行为基线)** | **§2.3(v3.0 重写)** |
| **10** | **generator 角色 + human_submit_token 降级** | **§2.2(v3.0 新增)** |
| **11** | **competition mode(竞争锁)** | **§5.4(v3.0 新增)** |

**核心定位回顾**:Agent **不执行开发,只协调提交**。CrewAI 角色(product/server/design/client/**generator**)agent 是"提交协调员",调用 MCP 工具把人员产出的产物引用提交到管理方。其中 `generator_agent` 是管理方内置 bot,负责 `derived_artifact`(SDK/文档/发布包)的派生提交。Constraint Skill 是 superpowers 风格的"约束 + 引导",定义"交什么"(元数据约束)+ 引导"建议交什么"(guide),不限制"怎么交"。

---

## 1. 深化总览图

```mermaid
graph TB
    subgraph LG["LangGraph 编排层"]
        READY["cascade 产出 ready 事件"]
        BRIDGE["事件桥接器<br/>(§4)"]
        WRITEBACK["状态回写节点"]
    end

    subgraph CREW["CrewAI 角色层(§2 §5)"]
        ORCH["CrewOrchestrator<br/>监听 ready → build_crew"]
        PA["product_agent<br/>LLM 配置(§2.1)"]
        SA["server_agent"]
        DA["design_agent"]
        CA["client_agent"]
        RETRY["失败重试/降级(§3)"]
    end

    subgraph SKILLS["Constraint Skills 层(§6 §7 §8)"]
        DISC["skill 发现(§8)<br/>node_type → skill"]
        CACHE["skill 缓存 + 热重载"]
        VER["版本化(§7)"]
        S1["10 个 skill.yaml"]
    end

    subgraph MCP["MCP 接口层"]
        TOOLS["submit/review/approve..."]
        PERM["工具权限矩阵(§2.4)"]
    end

    READY --> BRIDGE
    BRIDGE --> ORCH
    ORCH --> PA & SA & DA & CA
    PA & SA & DA & CA --> RETRY
    RETRY --> TOOLS
    TOOLS --> PERM
    TOOLS --> WRITEBACK
    WRITEBACK --> READY

    ORCH -.加载.-> DISC
    DISC --> CACHE
    CACHE --> S1
    S1 -.版本.-> VER
    TOOLS -.校验.-> S1

    style LG fill:#1a2a4a,color:#fff
    style CREW fill:#2a4a1a,color:#fff
    style SKILLS fill:#4a2a1a,color:#fff
    style MCP fill:#4a1a4a,color:#fff
```

---

## 2. CrewAI Agent 完整定义(深化点 1、7)

### 2.1 LLM 配置策略

Agent 职责是"协调提交"而非"开发",LLM 选型遵循三条原则:

| 原则 | 说明 |
|---|---|
| **工具调用可靠性优先** | agent 核心动作是调 MCP 工具,模型必须支持稳定 function calling,幻觉调错工具不可接受 |
| **低成本优先** | agent 不做创造性推理(代码/设计由人员完成),无需最强推理模型;用中等模型控成本 |
| **低 temperature 保稳定** | 协调提交是确定性流程,temperature 调低避免随机性导致工具参数漂移 |

**5 个 Agent 的 LLM 配置**(v3.0 新增 generator_agent):

| Agent | 推荐模型 | temperature | max_tokens | 选型理由 |
|---|---|---|---|---|
| `product_agent` | Claude Sonnet 4(或 GPT-4o) | 0.2 | 2048 | 需读懂 product_spec 上下文 + 引导人员补全验收标准;任务轻,中等模型够用 |
| `server_agent` | Claude Sonnet 4 | 0.2 | 2048 | 需校验 api_contract 产物引用与 deps 一致;契约字段结构化,工具调用为主 |
| `design_agent` | Claude Haiku 4(或 GPT-4o-mini) | 0.2 | 1024 | 任务最轻:提交 design_asset 引用(含 figma 链接),几乎无推理,用小模型省钱 |
| `client_agent` | Claude Sonnet 4 | 0.3 | 2048 | 需联调多端依赖(契约+设计+服务实现),上下文最复杂;temperature 略高以处理联调歧义 |
| `generator_agent` | Claude Haiku 4 | 0.1 | 1024 | 管理方内置 bot,负责 derived_artifact 派生提交;任务高度确定(按上游产物生成 SDK/文档),temperature 最低 |

**说明:**
- `max_tokens` 限制输出长度:agent 输出主要是工具调用参数 + 简短说明,无需长输出。`design_agent` / `generator_agent` 用 1024 因任务最简单;其余 2048 留余量。
- `temperature` 统一低值(0.1~0.3):协调提交是确定性流程,不需要创造性。`generator_agent` 最低(0.1)因派生逻辑高度确定;`client_agent` 联调场景略提到 0.3。
- 模型可配置(`config/llm.yaml`),不硬编码,支持切换 provider。`design_agent` / `generator_agent` 可降级到本地小模型进一步省钱。
- **`generator_agent` 与其他 4 角色的区别**:它是管理方内置 bot(非人员角色),不需要人员产出产物——它直接基于上游 done 产物自动派生(SDK/文档/发布包),通过 `report_generation_status` 回传结果。

### 2.2 LLM 配置与 Agent 定义(代码)

```python
# crew/llm_config.py
from crewai import LLM
import os

# 集中配置,支持环境变量切换 provider/model
def make_llm(model: str, temperature: float, max_tokens: int) -> LLM:
    return LLM(
        model=model,                       # 如 "anthropic/claude-sonnet-4"
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),  # 支持代理/自托管
        timeout=30,                          # 单次 LLM 调用超时 30s
        max_retries=2,                        # LLM 层重试(provider 级)
    )

# 5 个 agent 的 LLM 配置(集中管理,便于调参)
LLM_CONFIG = {
    "product":   make_llm("anthropic/claude-sonnet-4", 0.2, 2048),
    "server":    make_llm("anthropic/claude-sonnet-4", 0.2, 2048),
    "design":    make_llm("anthropic/claude-haiku-4",  0.2, 1024),
    "client":    make_llm("anthropic/claude-sonnet-4", 0.3, 2048),
    "generator": make_llm("anthropic/claude-haiku-4",  0.1, 1024),  # v3.0 新增
}
```

```python
# crew/agents.py
from crewai import Agent

product_agent = Agent(
    role="产品经理协调员",
    goal="为 product_spec 节点协调提交:校验人员产出的需求文档引用,通过 MCP 提交 PR",
    backstory=(
        "你是产品需求提交协调员,不写需求文档。"
        "人员用任意工具(ECC/OpenSpec/custom)产出 product_spec 后,"
        "你校验产物引用存在、元数据齐全,调用 MCP submit_artifact 提 PR。"
    ),
    llm=LLM_CONFIG["product"],
    tools=[mcp_submit_artifact, mcp_update_progress, mcp_get_deps],
    allow_delegation=False,          # 不允许委托给其他 agent(职责隔离)
    max_iter=5,                      # 单 Task 最大迭代 5 次,防死循环
    max_rpm=30,                      # 每分钟最大请求数(限流)
    verbose=True,
)

server_agent = Agent(
    role="服务端开发协调员",
    goal="为 api_contract / server_impl / server_test 节点协调提交",
    backstory=(
        "你是服务端提交协调员,不写代码/契约。"
        "人员产出契约或实现引用后,你校验引用与 api_contract 一致性,"
        "调用 MCP 提交。契约类首次提交可 request_approval 触发人工审核。"
    ),
    llm=LLM_CONFIG["server"],
    tools=[mcp_submit_artifact, mcp_update_progress, mcp_get_deps, mcp_request_approval],
    allow_delegation=False,
    max_iter=5,
    max_rpm=30,
    verbose=True,
)

design_agent = Agent(
    role="UI 设计协调员",
    goal="为 design_proto / design_asset 节点协调提交(含 figma 链接校验)",
    backstory=(
        "你是设计提交协调员,不做设计。"
        "人员用 Figma 或任意工具产出原型/标注后,你校验 figma 链接可达、元数据齐全,调 MCP 提交。"
    ),
    llm=LLM_CONFIG["design"],
    tools=[mcp_submit_artifact, mcp_update_progress, mcp_get_deps],
    allow_delegation=False,
    max_iter=3,                       # 任务简单,迭代次数更少
    max_rpm=30,
    verbose=True,
)

client_agent = Agent(
    role="客户端开发协调员",
    goal="为 client_ui / client_func / client_delivery 节点协调提交",
    backstory=(
        "你是客户端提交协调员,不写客户端代码。"
        "你处理多端依赖(契约+设计+服务实现),校验联调依赖完整性后调 MCP 提交。"
        "交付物可 request_approval 触发最终审批。"
    ),
    llm=LLM_CONFIG["client"],
    tools=[mcp_submit_artifact, mcp_update_progress, mcp_get_deps, mcp_request_approval],
    allow_delegation=False,
    max_iter=5,
    max_rpm=30,
    verbose=True,
)

# v3.0 新增:generator_agent(管理方内置 bot,负责 derived_artifact 派生提交)
generator_agent = Agent(
    role="派生产物生成器",
    goal="为 derived_artifact 节点协调提交:基于上游 done 产物自动派生 SDK/文档/发布包,通过 MCP 提交并回传生成状态",
    backstory=(
        "你是管理方内置的派生产物生成器,不服务于特定人员角色。"
        "当上游产物(如 api_contract)done 后,你基于其内容自动生成派生产物"
        "(如 SDK 代码包、API 文档、发布包),通过 MCP submit_artifact 提交引用,"
        "并调用 report_generation_status 回传生成结果。"
        "你必须遵守 key_constraints 中 level=must 的约束。"
    ),
    llm=LLM_CONFIG["generator"],
    tools=[mcp_submit_artifact, mcp_report_generation_status, mcp_get_deps],
    allow_delegation=False,
    max_iter=3,                       # 派生逻辑确定,迭代次数少
    max_rpm=30,
    verbose=True,
)

ROLE_TO_AGENT = {
    "product":   product_agent,
    "server":    server_agent,
    "design":    design_agent,
    "client":    client_agent,
    "generator": generator_agent,      # v3.0 新增
}
```

#### 2.2.1 human_submit_token 降级机制(v3.0 新增,对齐主 PRD §3.1)

当 LLM 持续不可用(agent 故障 + 规则引擎降级也失败时),人员可通过 `human_submit_token` 直接提交产物,绕过 agent:

```python
# crew/human_fallback.py
from datetime import datetime, timedelta, timezone

class HumanSubmitToken(BaseModel):
    """per-user 人工提交 token:仅允许推 feat 分支 + 开 PR,无 merge 权限"""
    token_id: str
    user_id: str                       # 人员 ID(非 agent)
    node_id: str                       # 绑定节点
    role: str                          # 该人员的角色
    allowed_tools: list[str]           # ["submit_artifact", "update_progress"](无 approve_pr)
    expires_at: datetime               # 24h 有效(agent 修复后回收)
    force_human_review: bool = True    # 人工提交的 PR 强制人工审核

def issue_human_submit_token(node_id: str, user_id: str, role: str) -> HumanSubmitToken:
    """LLM 故障时 admin 签发人工提交 token 给人员"""
    return HumanSubmitToken(
        token_id=f"hst_{node_id}_{user_id}",
        user_id=user_id,
        node_id=node_id,
        role=role,
        allowed_tools=["submit_artifact", "update_progress"],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
```

**降级触发链路**(三级降级):
1. **一级(agent 正常)**:LLM agent 协调提交 → 自动审核
2. **二级(LLM 故障)**:规则引擎降级直提(`fallback_direct_submit`,§3.3)→ 强制人工审核
3. **三级(LLM + 规则引擎均故障)**:`human_submit_token` 人员直提 → 强制人工审核

**token 回收**:agent 恢复后,admin 调用 `revoke_human_token(token_id)` 回收人工 token(对齐主 PRD §FR4.1 `revoke_human_token` 工具)。未回收的 token 24h 后自动过期。

### 2.3 三层硬预算与 Agent 行为护栏(v3.0 重写,对齐主 PRD §FR3.5)

> **对齐说明**:v2.x 版本硬预算数值(Task 10k/$5/$50)与主 PRD §FR3.5 矛盾,审核报告 review-part2 P0-2/P0-8 标记为 P0 阻塞项。v3.0 以主 PRD §FR3.5 为权威源全面对齐。

#### 2.3.1 四层硬预算(阈值 / 超限动作 / 恢复条件)

| 层级 | 限额(主 PRD §FR3.5 权威值) | 超限动作 | 恢复条件 |
|---|---|---|---|
| **Task 级** | 20k token(输入+输出)/ 3 次重试 | **硬中断**:Task 终止,节点标记 `need_human=True`(非状态,是标记);节点状态保持 `ready`/`in_progress`,Dashboard 高亮告警 | 人工介入处理(补字段/重提/转 human_submit_token 直提)后清除标记 |
| **Agent 级** | $10/日(按模型价格折算,日滚动窗口) | **排队等待**:新 Task 进队列不 dispatch,等待次日配额刷新;Langfuse 告警 ALR-15 | 次日 00:00(配置时区)配额重置,队列中的 Task 自动出队 dispatch |
| **管线级** | $100 | **暂停管线**:`pause_pipeline` 自动触发,ready 节点不再 dispatch,级联事件挂起(§FR2.7);已 in_progress 的 Task 完成后不再起新 Task | admin 手动 `resume_pipeline` + 追加预算或切换更便宜模型后恢复 |
| **平台级** | $4000/月 | **全局降级**:所有 agent 自动切换到更便宜模型(如 Sonnet→Haiku);通知 admin | 月初配额重置或 admin 手动上调预算后恢复原模型 |

**降级开关(平台级触发后生效)**:`design_agent` Haiku→本地小模型;`product/server/client_agent` Sonnet→Haiku。降级期间 PR 标记 `model_tier=degraded`,强制 `requires_human_review=true`。

**`need_human` 语义澄清**(对齐 review-part2 P0-8):`need_human` **不是节点状态**,而是节点上的布尔标记(`need_human: bool`)。节点状态机保持原态(`ready`/`in_progress`),Dashboard 高亮告警等待人工介入。这避免与 11 态状态机冲突。

#### 2.3.2 Session 级 Token 机制(对齐主 PRD §FR3.5 Agent 身份强绑定)

v2.x 的 token 是 RoleInstance 级(静态),v3.0 升级为 **session 级**(动态),防止 LLM 社会工程越权:

```python
# crew/session_token.py
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

class SessionToken(BaseModel):
    """session 级 token:绑定 session_id + node_id + allowed_tools,5min 有效"""
    token_id: str
    session_id: str                    # 一次 Task 执行 = 一个 session
    node_id: str                       # 绑定到具体节点(防跨节点越权)
    role: str                          # product/server/design/client/generator
    instance_id: str                   # RoleInstance ID
    allowed_tools: list[str]           # 该 session 允许调用的 MCP 工具子集
    expires_at: datetime               # 5min 有效(创建时刻 + 5min)
    classification_clearance: str      # 密级许可(public/internal/confidential/restricted)

def issue_session_token(node_id: str, role: str, instance_id: str,
                        skill_allowed_tools: list[str]) -> SessionToken:
    """节点 ready → build_crew 时签发 session token"""
    return SessionToken(
        token_id=f"st_{node_id}_{int(datetime.now(timezone.utc).timestamp())}",
        session_id=f"sess_{node_id}",
        node_id=node_id,
        role=role,
        instance_id=instance_id,
        allowed_tools=skill_allowed_tools,          # 来自 skill.allowed_mcp_tools
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        classification_clearance=get_role_instance(instance_id).clearance,
    )
```

**MCP Server 校验(每次调用)**:
1. token 未过期(`expires_at > now`)
2. `node_id` 匹配当前调用目标
3. 调用的工具在 `allowed_tools` 列表中
4. 产物的 `classification` ≤ token 的 `classification_clearance`

任一不满足 → 返回 `E_PERMISSION_DENIED` + 触发 ALR-14(越权尝试告警)。

#### 2.3.3 key_constraints 提取算法(对齐主 PRD §FR3.5 + review-part2 P0-8)

主 PRD §FR3.5 要求 `get_dependencies` 返回 `key_constraints` 字段,结构化高亮上游 must 级约束。review-part2 P0-8 指出原算法未定义。v3.0 定义如下:

**提取原则**:管理方**不解析业务内容**(§1.2),只按 skill 声明的元数据规则提取。

```python
# mcp_server/key_constraints.py
def extract_key_constraints(upstream_node_id: str, upstream_content: str,
                             upstream_skill: dict) -> list[dict]:
    """
    从上游产物提取 must 级关键约束,注入下游 agent 上下文。
    提取规则由 skill.yaml 的 key_constraints_extractor 声明(非 LLM 提取)。
    """
    extractor = upstream_skill.get("artifact_constraints", {}).get("key_constraints_extractor")
    if not extractor:
        return []                          # skill 未声明提取规则 → 返回空
    constraints = []
    for rule in extractor:
        if rule["type"] == "jsonpath":
            values = jsonpath_extract(upstream_content, rule["path"])
            if values:
                constraints.append({
                    "level": rule.get("level", "must"),     # must / should / info
                    "text": rule["template"].format(values=values),
                    "source_field": rule["path"],
                })
        elif rule["type"] == "regex":
            matches = re.findall(rule["pattern"], upstream_content)
            if matches:
                constraints.append({
                    "level": rule.get("level", "must"),
                    "text": rule["template"].format(matches=matches),
                    "source_field": rule["pattern"],
                })
    return constraints
```

**skill.yaml 中声明提取规则**(示例,api-contract-skill):
```yaml
artifact_constraints:
  key_constraints_extractor:
    - type: jsonpath
      path: "$.endpoints[*].method"
      level: must
      template: "上游契约定义了 {values} 方法,下游实现必须覆盖"
    - type: jsonpath
      path: "$.error_codes[*].code"
      level: must
      template: "上游契约错误码 {values} 必须在客户端处理"
```

**注入下游 agent context**:`get_dependencies` 返回结构(对齐主 PRD §6.5 行 1612):
```json
[{"node_id": "n1", "content": "...", "stability": "stable",
  "key_constraints": [{"level": "must", "text": "上游契约定义了 ['GET','POST'] 方法,下游实现必须覆盖"}]}]
```

agent backstory 强制要求(对齐主 PRD §FR3.5):"必须遵守 `key_constraints` 中 `level=must` 的约束"。

#### 2.3.4 Agent 行为基线(对齐主 PRD §FR3.5 ALR-13~15)

| 告警码 | 检测维度 | 基线定义 | 触发条件 | 动作 |
|---|---|---|---|---|
| **ALR-13** | 循环检测 | `allowed_sequences`:每个 role 声明合法工具调用序列(如 `get_deps → submit → update_progress`) | 同一 agent 对同一节点的工具调用序列偏离 `allowed_sequences` 超过 **N=3 次** | 告警 Langfuse + 中断 Task,节点标 `need_human=True` |
| **ALR-14** | 越权尝试 | `forbidden_tools`:每个 role 声明禁止调用的工具(如 product_agent 禁 `approve_pr`) | 调用不在 `allowed_tools` 列表中的工具(session token 校验拦截) | 拒绝调用(`E_PERMISSION_DENIED`)+ 告警 + 审计记录 |
| **ALR-15** | 成本异常 | 单 Task 基线 = 20k token;单 Agent 日基线 = $10 | 单 Task 突破 20k token 或单 Agent 突破 $10/日 | 硬中断 / 排队(见 §2.3.1)+ 告警 |

**allowed_sequences / forbidden_tools 声明**(在 RoleInstance 配置中):
```yaml
# config/role_instances.yaml
product:
  allowed_sequences:
    - [get_dependencies, submit_artifact, update_progress]
    - [get_dependencies, update_progress, submit_artifact]
  forbidden_tools:
    - approve_pr
    - reject_pr
    - set_gate_policy
  deviation_threshold: 3              # 偏离 N 次告警
```

#### 2.3.5 Task 重入队上限(对齐 review-part2 P0-8)

Task 失败后节点回 `ready`,CrewOrchestrator 重新入队等待下次 ready 事件。为防无限重试:

| 重入队次数 | 节点状态 | 动作 |
|---|---|---|
| 1~3 次 | `ready`(可重试) | 正常重入队,等待下次 dispatch |
| **>3 次** | `ready` + `need_human=True` | **停止自动重试**,Dashboard 高亮告警,等待人工介入 |

```python
# crew/crew_orchestrator.py(§4.3 _handle_ready 扩展)
MAX_REQUEUE = 3

async def _handle_ready(self, event: ReadyEvent):
    requeue_count = get_requeue_count(event.node_id)
    if requeue_count >= MAX_REQUEUE:
        await self.completion_queue.put(CompletionEvent(
            event_type="task_failed", node_id=event.node_id,
            error=f"Task 重入队超限({MAX_REQUEUE} 次),转 needs_human",
            trace_id=event.trace_id,
        ))
        await mark_need_human(event.node_id, reason="requeue_exceeded")
        return
    # ... 正常执行
    increment_requeue_count(event.node_id)
```

#### 2.3.6 成本归因 Dashboard(对齐主 PRD §FR7.3 + AC7.8)

主 PRD §FR7.3 定义"成本归因"视图(数据源:`agent.cost` span),AC7.8 要求展示 Task/Agent/管线/平台四级成本。v3.0 Dashboard 设计:

| 视图 | 聚合维度 | 展示内容 | 告警阈值 |
|---|---|---|---|
| Task 级成本 | `trace.span(cost)` 按 node_id 聚合 | 单 Task token 消耗 + 折算 USD;超 20k token 标红 | 20k token |
| Agent 级成本 | 按 instance_id + 日期聚合 | 各 RoleInstance 日累计成本;超 $10/日 标黄 + 排队状态 | $10/日 |
| 管线级成本 | 按 pipeline_id 聚合 | 管线全链路累计成本;超 $100 标橙 + 暂停状态 | $100 |
| 平台级成本 | 按月聚合 | 平台月累计成本;超 $4000 标红 + 降级状态 | $4000/月 |
| 预算利用率 | 各层级 actual/budget | 进度条:绿(<70%)/黄(70~90%)/红(>90%) | — |

**实现**:每次 LLM 调用经 `@langfuse_trace` 记录 token + cost span(`agent.cost`),按 agent_id/node_id/pipeline_id 聚合,Dashboard 实时查询 Langfuse API(详见 FR7 监控)。

### 2.4 Agent 工具权限矩阵(细化到参数级)

PRD §3.2 仅到工具级。下表细化每个 agent 调用每个工具时的**参数约束**——这是 MCP Server 鉴权层(见 fr4-data-api.md §3)的强制校验依据:

| 工具 | product_agent | server_agent | design_agent | client_agent | generator_agent | 参数级约束(所有 agent 通用) |
|---|---|---|---|---|---|---|
| `submit_artifact` | ✅ node_type ∈ {product_spec} | ✅ node_type ∈ {api_contract, server_impl, server_test, server_delivery} | ✅ node_type ∈ {design_proto, design_asset} | ✅ node_type ∈ {client_ui, client_logic, client_func, client_delivery} | ✅ node_type ∈ {derived_artifact} | `node_id` 必须属于本 agent 角色(按 pipeline.yaml 的 node.role 校验);`repo` 必须是注册的产物仓库;`branch` 命名 `feat/{role}/{node_type}-{seq}`;`toolspec_framework` 非空且 ≤ 64 字符;`classification` 必须声明且 ≤ token clearance |
| `update_progress` | ✅ 仅本角色节点 | ✅ 仅本角色节点 | ✅ 仅本角色节点 | ✅ 仅本角色节点 | ✅ 仅本角色节点 | `node_id` 属于本角色;`status` ∈ {in_progress}(只能置 in_progress,不能置 done/blocked);`note` ≤ 500 字符 |
| `get_dependencies` | ✅ | ✅ | ✅ | ✅ | ✅ | `node_id` 必须是调用方节点的上游(防越权读取无关节点产物);返回内容按 `classification_clearance` 过滤 |
| `request_approval` | ❌ | ✅ node_type ∈ {api_contract, server_delivery} | ❌ | ✅ node_type ∈ {client_delivery} | ❌ | `node_id` 属于本角色且为契约/交付物(首次/最终把关);`approver` 必须是合法 reviewer_id |
| `report_generation_status` | ❌ | ❌ | ❌ | ❌ | ✅ | `node_id` ∈ {derived_artifact};`status` ∈ {generated, failed};回传后触发下游消费 |
| `review_artifact_pr` | ❌ | ❌ | ❌ | ❌ | ❌ | 仅管理方 bot/reviewer 可调(非角色 agent 工具) |
| `approve_pr` / `reject_pr` | ❌ | ❌ | ❌ | ❌ | ❌ | 仅 reviewer/admin |
| `get_pipeline_state` | ✅ 只读 | ✅ 只读 | ✅ 只读 | ✅ 只读 | ✅ 只读 | 无副作用,所有 agent 可查全局状态 |
| `set_gate_policy` | ❌ | ❌ | ❌ | ❌ | ❌ | 仅 admin |

**关键约束说明:**
- **node_type 白名单**:agent 只能提交本角色产物类型,server_agent 不能提交 design_asset(防角色越权)。
- **node_id 归属校验**:MCP Server 查 pipeline.yaml 确认 `node.role == agent.role`,不符则返回 `FORBIDDEN_NODE_ROLE` 错误(对齐 fr4-data-api.md §2 错误码)。
- **update_progress 限制 status**:agent 只能置 `in_progress`,不能擅自置 `done`(必须经 PR 审核合并)或 `blocked`(由级联控制)。
- **get_dependencies 上游限制**:agent 只能读自己节点的上游产物,不能读无关节点(防信息泄漏)。

---

## 3. Agent 失败重试与降级(深化点 2)

### 3.1 失败分类

| 失败类型 | 示例 | 可重试? | 处理 |
|---|---|---|---|
| **LLM 调用失败** | 超时 / 限流(429) / provider 不可用 | ✅ | 指数退避重试,降级备用模型 |
| **MCP 工具调用失败 - 瞬时** | 产物仓库 git 不可达 / 网络抖动 | ✅ | 指数退避重试 |
| **MCP 工具调用失败 - 业务** | 元数据校验失败 / 依赖未 done / 权限拒绝 | ❌ | 不重试,Task 失败 + 通知人员修复 |
| **Agent 输出格式错误** | 未正确调用工具 / 参数缺失 | ✅(有限) | 重试 1 次,附错误反馈让 LLM 修正 |
| **Task 超时** | 单 Task 超 60s | ❌ | 中断,降级到规则引擎直提 |

### 3.2 重试策略

```python
# crew/retry.py
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TransientError(Exception):
    """可重试的瞬时错误(LLM 超时/限流/网络抖动)"""
class BusinessError(Exception):
    """不可重试的业务错误(校验失败/权限拒绝)"""

@retry(
    stop=stop_after_attempt(3),                          # 最多 3 次
    wait=wait_exponential(multiplier=1, min=1, max=8),   # 指数退避 1s/2s/4s
    retry=retry_if_exception_type(TransientError),       # 仅重试瞬时错误
    reraise=True,                                         # 重试耗尽后抛原异常
)
async def execute_task_with_retry(task: Task, agent: Agent) -> dict:
    try:
        result = await agent.execute_task(task)
        return result
    except LLMTimeoutError as e:
        raise TransientError(f"LLM 超时: {e}")
    except RateLimitError as e:
        raise TransientError(f"限流,稍后重试: {e}")
    except GitRepoUnreachableError as e:
        raise TransientError(f"产物仓库不可达: {e}")
    except (MetadataValidationError, DependencyNotDoneError, ForbiddenNodeRoleError) as e:
        raise BusinessError(f"业务错误,不重试: {e}")
```

### 3.3 超时与降级

| 机制 | 配置 | 降级动作 |
|---|---|---|
| 单 Task 超时 | 60s | 中断 Task,尝试**规则引擎降级直提**(见下) |
| 单 Agent max_iter | product/server/client=5,design=3 | 超限 Task 失败,通知人员 |
| Crew 整体超时 | 5 min(多 Task 累计) | 未完成 Task 标失败,已完成的不回滚 |
| LLM provider 不可用 | 心跳检测 | 切备用 provider(如 Anthropic→OpenAI) |

**规则引擎降级(关键逃生通道)**:当 LLM 持续不可用,agent 无法"理解上下文后调工具"时,降级为**直接构造 MCP 调用**——绕过 LLM 推理,用规则从 node 元数据(deps、role、type)直接拼装 `submit_artifact` 参数。牺牲"智能校验"换"流程不卡死"。

```python
# crew/fallback.py
async def fallback_direct_submit(node_id: str, state: PipelineState) -> dict:
    """LLM 不可用时的降级:规则引擎直接拼参数提交,不走 LLM 推理"""
    node = get_node(node_id)
    # 规则:从 node 配置 + 产物仓库约定直接推导提交参数
    branch = f"feat/{node['role']}/{node['type']}-{node_id}"
    path = f"{node['type']}/{node_id}.yaml"          # 约定路径
    # 校验产物已在分支上(git ls-file)
    if not verify_artifact_on_branch(ARTIFACT_REPO, branch, path):
        return {"ok": False, "error": "降级提交失败:产物文件不存在", "need_human": True}
    # 直接调 MCP(不经 LLM)
    return await mcp_submit_artifact(
        node_id=node_id, repo=ARTIFACT_REPO, branch=branch,
        path=path, toolspec_framework="fallback", deps_decl=node.get("deps", []),
    )
```

**降级原则**:降级提交的 PR 标记 `submitter=fallback-engine`,审核时 `requires_human_review` 强制提级为 true(规则引擎无智能校验,需人工把关)。

### 3.4 Mermaid 图:Agent 失败重试流程

```mermaid
flowchart TB
    START([Task 开始]) --> EXEC[agent.execute_task]
    EXEC --> CHECK{执行结果}

    CHECK -->|成功| OK([Task 成功<br/>回写 LangGraph])
    CHECK -->|瞬时错误| RETRY{重试 < 3 次?}
    CHECK -->|业务错误| FAIL([Task 失败<br/>通知人员修复])
    CHECK -->|超时 60s| TIMEOUT{降级?}

    RETRY -->|是| BACKOFF[指数退避<br/>1s/2s/4s] --> EXEC
    RETRY -->|否| TIMEOUT

    TIMEOUT -->|LLM 不可用| FALLBACK[规则引擎降级直提<br/>fallback_direct_submit]
    TIMEOUT -->|LLM 可用但超时| FAIL

    FALLBACK --> FB_CHECK{降级提交成功?}
    FB_CHECK -->|是| FB_OK([降级成功<br/>PR 标 fallback<br/>强制人工审核])
    FB_CHECK -->|否| FAIL

    FAIL --> NOTIFY[通知人员<br/>节点回 ready<br/>Langfuse 记 error span]

    style OK fill:#3fb950,color:#fff
    style FB_OK fill:#3fb950,color:#fff
    style FAIL fill:#b3261e,color:#fff
    style FALLBACK fill:#e3b341,color:#fff
```

### 3.5 失败后的状态处理

| 失败场景 | 节点状态 | 后续 |
|---|---|---|
| Task 失败(LLM/业务错误) | 回 `ready`(可重试) | 通知人员;CrewOrchestrator 重新入队等待下次 ready 事件 |
| 降级直提成功 | `pending_review` | 正常审核流(但强制人工审) |
| 降级直提失败 | 回 `ready` + `need_human=True` | 节点标记需人工介入,Dashboard 高亮告警 |
| Task 超时 | 回 `ready` | 限流:同一节点连续 3 次超时 → 暂停自动重试,转人工 |

---

## 4. CrewAI ↔ LangGraph 事件桥接(深化点 3)

### 4.1 桥接架构

PRD FR3.3 仅列了事件表,未定义双向同步机制。本节定义两种桥接模式,推荐**事件队列模式**(解耦):

| 模式 | 机制 | 优缺点 |
|---|---|---|
| **同步调用模式**(PRD FR2.4 现有) | LangGraph `crewai_assign` 节点直接同步调 CrewAI `crew.kickoff()` | 简单;但 LangGraph 阻塞等 CrewAI 完成,长任务卡状态机;CrewAI 失败拖垮 LangGraph |
| **事件队列模式**(本文推荐) | LangGraph 写 ready 事件到队列;CrewOrchestrator 异步消费;CrewAI 完成后回写事件 | 解耦,LangGraph 不阻塞;CrewAI 失败不波及编排;支持多 Crew 并行 |

**事件队列模式架构:**

```mermaid
graph LR
    subgraph LG["LangGraph"]
        CASCADE[cascade_node<br/>产出 ready 事件]
        WB[状态回写节点<br/>消费 completion 事件]
    end

    BUS[(事件总线<br/>asyncio.Queue / Redis Stream)]
    subgraph CREW["CrewAI"]
        ORCH[CrewOrchestrator<br/>异步消费 ready 事件]
        CREW1[Crew 执行<br/>agent 调 MCP]
    end
    subgraph MCP["MCP Server"]
        SUBMIT[submit_artifact<br/>触发 PR 审核]
    end

    CASCADE -- "1. emit ready(node_id)" --> BUS
    BUS -- "2. consume" --> ORCH
    ORCH -- "3. build_crew + kickoff" --> CREW1
    CREW1 -- "4. agent 调 MCP" --> SUBMIT
    SUBMIT -- "5. PR 审核合并后<br/>langgraph_invoke(set_done)" --> LG
    CREW1 -- "6. emit completion(node_id, pr_id)" --> BUS
    BUS -- "7. consume" --> WB

    style BUS fill:#4a1a4a,color:#fff
    style LG fill:#1a2a4a,color:#fff
    style CREW fill:#2a4a1a,color:#fff
```

### 4.2 事件契约

两类事件,JSON 结构固定:

```python
# crew/event_bridge.py
from pydantic import BaseModel

class ReadyEvent(BaseModel):
    """LangGraph → CrewAI:节点就绪,需分配 agent"""
    event_type: str = "node_ready"          # 固定
    node_id: str
    node_type: str                          # product_spec / api_contract / ...
    role: str                               # product / server / design / client
    deps_info: list[dict]                   # 上游产物引用 + 内容摘要(供 agent 参考)
    trace_id: str                           # Langfuse trace 贯穿

class CompletionEvent(BaseModel):
    """CrewAI → LangGraph:Task 完成(无论成功/失败/降级)"""
    event_type: str                          # task_completed / task_failed / task_fallback
    node_id: str
    pr_id: int | None                       # 成功时填充
    error: str | None                       # 失败时填充
    fallback_used: bool = False             # 是否用了降级直提
    trace_id: str
```

### 4.3 双向同步机制(代码示例)

```python
# crew/event_bridge.py
import asyncio
from langgraph.graph import StateGraph

class EventBridge:
    """CrewAI ↔ LangGraph 事件桥接器(事件队列模式)"""

    def __init__(self, langgraph_app, mcp_server):
        self.ready_queue: asyncio.Queue[ReadyEvent] = asyncio.Queue()
        self.completion_queue: asyncio.Queue[CompletionEvent] = asyncio.Queue()
        self.langgraph_app = langgraph_app
        self.mcp = mcp_server
        self._orchestrator_task: asyncio.Task | None = None
        self._writeback_task: asyncio.Task | None = None

    # ---------- LangGraph → CrewAI ----------

    async def on_langgraph_ready(self, node_id: str, state: PipelineState):
        """LangGraph cascade_node 产出 ready 事件时调用(注册为 LangGraph callback)"""
        node = get_node(node_id)
        deps_info = self._collect_deps_info(node_id, state)
        event = ReadyEvent(
            node_id=node_id, node_type=node["type"], role=node["role"],
            deps_info=deps_info, trace_id=state.get("current_trace_id", ""),
        )
        await self.ready_queue.put(event)
        # LangGraph 不阻塞等待 CrewAI,直接返回(异步解耦)

    async def _crew_orchestrator(self):
        """异步消费 ready 事件 → build_crew → 执行(独立协程)"""
        while True:
            event: ReadyEvent = await self.ready_queue.get()
            try:
                await self._handle_ready(event)
            except Exception as e:
                # 失败回写 completion(失败事件)
                await self.completion_queue.put(CompletionEvent(
                    event_type="task_failed", node_id=event.node_id,
                    error=str(e), trace_id=event.trace_id,
                ))

    async def _handle_ready(self, event: ReadyEvent):
        agent = ROLE_TO_AGENT[event.role]
        task = Task(
            description=f"为节点 {event.node_id}({event.node_type})协调提交产物",
            agent=agent,
            expected_output="产物 PR 已提交,等待审核",
            context={"node_id": event.node_id, "deps_info": event.deps_info},
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
        try:
            result = await execute_task_with_retry(task, agent)  # §3.2 重试
            pr_id = self._extract_pr_id(result)
            await self.completion_queue.put(CompletionEvent(
                event_type="task_completed", node_id=event.node_id,
                pr_id=pr_id, trace_id=event.trace_id,
            ))
        except BusinessError as e:
            await self.completion_queue.put(CompletionEvent(
                event_type="task_failed", node_id=event.node_id,
                error=str(e), trace_id=event.trace_id,
            ))

    # ---------- CrewAI → LangGraph ----------

    async def _state_writeback(self):
        """异步消费 completion 事件 → 回写 LangGraph 状态(独立协程)"""
        while True:
            event: CompletionEvent = await self.completion_queue.get()
            if event.event_type == "task_failed":
                # 失败:节点回 ready,记录 error 事件(累积追加)
                await self.langgraph_app.ainvoke({
                    "node_states_update": {event.node_id: NodeStatus.READY},
                    "events": [{"type": "task_failed", "node": event.node_id, "error": event.error}],
                })
                # 通知人员(飞书/Slack,详见 FR8)
                await notify_human(event.node_id, event.error)
            elif event.event_type == "task_completed":
                # 成功:节点进 pending_review(submit_artifact 已触发 PR,状态由 MCP 写)
                # 这里仅记录 completion 事件,实际状态由 MCP approve_pr 后 set_done
                await self.langgraph_app.ainvoke({
                    "events": [{"type": "task_completed", "node": event.node_id, "pr_id": event.pr_id}],
                })

    def start(self):
        """启动桥接器(在 main.py 中调用)"""
        self._orchestrator_task = asyncio.create_task(self._crew_orchestrator())
        self._writeback_task = asyncio.create_task(self._state_writeback())

    def _collect_deps_info(self, node_id, state) -> list[dict]:
        """收集上游产物引用 + 内容摘要"""
        deps_info = []
        for dep_id in get_upstream(node_id):
            ref = state["artifact_refs"].get(dep_id)
            if ref:
                content = fetch_artifact_content(ref)  # git show
                deps_info.append({"node_id": dep_id, "ref": ref, "summary": content[:500]})
        return deps_info
```

**关键设计点:**
1. **LangGraph 不阻塞**:cascade_node 产出 ready 事件后立即返回,不等 CrewAI 完成。CrewAI 在独立协程异步执行。
2. **状态回写分离**:CrewAI 完成 → 写 completion 事件 → 独立协程回写 LangGraph。即使回写失败,CrewAI 已完成的 PR 不丢失(MCP 已记录)。
3. **事件累积**:`events` 字段用 `Annotated[Sequence, operator.add]`(PRD FR2.3),completion/failed 事件累积追加,不覆盖。
4. **实际状态由 MCP 驱动**:`task_completed` 只记录事件;节点真正变 `done` 是 PR 审核合并后 MCP `approve_pr` → `langgraph_invoke(set_done)`(见 fr1-fr6-artifact-review.md)。桥接器不直接置 done,避免绕过审核。

### 4.4 LangGraph callback 注册(触发 ready 事件)

```python
# orchestration/langgraph_pipeline.py
from langgraph.graph import StateGraph

def build_graph(bridge: EventBridge):
    graph = StateGraph(PipelineState)

    async def cascade_node(state: PipelineState) -> dict:
        updates = {}
        for node_id, status in state["node_states"].items():
            if status == NodeStatus.DONE:
                for downstream in get_downstream(node_id):
                    if all_deps_done(downstream, state) and \
                       state["node_states"][downstream] == NodeStatus.BLOCKED:
                        state["node_states"][downstream] = NodeStatus.READY
                        # ★ 触发 ready 事件给 CrewAI(非阻塞)
                        await bridge.on_langgraph_ready(downstream, state)
        return {"node_states": state["node_states"]}

    graph.add_node("cascade_node", cascade_node)
    # ... 其余节点
    return graph.compile()
```

### 4.5 Mermaid 图:CrewAI ↔ LangGraph 事件桥接时序

```mermaid
sequenceDiagram
    participant LG as LangGraph
    participant BUS as 事件总线
    participant ORCH as CrewOrchestrator
    participant AGENT as 角色 Agent
    participant MCP as MCP Server
    participant AR as 产物仓库
    participant SK as Skill 校验

    Note over LG: 节点 n1 done
    LG->>LG: cascade_node 解锁 n2/n5 → ready
    LG->>BUS: emit ReadyEvent(n2) + ReadyEvent(n5)
    Note over LG: LangGraph 不阻塞,继续流转

    par server_agent 处理 n2
        BUS->>ORCH: consume ReadyEvent(n2)
        ORCH->>AGENT: server_agent.execute_task(n2)
        AGENT->>MCP: submit_artifact(n2, branch, path)
        MCP->>SK: review_artifact_pr(skill 校验)
        SK-->>MCP: verdict=approve
        MCP->>AR: approve_pr → bot merge
        MCP->>LG: langgraph_invoke(set_done n2)
        AGENT-->>ORCH: result(pr_id=42)
        ORCH->>BUS: emit CompletionEvent(n2, pr_id=42)
    and design_agent 处理 n5(并行)
        BUS->>ORCH: consume ReadyEvent(n5)
        ORCH->>AGENT: design_agent.execute_task(n5)
        AGENT->>MCP: submit_artifact(n5, branch, path)
        MCP->>LG: 节点 n5 → pending_review
        AGENT-->>ORCH: result(pr_id=43)
        ORCH->>BUS: emit CompletionEvent(n5, pr_id=43)
    end

    BUS->>LG: consume CompletionEvent(n2)
    Note over LG: n2 已由 MCP set_done,cascade n3 ready
    LG->>BUS: emit ReadyEvent(n3)
    Note over LG: 循环直到全链路 done
```

**时序关键点:**
- ready 事件从 LangGraph 异步发出,CrewAI 异步消费,两者解耦。
- `submit_artifact` 后节点进 `pending_review`,**审核合并后** MCP 才 `set_done`(不绕过审核闭环)。
- n2/n5 两个 ready 事件并行消费,server_agent 与 design_agent 并行执行。
- CompletionEvent 回写 LangGraph 仅记录事件流;真正状态推进由 MCP 驱动(单一状态写入源,避免竞争)。

---

## 5. CrewAI Process 模式选择(深化点 8)

### 5.1 模式对比

| 模式 | 机制 | 适用场景 | 本平台适用性 |
|---|---|---|---|
| `Process.sequential` | Task 串行执行,前一个完成才下一个 | 有依赖的 Task 链 | ✅ 同角色多节点串行 |
| `Process.hierarchical` | manager agent 协调,可并行 + 动态分配 | 复杂任务分解 + 并行 | ⚠️ 引入额外 manager agent,增成本与延迟 |

### 5.2 本平台并行策略

**核心洞察**:每个 ready 节点已绑定 `role`,Task 已绑定对应 agent。sequential 模式下不同 agent 的 Task 仍会串行。要并行需按角色分组:

**策略:按角色分组,每角色一个 Crew,多 Crew 并行**

```python
# crew/crew_orchestrator.py
async def handle_ready_batch(events: list[ReadyEvent]):
    """一批 ready 事件 → 按角色分组 → 每组一个 Crew → 多 Crew 并行"""
    by_role: dict[str, list[ReadyEvent]] = {}
    for e in events:
        by_role.setdefault(e.role, []).append(e)

    async def run_role_crew(role: str, role_events: list[ReadyEvent]):
        agent = ROLE_TO_AGENT[role]
        tasks = [build_task(e, agent) for e in role_events]
        # 同角色内 sequential(避免同角色节点并发提交冲突)
        crew = Crew(agents=[agent], tasks=tasks, process=Process.sequential)
        return await crew.kickoff_async()

    # 不同角色 Crew 并行(hierarchical 无需,用 asyncio.gather 即可)
    results = await asyncio.gather(
        *[run_role_crew(role, evs) for role, evs in by_role.items()],
        return_exceptions=True,  # 单角色失败不拖垮其他角色
    )
    return results
```

**为何不用 hierarchical:**
1. 本平台角色固定(4 个),无需 manager 动态分配——role 已由 pipeline.yaml 声明。
2. hierarchical 的 manager agent 额外消耗 LLM token,增成本。
3. `asyncio.gather` 并行多 Crew 已足够,且失败隔离更好(单 Crew 异常不影响其他)。

### 5.3 并发控制

| 维度 | 限制 | 理由 |
|---|---|---|
| 同角色节点 | 串行(sequential) | 避免同角色 agent 并发提交冲突(如 server 多节点抢同一产物仓库分支) |
| 不同角色 | 并行(gather) | server/design/product/client/generator 互不依赖,天然并行 |
| 全局并发 Crew | ≤ 5(每角色一个) | 对应 5 角色(含 generator) |
| 单 agent 并发 Task | 1(max_rpm 限流) | CrewAI 单 agent 串行处理 Task |

### 5.4 Competition Mode(竞争模式,v3.0 新增)

**场景**:同一节点的多个上游产物可由不同人员/团队**并行竞争产出**,谁先 done 谁成为该节点的有效上游,其余竞争者的 PR 自动 close。适用于"调研多方案选型""多团队竞速交付"等场景。

**配置**(pipeline.yaml 节点级声明):

```yaml
# pipeline.yaml 节点配置
nodes:
  - id: n_research
    type: research_spike
    role: product
    allow_competition: true              # 开启竞争模式
    competition_lock_ttl_sec: 14400      # 竞争锁 TTL = 4h(14400s)
    deps: []
```

**竞争锁机制**:

| 步骤 | 动作 | 说明 |
|---|---|---|
| 1. 竞争开始 | 多个 RoleInstance 同时对同一竞争节点提交 PR | 每个 PR 持有临时竞争锁(绑定 node_id + instance_id) |
| 2. 锁 TTL | 4h(TTL 内有效) | 超时未合并的 PR 自动释放锁,cancel 竞争资格 |
| 3. 首个合并 | 第一个 PR 审核通过 → bot merge → 节点 done | 竞争结束,该 PR 成为有效产物 |
| 4. 竞争收尾 | 其余竞争 PR 自动 close + 通知提交方 | close 原因标记 `competition_lost`,节点已 done |
| 5. 锁释放 | done 后竞争锁释放 | 允许后续 changed 重提(走标准 changed 级联) |

```python
# crew/competition.py
import asyncio
from datetime import datetime, timedelta, timezone

COMPETITION_LOCK_TTL = 14400  # 4h

class CompetitionLock:
    """竞争锁:绑定 node_id,首个合并者胜出"""
    node_id: str
    holder_instance_ids: list[str]     # 所有竞争者
    winner_instance_id: str | None     # 首个合并者
    locked_at: datetime
    ttl_sec: int = COMPETITION_LOCK_TTL

    def is_expired(self) -> bool:
        return (datetime.now(timezone.utc) - self.locked_at).total_seconds() > self.ttl_sec

    def declare_winner(self, instance_id: str):
        """首个 PR merge 后调用,close 其余竞争 PR"""
        self.winner_instance_id = instance_id
        for holder in self.holder_instance_ids:
            if holder != instance_id:
                asyncio.create_task(close_competition_pr(holder, reason="competition_lost"))
```

**与 §5.2 并行策略的关系**:竞争模式是**同角色多 instance 并行**(多个 team_a_server / team_b_server 竞争同一节点),§5.2 的 gather 是**不同角色并行**。两者正交,可组合(如 server 内竞争 + design/product 并行)。

**预算影响**:竞争模式会放大成本(多个 instance 同时消耗 token),触发 §2.3 Agent 级硬预算($10/日)时,竞争者中成本最低的优先合并。

---

## 6. 10 个完整 skill.yaml(深化点 4)

> **v3.0 更新**:对齐主 PRD §FR5.2 schema。所有 skill 均含 `artifact_constraints`(非 `review_rules`)。新增 `classification` 必填字段、`completeness_contract` 可选字段、`presence` 条件依赖语法。skill 总数 6→10(补 client-logic / server-delivery / research-spike / derived-artifact)。

PRD FR5.2 给出 skill.yaml 结构定义。本节补全全部 10 个,均含 `artifact_constraints` / `file_constraints` / `guide_summary` / `allowed_mcp_tools`。版本字段见 §7。

### 6.1 product-spec-skill

```yaml
# skills/product-spec-skill/skill.yaml
name: product-spec-skill
version: "1.1.0"
description: 约束产品需求文档 product_spec 的提交规范
trigger:
  node_type: product_spec
  role: product
artifact_constraints:
  required_fields:
    - title
    - version                   # semver,如 1.0.0
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework        # 不限取值(ECC/OpenSpec/custom 均可)
    - classification            # v3.0 新增:密级 public/internal/confidential/restricted
  deps: []                      # 根节点,无依赖
  min_version: {}
  file_constraints:
    allowed_extensions: [.yaml, .yml, .json, .md]
    max_size_kb: 512
    min_size_kb: 1              # 防空文件
  requires_human_review: false  # 需求文档,自动审核
guide_ref: guide.md
guide_summary: |
  建议 product_spec 包含:需求背景、用户故事、验收标准、非功能需求。
  可用 ECC / OpenSpec / 自定义格式,管理方不解析内容。
  建议含优先级与影响范围,供下游 api_contract/design 评估工作量。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.2 api-contract-skill(完善示例)

```yaml
# skills/api-contract-skill/skill.yaml
name: api-contract-skill
version: "1.2.0"
description: 约束服务端 api_contract 产物的提交规范
trigger:
  node_type: api_contract
  role: server
artifact_constraints:
  required_fields:
    - title
    - version                   # semver
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework        # spec-kit / OpenSpec / custom 均可
    - classification            # v3.0 新增:密级声明
  deps:                         # v3.0:条件依赖语法(对齐主 PRD §FR5.2)
    - node_type: product_spec
      presence: if_present      # 管线无 product_spec 时不计入 R_DEPS_DONE(支持 server_only 拓扑)
      strictness: strict
  min_version:
    product_spec: "1.0.0"
  file_constraints:
    allowed_extensions: [.yaml, .yml, .json]
    max_size_kb: 1024           # 契约可能较大
    min_size_kb: 1
  requires_human_review: true   # 首次契约影响下游多端,人工把关
  completeness_contract:        # v3.0 新增:结构存在性校验(对齐主 PRD §FR5.2)
    required_structures:
      - jsonpath: "$.endpoints"
        min_items: 1
      - jsonpath: "$.error_codes"
        min_items: 1
    on_fail: reject             # reject | warn
  key_constraints_extractor:    # v3.0 新增:为下游提取 must 级约束(§2.3.3)
    - type: jsonpath
      path: "$.endpoints[*].method"
      level: must
      template: "上游契约定义了 {values} 方法,下游实现必须覆盖"
    - type: jsonpath
      path: "$.error_codes[*].code"
      level: must
      template: "上游契约错误码 {values} 必须在客户端处理"
guide_ref: guide.md
guide_summary: |
  建议 api_contract 包含:端点(method+path)、请求/响应 schema、错误码、鉴权方式。
  可用 spec-kit、OpenSpec 或自定义格式,管理方不解析内容。
  建议含版本化策略(URI 版本 / header 版本),供客户端适配。
  变更契约需 bump version 并通知下游(client_ui/client_func 自动 blocked)。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
  - request_approval            # 契约可请求审批
```

### 6.3 design-handoff-skill

```yaml
# skills/design-handoff-skill/skill.yaml
name: design-handoff-skill
version: "1.1.0"
description: 约束设计交接产物(design_proto / design_asset)的提交规范
trigger:
  node_type: [design_proto, design_asset]   # 一个 skill 覆盖两种设计产物
  role: design
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework        # Figma / TemPad / custom 均可
    - classification            # v3.0 新增:密级声明
  deps:                         # v3.0:条件依赖语法
    - node_type: product_spec
      presence: if_present      # design_only 拓扑无 product_spec 时不阻断
      strictness: strict
  min_version:
    product_spec: "1.0.0"
  file_constraints:
    allowed_extensions: [.json, .md]          # figma 链接 JSON 或标注 Markdown
    max_size_kb: 2048                          # 标注文件可能含图片引用
    min_size_kb: 1
    requires_figma_link: true                  # design_asset 必须含 figma 链接(自定义约束)
  requires_human_review: true                  # 标注/切图影响客户端实现
guide_ref: guide.md
guide_summary: |
  design_proto:建议含页面流、交互说明、状态图。
  design_asset:必须含 figma 链接(源文件)+ 标注(尺寸/颜色/字体)+ 切图引用。
  可用 Figma / 即时设计 / TemPAD 导出,管理方不解析内容。
  标注建议含响应式断点与暗色模式变体。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.4 server-impl-skill

```yaml
# skills/server-impl-skill/skill.yaml
name: server-impl-skill
version: "1.1.0"
description: 约束服务端实现引用(server_impl / server_test)的提交规范
trigger:
  node_type: [server_impl, server_test]
  role: server
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo                # 代码仓库地址(非产物仓库)
    - source.path                # 代码路径
    - source.commit              # 代码 commit hash
    - toolspec.framework        # Claude Code / Cursor / custom
    - classification            # v3.0 新增:密级声明
  deps:                         # v3.0:条件依赖语法
    - node_type: api_contract
      presence: required        # 实现必须依赖契约
      strictness: strict
  min_version:
    api_contract: "1.0.0"
  file_constraints:
    allowed_extensions: [.json]                # 仅引用文件(ref.json)
    max_size_kb: 64                            # 引用文件很小
    min_size_kb: 1
    must_contain: [commit, repo]               # 引用必须含代码 commit(自定义约束)
  requires_human_review: false                 # 仅引用,代码在代码仓库审
guide_ref: guide.md
guide_summary: |
  server_impl:提交代码仓库的 commit 引用(不提交代码内容)。
  建议引用的 commit 已通过代码仓库 CI(lint/test)。
  server_test:提交测试报告引用,建议含覆盖率数据。
  管理方不解析代码内容,仅校验引用存在性。
  代码质量由代码仓库的 gate 节点(coverage_min)把控。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.5 client-ui-skill

```yaml
# skills/client-ui-skill/skill.yaml
name: client-ui-skill
version: "1.1.0"
description: 约束客户端 UI 实现(client_ui)的提交规范
trigger:
  node_type: client_ui
  role: client
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo                # 客户端代码仓库
    - source.path
    - source.commit
    - toolspec.framework        # Cursor / Claude Code / custom
    - classification            # v3.0 新增:密级声明
  deps:                         # v3.0:条件依赖语法
    - node_type: api_contract
      presence: required        # UI 依赖接口契约(数据绑定)
      strictness: strict
    - node_type: design_asset
      presence: if_present      # 无设计拓扑(no-design)时不阻断
      strictness: strict
  min_version:
    api_contract: "1.0.0"
    design_asset: "1.0.0"
  file_constraints:
    allowed_extensions: [.json]                # 引用文件
    max_size_kb: 64
    min_size_kb: 1
  requires_human_review: false                 # UI 实现,代码在代码仓库审
guide_ref: guide.md
guide_summary: |
  client_ui:提交客户端代码仓库的 commit 引用。
  建议实现已对照 design_asset 还原视觉(若 effective_deps 含 design_asset),并按 api_contract 对接数据层。
  建议含组件清单与页面路由,供 client_func 联调参考。
  管理方不解析代码内容,仅校验引用存在性 + 依赖完整性。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.6 client-delivery-skill

```yaml
# skills/client-delivery-skill/skill.yaml
name: client-delivery-skill
version: "1.1.0"
description: 约束客户端交付物(client_func / client_delivery)的提交规范
trigger:
  node_type: [client_func, client_delivery]
  role: client
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework
    - classification            # v3.0 新增:密级声明
  deps:                         # v3.0:条件依赖语法
    - node_type: client_ui
      presence: required        # 功能依赖 UI 实现
      strictness: strict
    - node_type: server_impl
      presence: if_present      # 联调依赖服务端实现(server_only 无 client 时不计)
      strictness: strict
  min_version:
    client_ui: "1.0.0"
    server_impl: "1.0.0"
  file_constraints:
    allowed_extensions: [.json, .md]            # 引用 + 联调报告(Markdown)
    max_size_kb: 256
    min_size_kb: 1
  requires_human_review: true                  # 交付物最终把关
guide_ref: guide.md
guide_summary: |
  client_func:提交联调结果引用,建议含联调通过的端点清单 + 异常处理记录。
  client_delivery:提交交付包引用,建议含交付清单、版本说明、已知问题。
  联调建议覆盖:正常流程 + 错误码处理 + 边界条件。
  交付物需对照 product_spec 验收标准自检。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
  - request_approval            # 交付物可请求最终审批
```

### 6.7 client-logic-skill(v3.0 新增,对齐主 PRD §FR5.4)

```yaml
# skills/client-logic-skill/skill.yaml
name: client-logic-skill
version: "1.0.0"
description: 约束纯客户端逻辑(client_logic,埋点/网络层等,无 UI)的提交规范
trigger:
  node_type: client_logic
  role: client
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework
    - classification
  deps:                         # 条件依赖语法
    - node_type: api_contract
      presence: if_present      # 纯逻辑可能不依赖契约(如埋点 SDK)
      strictness: strict
  min_version:
    api_contract: "1.0.0"
  file_constraints:
    allowed_extensions: [.json]
    max_size_kb: 64
    min_size_kb: 1
  requires_human_review: false
guide_ref: guide.md
guide_summary: |
  client_logic:提交纯客户端逻辑代码仓 commit 引用(无 UI 部分)。
  典型场景:埋点 SDK、网络层封装、工具函数库。
  若依赖 api_contract(如网络层对接接口),按契约实现。
  管理方不解析代码内容,仅校验引用存在性 + 依赖完整性。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.8 server-delivery-skill(v3.0 新增,对齐主 PRD §FR5.4)

```yaml
# skills/server-delivery-skill/skill.yaml
name: server-delivery-skill
version: "1.0.0"
description: 约束服务端交付门禁产物(server_delivery)的提交规范
trigger:
  node_type: server_delivery
  role: server
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework
    - classification
  deps:                         # 条件依赖语法
    - node_type: server_impl
      presence: required        # 交付必须依赖实现
      strictness: strict
    - node_type: server_test
      presence: required        # 交付必须依赖测试
      strictness: strict
  min_version:
    server_impl: "1.0.0"
    server_test: "1.0.0"
  file_constraints:
    allowed_extensions: [.json, .md]            # 引用 + 交付清单
    max_size_kb: 256
    min_size_kb: 1
  requires_human_review: true                  # 服务端交付门禁,人工把关
guide_ref: guide.md
guide_summary: |
  server_delivery:服务端交付门禁产物(对称 client_delivery;server_only 管线用)。
  建议含:交付清单、部署说明、已知问题、回滚方案。
  交付前需 server_impl + server_test 均 done。
  管理方不解析代码内容,仅校验引用存在性 + 依赖完整性。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
  - request_approval            # 交付物可请求审批
```

### 6.9 research-spike-skill(v3.0 新增,对齐主 PRD §FR5.4)

```yaml
# skills/research-spike-skill/skill.yaml
name: research-spike-skill
version: "1.0.0"
description: 约束调研/技术预研旁路产物(research_spike)的提交规范
trigger:
  node_type: research_spike
  role: product                  # 也可为 server(预研方角色)
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework
    - classification
  deps: []                       # 可作多根 DAG 的根节点,无依赖
  min_version: {}
  file_constraints:
    allowed_extensions: [.md, .yaml, .yml, .json]
    max_size_kb: 1024
    min_size_kb: 1
  requires_human_review: false   # 调研结论,自动审核
guide_ref: guide.md
guide_summary: |
  research_spike:调研/技术预研旁路产物,可与 product_spec 并行作多根。
  建议含:调研背景、方案对比、结论建议、风险点。
  可用任意工具产出(Markdown / Notion 导出 / 自定义格式)。
  管理方不解析内容,仅校验引用存在性。
  支持 allow_competition(§5.4 竞争模式,多方案并行调研)。
allowed_mcp_tools:
  - submit_artifact
  - update_progress
  - get_dependencies
```

### 6.10 derived-artifact-skill(v3.0 新增,对齐主 PRD §FR5.4)

```yaml
# skills/derived-artifact-skill/skill.yaml
name: derived-artifact-skill
version: "1.0.0"
description: 约束派生产物(derived_artifact,SDK/文档/发布包)的提交规范
trigger:
  node_type: derived_artifact
  role: generator                 # 管理方内置 bot
artifact_constraints:
  required_fields:
    - title
    - version
    - source.repo
    - source.path
    - source.commit
    - toolspec.framework          # 生成工具(generator 内部声明)
    - classification
    - derived_from                # v3.0 新增:派生源(上游产物 node_id)
    - generator_info              # v3.0 新增:生成器信息(模型/版本/命令)
  deps:                           # 条件依赖语法
    - node_type: derived_from
      presence: required          # 派生产物必须声明上游源
      strictness: strict
  min_version: {}
  file_constraints:
    allowed_extensions: [.json, .yaml, .md, .zip, .tar.gz]
    max_size_kb: 10240            # 发布包可能较大(>10MB 走 LFS)
    min_size_kb: 1
  requires_human_review: false    # 派生产物依赖上游已审产物,自动审核
guide_ref: guide.md
guide_summary: |
  derived_artifact:由 generator_agent 基于上游 done 产物自动派生。
  典型场景:SDK 代码包(api_contract → SDK)、API 文档、发布包。
  必须声明 derived_from(上游产物 node_id)+ generator_info(生成器信息)。
  管理方不解析派生产物内容,仅校验引用存在性 + 上游 done。
  生成结果通过 report_generation_status 回传。
allowed_mcp_tools:
  - submit_artifact
  - report_generation_status
  - get_dependencies
```

### 6.11 Skill 约束摘要对照表(v3.0 更新:10 个 skill)

> 对齐主 PRD §FR5.4 的 10 个 Skill 约束摘要。

| Skill | node_type | deps(presence) | requires_human_review | allowed_mcp_tools 数 |
|---|---|---|---|---|
| product-spec-skill | product_spec | 无 | false | 3 |
| api-contract-skill | api_contract | product_spec:`if_present` | true(首次) | 4 |
| design-handoff-skill | design_proto / design_asset | product_spec:`if_present` | true(design_asset) | 3 |
| server-impl-skill | server_impl / server_test | api_contract:`required` | false | 3 |
| client-ui-skill | client_ui | api_contract:`required`;design_asset:`if_present` | false | 3 |
| client-delivery-skill | client_func / client_delivery | client_ui:`required`;server_impl:`if_present` | true | 4 |
| **client-logic-skill** | client_logic | api_contract:`if_present` | false | 3 |
| **server-delivery-skill** | server_delivery | server_impl+server_test:`required` | true | 4 |
| **research-spike-skill** | research_spike | 无(可作多根) | false | 3 |
| **derived-artifact-skill** | derived_artifact | derived_from:`required` | false | 3 |

**S6 模型统一确认**:全部 10 个 skill 均使用 `artifact_constraints` 字段名(对齐主 PRD §FR5.2),**无 `review_rules` 字样**。新增字段:`classification`(全部必填)、`completeness_contract`(api-contract-skill 示例)、`key_constraints_extractor`(api-contract-skill 示例)、`presence`/`strictness` 条件依赖语法(全部 deps)。

---

## 7. Skill 版本化与演进(深化点 5)

### 7.1 版本管理策略

每个 skill.yaml 含 `version` 字段(semver: `MAJOR.MINOR.PATCH`):

| 版本号变更 | 含义 | 兼容性 |
|---|---|---|
| PATCH(1.0.0→1.0.1) | guide.md 更新 / 注释调整 / 修复约束笔误 | 完全向后兼容,旧产物不受影响 |
| MINOR(1.0.0→1.1.0) | 新增可选约束字段 / 新增 allowed_mcp_tools | 向后兼容,旧产物缺新字段不报错(可选字段) |
| MAJOR(1.0.0→2.0.0) | 新增必填字段 / 删除字段 / 改约束语义 | **不向后兼容**,旧产物引用需重新审核 |

### 7.2 产物记录 skill 版本

产物 PR 审核时,审计日志记录所用 skill 版本(扩展 PRD §5.2 AuditLogEntry):

```json
{
  "audit_id": "aud_20260804_001",
  "skill_used": "api-contract-skill",
  "skill_version": "1.1.0",
  "skill_verdict": "approve"
}
```

**已 done 产物的 skill 版本不可追溯变更**:产物合并时锁定 skill 版本,后续 skill 升级不影响已合并产物(避免历史产物被新约束打回)。

### 7.3 Skill 升级对历史产物的影响

| 场景 | 影响 | 处理 |
|---|---|---|
| skill PATCH/MINOR 升级 | 已 done 产物不受影响(锁定旧版本) | 新提交的 PR 用新版本校验 |
| skill MAJOR 升级(新增必填字段) | 已 done 产物不受影响;**重新提交变更**时按新版本校验,可能因缺字段被 reject | 提交方需补字段后重提 |
| skill 新增(新增 node_type) | 不影响现有节点 | 新节点类型用新 skill |
| skill 废弃 | 已 done 产物保留历史引用 | 新节点不再匹配该 skill(需迁移到新 skill) |

**MAJOR 升级迁移流程:**
1. 新 skill 版本发布,旧版本标记 `deprecated: true`(仍可用,但警告)
2. 宽限期(如 2 周):提交方可选新旧版本
3. 宽限期后:旧版本下线,重新提交必须用新版本(缺字段会被 reject,需补)

### 7.4 Skill 仓库与发布

Skill 文件存 `skills/` 目录(随管理方代码仓库版本化)。Skill 变更走管理方仓库 PR(人工评审),合并后触发 skill 索引重建(§8.3 热重载)。

---

## 8. Skill 发现与加载机制(深化点 6)

### 8.1 运行时匹配 node_type → skill

**启动时建立 skill 索引:**

```python
# skills/registry.py
import os, yaml
from pathlib import Path

class SkillRegistry:
    """skill 发现 + 索引 + 缓存"""

    def __init__(self, skills_dir: str = "skills/"):
        self.skills_dir = Path(skills_dir)
        self.index: dict[str, dict] = {}        # node_type → skill 配置
        self.cache: dict[str, dict] = {}        # skill_name → 解析后的 yaml(mtime 校验)
        self.mtimes: dict[str, float] = {}      # skill_name → 文件 mtime

    def build_index(self):
        """启动时扫描 skills/ 目录,建立 node_type → skill 映射"""
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            yaml_path = skill_dir / "skill.yaml"
            if not yaml_path.exists():
                continue
            skill = self._load_cached(str(yaml_path))
            trigger = skill.get("trigger", {})
            node_types = trigger.get("node_type", [])
            if isinstance(node_types, str):
                node_types = [node_types]
            for nt in node_types:
                if nt in self.index:
                    raise ValueError(f"node_type {nt} 重复匹配 skill: "
                                     f"{self.index[nt]['name']} vs {skill['name']}")
                self.index[nt] = skill

    def match_skill(self, node_type: str) -> dict | None:
        """运行时按 node_type 匹配 skill(节点 ready 时调用)"""
        return self.index.get(node_type)

    def _load_cached(self, yaml_path: str) -> dict:
        """加载 skill.yaml,带 mtime 校验的缓存"""
        mtime = os.path.getmtime(yaml_path)
        skill_name = Path(yaml_path).parent.name
        if skill_name in self.cache and self.mtimes.get(skill_name) == mtime:
            return self.cache[skill_name]       # 缓存命中
        with open(yaml_path) as f:
            skill = yaml.safe_load(f)
        self.cache[skill_name] = skill
        self.mtimes[skill_name] = mtime
        return skill
```

### 8.2 Skill 加载流程

节点 ready 时,EventBridge 在构造 Task context 时加载 skill:

```python
# crew/crew_orchestrator.py(§4.3 _handle_ready 扩展)
async def _handle_ready(self, event: ReadyEvent):
    skill = skill_registry.match_skill(event.node_type)
    if not skill:
        # 无匹配 skill:节点不允许提交(配置错误)
        await self.completion_queue.put(CompletionEvent(
            event_type="task_failed", node_id=event.node_id,
            error=f"无匹配 skill for node_type {event.node_type}", trace_id=event.trace_id,
        ))
        return
    agent = ROLE_TO_AGENT[event.role]
    # v3.0:签发 session 级 token(§2.3.2)
    session_token = issue_session_token(
        event.node_id, event.role, event.instance_id,
        skill.get("allowed_mcp_tools", []),
    )
    task = Task(
        description=f"为节点 {event.node_id}({event.node_type})协调提交产物引用:校验人员已产出的产物,通过 MCP submit_artifact 提 PR",
        agent=agent,
        expected_output="产物 PR 已提交",
        context={
            "node_id": event.node_id,
            "instance_id": event.instance_id,           # v3.0 新增(对齐主 PRD §FR3.2)
            "node_type": event.node_type,                # v3.0 新增
            "deps_info": event.deps_info,                # 含 key_constraints(§2.3.3)
            "key_constraints": extract_key_constraints_from_deps(event.deps_info),  # v3.0 新增:must 级约束高亮
            "participation_profile": state.get("participation", {}).get("profile"),  # v3.0 新增
            "session_token": session_token,              # v3.0 新增:session 级 token
            "skill": {                                   # 注入 skill 给 agent 参考
                "name": skill["name"],
                "version": skill.get("version", ""),
                "guide_summary": skill.get("guide_summary", ""),
                "allowed_mcp_tools": skill.get("allowed_mcp_tools", []),
                "required_fields": skill["artifact_constraints"]["required_fields"],
            },
        },
    )
    # ... 执行 Task
```

**PR 审核时也用 skill 校验**(对齐 fr1-fr6-artifact-review.md):

```python
# mcp_server/tools.py(review_artifact_pr)
async def review_artifact_pr(pr_id: int) -> dict:
    pr = await get_pr_detail(pr_id)
    node_type = pr["template"]["node_type"]
    skill = skill_registry.match_skill(node_type)   # 同一 skill 索引
    # 用 skill.artifact_constraints 校验元数据/依赖/文件格式
    ...
```

### 8.3 热重载

监听 `skills/` 目录变更,更新索引和缓存(无需重启):

```python
# skills/registry.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SkillHotReloadHandler(FileSystemEventHandler):
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def on_modified(self, event):
        if event.src_path.endswith("skill.yaml"):
            self.registry.build_index()       # 重建索引(mtime 缓存自动失效)
            logger.info("skill 索引已热重载")

def start_hot_reload(registry: SkillRegistry):
    observer = Observer()
    observer.schedule(SkillHotReloadHandler(registry), registry.skills_dir, recursive=True)
    observer.start()
```

**热重载安全约束:**
- 热重载仅影响**新 ready 节点**和**新 PR 审核**。
- 已 `pending_review` 的 PR 按提交时的 skill 版本审核(避免中途换规则导致结果不一致)——审核时从审计上下文恢复提交时的 skill 版本。

### 8.4 Mermaid 图:Skill 发现与加载流程

```mermaid
flowchart TB
    subgraph STARTUP["启动阶段"]
        SCAN[扫描 skills/ 目录] --> PARSE[解析每个 skill.yaml]
        PARSE --> INDEX[建立 node_type → skill 索引]
        INDEX --> CACHE[缓存解析结果 + mtime]
    end

    subgraph RUNTIME["运行时(节点 ready)"]
        READY[节点 ready] --> MATCH{match_skill<br/>node_type}
        MATCH -->|命中| LOAD[加载 skill 约束 + guide]
        MATCH -->|未命中| ERR[Task 失败:<br/>无匹配 skill<br/>配置错误]
        LOAD --> INJECT[注入 Task context<br/>供 agent 参考]
        INJECT --> EXEC[agent 执行 + 调 MCP]
    end

    subgraph REVIEW["PR 审核阶段"]
        PR[PR 提交] --> MATCH2{match_skill<br/>node_type}
        MATCH2 -->|命中| VALIDATE[按 artifact_constraints 校验<br/>required_fields/deps/file]
        MATCH2 -->|未命中| REJECT[reject:<br/>无匹配 skill]
        VALIDATE --> VERDICT{verdict}
        VERDICT -->|全过 + 非高危| AUTO[自动 approve]
        VERDICT -->|全过 + 高危| HUMAN[转人工审核]
        VERDICT -->|任一失败| REJ[reject + 原因]
    end

    subgraph HOT["热重载(运行中)"]
        WATCH[watchdog 监听 skills/ 变更] --> REBUILD[重建索引<br/>mtime 缓存自动失效]
        REBUILD --> INDEX
    end

    STARTUP --> RUNTIME
    STARTUP --> REVIEW
    HOT -.-> INDEX

    style INDEX fill:#a371f7,color:#fff
    style ERR fill:#b3261e,color:#fff
    style AUTO fill:#3fb950,color:#fff
    style REJ fill:#b3261e,color:#fff
    style WATCH fill:#e3b341,color:#fff
```

---

## 9. 验收标准补充

在 PRD FR3.4 / FR5.5 基础上补充:

### FR3 补充验收(v3.0 更新:编号从 AC3.6 起,避免与主 PRD AC3.1-AC3.5 冲突)

- AC3.6: 5 个 agent(含 generator)的 LLM 配置(模型/temperature/max_tokens)可配置且生效(config/llm.yaml)
- AC3.7: agent Task 失败时,瞬时错误自动重试 ≤ 3 次(指数退避),业务错误不重试
- AC3.8: LLM 不可用时,降级规则引擎能直提 PR(标记 fallback + 强制人工审)
- AC3.9: LangGraph ready 事件异步触发 CrewAI,LangGraph 不阻塞等待
- AC3.10: CompletionEvent 回写 LangGraph,失败 Task 节点回 ready + 通知人员
- AC3.11: 不同角色 Crew 并行执行(asyncio.gather),同角色节点串行
- AC3.12: agent 越权提交(如 server_agent 提交 design_asset)被 MCP 拒绝(FORBIDDEN_NODE_ROLE)
- AC3.13: 单 Task 超 60s 被中断,触发降级或失败通知
- AC3.14(v3.0): Task 级 token 突破 20k 触发硬中断,节点标记 `need_human=True`(非状态)
- AC3.15(v3.0): Agent 级日成本突破 $10 触发排队等待,新 Task 不 dispatch
- AC3.16(v3.0): 管线级成本突破 $100 触发 `pause_pipeline`,平台级突破 $4000/月触发全局降级
- AC3.17(v3.0): session 级 token 绑定 node_id + allowed_tools,5min 有效,越权调用返回 E_PERMISSION_DENIED + ALR-14 告警
- AC3.18(v3.0): get_dependencies 返回 key_constraints(must 级),agent backstory 强制遵守
- AC3.19(v3.0): agent 行为偏离 allowed_sequences 超 3 次 → ALR-13 告警 + 中断 Task
- AC3.20(v3.0): Task 重入队超 3 次 → 节点 `need_human=True`,停止自动重试
- AC3.21(v3.0): generator_agent 可提交 derived_artifact 并调 report_generation_status 回传
- AC3.22(v3.0): LLM + 规则引擎均故障时,human_submit_token 人员直提 PR(强制人工审),admin 可 revoke_human_token 回收
- AC3.23(v3.0): competition mode 开启时,首个 PR merge 后其余竞争 PR 自动 close(competition_lost)
- AC3.24(v3.0): 成本归因 Dashboard 展示 Task/Agent/管线/平台四级成本(对齐 AC7.8)

### FR5 补充验收(v3.0 更新:10 个 skill)

- AC5.7: 10 个 skill.yaml 均可被 skill_registry 加载,索引建立成功
- AC5.8: 节点 ready 时按 node_type 匹配到正确 skill(含多 node_type 的 skill 如 design-handoff)
- AC5.9: skill.yaml 变更后热重载生效,无需重启(watchdog 监听)
- AC5.10: skill 缓存命中时(mtime 未变)不重复解析 yaml
- AC5.11: skill MAJOR 升级后,已 done 产物不受影响;重新提交时按新版本校验
- AC5.12: 审计日志记录 skill_used + skill_version
- AC5.13: 无匹配 skill 的节点提交被拒(配置错误保护)
- AC5.14: guide_summary 内容注入 agent context 可见,但不强制
- AC5.15(v3.0): 全部 skill 使用 `artifact_constraints` 字段名,无 `review_rules` 残留
- AC5.16(v3.0): skill.required_fields 含 `classification`,缺失或超 clearance 的 PR 被拒
- AC5.17(v3.0): completeness_contract 结构缺失时按 on_fail(reject/warn)策略处理
- AC5.18(v3.0): skill.deps 使用 `presence: required/optional/if_present` 条件依赖语法,if_present 依赖未 done 不阻断 ready

---

## 10. 与其他深化文档的衔接

| 衔接点 | 关联文档 | 说明 |
|---|---|---|
| MCP 工具参数 schema / 错误码 | [fr4-data-api.md](./fr4-data-api.md) §2 §9 | agent 调 MCP 时的错误码(FORBIDDEN_NODE_ROLE 等)对齐 |
| PR 审核闭环 / review_artifact_pr | [fr1-fr6-artifact-review.md](./fr1-fr6-artifact-review.md) | skill 约束校验是审核流程的一环 |
| Langfuse trace 埋点 | PRD FR7 | agent Task 执行 + 失败/降级均记 Langfuse span |
| LangGraph state schema | PRD FR2.3 / §5.1 | CompletionEvent 回写 events 字段(累积追加) |
| Agent 注册与心跳 | 调研报告 §13.1(4) | CrewOrchestrator 消费 ready 事件前查 AgentRegistry 确认 agent 在线 |

---

## 附录 A:配置文件汇总

### llm.yaml(可选,集中管理 LLM 配置)

```yaml
# config/llm.yaml(v3.0:成本数值对齐主 PRD §FR3.5)
agents:
  product:
    model: anthropic/claude-sonnet-4
    temperature: 0.2
    max_tokens: 2048
    max_iter: 5
    max_rpm: 30
    daily_cost_limit_usd: 10        # v3.0: $5→$10(对齐主 PRD §FR3.5)
  server:
    model: anthropic/claude-sonnet-4
    temperature: 0.2
    max_tokens: 2048
    max_iter: 5
    max_rpm: 30
    daily_cost_limit_usd: 10        # v3.0: $5→$10
  design:
    model: anthropic/claude-haiku-4
    temperature: 0.2
    max_tokens: 1024
    max_iter: 3
    max_rpm: 30
    daily_cost_limit_usd: 10        # v3.0: $3→$10(主 PRD 统一 $10/日,不再按角色区分)
  client:
    model: anthropic/claude-sonnet-4
    temperature: 0.3
    max_tokens: 2048
    max_iter: 5
    max_rpm: 30
    daily_cost_limit_usd: 10        # v3.0: $5→$10
  generator:                        # v3.0 新增
    model: anthropic/claude-haiku-4
    temperature: 0.1
    max_tokens: 1024
    max_iter: 3
    max_rpm: 30
    daily_cost_limit_usd: 10
pipeline:
  total_cost_limit_usd: 100         # v3.0: $50→$100(对齐主 PRD §FR3.5)
task:
  timeout_sec: 60
  token_limit: 20000                # v3.0 新增:Task 级 20k token 硬中断(对齐主 PRD §FR3.5)
  max_requeue: 3                    # v3.0 新增:重入队上限 3 次(§2.3.5)
retry:
  max_attempts: 3
  backoff: exponential
  min_wait_sec: 1
  max_wait_sec: 8
fallback:
  enabled: true
  force_human_review: true
session_token:                      # v3.0 新增:session 级 token(§2.3.2)
  ttl_min: 5
platform:                           # v3.0 新增:平台级预算(§2.3.1)
  monthly_cost_limit_usd: 4000      # 对齐主 PRD §FR3.5
  degrade_action: switch_cheaper_model
```

### 目录结构补充(PRD §23.2 扩展)

```
coordination-platform/
├─ crew/
│  ├─ agents.py                 # 5 角色 Agent(§2.2,含 generator)
│  ├─ llm_config.py             # LLM 配置(§2.1)
│  ├─ crew_orchestrator.py      # Crew 编排 + 并行(§4.3 §5.2)
│  ├─ event_bridge.py           # 事件桥接器(§4.3)
│  ├─ retry.py                  # 失败重试(§3.2)
│  ├─ fallback.py               # 规则引擎降级(§3.3)
│  ├─ session_token.py          # session 级 token(§2.3.2,v3.0 新增)
│  ├─ human_fallback.py         # human_submit_token 降级(§2.2.1,v3.0 新增)
│  └─ competition.py            # 竞争锁(§5.4,v3.0 新增)
├─ skills/
│  ├─ registry.py               # skill 发现 + 索引 + 热重载(§8)
│  ├─ product-spec-skill/
│  ├─ api-contract-skill/
│  ├─ design-handoff-skill/
│  ├─ server-impl-skill/
│  ├─ client-ui-skill/
│  ├─ client-delivery-skill/
│  ├─ client-logic-skill/       # v3.0 新增
│  ├─ server-delivery-skill/    # v3.0 新增
│  ├─ research-spike-skill/     # v3.0 新增
│  └─ derived-artifact-skill/   # v3.0 新增
├─ config/
│  └─ llm.yaml                  # LLM 集中配置(附录 A,v3.0 数值对齐)
└─ ...
```
