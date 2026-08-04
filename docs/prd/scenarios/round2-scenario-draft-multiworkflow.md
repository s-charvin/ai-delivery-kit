# 第三轮压力测试:草案产物 / 多产物仓库 / 代码产物合一 / 管线模板复用

> **文档性质**:对《coordination-platform-prd.md》v2.0 及其深化文档(fr1-fr6-artifact-review.md / fr2-orchestration.md / fr3-fr5-crew-skills.md)的第三轮"压力测试"场景走查报告
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:待评审
> **方法**:选取 4 个真实开发场景(编号 A13-A16,不与第一轮 16 个场景、第二轮 A1-A12 重复),逐步走查 PRD 当前设计能否处理,定位"纸上谈兵"的设计缺陷,并提出可落地修正方案
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)
> **关联深化**:[fr1-fr6-artifact-review.md](../deep-dive/fr1-fr6-artifact-review.md) | [fr2-orchestration.md](../deep-dive/fr2-orchestration.md) | [fr3-fr5-crew-skills.md](../deep-dive/fr3-fr5-crew-skills.md)
> **核心原则**:需求 9"产物完全自由"——产物怎么定义由各端自己决定;设计只提供 figma 链接即可;客户端/服务端开发不限制方式。管理方不限制内容格式,只做管理约束。

---

## 0. 走查方法说明

第一轮(scenario-*.md 5 份)覆盖节点粒度、依赖模型、跨管线共享等结构性问题;第二轮(round2-scenario-concurrency / crossrepo-link / evolution / migration-ops 4 份,A1-A12)覆盖并发竞争、跨仓库引用、演进迁移、运维操作。本轮 4 个场景聚焦于**"产物自由"与"管理约束"的边界张力**以及**"通用性"的实现机制缺失**,选取前两轮未触及的 4 个真实情境:

| 场景 | 核心挑战 | 压测的 PRD 设计点 |
|---|---|---|
| A13 | 草案产物(未完成但要共享给下游预览) | 状态机 7 态无 draft、ArtifactRef 单值、节点锁 TTL、get_dependencies 拉取边界 |
| A14 | 多产物仓库(不同团队用不同 git 托管) | 单仓库假设、webhook 跨托管适配、CI 注入、角色→仓库权限、跨仓库 git show |
| A15 | 代码仓库与产物仓库合一(混合仓库) | 需求 6"独立"语义、webhook 路径过滤、CI 目录白名单、分支保护叠加、审核边界声明 |
| A16 | 管线模板复用(80% feature 走标准流程) | 模板抽象缺失、pipeline.yaml 无继承/参数化、模板版本化与实例化关系、模板审核、通用性实现机制 |

每个场景按 **场景描述 → PRD 走查 → 设计缺陷 → 修正方案 → 设计图** 组织,所有缺陷均可定位到 PRD 具体章节(含行号)。最后附**缺陷汇总表**。

---

## 1. 场景 A13:草案产物(产物未完成但要共享给下游预览)

### 1.1 场景描述

**业务背景**:登录功能管线中,`api_contract` 节点(n2)依赖 `product_spec`(n1,n1 已 done)。下游 `client_ui`(n7)依赖 `api_contract` + `design_asset`。

服务端团队正在起草 `api_contract`,但**契约尚未定稿**(还在和产品讨论字段命名、错误码),预计还要 2-3 天才能正式提交。客户端团队为了加速并行,想**基于当前草案**先把网络层骨架搭起来(URL 拼接、错误码枚举、模型映射),等服务端正式版出来再对齐细节。

**服务端的诉求**:
- 不想提交"正式 PR"——草案还会改,提了正式 PR 进 `pending_review` 会被 skill 校验(如 `required_fields` 缺失、字段不全)reject,还要消耗审核配额
- 但又想让客户端看到当前草案,避免客户端瞎猜

**客户端的诉求**:
- 愿意基于草案开发,接受"草案变更我要跟着改"的风险
- 需要在草案变更时收到通知,而不是等正式版 done 才知道

**关键特征**:需求 9 说"产物完全自由",产物的**完成度**也应该是自由的——草案 / 正式 / 废弃都是产物的合理状态。但 PRD 的状态机只有 ready → pending_review → done,没有"草案"概念。

### 1.2 PRD 走查

#### 走查点 1:状态机没有 draft 态

主 PRD §2 术语表(第 86 行):

> 状态机:节点状态流转:blocked → ready → pending_review → done / changed

fr2-orchestration.md §2.1(第 59 行)穷举了 7 态:`blocked` / `ready` / `pending_review` / `in_progress` / `review` / `done` / `changed`。fr2 §2.2(第 88-107 行)的非法转移防护表里,所有"非 pending_review → done"路径都被拒绝。

**结论**:草案无立身之处。要么走 `ready → pending_review`(提交正式 PR,被审核),要么不提交(草案留在本地 feat 分支,下游 `get_dependencies` 拉不到)。

#### 走查点 2:正式 PR 会被 skill 校验 reject

fr1-fr6 §3.3 manifest JSON Schema(第 266-444 行)规定 `required` 字段含 `title` / `version` / `source` / `toolspec` / `deps` / `created_at` / `submitter`。fr1 §4.1.1 规则 `R_META_REQUIRED`(priority 100, on_fail=reject)会校验这些字段全存在。

fr3-fr5 §6.2 `api-contract-skill`(第 711-749 行)guide 建议 api_contract 含"端点、schema、错误码"。草案阶段这些大概率不全。

**结论**:服务端若提正式 PR,`R_META_REQUIRED` / `R_DEPS_DONE` 等规则会 reject。草案根本进不了审核门。

#### 走查点 3:get_dependencies 只拉 main 上的 commit

主 PRD §6.5 `get_dependencies`(第 819-834 行):

```json
"description": "查上游产物内容(git show 拉取),供 agent 参考"
```

fr1 §2.3.1(第 169-180 行):

> 管理方 ArtifactRef 只指向"当前生效版本"的 commit,旧版本文件保留在仓库但不被引用。

**结论**:`get_dependencies` 拉 `artifact_refs[node_id].commit`(即 main 上已合并的 commit)。草案在 feat 分支,未合并,`artifact_refs[n2]` 为空,客户端 `get_dependencies(n7)` 拿不到 n2 的草案内容。

#### 走查点 4:节点锁 TTL 与草案长期持有矛盾

fr1 §5.2.1(第 784-803 行):

> 节点 `ready` 时,第一个调 `submit_artifact` 的 agent 获得锁……锁有 TTL(默认 12 小时,可配置),超时自动释放。

**结论**:服务端想长期持有草案(2-3 天)持续修改,但节点锁 TTL 12h,超时自动释放。草案场景下锁语义不适用——草案不是"独占编辑权",而是"持续预览"。

#### 走查点 5:草案变了下游怎么办

fr2 §2.1 T10(第 72 行):`done → changed` 是"已 done 产物被重新提交"。fr1 §5.3.3 依赖失效:依赖节点 `changed` 时,pending PR 自动 reject。

**结论**:`changed` 机制只针对 `done` 节点重提。草案从未 done,草案变更不触发任何下游通知。客户端无法感知草案 v1 → v2 的变化。

#### 走查点 6:草案与正式版如何在产物仓库共存

fr1 §2.3.1(第 169-180 行)示例:

```
api_contract/
├─ 001_login-contract.yaml      # n2 v1.0.0(commit a1b2c3)
├─ 002_login-contract.yaml      # n2 v1.1.0(变更)
└─ 003_login-contract.yaml      # n2 v2.0.0(breaking)
```

`ArtifactRef` 是 `dict[str, ArtifactRef]`(node_id → 单值引用),只指向"当前生效版本"。

**结论**:若草案与正式版都要存,同一 node_id 有 draft + final 两份产物,但 ArtifactRef 单值只能指向一份。数据模型无法表达"草案 + 正式版并存"。

### 1.3 设计缺陷

| # | 缺陷 | 定位 |
|---|---|---|
| D13.1 | 状态机缺 `draft` 态,产物完成度被强制二元化(要么没提交、要么正式提交审核) | fr2 §2.1(第 59 行)、主 PRD §2(第 86 行) |
| D13.2 | 无"软提交(soft submit)"机制——提交即进 `pending_review` 即被审核,草案无法"提交但不审核" | 主 PRD §6.1 `submit_artifact`(第 744-764 行)、fr2 T5/T6(第 67-68 行) |
| D13.3 | `ArtifactRef` 单值,无法同时表达 draft + final,下游无法选择"是否接受草案依赖" | 主 PRD §5.1(第 698-705 行)、fr1 §2.3.1(第 169-180 行) |
| D13.4 | `get_dependencies` 只拉 main commit,拉不到 feat 分支草案,下游预览机制缺失 | 主 PRD §6.5(第 819-834 行) |
| D13.5 | 节点锁 TTL 12h 与草案长期持有矛盾,草案场景锁语义错位 | fr1 §5.2.1(第 784-803 行) |
| D13.6 | `changed` 机制只针对 `done` 节点,草案变更无下游通知机制 | fr2 §2.1 T10(第 72 行)、fr1 §5.3.3(第 863-871 行) |
| D13.7 | 需求 9"产物自由"未延伸到"产物完成度自由",草案/正式/废弃的产物状态未纳入状态机 | 主 PRD §1.3(第 57 行)、§1.4(第 64-72 行) |

### 1.4 修正方案

#### 修正 1:状态机新增 `draft` 态 + 软提交工具

在 7 态基础上新增 `draft` 态,作为 `ready` 的并行分支(不进 `pending_review`):

| 转移 | 触发 | Guard | 副作用 |
|---|---|---|---|
| `ready` → `draft` | `soft_submit_artifact`(新工具) | 持锁者调用;产物文件在 feat 分支存在 | 写 `draft_refs[node_id]`(新字段,指向 feat 分支 commit);发 `DRAFT_PUBLISHED` event;**不进 pending_review,不触发 cascade** |
| `draft` → `draft` | 草案 push 新 commit | 同分支 | 更新 `draft_refs[node_id].commit`;发 `DRAFT_UPDATED` event;通知订阅者 |
| `draft` → `pending_review` | `submit_artifact`(正式提交) | skill 校验通过(草案可能字段不全,正式提交必须补全) | 清 `draft_refs[node_id]`;走原 T5 转移 |
| `draft` → `ready` | `abandon_draft` | 持锁者调用 | 清 `draft_refs[node_id]`;发 `DRAFT_ABANDONED` event;释放锁 |
| `draft` → `blocked` | 上游 `changed` 递归失效 | T16 既有逻辑 | 清 `draft_refs`;草案作废 |

**关键**:`draft` 态不触发 cascade——下游不会因草案发布而自动 ready(草案不是生效产物)。下游是否用草案,由下游自己声明。

#### 修正 2:PipelineState 新增 `draft_refs` + `draft_subscribers`

```python
class PipelineState(TypedDict):
    # ... 既有字段
    draft_refs: dict[str, DraftRef]            # node_id → 草案引用(feat 分支 commit)
    draft_subscribers: dict[str, list[str]]    # node_id → 订阅下游 node_id 列表

class DraftRef(TypedDict):
    node_id: str
    repo: str
    branch: str            # feat 分支(未合并)
    path: str
    commit: str            # feat 分支最新 commit
    version: str           # 草案版本(如 0.1.0-draft,允许 0.x.y)
    stability: str         # "draft" | "preview" | "abandoned"
    published_at: str
    updated_at: str
    trace_id: str
```

#### 修正 3:get_dependencies 支持 `include_draft` 参数

```json
{
  "name": "get_dependencies",
  "inputSchema": {
    "properties": {
      "node_id": {"type": "string"},
      "include_draft": {"type": "boolean", "default": false, "description": "是否拉取上游草案(feat 分支 commit)"},
      "draft_version": {"type": "string", "description": "指定草案版本(可选)"}
    }
  }
}
```

- `include_draft=false`(默认):行为不变,拉 `artifact_refs` 的 main commit
- `include_draft=true`:若上游 `artifact_refs` 为空但 `draft_refs` 有值,拉 feat 分支 commit(git show feat 分支);返回时标记 `stability=draft`,提示"草案内容,可能变更"

#### 修正 4:草案变更通知机制

草案 push 新 commit 时,webhook 触发管理方:
1. 更新 `draft_refs[node_id].commit`
2. 查 `draft_subscribers[node_id]`,向每个订阅下游发 `DRAFT_UPDATED` event(SSE 推送 + 飞书/Slack 通知)
3. 订阅下游可选择:a) 忽略,继续用旧草案;b) 拉新草案更新本地实现;c) 取消订阅

下游通过新工具 `subscribe_draft(node_id)` / `unsubscribe_draft(node_id)` 管理订阅。

#### 修正 5:节点锁对 draft 态的语义调整

`draft` 态下锁语义改为"草案发布权"(谁发布的草案谁负责更新),TTL 可配置更长(默认 72h,因草案周期长);正式 `submit_artifact` 时锁语义回到"编辑独占权"。`abandon_draft` 主动释放锁。

#### 修正 6:ArtifactRef 增加 `stability` 字段(向后兼容)

```python
class ArtifactRef(TypedDict):
    node_id: str
    repo: str
    path: str
    commit: str
    toolspec_framework: str
    trace_id: str
    stability: str    # 新增:"stable"(默认)| "draft"(草案合并标记,极少用)
```

`artifact_refs` 仍只指向生效版本(stable);草案走独立的 `draft_refs`,不污染 `artifact_refs` 单值语义。这样既满足"草案 + 正式并存",又不破坏既有 ArtifactRef 单值约束。

### 1.5 设计图:草案产物状态机与下游预览流程

```mermaid
stateDiagram-v2
    direction TB
    [*] --> blocked : T1 bootstrap(有deps未done)
    [*] --> ready : T2 bootstrap(根节点)

    blocked --> ready : T3 cascade(deps全done)

    ready --> in_progress : T4 update_progress
    ready --> pending_review : T5 submit_artifact(正式提交)
    ready --> draft : D1 soft_submit_artifact(软提交草案)

    in_progress --> pending_review : T6 submit_artifact
    in_progress --> ready : T18 gate失败打回

    draft --> draft : D2 草案push新commit(通知订阅者)
    draft --> pending_review : D3 submit_artifact(草案转正式)
    draft --> ready : D4 abandon_draft(废弃草案)
    draft --> blocked : T16 上游changed递归失效

    pending_review --> done : T7 approve_pr合并
    pending_review --> ready : T8 reject_pr
    done --> changed : T10 重提且commit不同
    changed --> pending_review : T12 重提PR
    changed --> done : T13 变更approve合并

    note right of draft
        draft 态特性:
        · 不进 pending_review(不审核)
        · 不触发 cascade(下游不自动 ready)
        · draft_refs 独立存储(不污染 artifact_refs)
        · 下游可选订阅 DRAFT_UPDATED 事件
        · 锁 TTL 72h(草案周期长)
    end note
```

```mermaid
sequenceDiagram
    participant SA as server_agent
    participant MCP as MCP Server
    participant STATE as PipelineState
    participant CA as client_agent
    participant REPO as 产物仓库
    participant SSE as SSE 推送

    Note over SA: n2(api_contract) ready,服务端起草中
    SA->>MCP: soft_submit_artifact(n2, branch=feat/server/api_contract-001, path, version=0.1.0-draft)
    MCP->>STATE: n2 ready→draft,写 draft_refs[n2]
    MCP->>REPO: 校验 feat 分支 commit 存在(git ls-file)
    MCP-->>SA: ok, draft published, draft_ref=...

    CA->>MCP: subscribe_draft(n2)
    MCP->>STATE: draft_subscribers[n2].append(n7)
    CA->>MCP: get_dependencies(n7, include_draft=true)
    MCP->>STATE: 查 artifact_refs[n2]=空, draft_refs[n2]=有
    MCP->>REPO: git show feat分支 commit
    REPO-->>MCP: 草案内容(stability=draft)
    MCP-->>CA: [{node_id:n2, content:..., stability:draft, warning:可能变更}]
    Note over CA: 客户端基于草案搭网络层骨架

    Note over SA: 草案修改 v2(push 新 commit)
    SA->>REPO: git push feat 分支(新 commit)
    REPO->>MCP: webhook(push 事件)
    MCP->>STATE: 更新 draft_refs[n2].commit, version=0.2.0-draft
    MCP->>SSE: 推 DRAFT_UPDATED(n2) 给订阅者
    SSE->>CA: 通知:n2 草案更新到 v0.2.0
    CA->>MCP: get_dependencies(n7, include_draft=true, draft_version=0.2.0)
    MCP-->>CA: 新草案内容

    Note over SA: 草案定稿,转正式提交
    SA->>MCP: submit_artifact(n2, version=1.0.0, 正式 manifest)
    MCP->>STATE: 清 draft_refs[n2], n2 draft→pending_review
    MCP->>REPO: 开正式 PR
    Note over MCP: 走原审核流程(skill校验→approve→merge→done→cascade)
    MCP->>STATE: n2 done, artifact_refs[n2] 指向 main commit
    MCP->>SSE: 推 DONE(n2),下游 n7 cascade ready
```

---

## 2. 场景 A14:多产物仓库工作流(不同团队用不同产物仓库)

### 2.1 场景描述

**业务背景**:大公司,部门墙明显。一个跨部门 feature"统一登录"涉及服务端、设计、客户端三端,各端产物强制存在各自部门的产物仓库:

| 仓库 | git 托管 | 归属部门 | 存放产物 |
|---|---|---|---|
| repo A | GitLab 内网 | 服务端中台 | `api_contract` / `server_impl` / `server_test` |
| repo B | GitHub 企业版 | 设计中心 | `design_proto` / `design_asset` |
| repo C | GitLab 内网 | 客户端团队 | `client_ui` / `client_func` / `client_delivery` |
| repo D | GitHub 企业版 | 产品中台 | `product_spec` |

需求 6(主 PRD §1.2 第 49 行)说"产物管理通过独立 git 仓库进行",但没说"只能一个仓库"。需求 9 说产物自由定义,各端可能用不同 git 托管。

**团队诉求**:
- 各端产物留在各自部门仓库(合规、审计、网络隔离要求),不强制集中到一个仓库
- 管理方要能统一编排跨 4 个仓库的产物依赖与审核
- 服务端 agent 只能提 repo A,设计 agent 只能提 repo B——权限按仓库隔离

**关键特征**:这是大公司的现实约束,不是"要不要多仓库"的选择题,而是"必须多仓库"的客观情况。PRD 若只支持单仓库,在大公司场景直接不可用。

### 2.2 PRD 走查

#### 走查点 1:数据模型假设单仓库

主 PRD §5.1 `ArtifactRef`(第 698-705 行):

```python
class ArtifactRef(TypedDict):
    repo: str                    # 产物仓库地址
```

`repo` 是单个 string。fr1 §1.1(主 PRD 第 152-174 行)仓库结构示例只有一个 `artifact-repo/`,9 种产物类型目录都在这一个仓库下。

fr1 §2.1.1(第 87-92 行):

> 产物类型目录名必须与节点 `type` 字段完全一致……禁止在产物类型目录下建子目录

**结论**:PRD 数据模型与目录规范都假设"一个产物仓库装所有产物",4 个仓库无法用单个 ArtifactRef.repo 表达,也无法用单仓库目录结构约束。

#### 走查点 2:webhook 跨 git 托管适配缺失

主 PRD §FR6.1(第 489-497 行):

> PR 提交 → webhook 通知管理方 → 解析 PR 模板(node_id/path/deps)

fr1 §8.1.3(第 1166-1199 行)CI 配置示例只给了 GitHub Actions(`.github/workflows/artifact-ci.yml`)。

**结论**:
- GitHub webhook payload 结构、GitLab webhook payload 结构、Bitbucket webhook payload 结构**完全不同**(字段名、事件类型、签名验证方式都不同)
- PR 模板:GitHub 用 `.github/pull_request_template.md`,GitLab 用 `.gitlab/merge_request_templates/`,Bitbucket 无原生模板
- PR API:GitHub `POST /repos/{owner}/{repo}/pulls/{number}/merge`,GitLab `PUT /projects/{id}/merge_requests/{iid}/merge`,完全不同
- PRD 的 webhook 解析、PR 模板、approve_pr 合并逻辑都假设 GitHub 语义,跨托管不可用

#### 走查点 3:CI 校验跨平台不统一

fr1 §8.1.1(第 1130-1145 行)CI 检查项 CI-1~CI-11。fr1 §8.1.3 只给 GitHub Actions 示例。

**结论**:
- GitHub Actions 用 `.github/workflows/*.yml`,GitLab CI 用 `.gitlab-ci.yml`,Bitbucket 用 `bitbucket-pipelines.yml`
- fr1 §8.1.3 的 `coord-ci check` 命令是平台无关的(Python 包),但**注入到各仓库 CI 的配置语法不同**
- PRD 没有提供 GitLab CI / Bitbucket Pipelines 的配置示例,也没说"skill 约束如何翻译为各平台 CI 规则"
- 分支保护:GitHub 用 branch protection rules(UI/API),GitLab 用 protected branches(API),配置方式与 API 都不同,fr1 §1.2(第 182-190 行)只给了规则表,没说跨平台如何落地

#### 走查点 4:角色→仓库权限映射缺失

fr3-fr5 §2.4(第 228-238 行)工具权限矩阵:

> `submit_artifact`:`repo` 必须是注册的产物仓库

但"注册的产物仓库"是单数还是多数?server 能提哪些仓库?PRD 未定义角色→仓库的映射表。

**结论**:大公司场景要求 server 只能提 repo A、design 只能提 repo B。当前权限矩阵只校验 `node_type` 白名单(server → {api_contract, server_impl, server_test}),不校验"该角色能提哪个仓库"。server agent 理论上能把 server_impl 提到 repo B(设计仓库),权限越界。

#### 走查点 5:跨仓库 get_dependencies 需要 clone 多仓库

主 PRD §6.5 `get_dependencies`(第 819-834 行)`git show` 拉取上游产物内容。

n7(client_ui,在 repo C)依赖 n2(api_contract,在 repo A)+ n6(design_asset,在 repo B)。管理方要 `get_dependencies(n7)`,需要从 repo A 拉 n2、从 repo B 拉 n6——**跨 3 个仓库的 git show**。

**结论**:
- 管理方必须持有所有产物仓库的 clone/访问凭证
- 内网 GitLab(repo A/C)与外网 GitHub(repo B/D)网络隔离,管理方需同时访问两边
- PRD 假设管理方持有"产物仓库"单数访问权,多仓库场景的凭证管理、网络打通、clone 维护都未设计

#### 走查点 6:仓库注册表缺失

fr1 §2.4.3(第 228-237 行)`repo-meta.yaml` 是**单仓库内**的元数据(schema_version、directory_layout_version、node_types_supported)。

**结论**:没有"管理方管辖哪些产物仓库"的注册表。管理方启动时不知道有几个产物仓库、各自的 git 托管类型、访问凭证、webhook 端点。

### 2.3 设计缺陷

| # | 缺陷 | 定位 |
|---|---|---|
| D14.1 | 数据模型假设单仓库,`ArtifactRef.repo` 单值 string,无仓库注册表 | 主 PRD §5.1(第 698-705 行) |
| D14.2 | webhook 解析、PR 模板、PR API、approve_pr 合并逻辑都硬编码 GitHub 语义,跨 git 托管不可用 | 主 PRD §FR6.1(第 489-497 行)、§6.3(第 783-799 行)、fr1 §1.3(第 192-213 行)、§8.1.3(第 1166-1199 行) |
| D14.3 | CI 校验注入只给 GitHub Actions 示例,GitLab CI / Bitbucket Pipelines 配置与 skill 约束翻译机制缺失 | fr1 §8.1.3(第 1166-1199 行) |
| D14.4 | 分支保护规则只给规则表,跨平台落地(GitHub branch protection vs GitLab protected branches)未设计 | fr1 §1.2(第 182-190 行) |
| D14.5 | 角色→仓库权限映射缺失,agent 理论上可越权提交到非本端仓库 | fr3-fr5 §2.4(第 228-238 行) |
| D14.6 | 跨仓库 `get_dependencies` 需管理方 clone 多仓库,凭证管理、网络隔离、mirror 维护未设计 | 主 PRD §6.5(第 819-834 行) |
| D14.7 | 需求 6"独立 git 仓库"未明确"独立"是"独立于管理层"还是"各端各自独立",多仓库场景未纳入设计 | 主 PRD §1.2(第 49 行) |

### 2.4 修正方案

#### 修正 1:引入 RepoRegistry(仓库注册表)

管理方维护多产物仓库注册表,替代"单产物仓库"假设:

```yaml
# config/repo-registry.yaml
repos:
  - repo_id: repoA
    url: git@gitlab.internal:server-middleware/artifact-repo.git
    provider: gitlab          # gitlab | github | bitbucket | gitea
    network: internal         # internal | external
    credential_ref: vault://artifact/repoA   # Vault 凭证引用,不硬编码
    managed_node_types: [api_contract, server_impl, server_test]
    allowed_roles: [server]
    webhook_secret_ref: vault://webhook/repoA
    branch_protection:
      main: { require_pr: true, min_reviewers: 1, squash_merge: true }
    ci_config_path: .gitlab-ci.yml
  - repo_id: repoB
    url: git@github.com:design-center/design-artifacts.git
    provider: github
    network: external
    credential_ref: vault://artifact/repoB
    managed_node_types: [design_proto, design_asset]
    allowed_roles: [design]
    webhook_secret_ref: vault://webhook/repoB
    branch_protection:
      main: { require_pr: true, min_reviewers: 1, squash_merge: true }
    ci_config_path: .github/workflows/artifact-ci.yml
  # repoC / repoD 同理
```

`ArtifactRef.repo` 改为 `repo_id`(指向 RepoRegistry),非直接 URL:

```python
class ArtifactRef(TypedDict):
    node_id: str
    repo_id: str           # 改:指向 RepoRegistry 的 repo_id(而非裸 URL)
    path: str
    commit: str
    toolspec_framework: str
    trace_id: str
```

#### 修正 2:引入 GitProvider 抽象层

抽象出 `GitProvider` 接口,各 git 托管实现适配器,管理方只依赖接口:

```python
class GitProvider(Protocol):
    """git 托管抽象层,屏蔽 GitHub/GitLab/Bitbucket 差异"""
    def parse_webhook(self, headers: dict, body: bytes) -> WebhookEvent: ...
    def verify_webhook_signature(self, headers: dict, body: bytes, secret: str) -> bool: ...
    def get_pr_detail(self, repo_id: str, pr_id: str) -> PRDetail: ...
    def approve_pr(self, repo_id: str, pr_id: str, bot_token: str) -> None: ...
    def merge_pr(self, repo_id: str, pr_id: str, merge_method: str) -> str: ...  # 返回 merge commit
    def close_pr(self, repo_id: str, pr_id: str) -> None: ...
    def comment_pr(self, repo_id: str, pr_id: str, body: str) -> None: ...
    def set_branch_protection(self, repo_id: str, branch: str, rules: dict) -> None: ...
    def get_pr_template(self, repo_id: str) -> str | None: ...
    def ls_file_at_ref(self, repo_id: str, ref: str, path: str) -> bytes: ...   # 跨仓库 git show 统一接口

class GitHubProvider(GitProvider): ...
class GitLabProvider(GitProvider): ...
class BitbucketProvider(GitProvider): ...
```

webhook 入口按 `repo_id` 查 RepoRegistry 得 `provider`,分发到对应适配器。PR 模板解析、approve_pr 合并、分支保护都走适配器,管理方核心逻辑平台无关。

#### 修正 3:CI 注入的平台无关化

`coord-ci`(Python 包)本身平台无关,各仓库 CI 配置只负责"安装 coord-ci + 调用 check",语法按平台翻译。管理方提供**各平台 CI 配置模板**(不是只给 GitHub):

| 平台 | 配置文件 | 模板内容(核心) |
|---|---|---|
| GitHub | `.github/workflows/artifact-ci.yml` | `pip install coord-ci && coord-ci check --pr $PR` |
| GitLab | `.gitlab-ci.yml` | `pip install coord-ci && coord-ci check --mr $MR` |
| Bitbucket | `bitbucket-pipelines.yml` | `pip install coord-ci && coord-ci check --pr $PR` |

skill 约束(`review_rules`)在 `coord-ci` 内统一执行,各平台 CI 只做"触发 + 报告",不重复实现校验逻辑。`coord-ci` 输出平台无关的 JSON 报告,适配器翻译为各平台评论格式(GitHub PR comment / GitLab MR note / Bitbucket comment)。

#### 修正 4:角色→仓库权限矩阵扩展

fr3-fr5 §2.4 权限矩阵增加 `repo_id` 校验:

```python
def authorize_submit(caller_role: str, node_type: str, repo_id: str) -> bool:
    repo = repo_registry.get(repo_id)
    # 1. node_type 必须在 repo.managed_node_types 内(仓库只装特定类型产物)
    if node_type not in repo.managed_node_types:
        return False  # 如 server_impl 不能提到 repoB(设计仓库)
    # 2. caller_role 必须在 repo.allowed_roles 内(角色只能提本端仓库)
    if caller_role not in repo.allowed_roles:
        return False  # 如 design 不能提到 repoA(服务端仓库)
    # 3. 既有 node_type 白名单校验(角色→节点类型)
    if node_type not in ROLE_NODE_TYPE_WHITELIST[caller_role]:
        return False
    return True
```

#### 修正 5:跨仓库 get_dependencies 的多仓库 mirror

管理方维护所有产物仓库的**只读 mirror**(定时同步或 webhook 触发同步):

```python
class ArtifactStore:
    """多仓库产物存储,统一 git show 接口"""
    def __init__(self, repo_registry: RepoRegistry):
        self.mirrors: dict[str, str] = {}   # repo_id → 本地 mirror 路径
        for repo in repo_registry.repos:
            self.mirrors[repo.repo_id] = clone_or_update(repo)

    async def get_content(self, repo_id: str, commit: str, path: str) -> bytes:
        """跨仓库统一 git show"""
        mirror = self.mirrors[repo_id]
        return await git_show(mirror, commit, path)
```

`get_dependencies` 内部调 `ArtifactStore.get_content`,对调用方透明(不感知多仓库)。内网/外网网络隔离通过**双网卡 mirror 节点**或**网关代理**解决,管理方核心进程只访问本地 mirror。

#### 修正 6:明确需求 6"独立"语义

建议主 PRD §1.2 修正为:

> 产物管理通过**独立于管理层的** git 仓库进行(管理方不持有产物内容,只持有引用)。支持**单仓库或多仓库**;各端可按组织约束使用不同 git 托管(GitHub/GitLab/Bitbucket),管理方通过 RepoRegistry 统一管辖。

### 2.5 设计图:多产物仓库架构

```mermaid
graph TB
    subgraph MGMT["管理方(Coordination Platform)"]
        REG[RepoRegistry<br/>config/repo-registry.yaml]
        GP[GitProvider 抽象层]
        GH[GitHubProvider]
        GL[GitLabProvider]
        BB[BitbucketProvider]
        AS[ArtifactStore<br/>多仓库 mirror]
        SK[Skill 校验 + 规则引擎]
        LG[LangGraph 编排]
    end

    subgraph REPOS["产物仓库(多 git 托管)"]
        RA[repoA<br/>GitLab 内网<br/>server 产物]
        RB[repoB<br/>GitHub 企业版<br/>design 产物]
        RC[repoC<br/>GitLab 内网<br/>client 产物]
        RD[repoD<br/>GitHub 企业版<br/>product 产物]
    end

    subgraph AGENTS["角色 Agent(权限按仓库隔离)"]
        PA[product_agent<br/>只能提 repoD]
        SA[server_agent<br/>只能提 repoA]
        DA[design_agent<br/>只能提 repoB]
        CA[client_agent<br/>只能提 repoC]
    end

    REG --> GP
    GP --> GH
    GP --> GL
    GP --> BB
    GH -.-> RB
    GH -.-> RD
    GL -.-> RA
    GL -.-> RC
    BB -.-> REPOS

    RA & RB & RC & RD -->|webhook(各平台 payload)| GP
    GP -->|解析为统一 WebhookEvent| SK
    SK --> LG

    AS -->|clone/sync| RA
    AS -->|clone/sync| RB
    AS -->|clone/sync| RC
    AS -->|clone/sync| RD
    LG -->|get_dependencies<br/>跨仓库 git show| AS

    PA & SA & DA & CA -->|submit_artifact<br/>repo_id 校验| SK
    SK -->|权限校验:role↔repo↔node_type| REG

    style REG fill:#a371f7,color:#fff
    style GP fill:#4a8ad6,color:#fff
    style AS fill:#3fb950,color:#fff
    style SK fill:#e3b341,color:#fff
```

```mermaid
sequenceDiagram
    participant SA as server_agent
    participant MCP as MCP Server
    participant REG as RepoRegistry
    participant GL as GitLabProvider
    participant RA as repoA(GitLab)
    participant AS as ArtifactStore
    participant CA as client_agent

    Note over SA: n2(api_contract) ready,提交到 repoA
    SA->>MCP: submit_artifact(n2, repo_id=repoA, branch, path)
    MCP->>REG: 查 repoA: provider=gitlab, allowed_roles=[server], managed_types=[api_contract,...]
    REG-->>MCP: 校验:server∈allowed_roles ✓, api_contract∈managed_types ✓
    MCP->>GL: 推 feat 分支 + 开 MR(GitLab 用 MR 非 PR)
    GL->>RA: 创建 MR !42
    RA->>MCP: webhook(GitLab MR payload)
    MCP->>GL: parse_webhook → 统一 WebhookEvent
    MCP->>MCP: skill 校验 + 规则引擎
    MCP->>GL: approve + merge(MR !42)
    GL->>RA: squash merge,返回 merge_commit
    MCP->>AS: 触发 repoA mirror 同步
    MCP-->>SA: ok, n2 done

    Note over CA: n7(client_ui) 依赖 n2(repoA) + n6(repoB),跨仓库拉取
    CA->>MCP: get_dependencies(n7)
    MCP->>AS: get_content(repoA, n2.commit, n2.path) + get_content(repoB, n6.commit, n6.path)
    AS->>AS: 从本地 mirror git show(不直连远端)
    AS-->>MCP: n2 内容 + n6 内容
    MCP-->>CA: [{n2, content}, {n6, content}]
```

---

## 3. 场景 A15:产物引用同一仓库(代码仓库和产物仓库合一)

### 3.1 场景描述

**业务背景**:小团队(5 人创业公司),做一个 feature"用户资料页"。团队不想维护两个仓库(代码仓库 + 产物仓库),想把产物存到代码仓库的 `docs/` 目录,代码和产物在一起:

```
team-app/                          # 代码仓库(唯一仓库)
├─ src/                            # 代码
│  ├─ api/
│  ├─ ui/
│  └─ ...
├─ docs/                           # 产物存放处
│  ├─ product_spec/
│  │  └─ 001.yaml
│  ├─ api_contract/
│  │  └─ 001.yaml
│  ├─ design_asset/
│  │  └─ 001_figma.json
│  └─ ...
├─ .github/
│  ├─ workflows/
│  │  ├─ code-ci.yml              # 代码 CI(lint/test/build)
│  │  └─ artifact-ci.yml          # 产物 CI(coord-ci)
│  └─ pull_request_template.md
└─ README.md
```

需求 6(主 PRD §1.2 第 49 行)说"产物管理通过独立 git 仓库进行",但需求 9(§1.3 第 57 行)说"产物格式中立、通用性"。小团队认为"独立"应理解为"独立于管理层"(管理方不持有内容),而非"必须与代码仓库物理分离"。

**团队诉求**:
- 代码和产物在同一仓库,PR 能同时改代码和产物(如改 API 实现同时更新 api_contract)
- 管理方只审核 `docs/` 下的产物 PR,不审核 `src/` 下的代码 PR(代码 PR 走团队自己的 code review)
- 分支保护规则:产物路径用管理方规则(1 个 bot approve),代码路径用团队规则(2 个人工 review + 代码 CI)

**关键特征**:这是需求 6 与需求 9 的边界冲突。产物仓库"独立"是硬性约束还是建议?若硬性,小团队被迫维护两个仓库,违反需求 9 的灵活性;若建议,则混合仓库的审核边界、webhook 过滤、分支保护叠加都需要设计。

### 3.2 PRD 走查

#### 走查点 1:需求 6"独立"语义模糊

主 PRD §1.2(第 49 行):

> 产物管理:通过独立 git 仓库管理所有产物内容,管理方只持有引用

主 PRD §1.4(第 64-72 行)范围边界:

> 产物仓库的分支保护 + PR 审核(做什么) | 不限制开发方用什么工具产出内容(不做什么)

fr1 §1.2(第 64-69 行)"不变的核心原则":

> 产物内容存独立 git 仓库,管理方只存引用(repo + path + commit)

**结论**:PRD 反复强调"独立 git 仓库",但"独立"的语义有两种解读:
- 解读 A(物理独立):产物仓库与代码仓库物理分离,两个仓库
- 解读 B(逻辑独立):产物内容独立于管理层(管理方不持有内容),存放位置可以是独立仓库或代码仓库子目录

PRD 未明确哪种。若解读 A,小团队场景被排除;若解读 B,则混合仓库的审核边界、CI、分支保护都需要设计,但 PRD 完全没涉及。

#### 走查点 2:webhook 没有路径过滤

主 PRD §FR6.1(第 489-497 行):

> PR 提交 → webhook 通知管理方 → 解析 PR 模板(node_id/path/deps)

fr1 §8.1.3(第 1166-1199 行)GitHub Actions 配置有 `paths` 过滤:

```yaml
on:
  pull_request:
    paths:
      - 'product_spec/**'
      - 'api_contract/**'
      # ... 9 种产物类型目录
```

但这是 **CI 触发过滤**,不是 **webhook 过滤**。管理方 webhook 收到的是整个仓库的所有 PR 事件(除非在 GitHub 侧配置 webhook 的 path 过滤,但 GitHub webhook 原生不支持 path 过滤,只有 CI 的 paths 过滤)。

**结论**:混合仓库下,代码 PR(改 `src/`)也会触发管理方 webhook,管理方会尝试解析代码 PR 的"PR 模板"(找不到 node_id)、走 skill 校验(失败)、reject——这是误伤。PRD 没有"管理方只处理产物路径下 PR"的过滤机制。

#### 走查点 3:CI 目录白名单冲突

fr1 §8.1.1(第 1130-1145 行)CI-1:

> 目录白名单:修改的目录在 9 种产物类型 + `manifests/` 内 → CI fail 若违反

fr1 §2.1.1(第 87-92 行):

> 不允许出现未在 9 种产物类型之外的目录(CI 阻断)

**结论**:混合仓库下,代码 PR 改 `src/` 目录,会触发 CI-1 "目录白名单"失败(因 `src/` 不在 9 种产物类型内)。PRD 的 CI 白名单假设仓库**只有产物目录**,混合仓库下白名单会误伤所有代码 PR。

#### 走查点 4:分支保护规则无法 per-path 叠加

fr1 §1.2(第 182-190 行)分支保护:

| 规则 | 配置 |
|---|---|
| main 分支 | 禁止直接 push,只接受 PR 合并 |
| PR 审核 | 至少 1 个管理方 bot approve |
| CI 校验 | manifest schema + skill 约束 |
| 合并方式 | squash merge |

**结论**:GitHub/GitLab 的分支保护是**仓库级**或**branch 级**的,不支持"per-path 不同规则"(如 `docs/` 要 1 bot approve、`src/` 要 2 人工 review)。混合仓库下,若仓库级要求"1 bot approve",代码 PR 也只需 1 bot approve(太松);若要求"2 人工 review",产物 PR 也要 2 人工 review(太严,违反 fr1 §1.2"至少 1 个管理方 bot approve"的自动审核设计)。

#### 走查点 5:ArtifactRef.path 限定在产物类型目录

fr1 §3.3 manifest schema `source.path`(第 346-354 行):

```json
"path": {
  "pattern": "^[a-z_]+/[0-9]{3}[_a-z0-9-]*\\.(yaml|yml|json|md|mdx)$"
}
```

**结论**:正则要求 path 形如 `api_contract/001_xxx.yaml`(产物类型目录开头)。混合仓库下产物在 `docs/api_contract/001.yaml`,前缀多了 `docs/`,不匹配正则。PRD 的 path 约束假设产物在仓库根的产物类型目录下,混合仓库需要 `docs/` 前缀。

#### 走查点 6:管理方审核边界未声明

PRD 全文假设"管理方审核该仓库的所有产物 PR",但没有"管理方管辖哪些路径"的声明机制。

**结论**:混合仓库下,管理方需要声明"我只管 `docs/` 下的 PR,`src/` 的 PR 不归我管"。PRD 没有这个声明机制,管理方默认接管整个仓库的所有 PR,与代码 PR 的团队 review 流程冲突。

### 3.3 设计缺陷

| # | 缺陷 | 定位 |
|---|---|---|
| D15.1 | 需求 6"独立 git 仓库"的"独立"语义模糊(物理独立 vs 逻辑独立),混合仓库场景被排除或未设计 | 主 PRD §1.2(第 49 行)、fr1 §1.2(第 64-69 行) |
| D15.2 | webhook 无路径过滤,混合仓库下代码 PR 会误触发管理方审核 | 主 PRD §FR6.1(第 489-497 行) |
| D15.3 | CI 目录白名单假设仓库只有产物目录,混合仓库下代码 PR 会被 CI-1 误伤 | fr1 §8.1.1 CI-1(第 1134 行)、fr1 §2.1.1(第 87-92 行) |
| D15.4 | 分支保护规则是仓库级,不支持 per-path 叠加(产物路径 vs 代码路径规则冲突) | fr1 §1.2(第 182-190 行) |
| D15.5 | `ArtifactRef.path` 正则限定产物类型目录开头,混合仓库的 `docs/` 前缀不匹配 | fr1 §3.3(第 346-354 行) |
| D15.6 | 管理方审核边界未声明,无"管辖路径"配置,默认接管整个仓库所有 PR | 主 PRD §FR6(第 483-568 行)整体 |
| D15.7 | 需求 6 与需求 9 在混合仓库场景直接冲突,PRD 未调和 | 主 PRD §1.2(第 49 行)vs §1.3(第 57 行) |

### 3.4 修正方案

#### 修正 1:明确"独立"语义 + 引入 RepoType

主 PRD §1.2 修正为:

> 产物管理通过**独立于管理层**的 git 仓库进行(管理方不持有产物内容,只持有引用)。仓库形态有两种:
> - **artifact-only 仓库**:仓库只装产物(默认,适合大团队/跨部门)
> - **hybrid 仓库**:代码与产物同仓(产物在指定子目录,适合小团队)
>
> 仓库类型由 RepoRegistry 声明,管理方按类型应用不同的审核边界与 CI 规则。

RepoRegistry 增加 `repo_type` 与 `managed_paths`:

```yaml
# config/repo-registry.yaml
repos:
  - repo_id: team-app
    url: git@github.com:team/team-app.git
    provider: github
    repo_type: hybrid            # artifact-only | hybrid
    managed_paths:               # 管理方管辖路径(hybrid 必填)
      - "docs/**"
    managed_node_types: [product_spec, api_contract, design_asset, ...]
    allowed_roles: [product, server, design, client]   # 小团队同仓库多角色
    # artifact-only 仓库:managed_paths 留空(整仓管辖)
```

#### 修正 2:webhook 路径过滤(管理方侧)

管理方 webhook 收到 PR 事件后,先按 `managed_paths` 过滤:

```python
def should_manage_pr(repo: RepoConfig, pr_files: list[str]) -> bool:
    """判断管理方是否应接管该 PR"""
    if repo.repo_type == "artifact-only":
        return True   # 整仓管辖
    # hybrid:只接管触及 managed_paths 的 PR
    for f in pr_files:
        for pattern in repo.managed_paths:
            if fnmatch(f, pattern):
                return True
    return False   # 纯代码 PR,管理方不接管
```

纯代码 PR(不触及 `docs/`)管理方不接管,直接忽略 webhook,不触发审核、不 reject、不评论——避免误伤。

混合 PR(同时改 `src/` 和 `docs/`)管理方只审核 `docs/` 部分的产物,`src/` 部分留给团队 code review(管理方对代码内容不解析,本就不关心)。

#### 修正 3:CI 目录白名单按 repo_type 区分

```python
def ci_directory_whitelist(repo: RepoConfig) -> list[str]:
    if repo.repo_type == "artifact-only":
        # 既有逻辑:9 种产物类型 + manifests/
        return NINE_ARTIFACT_TYPES + ["manifests/"]
    # hybrid:产物类型目录前缀 managed_paths + 允许代码目录
    product_dirs = [f"docs/{t}/" for t in NINE_ARTIFACT_TYPES]
    code_dirs = ["src/", "tests/", "config/"]   # 代码目录白名单(不归 CI-1 管)
    return product_dirs + code_dirs + ["manifests/"]
```

CI-1 校验逻辑调整:hybrid 仓库下,产物文件必须在 `docs/<产物类型>/` 下,代码文件必须在代码目录白名单内,二者都不在则 CI fail。

#### 修正 4:分支保护 per-path overlay

利用 GitHub 的 **rulesets**(2023+ 支持 path-based rules)或 GitLab 的 **push rules**(路径级),实现 per-path 规则叠加:

```yaml
# hybrid 仓库分支保护
branch_protection:
  main:
    base_rules:                    # 仓库级基础规则(所有 PR)
      require_pr: true
      squash_merge: true
    path_overlays:                 # 路径级叠加规则
      - paths: ["docs/**"]
        rules:
          min_reviewers: 1
          required_reviewer: mgmt-bot   # 产物 PR 需管理方 bot approve
          required_ci: [artifact-ci]
      - paths: ["src/**", "tests/**"]
        rules:
          min_reviewers: 2               # 代码 PR 需 2 人工 review
          required_ci: [code-ci]
          disallow_bot_review: true      # 代码 PR 不接受 bot review
```

GitProvider 适配器负责将 `path_overlays` 翻译为各平台原生配置(GitHub rulesets / GitLab push rules)。不支持 path-based rules 的旧平台降级为"仓库级统一规则 + 管理方 webhook 侧路径过滤兜底"。

#### 修正 5:ArtifactRef.path 正则支持 managed_paths 前缀

manifest schema `source.path` 正则放宽,支持可选前缀:

```json
"path": {
  "pattern": "^(docs/)?[a-z_]+/[0-9]{3}[_a-z0-9-]*\\.(yaml|yml|json|md|mdx)$"
}
```

或更通用地,正则从 RepoRegistry 的 `managed_paths` 动态生成:

```python
def path_regex(repo: RepoConfig) -> str:
    prefix = repo.managed_paths[0].replace("/**", "/")  # "docs/**" → "docs/"
    return f"^{prefix}[a-z_]+/[0-9]{{3}}[_a-z0-9-]*\\.(yaml|yml|json|md|mdx)$"
```

#### 修正 6:管理方审核边界显式声明

RepoRegistry 每个仓库声明 `managed_paths`,管理方启动时加载并据此过滤 webhook。Dashboard 展示每个仓库的"管辖路径",让 admin 明确管理方管什么、不管什么。审计日志记录"该 PR 因触及 managed_paths 被接管/因未触及被忽略",可追溯。

### 3.5 设计图:代码产物合一的审核边界

```mermaid
flowchart TD
    PR["代码仓库收到 PR<br/>(team-app repo)"]
    PR --> FILES[获取 PR 修改文件列表]
    FILES --> FILTER{管理方路径过滤<br/>should_manage_pr}

    FILTER -->|纯代码 PR<br/>只改 src/| IGNORE[管理方忽略<br/>不触发审核<br/>不评论不 reject]
    IGNORE --> TEAM[团队 code review 流程<br/>2 人工 review + code-ci]

    FILTER -->|纯产物 PR<br/>只改 docs/| MGMT[管理方接管<br/>skill 校验 + 规则引擎]
    MGMT --> MERGE1[bot approve + squash merge<br/>触发 LangGraph set_done + cascade]

    FILTER -->|混合 PR<br/>改 src/ + docs/| SPLIT[管理方只审 docs/ 部分<br/>src/ 部分留给团队]
    SPLIT --> MGMT
    SPLIT --> TEAM
    SPLIT --> COORD[协调:产物部分 merge 需等<br/>代码部分 review 通过?<br/>见下方策略]

    subgraph STRATEGY["混合 PR 合并策略(可配置)"]
        S1[策略 A:产物与代码独立合并<br/>产物部分走 bot merge<br/>代码部分走人工 merge]
        S2[策略 B:产物等代码<br/>产物 merge 阻塞至代码 review 通过<br/>避免产物先合代码后改]
    end

    COORD --> STRATEGY

    style IGNORE fill:#6e7681,color:#fff
    style MGMT fill:#4a8ad6,color:#fff
    style MERGE1 fill:#3fb950,color:#fff
    style SPLIT fill:#e3b341,color:#fff
```

```mermaid
graph LR
    subgraph REPO["hybrid 仓库(team-app)"]
        SRC[src/<br/>代码]
        DOCS[docs/<br/>产物]
        CI_CODE[.github/workflows/code-ci.yml]
        CI_ART[.github/workflows/artifact-ci.yml]
    end

    subgraph BRANCH["main 分支保护(per-path overlay)"]
        BASE[基础规则<br/>require_pr + squash_merge]
        OV1[docs/ overlay<br/>1 bot approve + artifact-ci]
        OV2[src/ overlay<br/>2 人工 review + code-ci<br/>disallow bot]
    end

    subgraph MGMT["管理方"]
        REG[RepoRegistry<br/>repo_type=hybrid<br/>managed_paths=docs/**]
        FILTER[webhook 路径过滤]
        SK[skill 校验]
    end

    SRC --> OV2
    DOCS --> OV1
    OV1 --> SK
    OV2 -.->|不归管理方| TEAM[团队 review]
    DOCS --> CI_ART
    SRC --> CI_CODE

    REPO -->|webhook(所有 PR)| FILTER
    FILTER -->|触及 docs/| SK
    FILTER -->|不触及 docs/| IGNORE[管理方忽略]
    REG --> FILTER

    style OV1 fill:#4a8ad6,color:#fff
    style OV2 fill:#3fb950,color:#fff
    style FILTER fill:#e3b341,color:#fff
    style IGNORE fill:#6e7681,color:#fff
```

---

## 4. 场景 A16:管线模板复用(多个类似 feature 用同一管线模板)

### 4.1 场景描述

**业务背景**:某产品团队复盘过去半年的 30 个 feature,发现 **80% 的 feature 都走"标准流程"**:

```
product_spec → api_contract → design_proto → design_asset → server_impl → client_ui → client_func → client_delivery
```

每个 feature 新建时,都要手写一遍 `pipeline.yaml`(8 个节点 + 7 条依赖边 + 各节点 role/type/deps),重复且易错:

- 节点 id 要重新编(n1-n8)
- 依赖关系要重新声明
- 偶尔漏掉某个依赖边(如忘声明 client_ui 依赖 design_asset),导致下游不阻塞、联调才发现
- 不同 feature 的管线"应该一样但实际有细微差异"(人为失误)

**团队诉求**:
- 定义"标准流程模板",新 feature 实例化模板即可,只填 feature 特有参数(如 approver 是谁、gate 的 coverage_min 阈值)
- 某些 feature 不需要全套(如纯后端 feature 不需要 design_proto/design_asset/client_ui),模板支持"裁剪"
- 模板升级了(如标准流程新增 `security_review` 节点),已实例化的管线要不要同步更新?
- 跨团队共享模板(如设计团队的"设计交付标准流程"模板),怎么管理?

**关键特征**:主 PRD §1.3(第 57 行)宣称"通用性:覆盖服务端/客户端/UI 设计全流程"——但"通用性"靠什么机制实现?PRD 没有管线模板抽象,每个 `pipeline.yaml` 都是独立的,通用性只是"理论上能描述任意流程",而非"提供标准流程的复用机制"。这是"纸上谈兵"的典型:声称通用,实则无复用机制。

### 4.2 PRD 走查

#### 走查点 1:无管线模板抽象

主 PRD §5.1 `Pipeline`(第 664-693 行):

```yaml
pipeline:
  id: "login-feature"
  name: "登录功能全链路"
  nodes:
    - id: "n1"
      type: "product_spec"
      role: "product"
      deps: []
    # ... 8 个节点逐个声明
  edges: []  # 由 deps 推导
```

fr2 §7.1(第 730-758 行)管线加载流程:`读取 pipeline.yaml → 解析 YAML → Pipeline 对象 → DAG 校验 → 构建 StateGraph`。

**结论**:每个 `pipeline.yaml` 是完全独立的声明,无 `extends` / `template` 字段。30 个 feature 要写 30 份几乎一样的 pipeline.yaml,无复用机制。

#### 走查点 2:pipeline.yaml 无继承/参数化机制

fr2 §7.5(第 813-827 行)热重载:

> `pipeline.yaml` 进 git,webhook 触发重载。重载用新 `pipeline_id`(版本化,如 `login-feature@v2`)。

**结论**:
- pipeline.yaml 是静态声明,节点 id / type / role / deps 全部硬编码
- 无参数化:approval 节点的 `approver`、gate 节点的 `policy.coverage_min` 每个 feature 都要手填,无法用 `${param}` 占位
- 无继承:无法 `extends: standard-pipeline-template` 后只覆盖差异(如裁剪 design 节点)

#### 走查点 3:模板版本化与实例化管线关系未定义

fr2 §7.5(第 820-822 行):

> 修改 deps:pipeline.yaml git push → 重新校验无环 → 重新计算下游 ready 状态 → 发 DEPS_CHANGED event

fr2 §7.5(第 825-827 行):

> 重载用新 `pipeline_id`(版本化,如 `login-feature@v2`),旧 pipeline_id 继续运行至完成或手动迁移

**结论**:PRD 的"版本化"是**单管线实例**的版本化(login-feature@v1 → @v2),不是**模板**的版本化。模板升级(standard-template@v1 → @v2)后,已用 v1 实例化的 30 个管线要不要同步升级?PRD 无此机制。若强制同步,可能破坏运行中管线;若不同步,模板升级只对新 feature 生效,旧 feature 用旧模板,长期分化。

#### 走查点 4:模板存储位置未定义

fr1 §2.4.3(第 228-237 行)`repo-meta.yaml` 是产物仓库元数据。主 PRD §5.2(第 730-738 行)存储方案:

| 数据 | 存储 |
|---|---|
| Constraint Skills | 文件系统(skills/ 目录) |
| 产物内容 | 产物仓库(git) |

**结论**:管线模板存哪?PRD 没有"模板仓库"或"模板目录"的设计。若存管理方仓库的 `templates/` 目录,模板变更走管理方 PR(人工评审);若存产物仓库,与产物混在一起。PRD 未定义。

#### 走查点 5:模板审核机制缺失

fr1 §FR6(第 483-568 行)审核机制只针对**产物 PR**。模板本身不是产物(不对应任何 node_type),不进 skill 校验流程。

**结论**:模板错了(如标准流程漏了 client_ui 对 design_asset 的依赖),所有实例化的管线都错。模板变更无审核机制,admin 改模板直接生效,风险高。模板应该有审核 + dry-run 校验(用模板实例化一个测试管线,跑一遍校验)。

#### 走查点 6:跨团队模板共享未设计

需求 1(主 PRD §1.3 第 57 行)"通用性"暗示跨团队复用,但 PRD 无团队级模板隔离/共享机制。

**结论**:设计团队有自己的"设计交付标准流程"模板(只含 design_proto → design_asset → handoff),客户端团队有"客户端交付标准流程"模板。模板如何跨团队共享?权限?版本?PRD 未设计。

#### 走查点 7:模板裁剪机制缺失

标准流程 8 节点,纯后端 feature 不需要 design_proto/design_asset/client_ui。PRD 无"模板裁剪"机制——只能手写裁剪后的 pipeline.yaml,又回到"重复且易错"的问题。

### 4.3 设计缺陷

| # | 缺陷 | 定位 |
|---|---|---|
| D16.1 | 无管线模板抽象,每个 pipeline.yaml 独立,通用性(需求 1)无复用机制支撑 | 主 PRD §1.3(第 57 行)、§5.1(第 664-693 行) |
| D16.2 | pipeline.yaml 无继承(`extends`)与参数化(`${param}`)机制 | fr2 §7.1(第 730-758 行) |
| D16.3 | 模板版本化与实例化管线的关系未定义(模板升级是否同步到实例) | fr2 §7.5(第 813-827 行) |
| D16.4 | 模板存储位置未定义(管理方仓库 / 产物仓库 / 独立模板仓库) | 主 PRD §5.2(第 730-738 行) |
| D16.5 | 模板审核机制缺失,模板变更无 skill 校验 + dry-run,错模板级联影响所有实例 | 主 PRD §FR6(第 483-568 行) |
| D16.6 | 跨团队模板共享与权限未设计 | 主 PRD §1.3(第 57 行) |
| D16.7 | 模板裁剪机制缺失(标准流程裁剪为子流程)缺失 | fr2 §7.1(第 730-758 行) |
| D16.8 | fr2 §7 管线加载校验无"模板实例化后的校验"(模板本身可能非法) | fr2 §7.6(第 829-843 行) |

### 4.4 修正方案

#### 修正 1:引入 PipelineTemplate 抽象

```yaml
# templates/standard-fullstack.yaml
name: standard-fullstack
version: "1.2.0"
description: 全栈 feature 标准流程模板(8 节点)
author: platform-team

# 参数定义(实例化时填充)
parameters:
  - name: approver_contract
    type: string
    description: api_contract 审批人
    required: true
  - name: approver_delivery
    type: string
    description: client_delivery 审批人
    required: true
  - name: coverage_min
    type: integer
    default: 80
    description: gate 覆盖率阈值
  - name: skip_design
    type: boolean
    default: false
    description: 是否裁剪设计节点(纯后端 feature)

# 节点骨架(id 用占位符,实例化时按序号生成)
nodes:
  - id: "${seq.product}"
    type: product_spec
    role: product
    deps: []
  - id: "${seq.contract}"
    type: api_contract
    role: server
    deps: ["${seq.product}"]
  - id: "${seq.proto}"
    type: design_proto
    role: design
    deps: ["${seq.product}"]
    condition: "${not skip_design}"    # 条件节点:skip_design=true 时裁剪
  - id: "${seq.asset}"
    type: design_asset
    role: design
    deps: ["${seq.proto}"]
    condition: "${not skip_design}"
  - id: "${seq.impl}"
    type: server_impl
    role: server
    deps: ["${seq.contract}"]
  - id: "${seq.ui}"
    type: client_ui
    role: client
    deps: ["${seq.contract}", "${seq.asset}"]
    condition: "${not skip_design}"
    deps_dynamic: "${skip_design ? [contract] : [contract, asset]}"  # 裁剪时依赖收缩
  - id: "${seq.func}"
    type: client_func
    role: client
    deps: ["${seq.ui}", "${seq.impl}"]
  - id: "${seq.delivery}"
    type: client_delivery
    role: client
    deps: ["${seq.func}"]
  # 控制节点
  - id: "${seq.gate}"
    type: gate
    role: control
    deps: ["${seq.impl}"]
    policy: { lint: true, test: true, coverage_min: "${coverage_min}" }
  - id: "${seq.approval}"
    type: approval
    role: control
    deps: ["${seq.delivery}"]
    approver: "${approver_delivery}"
```

#### 修正 2:pipeline.yaml 支持 extends + override

```yaml
# pipelines/login-feature.yaml
extends: standard-fullstack@1.2.0       # 继承模板(锁定版本)
id: login-feature
name: 登录功能全链路

# 实例化参数
parameters:
  approver_contract: reviewer-alice
  approver_delivery: reviewer-bob
  coverage_min: 85                       # 本 feature 收紧覆盖率
  skip_design: false

# 覆盖差异(可选)
overrides:
  - node_id: "${seq.approval}"
    approver: reviewer-carol             # 本 feature 换审批人
  - add_node:                            # 本 feature 新增安全审查节点
      id: n_sec
      type: approval
      role: control
      deps: ["${seq.contract}"]
      approver: security-team
  - insert_edge:                         # 在 contract done 后插入 n_sec
      from: "${seq.contract}"
      to: "n_sec"
      before: "${seq.impl}"              # n_sec done 后才 impl
```

实例化流程:
1. 加载 `extends` 指向的模板(锁定版本 `@1.2.0`)
2. 用 `parameters` 填充模板参数占位符
3. 按 `condition` 裁剪节点(skip_design=true 时移除 design 节点)
4. 应用 `overrides`(覆盖节点配置、新增节点、插入边)
5. 生成最终的 `pipeline.yaml`(展开后的、无占位符的、可直接加载的)
6. 走 fr2 §7 既有管线加载校验(DAG 无环、引用完整等)

实例化后的 pipeline.yaml 缓存到管理方,运行时加载的是展开后的版本(模板变更不影响已实例化管线,见修正 3)。

#### 修正 3:模板版本化与实例化管线的关系

| 策略 | 行为 | 适用场景 |
|---|---|---|
| **锁定版本**(默认) | pipeline.yaml `extends: template@1.2.0`,实例化后锁定 1.2.0,模板升级不影响已实例化管线 | 生产环境,稳定性优先 |
| **浮动版本**(可选) | `extends: template@^1.0`(semver range),模板 PATCH/MINOR 升级时,新实例化的管线用新版 | 开发环境,跟进模板修复 |
| **显式升级** | admin 调 `upgrade_pipeline(pipeline_id, to_template_version)` 命令,重新实例化 + 校验 + 迁移 state | 已实例化管线主动升级模板 |

模板 MAJOR 升级(不向后兼容)**永不自动同步**到已实例化管线,必须显式升级 + 人工确认。

#### 修正 4:模板存储与审核

模板存管理方仓库的 `templates/` 目录,走管理方 PR 审核:

```
coordination-platform/
├─ templates/
│  ├─ standard-fullstack.yaml
│  ├─ standard-backend.yaml          # 纯后端模板(裁剪 design/client)
│  ├─ standard-design-handoff.yaml   # 设计交付模板
│  └─ ...
├─ skills/
├─ crew/
└─ ...
```

模板 PR 审核流程(新增):
1. **语法校验**:模板 YAML 符合 PipelineTemplate schema(参数定义、节点骨架、condition 合法)
2. **dry-run 实例化**:用测试参数实例化模板,生成测试 pipeline.yaml,走 fr2 §7.6 加载校验清单(DAG 无环、引用完整、控制节点配置合法)
3. **diff 评估**:模板变更时,自动实例化一个 dry-run 管线,与旧版本实例化结果 diff,评估影响(新增/删除/改了哪些节点)
4. **admin 审核**:模板 MAJOR 升级需 admin 人工审核 + 签名
5. **影响面告知**:模板 PR 评论列出"该模板被 N 个管线实例化使用",提示影响面

模板审核不进 skill 校验(模板不是产物,无 node_type),走独立的 `template-review-ci`。

#### 修正 5:跨团队模板共享与权限

```yaml
# templates/standard-design-handoff.yaml
name: standard-design-handoff
version: "1.0.0"
owner_team: design-center          # 模板归属团队
visibility: shared                 # private(仅本团队) | shared(全组织共享)
allowed_consumer_teams: [client-team, product-team]   # shared 时可限制消费方
```

模板权限:
- `private`:仅 owner_team 可实例化
- `shared`:allowed_consumer_teams 内的团队可实例化;留空则全组织可实例化
- 模板变更需 owner_team 审核;消费团队只能"用",不能"改"
- 模板废弃(`deprecated: true`)后,新管线不可实例化,已实例化管线继续运行

#### 修正 6:模板裁剪机制(condition + deps_dynamic)

模板节点支持 `condition` 字段(布尔表达式),实例化时按参数求值:
- `condition: false` 的节点被裁剪
- 被裁剪节点的下游 `deps` 自动收缩(通过 `deps_dynamic` 表达式重新计算依赖)
- 裁剪后重新校验 DAG 无环(裁剪可能产生孤立节点或断链)

fr2 §7.1 加载流程增加"模板实例化 + 裁剪"步骤,在 DAG 校验前完成。

### 4.5 设计图:管线模板继承与实例化

```mermaid
flowchart TD
    subgraph TEMPLATES["模板仓库(templates/)"]
        T1[standard-fullstack@1.2.0<br/>8 节点全栈模板]
        T2[standard-backend@1.0.0<br/>纯后端模板(裁剪 design/client)]
        T3[standard-design-handoff@1.0.0<br/>设计交付模板]
    end

    subgraph INSTANCE["实例化流程"]
        EXT[读取 pipeline.yaml<br/>extends: standard-fullstack@1.2.0]
        PARAM[填充 parameters<br/>approver/coverage_min/skip_design]
        COND[求值 condition<br/>裁剪节点]
        OVERRIDE[应用 overrides<br/>覆盖/新增/插边]
        EXPAND[展开为最终 pipeline.yaml<br/>无占位符]
        VALIDATE[fr2 §7.6 加载校验<br/>DAG 无环/引用完整/控制节点]
    end

    subgraph PIPELINES["实例化管线(运行时)"]
        P1[login-feature<br/>基于 standard-fullstack@1.2.0]
        P2[user-profile<br/>基于 standard-fullstack@1.2.0<br/>skip_design=false]
        P3[batch-job<br/>基于 standard-backend@1.0.0<br/>纯后端]
        P4[icon-refresh<br/>基于 standard-design-handoff@1.0.0]
    end

    T1 --> EXT
    EXT --> PARAM
    PARAM --> COND
    COND --> OVERRIDE
    OVERRIDE --> EXPAND
    EXPAND --> VALIDATE
    VALIDATE -->|通过| P1
    VALIDATE -->|失败| FAIL[拒绝加载<br/>error: TEMPLATE_INVALID]

    T1 -.-> P2
    T2 -.-> P3
    T3 -.-> P4

    subgraph UPGRADE["模板升级策略"]
        U1[锁定版本<br/>extends: tmpl@1.2.0<br/>模板升级不影响实例]
        U2[浮动版本<br/>extends: tmpl@^1.0<br/>PATCH/MINOR 自动跟进]
        U3[显式升级<br/>upgrade_pipeline cmd<br/>重新实例化+迁移 state]
        U4[MAJOR 升级<br/>永不自动同步<br/>必须人工确认]
    end

    TEMPLATES -.-> UPGRADE

    style T1 fill:#a371f7,color:#fff
    style EXPAND fill:#4a8ad6,color:#fff
    style VALIDATE fill:#3fb950,color:#fff
    style FAIL fill:#b3261e,color:#fff
    style UPGRADE fill:#e3b341,color:#fff
```

```mermaid
sequenceDiagram
    participant DEV as 开发者
    participant MGMT as 管理方
    participant TREG as TemplateRegistry
    participant INST as 实例化引擎
    participant VAL as fr2 管线校验
    participant LG as LangGraph

    Note over DEV: 新建 feature,基于标准模板
    DEV->>MGMT: 提交 pipeline.yaml(extends: standard-fullstack@1.2.0, parameters: {...})
    MGMT->>TREG: 加载模板 standard-fullstack@1.2.0(锁定版本)
    TREG-->>MGMT: 模板骨架(8 节点 + 参数定义)

    MGMT->>INST: 实例化(模板 + parameters + overrides)
    INST->>INST: 1. 填充参数占位符 ${approver} ${coverage_min}
    INST->>INST: 2. 求值 condition(skip_design=false → 保留 design 节点)
    INST->>INST: 3. 应用 overrides(覆盖审批人、新增安全节点)
    INST->>INST: 4. 生成 seq(n1-n10 含新增节点)
    INST-->>MGMT: 展开后的 pipeline.yaml(无占位符)

    MGMT->>VAL: 校验展开后的 pipeline.yaml
    VAL->>VAL: DAG 无环(Kahn) ✓
    VAL->>VAL: 引用完整(无 DANGLING_REF) ✓
    VAL->>VAL: 控制节点配置合法 ✓
    VAL-->>MGMT: 校验通过

    MGMT->>MGMT: 缓存展开后的 pipeline.yaml(运行时加载此版本)
    MGMT->>LG: 构建 StateGraph + bootstrap
    LG-->>MGMT: 管线就绪,根节点 ready

    Note over DEV: 模板升级 standard-fullstack@1.3.0(新增 security_review 节点)
    DEV->>MGMT: 模板 PR(1.2.0 → 1.3.0,新增节点)
    MGMT->>MGMT: 模板审核:语法校验 + dry-run 实例化 + diff 评估
    MGMT->>MGMT: 影响面:该模板被 N 个管线实例化使用
    MGMT->>MGMT: admin 审核 + 合并 → 模板 1.3.0 发布

    Note over MGMT: 已实例化的 login-feature 仍用 1.2.0(锁定版本)
    Note over DEV: 新 feature 用 1.3.0;旧 feature 显式 upgrade
    DEV->>MGMT: upgrade_pipeline(login-feature, to=1.3.0)
    MGMT->>INST: 重新实例化(1.3.0 + 原 parameters)
    INST->>VAL: 校验 + 与旧管线 diff(新增 security_review 节点)
    VAL-->>MGMT: 校验通过,diff: +1 节点
    MGMT->>LG: 迁移 state(旧 state + 新节点 blocked 初始化)
    LG-->>MGMT: 升级完成,login-feature@v2 运行
```

---

## 5. 缺陷汇总表

| 场景 | 缺陷 # | 缺陷描述 | 严重度 | PRD 定位 | 修正方案 |
|---|---|---|---|---|---|
| A13 | D13.1 | 状态机缺 draft 态,产物完成度被强制二元化 | 高 | fr2 §2.1(第 59 行) | 新增 draft 态 + 转移 D1-D4 |
| A13 | D13.2 | 无软提交机制,提交即审核,草案无法"提交但不审核" | 高 | 主 PRD §6.1(第 744-764 行) | 新增 soft_submit_artifact 工具 |
| A13 | D13.3 | ArtifactRef 单值,无法表达 draft + final 并存 | 高 | 主 PRD §5.1(第 698-705 行) | 新增 draft_refs 独立字段 |
| A13 | D13.4 | get_dependencies 只拉 main commit,拉不到 feat 分支草案 | 高 | 主 PRD §6.5(第 819-834 行) | 增加 include_draft 参数 |
| A13 | D13.5 | 节点锁 TTL 12h 与草案长期持有矛盾 | 中 | fr1 §5.2.1(第 784-803 行) | draft 态锁 TTL 72h |
| A13 | D13.6 | changed 机制只针对 done,草案变更无下游通知 | 中 | fr2 §2.1 T10(第 72 行) | DRAFT_UPDATED event + 订阅机制 |
| A13 | D13.7 | 需求 9 产物自由未延伸到完成度自由 | 中 | 主 PRD §1.3(第 57 行) | 草案/正式/废弃纳入状态机 |
| A14 | D14.1 | 数据模型假设单仓库,无仓库注册表 | 高 | 主 PRD §5.1(第 698-705 行) | 引入 RepoRegistry |
| A14 | D14.2 | webhook/PR 模板/PR API/合并逻辑硬编码 GitHub 语义 | 高 | 主 PRD §FR6.1(第 489-497 行) | GitProvider 抽象层 + 适配器 |
| A14 | D14.3 | CI 注入只给 GitHub Actions 示例,跨平台翻译缺失 | 中 | fr1 §8.1.3(第 1166-1199 行) | coord-ci 平台无关 + 各平台配置模板 |
| A14 | D14.4 | 分支保护跨平台落地未设计 | 中 | fr1 §1.2(第 182-190 行) | GitProvider 适配器翻译 |
| A14 | D14.5 | 角色→仓库权限映射缺失,可越权提交 | 高 | fr3-fr5 §2.4(第 228-238 行) | 权限矩阵增加 repo_id 校验 |
| A14 | D14.6 | 跨仓库 get_dependencies 需 clone 多仓库,未设计 | 高 | 主 PRD §6.5(第 819-834 行) | ArtifactStore 多仓库 mirror |
| A14 | D14.7 | 需求 6"独立"语义未明确,多仓库场景未纳入 | 中 | 主 PRD §1.2(第 49 行) | 明确"独立于管理层" + 支持多仓库 |
| A15 | D15.1 | 需求 6"独立"语义模糊,混合仓库被排除或未设计 | 高 | 主 PRD §1.2(第 49 行) | 引入 RepoType:artifact-only / hybrid |
| A15 | D15.2 | webhook 无路径过滤,代码 PR 误触发管理方审核 | 高 | 主 PRD §FR6.1(第 489-497 行) | should_manage_pr 路径过滤 |
| A15 | D15.3 | CI 目录白名单假设纯产物仓库,代码 PR 被 CI-1 误伤 | 高 | fr1 §8.1.1(第 1134 行) | CI 白名单按 repo_type 区分 |
| A15 | D15.4 | 分支保护仓库级,不支持 per-path 叠加 | 中 | fr1 §1.2(第 182-190 行) | path_overlays + GitHub rulesets/GitLab push rules |
| A15 | D15.5 | ArtifactRef.path 正则限定产物类型目录开头,docs/ 前缀不匹配 | 中 | fr1 §3.3(第 346-354 行) | 正则支持可选前缀 / 动态生成 |
| A15 | D15.6 | 管理方审核边界未声明,默认接管整仓所有 PR | 高 | 主 PRD §FR6(第 483-568 行) | managed_paths 显式声明 |
| A15 | D15.7 | 需求 6 与需求 9 在混合仓库场景直接冲突 | 中 | 主 PRD §1.2 vs §1.3 | RepoType 调和二者 |
| A16 | D16.1 | 无管线模板抽象,通用性(需求 1)无复用机制支撑 | 高 | 主 PRD §1.3(第 57 行)、§5.1(第 664-693 行) | 引入 PipelineTemplate |
| A16 | D16.2 | pipeline.yaml 无继承与参数化机制 | 高 | fr2 §7.1(第 730-758 行) | extends + parameters + overrides |
| A16 | D16.3 | 模板版本化与实例化管线关系未定义 | 中 | fr2 §7.5(第 813-827 行) | 锁定/浮动/显式升级三策略 |
| A16 | D16.4 | 模板存储位置未定义 | 低 | 主 PRD §5.2(第 730-738 行) | templates/ 目录(管理方仓库) |
| A16 | D16.5 | 模板审核机制缺失,错模板级联影响所有实例 | 高 | 主 PRD §FR6(第 483-568 行) | 模板 PR 审核 + dry-run 实例化 |
| A16 | D16.6 | 跨团队模板共享与权限未设计 | 中 | 主 PRD §1.3(第 57 行) | visibility + owner_team + allowed_consumer_teams |
| A16 | D16.7 | 模板裁剪机制缺失 | 中 | fr2 §7.1(第 730-758 行) | condition + deps_dynamic |
| A16 | D16.8 | 管线加载校验无模板实例化后的校验 | 中 | fr2 §7.6(第 829-843 行) | 实例化后走 §7.6 校验清单 |

---

## 6. 关键发现与优先级建议

### 6.1 三类"纸上谈兵"问题

本轮 4 个场景暴露的 29 项缺陷可归为三类:

| 类别 | 典型缺陷 | 根因 |
|---|---|---|
| **假设单数、实则多数** | D13.3(ArtifactRef 单值)、D14.1(单仓库)、D15.6(接管整仓) | PRD 用"产物仓库"单数叙述,数据模型与流程都按单数设计,但现实是多草案、多仓库、多路径 |
| **声明通用、缺实现机制** | D13.7(产物完成度自由)、D16.1(通用性无复用机制) | 需求 9 声称"产物自由"、需求 1 声称"通用",但状态机/数据模型/管线定义都没有支撑自由与通用的具体机制 |
| **平台耦合、缺抽象层** | D14.2(GitHub 语义硬编码)、D14.3(CI 仅 GitHub Actions)、D15.4(分支保护跨平台) | PRD 以 GitHub 为隐式假设,未抽象 GitProvider,跨 git 托管不可用 |

### 6.2 优先级建议

| 优先级 | 缺陷 | 理由 |
|---|---|---|
| P0(MVP 必修) | D14.1、D14.2、D14.5、D15.2、D15.3、D15.6 | 多仓库与混合仓库是真实部署的硬约束,不修则大公司/小团队两类场景都不可用 |
| P0(MVP 必修) | D13.1、D13.2、D13.4 | 草案是开发常态(并行加速),无 draft 态则并行开发被阻塞 |
| P1(Phase 2) | D13.3、D13.6、D14.6、D15.1、D15.4、D15.7、D16.1、D16.2、D16.5 | 影响数据模型完整性与通用性兑现,Phase 2 落地 |
| P2(Phase 3) | D13.5、D13.7、D14.3、D14.4、D14.7、D15.5、D16.3、D16.4、D16.6、D16.7、D16.8 | 优化项,不影响主干,可迭代 |

### 6.3 与既有深化的对齐

- A13 的 `draft_refs` 与 fr1 §2.3.1 的多版本共存一致(同 node_id 多版本),但草案是 feat 分支 commit(未合并),与 fr1 的"main 上多 seq 共存"不同——草案不入 main,走独立 `draft_refs`
- A14 的 `RepoRegistry` 与 fr1 §2.4.3 `repo-meta.yaml` 互补:repo-meta 是**单仓库内**元数据,RepoRegistry 是**管理方管辖多仓库**的注册表,二者层级不同
- A15 的 `managed_paths` 与 fr1 §8.1.3 的 CI `paths` 过滤互补:CI paths 是**CI 触发**过滤,managed_paths 是**管理方 webhook 接管**过滤,职责不同
- A16 的 `PipelineTemplate` 与 fr2 §7.5 热重载互补:热重载是**单管线实例**版本化,模板是**跨管线复用**抽象,模板实例化后仍走热重载的版本化机制
- A13/A14 的 `ArtifactRef` 修改(repo_id 替代 repo URL)与 A15 的 path 正则修改,建议在主 PRD §5.1 统一修订,避免分散

---

**走查结束。** 本轮 4 个场景共发现 29 项设计缺陷,其中 9 项 P0(MVP 必修)、9 项 P1、11 项 P2。核心结论:PRD 在"产物自由"与"通用性"的声明与实现之间存在显著落差,需通过 draft 态、RepoRegistry、RepoType、PipelineTemplate 四个核心抽象补全。
