# PRD 评审报告 Part 2:§FR2 编排引擎 + §FR3 CrewAI

> **评审范围**:coordination-platform-prd.md §FR2(行 359-779)、§FR3(行 782-873)
> **深化文档**:fr2-orchestration.md(完整,1368 行)、fr3-fr5-crew-skills.md(§2/§5,1263 行)
> **评审维度**:内容缺失 / 边界模糊 / 细节不足 / 规则冲突
> **评审日期**:2026-08-04
> **文档状态**:待评审

---

## 0. 汇总

### 0.1 各维度发现数量

| 维度 | 发现数量 | P0 | P1 | P2 |
|---|---|---|---|---|
| 维度 1:内容缺失 | 7 | 2 | 3 | 2 |
| 维度 2:边界模糊 | 6 | 1 | 3 | 2 |
| 维度 3:细节不足 | 9 | 1 | 5 | 3 |
| 维度 4:规则冲突或矛盾 | 7 | 4 | 2 | 1 |
| **合计** | **29** | **8** | **13** | **8** |

### 0.2 P0 级发现清单(8 项,阻塞性)

| 编号 | 维度 | 章节 | 发现摘要 |
|---|---|---|---|
| P0-1 | 维度 4 | §FR2.1 / D11 | 状态机态数三重不一致:主 PRD 说 10 态,D11 新增 skipped 成 11 态未回写,fr2 深化只覆盖 7 态 |
| P0-2 | 维度 4 | §FR3.5 vs fr3 §2.3 | Cost 硬预算数值主 PRD 与 fr3 矛盾(20k vs 10k,$10 vs $5),超限动作冲突(硬中断 vs warning) |
| P0-3 | 维度 4 | §FR3.1 vs §FR3.2 | Task description "产出产物" 与 agent 定位"不执行开发,只协调提交"直接矛盾 |
| P0-4 | 维度 4 | §FR3.4 vs fr3 §9 | AC 编号冲突:AC3.4/AC3.5 在主 PRD 与 fr3 中双重定义且内容不同 |
| P0-5 | 维度 4 | §FR2.2 vs §FR2.2.1 vs AC2.3 | "全 done 才 ready"与"optional dep 不参与 ready 判定"矛盾,AC2.3 未区分 required/optional |
| P0-6 | 维度 1 | §FR2.1 / §FR2.5.1 | D1-D6(draft/deprecated/sunset)转移表和 guard 完全缺失,fr2 §2.1 只覆盖 T1-T18 |
| P0-7 | 维度 1 | §FR2.4 / §FR2.5.1 | addendum 级联(must/should/info)无对应 StateGraph 节点,执行入口未定义 |
| P0-8 | 维度 3 | §FR3.5 | 硬预算阈值和超限动作两份文档矛盾,且 key_constraints 提取算法完全未定义 |

### 0.3 最关键的 3 个发现

1. **【P0-1】状态机态数三重不一致**:主 PRD §FR2.1(行 363)声明"10 态",但附录 D11(行 2128)新增 `skipped` 态成 11 态且 P0-R5.17 明确要求"状态机扩展 skipped 态 + AC2.7 修正",然而主 PRD §FR2.1 状态机表(行 367-378)未列入 skipped,AC2.7(行 732)未修正。同时 fr2 深化文档 §2.1(行 59)状态枚举只列 7 态(blocked/ready/pending_review/in_progress/review/done/changed),T1-T18 转移表完全未覆盖 draft(D1-D4)/deprecated(D5)/sunset(D6)的转移条目和 guard。三份文档对状态机态数的描述严重不一致,实现时无法判断以哪个为准。

2. **【P0-2】Cost 硬预算数值矛盾且超限动作冲突**:主 PRD §FR3.5(行 855-859)定义 Task 级 20k token/3 次重试 → "硬中断,转 needs_human";Agent 级 $10/日;管线级 $100;平台级 $4000。fr3 §2.3(行 215-219)定义单 Task ≤ 10k token → "超限记录 warning,不强制中断";单 Agent/日 ≤ $5;管线级 ≤ $50。两者数值全部差 2 倍,且 Task 级超限动作直接冲突(主 PRD 硬中断 vs fr3 不中断)。fr3 附录 A llm.yaml(行 1226)又用 `total_cost_limit_usd: 50`,与主 PRD $100 矛盾。实现时无法判断真实阈值。

3. **【P0-3】Task description 与 agent 定位直接矛盾**:主 PRD §FR3.1(行 796)明确"Agent 不执行开发,只协调提交。真正开发由人员自由完成,Agent 是'提交协调员'"。但 §FR3.2(行 819)的 Task description 是 `f"为节点 {node_id}({node['type']})产出产物,通过 MCP 提交"`——"产出产物"语义上等同于"执行开发产出交付物",与"不执行开发"直接冲突。fr3 §2.2(行 144)的 goal 已修正为"协调提交",但主 PRD §FR3.2 的 Task description 未同步修正,会导致 agent 行为偏差(LLM 可能尝试自行产出产物而非协调人员提交)。

---

## 1. 维度 1:内容缺失(7 项)

### 1.1【P0-6】D1-D6 转移表和 guard 完全缺失

**位置**:主 PRD §FR2.1(行 387-417)、fr2 §2.1(行 57-86)

**问题**:主 PRD §FR2.1 的 mermaid 状态流转图(行 388-417)定义了 D1-D6 转移(D1 soft_submit→draft、D2 草案 push、D3 submit 转正式、D4 abandon、D5 deprecated、D6 sunset),但 fr2 §2.1 的完整转移表(行 61-80)只有 T1-T18,完全未覆盖 D1-D6。fr2 §2.1(行 59)状态枚举只列 7 态:"blocked / ready / pending_review / in_progress / review / done / changed",draft/deprecated/sunset 三态的转移条目、guard、副作用、幂等性全部缺失。

**影响**:draft/deprecated/sunset 是第五轮新增的核心状态(支持草案共享、废弃下线),无转移表和 guard 定义,实现时无法编码,且 fr2 §2.2 非法转移防护表(行 92-107)无法覆盖这三态的非法转移。

**建议补充**(fr2 §2.1 转移表追加):

```markdown
| D1 | `ready` | `draft` | `soft_submit_artifact` | 节点非根时上游 deps 满足 strictness(accepts_draft 允许 draft 上游) | 写 `draft_refs[nid]`,发 `DRAFT_CREATED` event,通知订阅者 | 草案 |
| D2 | `draft` | `draft` | feat 分支 push 新 commit | 新 commit ≠ 旧 commit | 更新 `draft_refs[nid]`,发 `DRAFT_UPDATED` event | 草案迭代 |
| D3 | `draft` | `pending_review` | `submit_artifact`(转正式) | 同 T5 guard | 清 `draft_refs[nid]`,写 `pending_prs[nid]`,发 `PENDING_REVIEW` event | 草案转正式 |
| D4 | `draft` | `ready` | `abandon_draft` | 调用方为 assignee 或 admin | 清 `draft_refs[nid]`,发 `DRAFT_ABANDONED` event | 放弃草案 |
| D5 | `done` | `deprecated` | 管理方标记 / 版本 superseded / 外部依赖失效 | 调用方为 admin 或 ExternalHealthMonitor 触发 | 发 `DEPRECATED` event,通知 CrossPipelineReferenceRegistry 中所有引用方 | 废弃 |
| D6 | `deprecated` | `sunset` | deprecated 后 N 天(NFR 可配,默认 30) | 距 deprecated 时间 ≥ N 天 | 发 `SUNSET` event,强制所有下游 blocked | 终态下线 |
| D7 | `draft` | `blocked` | 上游 changed(T16) | 本节点是 changed 节点的下游可达节点 | 清 `draft_refs[nid]`,发 `INVALIDATED` event | 草案级联失效 |
```

### 1.2【P1】DAG 规则未覆盖 presence 和 coupling 字段的语义

**位置**:主 PRD §FR2.2(行 419-432)、DepDeclaration(行 437-445)

**问题**:DepDeclaration 定义了 `presence`(required/optional/if_present)和 `coupling`(hard/soft/informational)字段,但 §FR2.2 的 DAG 规则表(行 423-431)只描述了 strictness 的级联行为,未定义:
- `presence: if_present` 的具体语义:节点存在时如何成为硬依赖?节点不存在时 deps 边如何处理?
- `coupling` 字段与 strictness 的关系:两者都影响级联,但 coupling 是"上游变更时下游失效强度",strictness 是"依赖是否要求 done",组合矩阵未定义。
- §FR2.2.1(行 500)提到 `breaking+hard → hard_invalidate`、`compatible+soft → soft + ack`、`docs_only|informational → cascade_skip`,这是 change_class × coupling 的组合,但 coupling=hard + change_class=compatible 的行为未明确。

**建议补充**(§FR2.2 DAG 规则表追加):

```markdown
| presence 语义 | presence=required:deps 边始终生效,参与 ready 判定和级联;presence=optional:deps 边生效但不参与 ready 判定(节点可 ready 即使 optional dep 未 done),级联时可选通知;presence=if_present:仅当 dep 节点在 materialized 管线中存在时才成为 required 依赖,否则 deps 边删除 |
| coupling × change_class 级联矩阵 | hard+breaking → hard_invalidate(清引用+blocked);hard+compatible → soft_invalidate(ack 后保持);soft+breaking → soft_invalidate;soft+compatible → cascade_skip(通知);informational+任意 → cascade_skip(通知) |
```

### 1.3【P1】控制节点输入输出未完整定义

**位置**:主 PRD §FR2.5(行 697-720)

**问题**:
- `switch` 节点(行 706)说"按上游产物字段路由(如风险高走 review-agent 分支)",但字段提取逻辑未定义:如何从产物中提取"风险"字段?这是否违反"管理方不解析业务内容"原则(§1.2 行 50)?若产物是 YAML/JSON,switch 是否解析?若产物是 Figma 链接,switch 如何提取字段?
- `notify` 节点(行 707)说"读取产物 consumers 配置",但 consumers 配置在产物 PR 模板(§FR1.3 行 312-316)中,notify 节点如何读取?是从 ArtifactRef.consumers 字段读取(§5.1 行 1361),还是从 manifest 读取?
- `gate` 节点的输入是上游产物的什么?gate 评估 policy 时,lint/test/coverage 是对哪个产物或代码仓执行?主 PRD 未定义 gate 的输入源。

**建议补充**:明确 switch 节点字段提取的"白名单机制"(只允许从 ArtifactRef 的元数据字段提取,不从产物内容提取,以符合"不解析内容"原则);明确 gate 节点的执行环境(对引用型产物的 external_repo 执行 lint/test,还是仅校验 ArtifactRef 元数据)。

### 1.4【P1】CrewAI Task 的 context 结构两份文档不一致

**位置**:主 PRD §FR3.2(行 822-827)、fr3 §4.3(行 481-482)

**问题**:
- 主 PRD §FR3.2 的 Task context:`{node_id, instance_id, deps, participation_profile}`
- fr3 §4.3 的 Task context:`{node_id, deps_info}`
- 两者字段不一致:主 PRD 有 instance_id 和 participation_profile,fr3 没有;fr3 的 deps_info 是结构化列表(含 ref + summary),主 PRD 的 deps 未明确结构。
- 两份文档均未包含 `key_constraints` 字段(§FR3.5 行 867 提到 get_dependencies 返回 key_constraints,但 Task context 未注入)。
- 两份文档均未包含 `skill` 信息(节点对应的 skill 约束和 guide_summary)。

**建议统一**(主 PRD §FR3.2 Task context 修正):

```python
context={
    "node_id": node_id,
    "instance_id": instance_id,
    "node_type": node["type"],
    "deps_info": get_deps_info(node_id, state),  # 含 ref + summary + key_constraints
    "key_constraints": extract_key_constraints(node_id, state),  # must 级约束高亮
    "participation_profile": state["participation"]["profile"],
    "skill": {  # 节点对应的约束技能
        "name": skill["name"],
        "version": skill["version"],
        "guide_summary": skill["guide_summary"],
        "required_fields": skill["artifact_constraints"]["required_fields"],
    },
},
```

### 1.5【P1】LangGraph ↔ CrewAI 事件契约不完整

**位置**:主 PRD §FR3.3(行 832-839)、fr3 §4.2(行 408-429)

**问题**:主 PRD §FR3.3 只列了 4 个事件(节点 ready / agent 调 submit / PR 合并 / 下游 ready),但 fr3 §4.2 定义了 CompletionEvent 的 3 个子类型(task_completed/task_failed/task_fallback),主 PRD 未体现 task_failed 和 task_fallback 事件的处理。此外,addendum 相关事件(ADDENDUM_MUST_ACK/ADDENDUM_SHOULD_ACK/ADDENDUM_INFO/ADDENDUM_TIMEOUT,§FR2.5.1 行 547-549)在 CrewAI 侧的处理未定义:agent 是否需要处理 addendum 事件?是否需要调 reack_addendum 工具?

**建议补充**:主 PRD §FR3.3 事件表追加 task_failed/task_fallback/addendum_* 事件,明确 CrewAI 对每类事件的响应动作。

### 1.6【P2】状态机 mermaid 图缺少 deprecated/sunset 的外部依赖失效路径

**位置**:主 PRD §FR2.1(行 388-417)

**问题**:状态流转图(行 388-417)只画了 D5(管理方标记废弃)一条进入 deprecated 的路径,但 §FR2.1 表格(行 377)和 §FR2.2(行 455)提到 deprecated 有 3 种进入路径:管理方标记 / 版本 superseded / 外部依赖失效。后两条路径未在 mermaid 图中体现。ExternalHealthMonitor 触发的 `done→deprecated` 转移(§FR2.2 行 455)是自动化关键路径,应在图中明确。

### 1.7【P2】generator_agent 和 reviewer 角色在 CrewAI 中未定义 agent

**位置**:主 PRD §FR3.1(行 786-794)、§3.1(行 137-145)

**问题**:§3.1 定义了 7 个角色(product/server/design/client/generator/reviewer/admin),但 §FR3.1 的 Agent 表(行 788-794)只定义了 5 个 agent(product/server/design/client/generator),reviewer 和 admin 没有 agent 定义。reviewer 的 approve_pr/reject_pr 由谁调用?是人工还是 agent?主 PRD §FR3.1(行 784)说"用 CrewAI 定义 4 角色",但实际定义了 5 个 agent,数字不一致。

---

## 2. 维度 2:边界模糊(6 项)

### 2.1【P2】draft 和 in_progress 的区别模糊

**位置**:主 PRD §FR2.1(行 367-378)

**问题**:
- `in_progress`:"开发中(进度更新)",由 `update_progress` 进入,退出条件"重新 submit"。
- `draft`:"草案(未完成但可共享)",由 `soft_submit_artifact` 进入,退出条件"submit(转正式)/abandon"。
- 边界模糊点:一个节点能否同时处于 in_progress 和 draft?状态机是单态的,但语义上"开发中"和"草案"可以并存(开发人员在写代码,同时分享草案给下游)。
- in_progress 和 draft 都涉及"submit":in_progress 退出是"重新 submit"(正式 PR),draft 退出是"submit 转正式"(也是正式 PR),两者 submit 的语义重叠。
- draft 的"可共享"与 in_progress 的"开发中"区别:in_progress 时产物尚未提交,draft 时已有 feat 分支 commit 可共享。但 in_progress 时也可以有 feat 分支 commit(只是未 soft_submit),边界仍模糊。

**建议明确**:draft 是 in_progress 的"可共享子状态",还是独立状态?若独立,需明确"in_progress 时不能 soft_submit"(否则状态冲突)。

### 2.2【P0-7】addendum 级联无对应 StateGraph 节点

**位置**:主 PRD §FR2.4(行 683-695)、§FR2.5.1(行 543-549)

**问题**:§FR2.4 的 StateGraph 节点表(行 685-695)定义了 9 个节点(bootstrap/dispatch_router/crewai_assign/cascade_node/invalidate_node/approval_node/draft_publish_node/external_health_node/wait_node),但没有 addendum 级联节点。§FR2.5.1(行 543-549)说 addendum 按 cascade_level(must/should/info)分级通知下游,must 级"发 ADDENDUM_MUST_ACK 事件;下游若 incompatible 则需主动 changed"。这个"发事件 + 判定 incompatible + 触发下游 changed"的动作由哪个 StateGraph 节点执行?是复用 cascade_node?还是 invalidate_node?还是新增 addendum_cascade_node?主 PRD 未定义。

**影响**:addendum 是第五轮 P0-R5.12 修正项,无执行入口则无法实现。

**建议补充**(§FR2.4 StateGraph 节点表追加):

```markdown
| `addendum_cascade_node` | addendum 级联:按 cascade_level 分发 must/should/info 事件;must 级检查下游 incompatible_with,触发下游 → changed;超时检查(7 天) | add_addendum 调用后 |
```

### 2.3【P1】cascade 和 invalidate 与 addendum 级联的触发边界

**位置**:主 PRD §FR2.2(行 428-430)、§FR2.5.1(行 510-515)

**问题**:三种级联类型:
- cascade:done → 下游 ready(解锁)
- invalidate:changed → 下游 blocked(失效)
- addendum 级联:done 节点附加 addendum → 下游 must/should/info(弱级联)

边界模糊:addendum 级联属于 cascade 还是独立类型?addendum 级联时节点状态保持 done(§FR2.5.1 行 510),但 must 级 addendum 可能触发下游 changed(行 547),这个"下游 changed"是 invalidate 行为还是 addendum 行为?addendum_cascade_node 和 invalidate_node 的职责边界未划分。

**建议明确**:addendum 级联是独立类型,由 addendum_cascade_node 执行;must 级触发下游 changed 时,委托 invalidate_node 执行 changed 级联(复用现有失效逻辑)。

### 2.4【P1】ParticipationProfile 的 roles_absent 与节点 optional 的关系

**位置**:主 PRD §FR2.2.1(行 457-490)

**问题**:
- `roles_absent`(行 467):管线级裁剪,materialize 时删除缺席角色的节点。
- `DepDeclaration.presence`(行 443):依赖级标记,optional/if_present。
- `ParticipationProfile.completion.optional_node_types`(行 472):完成谓词中的可选节点类型。
- 三者关系模糊:如果一个节点因 roles_absent 被裁剪(如 design_asset 在 server_only 管线中),其下游节点(如 client_ui)的 deps 中指向 design_asset 的边如何处理?§FR2.2.1 行 488 说"删除指向已裁剪节点的 deps(禁止 dangling)",但 D11 P0-R5.15(行 2124)说"DepDeclaration 新增 optional 标记",两者是否冲突——是删除 deps 边,还是标记为 optional?
- 行 490 说"optional 节点失败只告警不挡完成",这里"optional 节点"指 presence=optional 的 dep,还是 completion.optional_node_types 中的节点?

**建议明确**:roles_absent 裁剪节点时,下游 deps 边的处理策略(删除 vs 标记 optional),以及 completion.optional_node_types 与 DepDeclaration.presence=optional 的语义关系。

### 2.5【P1】addendum cascade_level=must 和 changed 的边界

**位置**:主 PRD §FR2.5.1(行 543-549、行 644-655)

**问题**:
- 行 547:must 级 addendum "下游若 incompatible 则 → changed;否则保持"。
- 行 652-655:must 级 addendum 超时 7 天未 ack,"下游自动 → changed"。
- "incompatible"的判定标准未定义:是基于 addendum.incompatible_with 列表(行 529),还是下游主动判断?若基于列表,列表由 addendum 提交方声明,提交方如何知道下游是否 incompatible?
- 超时后"下游自动 → changed":这个 changed 是下游节点自身 changed(走 T12 重提 PR),还是上游节点 changed 触发下游 blocked?若下游 changed,其下游的下游如何级联?
- must 级 addendum 下游 ack=accepted 时,下游状态保持 done;ack=rejected 时,下游状态如何?未定义。

**建议补充**:明确 incompatible 判定标准(基于 incompatible_with 列表 + 下游主动评估);ack=rejected 时下游 → changed;超时 → changed 后走标准 changed 级联(T12/T13)。

### 2.6【P2】管线级 paused 和节点级 blocked 的关系

**位置**:主 PRD §FR2.7(行 753-771)、§FR2.3(行 679)

**问题**:
- §FR2.7(行 756):paused 时"ready 节点不再 dispatch,级联事件挂起"。
- 但 paused 时已有的 in_progress 节点如何处理?agent 仍在执行 Task,完成后调 submit_artifact 是否被接受?
- §FR2.3(行 679)的 `cascade_pending: list[dict]` 字段存储挂起的级联事件,但 paused 时新的状态变更(如 pending_review → done 的 PR 合并)是否被阻塞未明确。
- paused 和 blocked 的优先级:如果一个节点同时处于 blocked(依赖未满足)和管线 paused,resume 管线时该节点状态如何?仍是 blocked 还是重新评估?
- cancelled 时(行 757),处于 blocked/pending_review/review 状态的节点是否统一置为某个终态?还是保持原状态?管线 cancelled 后,节点级状态变更是否被拒绝?

**建议补充**:明确 paused 时 in_progress/pending_review 节点的行为(继续/暂停);cancelled 时各状态节点的终态处理;paused/blocked 优先级。

---

## 3. 维度 3:细节不足(9 项)

### 3.1【P1】状态转移 guard 的具体逻辑未展开

**位置**:fr2 §2.1(行 61-80)、§2.3(行 114-146)

**问题**:fr2 §2.1 的 T1-T18 给出了 guard 概要(如 T5 的"skill 元数据 + 依赖完整性预校验通过"),但具体校验逻辑未展开:
- "skill 元数据预校验"校验哪些字段?是 required_fields 全部存在,还是包含 file_constraints?
- "依赖完整性"是检查所有 deps 的 strictness,还是仅检查存在性?strictness=accepts_draft 时上游 draft 是否算满足?
- T10 的 guard"新 commit ≠ 旧 commit":commit 比较的是 hub 仓 merge commit 还是 feat 分支 commit?
- fr2 §2.3(行 119-146)的三层 Guard(身份/前置状态/上下文)是框架,但 check_context 的具体实现未给出。

**建议补充**:fr2 §2.3 的 check_context 函数补充每个转移的上下文校验逻辑伪代码。

### 3.2【P1】cascade 递归终止条件不完整

**位置**:fr2 §2.1 T16(行 78)、§FR2.5.1(行 644-650)

**问题**:
- T16 说"递归失效,需用 visited set 防环",但递归终止的完整条件未定义:
  - 是否所有下游都置 blocked?还是按 strictness/coupling 分级?
  - strictness=accepts_draft 的下游是否保持(§FR2.2 行 429)?
  - coupling=informational 的下游是否不失效(§FR2.2.1 行 500)?
  - 下游 blocked 后,下游的下游是否也 blocked(递归传播)?
- §FR2.5.1(行 644-650)的"已进入开发节点的修改处理"表给出了不同下游状态 × 上游变更类型的处理,但这是单层处理,递归传播规则未明确:下游 → blocked 后,下游的下游按什么规则传播?

**建议补充**:明确递归传播规则——changed 节点的所有下游按 coupling 分级:hard → blocked(递归传播);soft → 保持 + ack;informational → 通知不传播。递归终止于 coupling ≠ hard 的边。

### 3.3【P2】DAG 无环校验未覆盖跨管线引用

**位置**:fr2 §7.2(行 762-786)

**问题**:fr2 §7.2 的 Kahn 算法只处理单管线内 deps(`node.deps` 中的 node_id),未处理跨管线引用(`hub_ref: "hub://{pipeline_id}/{node_id}@{version}"`)。如果 A 管线节点 n1 引用 B 管线节点 n2,B 管线节点 n2 又引用 A 管线节点 n1,形成跨管线环,但单管线校验无法检测。§FR2.2(行 432)说"跨管线引用经 CrossPipelineReferenceRegistry 注册",但注册时是否做环检测未定义。

**建议补充**:CrossPipelineReferenceRegistry 注册时追加跨管线环检测(构建全局依赖图,Kahn 校验)。

### 3.4【P1】PipelineState 字段初始值和更新时机未定义

**位置**:主 PRD §FR2.3(行 666-681)、fr2 §3.1(行 214-242)

**问题**:§FR2.3 的 PipelineState 列出了 13 个字段,但未给出初始值:
- `node_states`:初始全 blocked,还是按 deps 判断(根节点 ready,非根 blocked)?
- `active_version`:初始空 dict,还是初始为 "0.0.0"?
- `draft_refs` / `draft_subscribers`:初始空 dict?
- `cascade_pending`:初始空 list?
- `external_health`:初始空 dict,还是初始为 healthy?

更新时机:
- `cascade_pending`:pause 时写入、resume 时清空?还是 resume 时逐条应用后清空?
- `draft_subscribers`:subscribe_draft 时追加、unsubscribe_draft 时移除,但节点 done 或 abandoned 时是否自动清空订阅者?
- `external_health`:ExternalHealthMonitor 多久更新一次?失效时立即更新?

**建议补充**:§FR2.3 追加字段初始值表和更新时机表。

### 3.5【P1】StateGraph 节点执行顺序和并发模型主 PRD 未说明

**位置**:主 PRD §FR2.4(行 683-695)

**问题**:§FR2.4 只列出 9 个 StateGraph 节点及其触发条件,但执行顺序和并发模型未在主 PRD 中说明:
- bootstrap → dispatch_router → (crewai_assign/cascade/invalidate/...) → dispatch_router 循环,这个循环结构只在 fr2 §9.1(行 928-986)体现,主 PRD 未提及。
- 并发模型:fr2 §9.4(行 1058-1085)用 Send API 并行 fan-out,fr3 §5(行 619-666)用 asyncio.gather 按角色分组并行,两份文档的并发模型不同(Send API vs asyncio.gather),主 PRD 未仲裁。
- dispatch_router 的路由逻辑:fr2 §9.4(行 1058-1085)给出了按节点状态分发的逻辑,但主 PRD §FR2.4 只说"按节点状态分发",未明确路由规则。

**建议补充**:主 PRD §FR2.4 追加执行顺序图和并发模型说明,仲裁 Send API 与 asyncio.gather 的关系(Send API 是 LangGraph 层 fan-out,asyncio.gather 是 CrewAI 层并行,两者可共存)。

### 3.6【P2】gate policy 的具体格式和执行逻辑未定义

**位置**:主 PRD §5.1(行 1330)、fr2 §7.4(行 806)、§8.1(行 852-862)

**问题**:
- §5.1(行 1330)给出 gate policy 示例:`{ lint: true, test: true, coverage_min: 80, security_scan: true }`。
- fr2 §7.4(行 806)说"policy.lint/policy.test/policy.coverage_min/policy.security 至少一项"。
- 但每个字段的具体执行逻辑未定义:
  - `lint: true` 跑什么命令?对哪个产物或代码仓执行?
  - `test: true` 跑哪个测试套件?是产物仓库的 CI 还是代码仓的 CI?
  - `coverage_min: 80` 单位是百分比(80%)还是小数(0.80)?
  - `security_scan: true` 扫描哪些规则族(§FR6 提到 R_SECRET_SCAN/R_URL_SAFETY/R_MALWARE_SCAN)?
  - 是否支持自定义 gate(如自定义脚本)?

**建议补充**:gate policy 完整 schema 定义 + 每个字段的执行环境和命令模板。

### 3.7【P1】CrewAI Task 的 expected_output 格式和校验机制未定义

**位置**:主 PRD §FR3.2(行 822)、fr3 §4.2(行 421-428)

**问题**:
- §FR3.2 的 expected_output="产物已提交 PR,等待审核"是自由文本字符串。
- fr3 §4.2 的 CompletionEvent 是结构化 JSON(event_type/node_id/pr_id/error/fallback_used/trace_id)。
- 两者如何对应未说明:expected_output 是否用于 Task 完成判定?如何校验"产物已提交 PR"?是解析 agent 输出文本提取 pr_id,还是从 MCP 调用结果获取?
- expected_output 的格式未标准化:不同 agent 的 expected_output 是否统一?是否用 Pydantic 模型校验?

**建议补充**:expected_output 改为结构化格式(如 `{"status": "pr_submitted", "pr_id": int, "node_id": str}`),并用 Pydantic 校验。

### 3.8【P0-8】硬预算阈值和超限动作矛盾,key_constraints 提取算法未定义

**位置**:主 PRD §FR3.5(行 849-868)、fr3 §2.3(行 215-219)

**问题**(数值矛盾见 P0-2,此处聚焦算法缺失):
- §FR3.5(行 866-868)说"get_dependencies 返回增加 key_constraints 字段,结构化高亮上游 must 级约束",但提取算法完全未定义:
  - 如何从产物内容中提取 must 级约束?是解析 YAML/JSON 的特定字段,还是用 LLM 提取?
  - 提取规则是否依赖 skill 定义?skill.yaml 中未定义 key_constraints 提取规则。
  - 提取是否违反"管理方不解析业务内容"原则(§1.2 行 50)?若由管理方提取,需解析内容;若由 agent 提取,agent 不在 get_dependencies 调用链中。
- §6.5 get_dependencies 返回(行 1578)的 key_constraints 结构是 `[{level: must, text: "..."}]`,但 level 的取值(must/should/info?)和 text 的来源未定义。
- 硬预算的超限动作:主 PRD Task 级"硬中断,转 needs_human"与 fr3"超限记录 warning,不强制中断"矛盾,且"needs_human"状态的节点在状态机中未定义(10 态/11 态均无 needs_human)。

**建议补充**:
1. key_constraints 提取由 skill 定义(skill.yaml 增加 `key_constraints_extractor` 字段,声明提取规则 jsonpath 或正则),管理方按规则提取(符合"不解析业务内容"——只按 skill 声明的元数据规则提取)。
2. 统一硬预算阈值(见 P0-2 建议)。
3. "needs_human"不是节点状态,而是节点标记(`need_human: true`),节点状态保持 ready/in_progress。

### 3.9【P2】fr2 §2.4 幂等键设计未覆盖 addendum 和 draft 操作

**位置**:fr2 §2.4(行 148-162)

**问题**:fr2 §2.4 的幂等键表覆盖了 submit_artifact/approve_pr/reject_pr/update_progress/approve,但未覆盖:
- `add_addendum`:重复调用(同 node_id + 同 content hash)是否返回首次 addendum_id?
- `soft_submit_artifact`:重复调用(同 node_id + 同 commit)是否返回首次 draft_ref?
- `transfer_owner`:重复调用(同 node_id + 同 new_owner)是否幂等?
- `reack_addendum`:重复调用(同 addendum_id + 同 ack_status)是否幂等?

**建议补充**:幂等键表追加 add_addendum/soft_submit/transfer_owner/reack_addendum 的幂等规则。

---

## 4. 维度 4:规则冲突或矛盾(7 项)

### 4.1【P0-1】状态机态数三重不一致

**位置**:主 PRD §FR2.1(行 363)、fr2 §2.1(行 59)、附录 D11(行 2128)

**冲突**:
- 主 PRD §FR2.1(行 363):"状态机定义(10 态)",状态机表(行 367-378)列出 10 态(blocked/ready/pending_review/in_progress/review/done/changed/draft/deprecated/sunset)。
- fr2 §2.1(行 59):"状态枚举:blocked / ready / pending_review / in_progress / review / done / changed"——只有 7 态,完全未覆盖 draft/deprecated/sunset。
- 附录 D11(行 2128):"状态机扩展:10 态 → 11 态(新增 skipped)",P0-R5.17(行 2126)明确要求"状态机扩展 skipped 态 + AC2.7 修正"。
- 主 PRD §FR2.1 状态机表未列入 skipped,AC2.7(行 732)未修正(仍是"core 节点全 done 时进入 completed",未体现 optional 节点 skipped 语义)。

**矛盾判定**:三份文档对状态机态数的描述严重不一致。主 PRD 说 10 态,D11 说扩展到 11 态但未回写主 PRD,fr2 深化只覆盖 7 态。实现时无法判断以哪个为准。

**建议修正**:
1. 主 PRD §FR2.1 状态机表追加 `skipped` 态(11 态),定义进入条件(optional 节点未 done 且管线将终止)、退出条件(终态)。
2. AC2.7 修正为:"管线 core 节点全 done 且 optional 节点全 done 或 skipped 时进入 completed"。
3. fr2 §2.1 状态枚举追加 draft/deprecated/sunset/skipped 四态,转移表追加 D1-D7 + skipped 转移条目。

### 4.2【P0-5】"全 done 才 ready"与"optional dep 不参与"矛盾,AC2.3 未区分

**位置**:主 PRD §FR2.2(行 427)、§FR2.2.1(行 500)、AC2.3(行 728)、D11 P0-R5.16(行 2125)

**冲突**:
- §FR2.2(行 427):"多入边:全部 done → 本节点 ready"。
- AC2.3(行 728):"多入边节点,部分依赖 done 时仍 blocked"。
- §FR2.2.1(行 500):"breaking+hard → hard_invalidate"等,暗示分级处理。
- D11 P0-R5.16(行 2125):"级联公式修正(仅 required deps 参与 ready 判定)"——即 optional dep 不参与 ready 判定。

**矛盾判定**:若节点有 2 个 deps,1 个 required(done)、1 个 optional(blocked),按 P0-R5.16 节点应 ready(optional 不参与);但按 AC2.3"部分依赖 done 时仍 blocked"会 blocked。AC2.3 未区分 required/optional,与 P0-R5.16 矛盾。

**建议修正**:AC2.3 修正为:"多入边节点,部分 required 依赖 done 时仍 blocked;optional 依赖未 done 不影响 ready 判定"。

### 4.3【P0-3】Task description "产出产物"与 agent 定位"不执行开发"矛盾

**位置**:主 PRD §FR3.1(行 796)、§FR3.2(行 819)

**冲突**:
- §FR3.1(行 796):"Agent 不执行开发,只协调提交。真正开发由人员自由完成,Agent 是'提交协调员'。"
- §FR3.2(行 819):Task description = `f"为节点 {node_id}({node['type']})产出产物,通过 MCP 提交"`——"产出产物"语义上等同于"执行开发产出交付物"。
- fr3 §2.2(行 144)的 goal 已修正为"为 product_spec 节点协调提交:校验人员产出的需求文档引用,通过 MCP 提交 PR"。
- fr3 §4.3(行 478)的 Task description 也修正为"为节点 {event.node_id}({event.node_type})协调提交产物"。

**矛盾判定**:主 PRD §FR3.2 的 Task description 未同步修正,"产出产物"与"不执行开发"直接矛盾。LLM 收到"产出产物"指令可能尝试自行产出产物,违反 agent 定位。

**建议修正**:主 PRD §FR3.2 Task description 改为:

```python
description=f"为节点 {node_id}({node['type']})协调提交产物引用:校验人员已产出的产物,通过 MCP submit_artifact 提 PR",
```

### 4.4【P0-4】AC 编号冲突:AC3.4/AC3.5 双重定义

**位置**:主 PRD §FR3.4(行 843-847)、fr3 §9(行 1156-1163)

**冲突**:
- 主 PRD §FR3.4:
  - AC3.4:"同一角色多 RoleInstance 时,任务按 instance_id 正确路由"
  - AC3.5:"roles_absent 角色不出现在 Crew agents 列表中"
- fr3 §9:
  - AC3.4:"4 个 agent 的 LLM 配置(模型/temperature/max_tokens)可配置且生效"
  - AC3.5:"agent Task 失败时,瞬时错误自动重试 ≤ 3 次"
  - AC3.6-AC3.11:后续补充

**矛盾判定**:AC3.4 和 AC3.5 在两份文档中编号相同但内容完全不同,实现时无法判断验收哪个。

**建议修正**:fr3 §9 的 AC 编号从 AC3.6 开始(主 PRD AC3.5 之后的编号),或采用 AC3.1.1/AC3.1.2 子编号方案。同时主 PRD §FR3.4 应合并 fr3 的补充 AC,统一编号。

### 4.5【P0-2】Cost 硬预算数值和超限动作矛盾

**位置**:主 PRD §FR3.5(行 855-859)、fr3 §2.3(行 215-219)、fr3 附录 A(行 1226)

**冲突**:

| 层级 | 主 PRD §FR3.5 | fr3 §2.3 | fr3 附录 A llm.yaml |
|---|---|---|---|
| Task 级 | 20k token / 3 次重试 → 硬中断,转 needs_human | ≤ 10k token → 超限 warning,不强制中断 | task.timeout_sec: 60 |
| Agent 级 | $10/日 → 排队等待 | ≤ $5/日 → 告警,新 Task 排队 | daily_cost_limit_usd: 5(product/server/client)、3(design) |
| 管线级 | $100 → 暂停管线 | ≤ $50 → 告警,允许继续(不阻塞) | total_cost_limit_usd: 50 |
| 平台级 | $4000 → 全局降级(切便宜模型) | 未定义 | 未定义 |

**矛盾判定**:数值全部差 2 倍,Task 级超限动作直接冲突(硬中断 vs warning),管线级行为冲突(暂停 vs 允许继续)。fr3 附录 A 的 daily_cost_limit_usd 与 fr3 §2.3 一致($5/$3),但与主 PRD($10)矛盾。

**建议修正**:以 fr3 §2.3 + 附录 A 为准(更细粒度,区分角色),主 PRD §FR3.5 修正为:

```markdown
| 层级 | 限额 | 触发动作 |
|---|---|---|
| Task 级 | 10k token(输入+输出) | 超限记录 warning;单 Task 超 60s 硬中断,转 needs_human |
| Agent 级 | product/server/client $5/日,design $3/日 | 超限告警,新 Task 排队等待配额刷新 |
| 管线级 | $50 | 超限告警,允许继续但记审计(不阻塞交付) |
| 平台级 | $4000 | 全局降级(切便宜模型),通知 admin |
```

### 4.6【P1】fr2 §2.1 状态枚举 7 态与主 PRD 10 态不一致

**位置**:fr2 §2.1(行 59)、主 PRD §FR2.1(行 87)

**冲突**:见 P0-1。fr2 §2.1(行 59)明确写"状态枚举:blocked / ready / pending_review / in_progress / review / done / changed"——7 态。fr2 §12(行 1233)说"§2.1 状态机 7 态 → §2.1 完整转移表 T1-T18,✅ 扩展,不冲突",但主 PRD §FR2.1 已是 10 态(含 draft/deprecated/sunset),fr2 仍按 7 态深化,严重不一致。

**建议修正**:fr2 §2.1 状态枚举追加 draft/deprecated/sunset/skipped 四态(共 11 态),转移表追加 D1-D7 + skipped 转移条目,fr2 §12 对齐说明修正。

### 4.7【P1】fr2 §2.1 T15 说"上游最近产物节点 changed"但状态机无"最近产物节点"定义

**位置**:fr2 §2.1 T15(行 77)、§FR2.5(行 704)

**冲突**:
- fr2 T15:"review → changed(reject approval 控制节点),上游最近产物节点 changed,递归失效下游"。
- §FR2.5(行 704):"approval reject → 上游最近产物节点 changed"。
- 但"上游最近产物节点"的判定算法未定义:approval 节点的上游可能是控制节点(fork/gate),如何穿透控制节点找到最近的产物节点?fr2 §8.2(行 875)说"递归找最近的产物节点 changed;若全是控制节点,标记 NO_ARTIFACT_UPSTREAM 告警",但递归穿透逻辑未给出。

**建议补充**:明确"上游最近产物节点"的查找算法(沿 deps 反向遍历,跳过 control 节点,找到第一个 artifact 节点;若无,标记 NO_ARTIFACT_UPSTREAM)。

---

## 5. 优先级汇总与建议补充内容

### 5.1 优先级分布

| 优先级 | 数量 | 处理建议 |
|---|---|---|
| P0(阻塞) | 8 | Phase 1 必须修正,否则实现时无法判断行为 |
| P1(重要) | 13 | Phase 1/2 修正,影响实现细节和验收 |
| P2(改进) | 8 | Phase 2/3 修正,不影响核心流程 |

### 5.2 P0 级修正建议汇总

| P0 编号 | 修正项 | 影响文件 | 修正方式 |
|---|---|---|---|
| P0-1 | 状态机统一为 11 态(追加 skipped) | 主 PRD §FR2.1、fr2 §2.1 | 主 PRD 状态机表追加 skipped;fr2 状态枚举追加 4 态;AC2.7 修正 |
| P0-2 | Cost 硬预算统一(以 fr3 为准) | 主 PRD §FR3.5 | 数值改为 10k/$5/$50/$4000;Task 级区分 token 超限(warning)和超时(硬中断) |
| P0-3 | Task description 改"协调提交产物引用" | 主 PRD §FR3.2 | description 字符串修正 |
| P0-4 | AC 编号去重 | fr3 §9 | fr3 AC 从 AC3.6 起,或主 PRD 合并 fr3 AC |
| P0-5 | AC2.3 区分 required/optional | 主 PRD §FR2.6 | AC2.3 追加"required 依赖"限定 |
| P0-6 | D1-D7 转移表和 guard 补全 | fr2 §2.1 | 追加 D1-D7 行(见 §1.1 建议) |
| P0-7 | addendum_cascade_node 节点补全 | 主 PRD §FR2.4 | StateGraph 节点表追加 addendum_cascade_node |
| P0-8 | key_constraints 提取算法定义 | 主 PRD §FR3.5、§FR5.2 | skill.yaml 增加 key_constraints_extractor;needs_human 改为标记非状态 |

### 5.3 建议直接粘贴的补充内容

#### 5.3.1 主 PRD §FR2.1 状态机表追加 skipped 态

```markdown
| `skipped` | 可选节点跳过(optional 节点未 done 且管线将终止) | optional 节点 + 管线 core 节点全 done | —(终态) |
```

状态流转图追加:

```mermaid
    blocked --> skipped : D8 optional节点+core全done
    ready --> skipped : D8 optional节点+core全done
```

#### 5.3.2 主 PRD §FR2.2 DAG 规则表追加 presence 和 coupling 语义

```markdown
| presence 语义 | presence=required:deps 边始终生效,参与 ready 判定和级联;presence=optional:deps 边生效但不参与 ready 判定(节点可 ready 即使 optional dep 未 done),级联时可选通知;presence=if_present:仅当 dep 节点在 materialized 管线中存在时才成为 required 依赖,否则 deps 边删除 |
| coupling × change_class 级联矩阵 | hard+breaking → hard_invalidate(清引用+blocked,递归);hard+compatible → soft_invalidate(ack 后保持);soft+breaking → soft_invalidate;soft+compatible → cascade_skip(通知);informational+任意 → cascade_skip(通知) |
| ready 判定公式 | `all(dep_state==done for dep in deps(nid) if dep.presence==required) and all(dep_state in (done,draft) for dep in deps(nid) if dep.presence==required and dep.strictness==accepts_draft)` |
```

#### 5.3.3 主 PRD §FR2.4 StateGraph 节点表追加 addendum_cascade_node

```markdown
| `addendum_cascade_node` | addendum 级联:按 cascade_level 分发 must/should/info 事件;must 级检查下游 incompatible_with,触发下游 → changed(委托 invalidate_node);超时检查(7 天,定时任务) | add_addendum 调用后 / 定时扫描超时 |
```

#### 5.3.4 主 PRD §FR3.2 Task description 修正

```python
tasks.append(Task(
    description=f"为节点 {node_id}({node['type']})协调提交产物引用:校验人员已产出的产物,通过 MCP submit_artifact 提 PR",
    agent=agent,
    expected_output={"status": "pr_submitted", "pr_id": "int", "node_id": "str"},
    context={
        "node_id": node_id,
        "instance_id": instance_id,
        "node_type": node["type"],
        "deps_info": get_deps_info(node_id, state),
        "key_constraints": extract_key_constraints(node_id, state),
        "participation_profile": state["participation"]["profile"],
        "skill": get_skill_summary(node["type"]),
    },
))
```

#### 5.3.5 主 PRD §FR3.5 硬预算统一

```markdown
**三层硬预算**(统一 fr3 §2.3):

| 层级 | 限额 | 触发动作 |
|---|---|---|
| Task 级 | 10k token(输入+输出) | 超限记录 warning;单 Task 超 60s 硬中断,节点标记 need_human=True |
| Agent 级 | product/server/client $5/日,design $3/日 | 超限告警 Langfuse,新 Task 排队等待配额刷新 |
| 管线级 | $50 | 超限告警,允许继续(不阻塞交付)但记审计 |
| 平台级 | $4000 | 全局降级(切便宜模型),通知 admin |

**needs_human 处理**:needs_human 不是节点状态,而是节点标记(`need_human: bool`)。节点状态保持 ready/in_progress,Dashboard 高亮告警,等待人工介入。
```

#### 5.3.6 主 PRD §FR2.6 AC2.3 修正

```markdown
- AC2.3: 多入边节点,部分 **required** 依赖 done 时仍 blocked;optional 依赖未 done 不影响 ready 判定(第五轮)
```

#### 5.3.7 主 PRD §FR2.6 AC2.7 修正

```markdown
- AC2.7: 管线 **core 节点**全 done 且 **optional 节点**全 done 或 skipped 时进入 completed(`completion.mode=core_nodes_done`);optional 节点失败不挡完成(自动 skipped)
```

#### 5.3.8 fr2 §2.1 转移表追加 D1-D8(见 §1.1)

#### 5.3.9 fr3 §9 AC 编号修正

```markdown
### FR3 补充验收(编号从 AC3.6 起,避免与主 PRD AC3.1-AC3.5 冲突)

- AC3.6: 4 个 agent 的 LLM 配置(模型/temperature/max_tokens)可配置且生效(config/llm.yaml)
- AC3.7: agent Task 失败时,瞬时错误自动重试 ≤ 3 次(指数退避),业务错误不重试
- AC3.8: LLM 不可用时,降级规则引擎能直提 PR(标记 fallback + 强制人工审)
- AC3.9: LangGraph ready 事件异步触发 CrewAI,LangGraph 不阻塞等待
- AC3.10: CompletionEvent 回写 LangGraph,失败 Task 节点回 ready + 通知人员
- AC3.11: 不同角色 Crew 并行执行(asyncio.gather),同角色节点串行
- AC3.12: agent 越权提交(如 server_agent 提交 design_asset)被 MCP 拒绝(FORBIDDEN_NODE_ROLE)
- AC3.13: 单 Task 超 60s 被中断,触发降级或失败通知
```

---

## 6. 评审结论

### 6.1 总体评估

§FR2 编排引擎和 §FR3 CrewAI 的核心设计(LangGraph StateGraph + 10/11 态状态机 + 依赖 DAG + CrewAI 4 角色 + 事件桥接)架构合理,经过 5 轮压力测试迭代已覆盖大量边界场景。但主 PRD 与深化文档之间存在 **8 项 P0 级不一致**(状态机态数、Cost 数值、Task description、AC 编号等),实现前必须统一。

### 6.2 关键风险

1. **状态机实现风险**:三份文档对态数描述不一致(10/11/7 态),fr2 深化完全未覆盖 draft/deprecated/sunset/skipped 的转移表和 guard,实现时状态机编码可能遗漏 4 态。
2. **Cost 预算实现风险**:数值矛盾 2 倍,超限动作冲突(硬中断 vs warning),可能导致 agent 行为异常(该中断不中断,或过度中断)。
3. **addendum 级联实现风险**:无 StateGraph 节点执行入口,P0-R5.12 修正项无法落地。

### 6.3 建议处理顺序

1. **立即修正 P0-1/P0-6**(状态机统一 11 态 + D1-D8 转移表):这是所有状态相关逻辑的基础。
2. **立即修正 P0-2/P0-8**(Cost 统一 + key_constraints 算法):影响 agent 行为护栏。
3. **立即修正 P0-3/P0-4/P0-5**(Task description + AC 编号 + AC2.3):影响验收和 agent 指令。
4. **立即修正 P0-7**(addendum_cascade_node):补全 StateGraph 节点表。
5. P1 项在 Phase 1/2 实现中逐步修正,P2 项在 Phase 3 修正。

---

**评审完成。** 共发现 29 项问题(8 P0 / 13 P1 / 8 P2),建议在实现前完成全部 P0 修正。
