# PRD 评审报告 Part 4:监控 + 数据模型 + NFR + 验收 + 附录

> **评审范围**:主 PRD §FR7 监控与可观测性、§5 数据模型、§6 接口规范、§7 非功能需求、§8 验收标准、§9 实施阶段、附录 D7-D11;深化文档 fr4-data-api.md 全文(§8 Postgres schema、§9 MCP 工具 schema、§10 工具矩阵)
> **评审维度**:内容缺失 / 边界模糊 / 细节不足 / 规则冲突
> **评审日期**:2026-08-04
> **主 PRD 版本**:v3.1
> **深化文档版本**:fr4-data-api.md v2.1

---

## 评审摘要

| 维度 | 发现数量 | P0 | P1 | P2 |
|---|---|---|---|---|
| 维度 1:内容缺失 | 19 | 9 | 7 | 3 |
| 维度 2:边界模糊 | 9 | 2 | 5 | 2 |
| 维度 3:细节不足 | 14 | 3 | 8 | 3 |
| 维度 4:规则冲突 | 14 | 8 | 5 | 1 |
| **合计** | **56** | **22** | **25** | **9** |

---

## 维度 1:内容缺失

### 1.1 [P0] §5 数据模型缺少 Node / Edge TypedDict 定义

**位置**:主 PRD §5.1 核心数据结构(L1297-L1461)

**问题**:任务要求审核的 Node/Edge 数据结构在 §5 中无独立 TypedDict 定义。§5.1 仅在 Pipeline YAML 示例(L1305-L1337)中以内联形式展示节点,未提取为独立的 `Node` / `Edge` TypedDict。对比深化文档 fr4-data-api.md §7 ER 图(L742-L753)和 §8.1 Postgres `node` / `node_dep` 表(L921-L948),数据库层有完整的表结构,但 §5 数据模型层缺少对应的 TypedDict,导致"数据模型"与"存储 schema"之间出现断层。

**影响**:开发者在实现 PipelineState.node_states(L670)时,无法从 §5 获取 Node 的字段约束,只能反向从 Postgres DDL 推导,违反"数据模型先行"原则。

**建议**:在 §5.1 补充 `Node` 和 `Edge`(或 `DepDeclaration`)的 TypedDict 定义,字段对齐 Postgres `node` / `node_dep` 表。

---

### 1.2 [P0] §5 数据模型缺少 HubRepoConfig 定义

**位置**:主 PRD §5.1(L1297-L1461);附录 D7(L1893-L1916)

**问题**:附录 D7(L1902)明确指出"RepoRegistry → HubRepoConfig(单一配置)",D8 P0 修正 #5(L1940)也声明"HubRepoConfig 增强(clone_strategy / lfs / capacity)→ §FR1.1"。但 §5 数据模型中完全没有 `HubRepoConfig` 的 TypedDict 或配置定义,§5.2 存储方案表(L1466-L1476)也未列出 HubRepoConfig 的存储位置。

**影响**:hub 仓的 clone_strategy、LFS 配置、容量策略等关键配置无数据模型支撑,开发时无从落地。

**建议**:在 §5.1 补充 `HubRepoConfig` TypedDict,字段至少包含 repo_url、clone_strategy、lfs_enabled、capacity_limit、git_provider 等。

---

### 1.3 [P0] §5 PipelineState 定义碎片化,§5.1 仅有 2 字段片段

**位置**:主 PRD §5.1(L1377-L1381)vs FR2.3(L662-L681)

**问题**:PipelineState 的完整定义在 FR2.3(L667-L681)共 13 个字段,但 §5.1(L1378-L1381)仅重复了 `artifact_refs` 和 `active_version` 两个字段,并以注释"# PipelineState 中 artifact_refs 改为多版本映射"引出。这造成:
- 同一数据结构在两处定义,§5.1 版本只有 2 字段,易误导读者
- 两处定义未交叉引用,§5.1 未注明"完整定义见 FR2.3"

**影响**:PipelineState 是核心状态结构,定义碎片化会导致实现时遗漏字段。

**建议**:§5.1 删除 PipelineState 片段,改为引用 FR2.3;或将完整定义统一放在 §5,FR2.3 引用 §5。

---

### 1.4 [P0] §5.1 ArtifactRef 缺少 current_owner 字段(D11 P0-R5.9 未回写)

**位置**:主 PRD §5.1 ArtifactRef(L1344-L1363);附录 D11(L2118)

**问题**:D11 P0-R5.9(L2118)明确声明"ArtifactRef 新增 current_owner 字段 → §5.1",标注为"**新增**(D10 未覆盖)"。但 §5.1 ArtifactRef TypedDict(L1344-L1363)中并无 `current_owner` 字段。同时,§FR2.5.1(L525)的 addendum 机制引用了 current_owner("author: str # 添加者(current_owner 或 admin)"),§FR4.1(L896)也有 `transfer_owner` 工具,均依赖此字段,但数据模型层缺失。

**影响**:transfer_owner 工具和 addendum 权限校验无数据支撑,D11 修正未落地。

**建议**:在 §5.1 ArtifactRef 补充 `current_owner: str` 字段。

---

### 1.5 [P0] §5.1 ArtifactRef 缺少 addenda 字段(D11 P0-R5.11 部分未回写)

**位置**:主 PRD §5.1 ArtifactRef(L1344-L1363)vs §FR2.5.1(L535-L541)

**问题**:§FR2.5.1(L535-L540)明确定义了"ArtifactRef.addenda 字段扩展",声明 `addenda: list[Addendum]`,但 §5.1 的 ArtifactRef TypedDict(L1344-L1363)未包含此字段。Addendum TypedDict(L522-L533)本身定义完整,但宿主字段在 §5.1 缺失,形成"有 Addendum 定义但无处挂载"的矛盾。

**影响**:addendum 机制的数据模型不完整,实现时 artifact_ref 序列化/反序列化会丢失 addenda。

**建议**:在 §5.1 ArtifactRef 补充 `addenda: list[Addendum]` 字段,并引用 §FR2.5.1 的 Addendum 定义。

---

### 1.6 [P0] §6 接口规范仅 5 个工具有完整 schema,约 29 个工具无 inputSchema/outputSchema

**位置**:主 PRD §6(L1479-L1606)

**问题**:§6.1-§6.5 仅为 submit_artifact、review_artifact_pr、approve_pr、reject_pr、get_dependencies 五个工具提供了完整的 inputSchema。§6.6(L1580-L1606)以简表形式列出约 29 个工具(含 update_progress、get_pipeline_state、request_approval、approve、reject、set_gate_policy、list_pending_prs、get_pr_detail、get_audit_log、export_compliance_report、soft_submit_artifact、subscribe_draft、cancel_pipeline、pause_pipeline、resume_pipeline、merge_pipelines、split_pipeline、report_consumption_status、report_generation_status、handle_security_incident、emergency_local_commit、sync_pending_artifacts、emergency_approve 等),仅给出"参数 / 返回"文字描述,无 JSON Schema。深化文档 fr4-data-api.md §9(L1250-L1947)也仅覆盖 14 个工具。

**影响**:约 20 个工具(含 D11 新增的 add_addendum、reack_addendum、list_addenda、transfer_owner、revoke_human_token)完全没有 inputSchema/outputSchema,无法进入开发。

**建议**:§6 对齐 FR4 全部工具(34 个),每个工具提供完整 inputSchema/outputSchema;或明确委托深化文档覆盖,并在 §6 交叉引用。

---

### 1.7 [P1] §6.6 工具表遗漏 5 个 FR4.1 已声明工具

**位置**:主 PRD §6.6(L1580-L1606)vs FR4.1(L881-L901)

**问题**:FR4.1 声明了 `add_addendum`(L896)、`reack_addendum`(L897)、`list_addenda`(L898)、`transfer_owner`(L899)、`revoke_human_token`(L900)五个工具,但 §6.6 的"其他工具"表未列出这五个工具,无任何参数/返回描述。

**影响**:这五个工具(尤其是 D11 P0 级的 transfer_owner 和 addendum 系列)在接口规范中完全缺席。

**建议**:§6.6 补充这五个工具的参数和返回说明,或提供完整 schema。

---

### 1.8 [P0] Postgres audit_log 表缺少 hash 链字段(prev_hash / entry_hash)

**位置**:深化 fr4-data-api.md §8.1 audit_log 表(L1074-L1089)vs 主 PRD §5.1 AuditLogEntry(L1388-L1411)

**问题**:主 PRD §5.1 AuditLogEntry TypedDict 包含 `prev_hash`(L1408)和 `entry_hash`(L1409)字段,FR7.2(L1216)和 NFR15(L1627)也要求"审计 hash 链 + WORM 存储"。但深化 fr4-data-api.md §8.1 的 `audit_log` 建表语句(L1074-L1089)完全没有 `prev_hash` 和 `entry_hash` 列。这意味着 hash 链在数据库层无存储位置,无法实现。

**影响**:NFR15(审计防篡改)和 AC7.6(hash 链完整性校验)无法落地,合规需求被阻断。

**建议**:在 audit_log 表补充 `prev_hash TEXT` 和 `entry_hash TEXT NOT NULL` 列,并增加索引 `idx_audit_hash_chain`。

---

### 1.9 [P0] Postgres artifact_ref 表主键不支持多版本,与 §5 多版本模型矛盾

**位置**:深化 fr4-data-api.md §8.1 artifact_ref 表(L951-L963)vs 主 PRD §5.1(L1377-L1379)、FR2.3(L671)

**问题**:§5.1 和 FR2.3 明确定义 `artifact_refs: dict[str, dict[str, ArtifactRef]]`(node_id -> {version -> ArtifactRef}),支持多版本共存。但 Postgres `artifact_ref` 表(L961)的主键为 `PRIMARY KEY (node_id, pipeline_id)`,即每个节点只能有一行记录,无法存储多版本。D8 P0 修正 #2(L1937)明确要求"ArtifactRef 多版本映射",但 schema 未对齐。

**影响**:多版本共存(D8 P0-2、场景 A14 契约 v2 不兼容共存)无法实现,是数据模型级阻断。

**建议**:主键改为 `PRIMARY KEY (node_id, pipeline_id, version)`,增加 `is_active BOOLEAN` 列标记当前生效版本,对齐 `active_version` 映射。

---

### 1.10 [P0] Postgres artifact_ref 表缺少 10+ 个 TypedDict 字段

**位置**:深化 fr4-data-api.md §8.1 artifact_ref 表(L951-L963)vs 主 PRD §5.1 ArtifactRef(L1344-L1363)

**问题**:§5.1 ArtifactRef TypedDict 有 17 个字段,Postgres artifact_ref 表仅有 9 列(node_id, pipeline_id, repo, path, commit, toolspec_framework, version, trace_id, merged_at),缺少以下关键字段:

| 缺失字段 | TypedDict 行号 | 重要性 |
|---|---|---|
| `artifact_kind` | L1351 | P0(区分 content/reference) |
| `artifact_qualifier` | L1352 | P0(official/mock/draft/experimental) |
| `external_repo` | L1354 | P0(引用型产物) |
| `external_commit` | L1355 | P0(引用型产物) |
| `commit_stability` | L1356 | P1(stable/volatile) |
| `content_integrity_hash` | L1357 | P0(完整性校验) |
| `classification` | L1358 | P0(密级,NFR17) |
| `provenance` | L1359 | P0(溯源,JSONB) |
| `derived_from` | L1360 | P1(派生产物) |
| `consumers` | L1361 | P1(消费订阅) |
| `addenda` | §FR2.5.1 L540 | P0(补充机制) |
| `current_owner` | D11 P0-R5.9 | P0(owner 交接) |

**影响**:D7/D8/D9/D11 的多项 P0 修正在数据库层无法落地。

**建议**:按 TypedDict 补全列,`provenance`/`consumers`/`addenda` 用 JSONB,主键改为多版本复合键。

---

### 1.11 [P0] Postgres audit_log 表缺少 10 个 TypedDict 字段

**位置**:深化 fr4-data-api.md §8.1 audit_log 表(L1074-L1089)vs 主 PRD §5.1 AuditLogEntry(L1388-L1411)

**问题**:AuditLogEntry TypedDict 有 22 个字段,Postgres audit_log 表有 14 列,缺少:`pr_url`、`node_type`、`artifact_path`、`content_integrity_hash`、`classification`、`reviewer`、`submitter`、`submitter_instance_id`、`prev_hash`、`entry_hash`。其中 `content_integrity_hash`(NFR15 完整性)、`classification`(NFR17 密级)、`prev_hash`/`entry_hash`(hash 链)均为 P0 级缺失。

**影响**:审计日志无法满足 NFR15(防篡改)和 NFR17(密级)要求。

**建议**:补全缺失列,`deps_at_review` 已有,需追加 hash 链和密级相关列。

---

### 1.12 [P1] Postgres agent 表与 RoleInstance TypedDict 字段不一致

**位置**:深化 fr4-data-api.md §8.1 agent 表(L1003-L1011)vs 主 PRD §5.1 RoleInstance(L1452-L1460)

**问题**:RoleInstance TypedDict 字段为 `instance_id`、`role`、`agent_config`、`allowed_node_types`、`allowed_external_repos`、`approvers`、`clearance`。Postgres `agent` 表字段为 `agent_id`、`role`、`allowed_node_types`、`status`、`max_concurrent`、`last_heartbeat`、`created_at`。不一致点:
- 标识字段名不同:`instance_id` vs `agent_id`
- 缺少 `agent_config`(LLM 配置)、`allowed_external_repos`(代码仓白名单)、`approvers`(审批人)、`clearance`(密级,NFR17 依赖)
- 多出 `status`、`max_concurrent`、`last_heartbeat`(TypedDict 未定义)

**影响**:NFR17(密级与 clearance 匹配)无法在 DB 层落地;RoleInstance 与 agent 表映射关系不明确。

**建议**:统一字段命名,补充缺失列,或在 §5.1 RoleInstance 补充 status/max_concurrent/last_heartbeat 字段。

---

### 1.13 [P1] §7 NFR 多数条款缺少量化指标

**位置**:主 PRD §7(L1609-L1631)

**问题**:18 条 NFR 中,仅 NFR4(<2s)、NFR5(<5s)、NFR9(≥1年)有明确量化。以下 NFR 无量化指标:

| NFR | 描述 | 缺失量化 |
|---|---|---|
| NFR1 | Langfuse 挂掉时降级 | 降级响应时间?WAL 补写时限? |
| NFR6 | 支持多 agent 并行 | 多少 agent?50?100? |
| NFR7 | 按角色权限限制 | 校验延迟? |
| NFR8 | 全链路 trace | trace 查询延迟? |
| NFR10 | docker compose | 资源限制? |
| NFR11 | 四级成本硬预算 | 各级预算上限?超限阈值? |
| NFR12 | session 级 token | token 有效期?续期窗口? |
| NFR13 | 安全扫描零容忍 | 扫描超时? |
| NFR14 | 外部依赖监控 | 检查频率?超时阈值? |
| NFR16 | 管线生命周期操作 | 操作延迟? |
| NFR17 | 密级与 clearance | 校验延迟? |
| NFR18 | Vault 管理 | 密钥轮换周期? |

深化 fr4-data-api.md §1(L39-L46)有部分量化(P95 < 2s、≥50 agent、60 req/min 等),但未回写主 PRD §7。

**影响**:NFR 不可测试,验收时无法判定通过/失败。

**建议**:每条 NFR 补充可测量指标,对齐深化文档中的数值。

---

### 1.14 [P1] §7 缺少 NFR19 / NFR20(附录 C5 声明但未回写)

**位置**:主 PRD §7(L1609-L1631)vs 附录 C5(L1769-L1771)

**问题**:附录 C5(L1771)声明"深化文档补充 NFR11 ~ NFR20(共 10 条)",指向 fr7-fr8-monitoring-visual.md §9。但主 PRD §7 仅到 NFR18,缺少 NFR19 和 NFR20。附录 C5 本身作为"修正记录"存在,但修正内容未回写到 §7 正文。

**影响**:NFR19/NFR20 的具体内容(推测为容量规划和灾备 RTO/RPO)在主 PRD 中缺失,实施时可能遗漏。

**建议**:将 NFR19/NFR20 从深化文档回写到 §7 正文。

---

### 1.15 [P1] 数据生命周期不完整,仅 node_event 和 audit_log 有保留期

**位置**:深化 fr4-data-api.md §8.4(L1201-L1225)

**问题**:§8.4 分区策略表(L1222-L1225)仅定义了 `node_event`(6 个月)和 `audit_log`(≥12 个月)的保留期和归档策略。以下数据的生命周期完全未定义:

| 数据 | 存储位置 | 保留期 | 清理策略 |
|---|---|---|---|
| artifact_ref(历史版本) | Postgres | 未定义 | 未定义 |
| pull_request(已合并/关闭) | Postgres | 未定义 | 未定义 |
| pr_review | Postgres | 未定义 | 未定义 |
| approval_request(已决) | Postgres | 未定义 | 未定义 |
| role_assignment(已完成) | Postgres | 未定义 | 未定义 |
| quota_usage(历史周期) | Postgres | 未定义 | 未定义 |
| Langfuse trace | Langfuse Postgres | 未定义 | 未定义 |
| 审计 WAL(降级本地文件) | 本地文件系统 | 未定义 | 未定义 |
| cross_pipeline_reference | Postgres | 未定义 | 未定义 |
| LangGraph checkpoint | Postgres | 未定义 | 未定义 |

**影响**:数据无限增长,生产环境面临存储膨胀和查询性能退化。

**建议**:为每类数据定义保留期、清理 cron 频率和归档策略。

---

### 1.16 [P1] ALR-13~15 告警规则在主 PRD §FR7 未定义

**位置**:主 PRD §FR7.3 Dashboard(L1233)

**问题**:§FR7.3(L1233)提到"Agent 行为基线:安全事件 + 成本 span → ALR-13~15 循环/越权/成本异常告警",但 ALR-13、ALR-14、ALR-15 的具体规则(触发条件/阈值/告警通道/抑制策略)在主 PRD 中完全未定义。D9 P0 修正 #18(L2012)声明"agent 行为基线与告警(ALR-13~15)→ §FR7",但 §FR7 正文仅有引用,无定义。

**影响**:agent 行为护栏(D9 根因 5)无法实现,agent 循环/越权/成本异常无告警机制。

**建议**:在 §FR7 补充 ALR-13~15 的完整规则定义,或明确引用 fr7-fr8-monitoring-visual.md 的对应章节。

---

### 1.17 [P1] §8 验收用例缺少 NFR13-NFR18 的测试用例

**位置**:主 PRD §8.1(L1636-L1651)

**问题**:§8.1 共 12 个端到端测试用例(TC-01 ~ TC-12),仅覆盖 HappyPath、并行、级联、门禁、审批、监控、降级等场景。以下 NFR 无对应测试用例:

| NFR | 主题 | 缺失用例 |
|---|---|---|
| NFR13 | 安全扫描零容忍 | 无安全扫描阻断测试 |
| NFR14 | 外部依赖健康监控 | 无外部失效→deprecated 测试 |
| NFR15 | 审计 hash 链 | 无 hash 链完整性校验测试 |
| NFR16 | 管线生命周期 | 无 cancel/pause/resume/merge/split 测试 |
| NFR17 | 密级与 clearance | 无低密级访问高密级产物被拒测试 |
| NFR18 | Vault 密钥管理 | 无密钥轮换/永不硬编码测试 |

**影响**:NFR13-18 无法通过端到端用例验证,验收时遗漏风险高。

**建议**:补充 TC-13 ~ TC-18 覆盖上述 NFR。

---

### 1.18 [P1] §8 验收用例缺少 D8-D11 新增机制的测试

**位置**:主 PRD §8.1(L1636-L1651)

**问题**:§8.1 的 12 个用例基于 v2.0 设计,未覆盖 D8-D11 新增的核心机制:

| 缺失场景 | 来源 | 重要性 |
|---|---|---|
| 多版本 ArtifactRef 共存 | D8 P0-2 | P0 |
| addendum 附加 + must 级联 | D11 P0-R5.11/12 | P0 |
| owner 交接(transfer_owner) | D11 P0-R5.10 | P0 |
| 管线级生命周期(cancel/pause/merge/split) | D9 P0-6/7 | P0 |
| hub 仓降级(emergency_*) | D8 P0-4 | P1 |
| 安全事件闭环(handle_security_incident) | D9 P0-16 | P1 |
| 产物消费订阅(report_consumption_status) | D9 P0-9/10 | P1 |
| RoleInstance 多团队实例 | D8 P0-8 | P1 |
| 参与拓扑(server_only/no_design) | D10 B1-B5 | P1 |

**影响**:D8-D11 的 P0 修正无验收用例,无法验证是否正确实现。

**建议**:补充对应测试用例,对齐 D8-D11 的 P0 修正项。

---

### 1.19 [P2] 深化 fr4-data-api.md §10 标题与任务描述的"数据生命周期"不符

**位置**:深化 fr4-data-api.md §10(L1950)

**问题**:任务描述称深化文档"重点是 §10 数据生命周期",但 fr4-data-api.md §10 实际标题为"工具调用矩阵速查"(L1950),内容是角色→工具→错误码映射表和工具→LangGraph action 映射表。数据生命周期相关内容实际在 §8.4"分区与迁移策略"(L1201-L1237),且不完整(见发现 1.15)。

**影响**:数据生命周期在深化文档中无独立章节,分散在 §8.4 分区策略中,且覆盖不全。

**建议**:在深化文档或主 PRD §5.2 补充独立的"数据生命周期"章节,覆盖全量数据的保留/清理/归档策略。

---

## 维度 2:边界模糊

### 2.1 [P0] Langfuse 旁路降级的具体策略和顺序保证未定义

**位置**:主 PRD §FR7.2(L1209-L1216)、NFR1(L1613);深化 fr4-data-api.md §2.3(L145)

**问题**:§FR7.2(L1213)声明"不阻塞主流程:Langfuse 调用失败时降级",L1216 声明"审计 hash 链降级:先将事件持久化到本地 WAL,恢复后补写 hash 链"。但以下边界未明确:
- **降级触发条件**:Langfuse 超时多少毫秒后降级?是同步等待还是 fire-and-forget?
- **WAL 补写顺序保证**:多个事件在 WAL 中待补写时,如何保证 hash 链的 prev_hash 顺序?WAL 中事件跨进程/跨实例时如何排序?
- **WAL 与 DB 的一致性**:WAL 补写到 DB 时,如果 DB 也不可用,如何处理?
- **降级期间查询**:Dashboard 在 Langfuse 降级期间查询 trace 时返回什么?空结果还是缓存?
- **降级恢复检测**:如何检测 Langfuse 恢复?健康检查频率?

深化 §2.3(L145)仅定义了 `INTERNAL_LANGFUSE_DOWN` 错误码(HTTP 200,不返回错误),但无降级流程细节。

**影响**:降级实现方案不唯一,可能导致 hash 链断裂或事件丢失。

**建议**:定义完整的降级流程:超时阈值(如 500ms)、WAL 格式与排序策略、补写幂等性、恢复探测机制。

---

### 2.2 [P0] audit hash 链的信任边界(防 DBA 篡改)未定义

**位置**:主 PRD §5.1 AuditLogEntry(L1408-L1409)、NFR15(L1627);深化 fr4-data-api.md §8.3(L1186-L1199)

**问题**:NFR15 要求"审计日志采用 hash 链 + WORM 存储,支持合规导出与完整性校验"。深化 §8.3(L1186-L1199)通过 Postgres 触发器禁止 UPDATE/DELETE。但信任边界未明确:
- **DBA(superuser)可绕过**:Postgres superuser 可 `ALTER TABLE ... DISABLE TRIGGER`,直接修改或删除审计行,hash 链即被破坏
- **无外部锚定**:hash 链仅链式存储在 DB 内,无定期将链头 hash 写入外部不可变存储(如 S3 Object Lock、区块链、独立日志服务器)的机制
- **hash 计算方式未定义**:`entry_hash` 是 SHA-256(prev_hash + 哪些字段)?字段顺序如何?
- **prev_hash 为空时的处理**:第一条记录的 prev_hash 是什么?固定值?空字符串?

**影响**:有 DBA 权限的内部人员可篡改审计日志而不被发现,不满足合规审计要求。

**建议**:定义 hash 计算公式;增加链头 hash 定期外部锚定(如每 N 分钟写入 WORM 存储);明确 DBA 权限隔离策略(审计表用独立 ROLE,仅授予 INSERT)。

---

### 2.3 [P1] NFR"本期落地"与"v3 规划"边界不一致

**位置**:主 PRD §1.4(L72);深化 fr4-data-api.md §5.4(L526-L537)

**问题**:§1.4(L72)声明"成本硬预算本期落地;配额管理 v3 规划"。但:
- NFR11(L1623)声明"Task/Agent/管线/平台四级成本硬预算,超限触发降级或人工介入"——本期落地
- 深化 fr4-data-api.md §5.4(L526-L537)定义了详细的**配额设计**(日调用 10000 req、月调用 200000 req、日 submit 100 次等),包括 Postgres `quota_usage` 表(L1037-L1045)和 Redis 实时计数——这属于"配额管理"
- §1.4 说配额管理是 v3,但深化文档已设计配额表和限流逻辑,且 §8.2 验收检查清单未区分

**矛盾**:§1.4 将配额管理划为 v3,但深化文档已将配额设计为 Phase 2(P1 优先级,L2001),实施阶段 §9(L1688-L1698)Phase 2 也在"角色协调 + 监控"范围内。

**影响**:开发团队无法判断配额管理是否本期实现。

**建议**:明确"限流(per-agent QPS/并发)"本期落地、"配额(日/月调用上限)"是否同期;修正 §1.4 或深化文档的优先级声明。

---

### 2.4 [P1] §1.4"不做 RBAC"与 §3.2 权限矩阵 + 深化 RBAC 中间件矛盾

**位置**:主 PRD §1.4(L71);§3.2(L156-L180);深化 fr4-data-api.md §3.3(L264-L305)

**问题**:§1.4(L71)声明"不做多租户/RBAC(v3 规划)"。但:
- §3.2(L156-L180)定义了完整的角色权限矩阵(product/server/design/client/reviewer/admin → 工具映射)
- 深化 §3.3(L264-L305)实现了 `AuthzMiddleware`,包含 `ROLE_TOOLS` 白名单和 `ROLE_NODE_TYPES` 校验——这是标准的 RBAC 实现
- 深化 §3.3(L277-L283)的 `ROLE_NODE_TYPES` 映射就是 RBAC 中的"角色-资源"权限模型

**矛盾**:§1.4 说不做 RBAC,但 §3.2 和深化 §3.3 已经实现了 RBAC。可能 §1.4 的"RBAC"特指"企业级 RBAC(如多租户隔离、自定义角色、细粒度资源权限)",而非"基础角色权限"。但这一区分未在文档中说明。

**影响**:范围边界模糊,开发团队可能误解为"不需要权限校验"。

**建议**:§1.4 明确区分"基础角色权限(本期)"和"企业级 RBAC(多租户/自定义角色,v3)"。

---

### 2.5 [P1] 数据保留策略的边界(产物/审计/日志分别保留多久)未全面定义

**位置**:主 PRD §5.2(L1462-L1476);深化 fr4-data-api.md §8.4(L1222-L1225)

**问题**:§5.2 存储方案表(L1466-L1476)列出 8 类数据的存储位置,但仅 `audit_log` 在 NFR9(L1621)声明"保留 ≥ 1 年",深化 §8.4 补充了 `node_event`(6 个月)和 `audit_log`(≥12 个月)。以下数据的保留边界完全未定义:
- **产物内容**(git 仓库):产物仓库中的历史版本、已 sunset 产物保留多久?
- **Langfuse trace**:自托管但无保留期和清理策略
- **审计 WAL**(本地文件):降级时写入,补写后是否删除?保留多久?
- **PipelineState**(LangGraph checkpointer):已 completed/cancelled 的管线 state 保留多久?
- **PR 数据**:已 merged/closed 的 PR 保留多久?
- **cross_pipeline_reference**:目标产物 sunset 后引用记录保留多久?

**影响**:数据无清理策略,存储成本持续增长;合规数据(审计)与非合规数据(trace)未区分保留级别。

**建议**:按数据类型定义保留期:合规数据(审计)≥1 年;运维数据(trace/node_event)6 个月;业务数据(产物/PR)与管线生命周期绑定;WAL 补写后即删。

---

### 2.6 [P1] 成本硬预算的"降级或人工介入"边界不明确

**位置**:主 PRD NFR11(L1623);§FR7.3 成本归因(L1232)

**问题**:NFR11 声明"Task/Agent/管线/平台四级成本硬预算,超限触发降级或人工介入"。但:
- **各级预算上限未定义**:Task 级预算多少?Agent 级?管线级?平台级?
- **"降级"具体动作**:Task 超限是终止 Task 还是降低 LLM 模型等级?Agent 超限是停止接收新任务还是完全终止?管线超限是暂停管线还是拒绝新提交?
- **"人工介入"触发条件**:什么级别的超限触发人工介入而非自动降级?
- **成本归因粒度**:`agent.cost` span(L1206)记录 token_count 和 cost_usd,但 Task 级成本如何从 Agent 级拆分?管线级如何从 Task 级汇总?

**影响**:成本控制无法实现,超限行为未定义。

**建议**:定义四级预算默认值、超限动作矩阵(降级/终止/告警/人工)、成本归因计算公式。

---

### 2.7 [P1] 附录修正与正文章节的一致性边界未明确管理

**位置**:主 PRD 附录 D7-D11(L1893-L2147)

**问题**:附录 D7-D11 声明了大量"影响章节"和"P0 已回写",但多处修正未实际回写正文(详见维度 4 发现 4.4-4.8)。附录作为"压力测试修正汇总",与正文之间缺少一致性的管理机制:
- D10(L2047-L2054)声称"P0 已回写本 PRD",但未说明回写的验证方式
- D11(L2106-L2127)列出 17 项 P0 修正,标注影响章节,但多项未回写(current_owner、addenda、skipped 态等)
- 附录 C(L1746-L1771)作为"深化修正记录",与附录 D 的"压力测试修正"之间存在交叉但不统一

**影响**:读者信任附录的"已回写"声明,但实际正文未更新,导致实现时遗漏修正。

**建议**:建立"修正追溯矩阵"(修正编号 → 正文行号 → 验证状态),在附录中明确标注每项修正的回写状态。

---

### 2.8 [P2] 外部依赖健康监控的检查频率/超时/重试边界未定义

**位置**:主 PRD §5.1 ExternalHealthMonitor(L1437-L1445);NFR14(L1626)

**问题**:ExternalHealthMonitor(L1440-L1444)的 `run()` 方法遍历所有 done 产物的 external_resources 执行 `check_reachable`,但:
- 检查频率未定义(每 5 分钟?每小时?)
- `check_reachable` 的超时阈值未定义(3s?10s?)
- 检查失败后的重试策略未定义(连续 N 次失败才触发 deprecated?还是首次失败即触发?)
- 外部资源类型(figma URL / 第三方 API / 代码仓 commit)的检查方式差异未区分

**影响**:外部依赖监控可能过于敏感(误报)或过于迟钝(漏报)。

**建议**:定义检查频率(如每 15 分钟)、超时(5s)、连续失败阈值(3 次才 deprecated)、按资源类型区分检查逻辑。

---

### 2.9 [P2] hub 仓降级的"emergency_*"工具使用边界未明确

**位置**:主 PRD §6.6(L1603-L1605);FR4.3(L937-L944);D8 P0-4(L1939)

**问题**:FR4.3 定义了 `emergency_local_commit`、`sync_pending_artifacts`、`emergency_approve` 三个 hub 仓降级工具,但:
- **触发条件**:hub 仓不可达到什么程度触发降级?(完全不可达?超时?部分分支不可用?)
- **退出条件**:hub 仓恢复后如何从降级模式退出?`sync_pending_artifacts` 完成后是否自动退出?
- **权限边界**:降级期间仅 admin 可操作?其他角色工具是否全部拒绝?
- **数据一致性**:降级期间本地暂存的 manifest 与 hub 仓恢复后的状态如何保证一致?冲突如何处理?
- **审批有效性**:`emergency_approve` 记录的审批在 hub 仓恢复后是否需要重新审核?

**影响**:hub 仓降级是 D8 P0 级修正,但操作边界不明确,可能产生数据不一致。

**建议**:定义降级模式的进入/退出条件、权限模型、数据一致性保障和冲突处理策略。

---

## 维度 3:细节不足

### 3.1 [P0] ArtifactRef 的 provenance 和 consumers 字段类型约束不完整

**位置**:主 PRD §5.1 ArtifactRef(L1344-L1363)、Provenance(L1365-L1375)

**问题**:
- `provenance: Provenance`(L1359)引用了 Provenance TypedDict,但 Provenance 的字段(如 `llm_prompt_hash`、`business_source`)无格式约束(如 hash 长度、枚举值)
- `consumers: list[ArtifactConsumer]`(L1361)引用了 `ArtifactConsumer` 类型,但 §5.1 未定义 `ArtifactConsumer` TypedDict,全文搜索也未找到定义
- `derived_from: str | None`(L1360)声明为 node_id,但无格式约束(如 `{pipeline_id}.{local_id}` 格式)
- `commit_stability: str`(L1356)声明为"stable | volatile"但未用 `Literal` 约束

**影响**:`ArtifactConsumer` 类型缺失导致 consumers 字段无法实现;其他字段缺少约束可能导致运行时数据不一致。

**建议**:补充 `ArtifactConsumer` TypedDict 定义;用 `Literal` 约束枚举字段;定义 node_id 格式 pattern。

---

### 3.2 [P0] Postgres 索引策略不完整,多版本查询和密级过滤无索引

**位置**:深化 fr4-data-api.md §8.2(L1109-L1160)

**问题**:索引设计缺少以下场景的覆盖:
- **多版本 artifact_ref 查询**:如果按建议 1.9 修改主键为 (node_id, pipeline_id, version),需增加 `idx_artifact_ref_active`(node_id, pipeline_id) WHERE is_active = true 的部分索引,但当前无此索引
- **classification 过滤**:NFR17 要求密级与 clearance 匹配,查询产物时需按 classification 过滤,但 artifact_ref 表无 classification 列(见发现 1.10),更无索引
- **content_integrity_hash 查询**:变更追溯需按 hash 反查,但无索引
- **derived_from 查询**:派生产物溯源需按 derived_from 反查,但无索引
- **current_owner 查询**:owner 交接时需按 owner 查询其名下产物,但无索引
- **cross_pipeline_reference 表无索引**:target_node_id 和 target_pipeline_id 无索引,deprecated 通知时反查引用方管线效率低

**影响**:多版本查询和密级过滤全表扫描,性能不达标。

**建议**:补全上述索引,对齐 D8-D11 新增字段。

---

### 3.3 [P0] MCP 工具 error response 格式在主 PRD §6 未定义

**位置**:主 PRD §6(L1479-L1606)vs 深化 fr4-data-api.md §2.1(L52-L87)

**问题**:深化 §2.1(L52-L87)定义了标准错误响应结构(ok/error.code/error.message/error.http_status/error.details/error.trace_id/error.request_id/error.retryable),以及 37 个错误码全量表(L111-L148)。但主 PRD §6 的工具规范中:
- §6.1-§6.5 的返回示例仅有成功响应(如 `{"ok": true, "pr_id": 42, "status": "pending_review"}`),无错误响应示例
- §6.6 的简表仅列出工具参数和返回,无错误码
- 主 PRD 未引用深化 §2 的错误码体系

**影响**:开发者阅读主 PRD 时不知道错误响应格式,可能自行实现不一致的错误处理。

**建议**:§6 开头补充错误响应格式说明,引用深化 §2;或在每个工具 schema 中增加 errorResponse 示例。

---

### 3.4 [P1] NFR 具体数值缺失(延迟/吞吐/可用性)

**位置**:主 PRD §7(L1609-L1631)

**问题**:除 NFR4(<2s)、NFR5(<5s)外,以下性能/吞吐/可用性指标未量化:
- **可用性**:无 SLA 指标(如 99.9% uptime),NFR1 仅说"降级"无可用性目标
- **吞吐**:NFR6 仅说"支持多 agent 并行",无具体数值(深化 §1 L43 有"≥ 50 agent",但未回写)
- **限流**:无 per-agent/per-tool/per-pipeline 限流数值(深化 §5.1 L475-L479 有详细数值,未回写)
- **并发**:无单 agent 并发上限(深化 §5.1 L476 有"≤ 5 并发",未回写)
- **LangGraph 超时**:无 langgraph_invoke 超时(深化 §6.3 L646-L650 有"30s 同步/300s 异步",未回写)
- **SSE 推送延迟**:§8.1 TC-11(L1650)提到"< 1s 延迟",但 §7 NFR 中无此项

**影响**:NFR 不可测试,深化文档的量化指标未纳入主 PRD 的正式需求。

**建议**:将深化文档的量化指标回写 §7,补充 SLA/吞吐/限流/超时等 NFR。

---

### 3.5 [P1] 数据清理的 cron 频率和批量大小未指定

**位置**:深化 fr4-data-api.md §8.4(L1201-L1225)

**问题**:§8.4 提到 `node_event` 和 `audit_log` 按月分区,保留 6/12 个月,归档到 S3/冷存储。但:
- **分区创建频率**:`pg_partman` 自动创建,但配置参数(如 ` premake` 值)未定义
- **归档 cron 频率**:每月归档一次?每天检查?
- **批量大小**:归档和删除时每批多少行?避免长事务锁表
- **归档格式**:S3 上的存储格式(Parquet?JSON?CSV?)
- **归档恢复**:冷存储数据如何查询?需要恢复时流程是什么?
- **过期分区删除**:分区过期后是直接 DROP 还是先归档再 DROP?

**影响**:数据清理运维流程不明确,可能导致锁表或存储超限。

**建议**:定义 pg_partman 配置、归档 cron(如每日 02:00)、批量大小(如 10000 行/批)、归档格式和恢复流程。

---

### 3.6 [P1] Langfuse span 的具体属性和采样策略不完整

**位置**:主 PRD §FR7.1 埋点设计(L1195-L1207)

**问题**:§FR7.1 的埋点表(L1199-L1207)列出了 7 类 span 及关键属性,但:
- **采样策略未定义**:是 100% 采样?还是 head-based/tail-based 采样?高流量场景如何降采样?
- **span 状态码**:span 的 status(OK/ERROR)如何设置?哪些工具失败标 ERROR?
- **span duration**:span 是否记录 duration?是否有 duration 上限(如 > 30s 标异常)?
- **context propagation**:trace_id 如何从 MCP 层传递到 LangGraph 层?是通过 LangGraph config 还是环境变量?
- **`agent.cost` span 的成本计算**:token_count 和 cost_usd 如何计算?是调用 LLM provider API 获取还是本地估算?不同模型的价格表从哪里来?
- **`security.incident` span**:incident_id 如何生成?与 `handle_security_incident` 工具的 incident_id 是否一致?

**影响**:Langfuse 集成的实现细节不完整,可能导致 trace 数据不一致或成本归因不准。

**建议**:补充采样策略(如 100% for errors, 10% for success)、context propagation 方式、成本计算模型。

---

### 3.7 [P1] hash 链计算方式未定义

**位置**:主 PRD §5.1 AuditLogEntry(L1408-L1409);NFR15(L1627)

**问题**:AuditLogEntry 包含 `prev_hash` 和 `entry_hash`,但:
- **hash 算法**:SHA-256?SHA-3?BLAKE3?
- **hash 输入**:entry_hash = SHA-256(prev_hash + 哪些字段)?字段拼接顺序如何?用什么分隔符?
- **prev_hash 为空的处理**:第一条记录(prev_hash 为空或 null)的 entry_hash 如何计算?
- **编码方式**:字段值是 UTF-8 编码拼接?还是 JSON 序列化后拼接?
- **hash 链校验流程**:AC7.6(L1244)要求"hash 链可校验完整性",但校验流程未定义(遍历全部记录?抽样校验?按时间范围校验?)

**影响**:hash 链实现不唯一,不同开发者可能实现不同的 hash 计算逻辑,导致校验失败。

**建议**:定义 hash 计算公式,如 `entry_hash = SHA-256(prev_hash || "|" || action || "|" || node_id || "|" || ts)`,明确编码和拼接规则。

---

### 3.8 [P1] MCP 工具 schema 在主 PRD §6 和深化 §9 之间存在大量字段差异

**位置**:主 PRD §6.1(L1483-L1505)vs 深化 fr4-data-api.md §9.1(L1262-L1309)

**问题**:以 `submit_artifact` 为例,两个版本的 inputSchema 差异显著:

| 字段 | 主 PRD §6.1 | 深化 §9.1 | 差异 |
|---|---|---|---|
| `artifact_kind` | ✅ required | ❌ 不存在 | 主 PRD 有,深化无 |
| `artifact_qualifier` | ✅ required | ❌ 不存在 | 主 PRD 有,深化无 |
| `classification` | ✅ required | ❌ 不存在 | 主 PRD 有,深化无 |
| `external_repo` | ✅ optional | ❌ 不存在 | 主 PRD 有,深化无 |
| `external_commit` | ✅ optional | ❌ 不存在 | 主 PRD 有,深化无 |
| `version` | ❌ 不存在 | ✅ required | 深化有,主 PRD 无 |
| `branch` pattern | 无约束 | `^feat/(product\|server\|design\|client)/...` | 深化有 pattern |
| `additionalProperties` | 未声明 | `false` | 深化更严格 |

此外,§6.1 的 outputSchema 完全缺失(仅文字返回 `{"ok": true, "pr_id": 42, "status": "pending_review"}`),深化 §9.1 有完整 outputSchema。

**影响**:开发者使用哪个版本?两个版本的必填字段不同,实现行为不一致。

**建议**:以主 PRD §6.1 为准(包含 D7 的 artifact_kind 等字段),深化 §9 对齐;同时补充 version 字段(深化有但主 PRD 无,而 §5.1 ArtifactRef 有 version 字段)。

---

### 3.9 [P1] branch pattern 与 D8 P0-4 路径修正不一致

**位置**:深化 fr4-data-api.md §9.1(L1272);主 PRD 附录 D8 P0-4(L1855)

**问题**:D8 P0-4(L1855)声明"产物路径改 `features/{pipeline_id}/...`",但深化 §9.1(L1272)的 branch pattern 仍为 `^feat/(product|server|design|client)/[a-z_]+-[0-9]+$`,未更新为 `features/{pipeline_id}/` 前缀。主 PRD §6.1(L1492)的 branch 描述仅为"feat 分支名",无 pattern 约束。

**影响**:branch/路径命名规范在三个位置(D8 P0-4、深化 §9.1、主 PRD §6.1)互不一致。

**建议**:统一 branch/路径命名规范,对齐 D8 P0-4 的 `features/{pipeline_id}/` 前缀。

---

### 3.10 [P1] Postgres 多表缺少 created_at / updated_at 审计字段

**位置**:深化 fr4-data-api.md §8.1(L901-L1107)

**问题**:以下表缺少 `created_at` 和/或 `updated_at` 时间戳字段,不利于数据审计和增量同步:

| 表 | 缺少字段 |
|---|---|
| `artifact_ref` | 有 `merged_at`,无 `updated_at`(多版本时无法记录版本更新时间) |
| `gate_policy` | 有 `updated_at`,无 `created_at` |
| `approval_request` | 有 `requested_at`/`decided_at`,无 `updated_at` |
| `pull_request` | 有 `opened_at`/`merged_at`,无 `updated_at` |
| `pr_review` | 有 `reviewed_at`,无 `updated_at` |
| `audit_log` | 有 `ts`,无 `updated_at`(append-only 可不需要) |
| `skill` | 有 `updated_at`,无 `created_at` |
| `cross_pipeline_reference` | 有 `registered_at`,无 `updated_at` |

**影响**:数据变更时间不可追溯,增量同步和调试困难。

**建议**:统一补充 `created_at`/`updated_at`,使用 `DEFAULT now()` 和触发器自动维护。

---

### 3.11 [P2] 分区表 pg_partman 配置细节不足

**位置**:深化 fr4-data-api.md §8.4(L1208-L1218)

**问题**:§8.4 提到"pg_partman 自动维护"和"后续月份由 pg_partman 自动创建",但:
- pg_partman 扩展版本要求未指定
- `premake` 参数(预创建多少个未来分区)未定义
- 分区表命名规则未完整定义(如 `node_event_2026_08` 是手动示例,pg_partman 的默认命名可能不同)
- 分区表的默认表空间和索引表空间未指定
- 旧分区的 detach/drop 策略(detach 后保留多久才 drop)未定义

**影响**:分区运维配置不完整,可能需要额外排查。

**建议**:补充 pg_partman 配置参数和分区运维策略。

---

### 3.12 [P2] 外部依赖健康检查的 check_reachable 实现细节缺失

**位置**:主 PRD §5.1 ExternalHealthMonitor(L1437-L1445)

**问题**:`ExternalHealthMonitor.run()` 方法(L1440-L1444)调用 `self.check_reachable(resource)`,但:
- `resource` 的数据结构未定义(是 URL 字符串?还是包含 type/url/headers 的对象?)
- `check_reachable` 的实现方式未定义(HTTP GET?git ls-remote?TCP connect?)
- 不同类型资源(figma URL / 第三方 API / 代码仓 commit)的检查方式差异未区分
- 检查结果的数据结构未定义(仅 boolean?还是包含 status_code/latency/error_message?)

**影响**:ExternalHealthMonitor 实现方案不唯一。

**建议**:定义 resource 数据结构、check_reachable 的分类型实现、检查结果格式。

---

### 3.13 [P2] Langfuse trace 保留期和清理策略未定义

**位置**:主 PRD §5.2(L1473);深化 fr4-data-api.md §5.4(L535)

**问题**:§5.2(L1473)声明"Langfuse trace → Langfuse 自托管(Postgres) → 独立存储",深化 §5.4(L535)声明"Langfuse trace 量 → 不限 → Langfuse 自托管,无配额"。但:
- trace 数据保留多久?无限期保留会导致 Postgres 膨胀
- 清理 cron 频率?
- 是否有冷热分层(近期 trace 在热 DB,历史 trace 归档)?
- Langfuse 自托管 Postgres 与管理方 Postgres 是否共享实例?资源隔离如何保证?

**影响**:Langfuse trace 无限增长可能拖垮数据库。

**建议**:定义 trace 保留期(如 90 天热数据 + 1 年冷归档)和清理策略。

---

### 3.14 [P2] 渐深 §9 工具 outputSchema 缺少 _meta 字段定义

**位置**:深化 fr4-data-api.md §9(L1252-L1256)

**问题**:§9 开头的"通用约定"(L1252-L1256)声明"所有工具响应带 `_meta.trace_id` 和 `_meta.rate_limit`",且 §5.5(L539-L561)定义了 `_meta` 结构。但 §9.1-§9.14 的 outputSchema 中均未包含 `_meta` 字段,outputSchema 的 `required` 数组也未提及 `_meta`。

**影响**:outputSchema 与通用约定不一致,客户端按 outputSchema 校验响应时会因 `_meta` 字段失败(additionalProperties 默认允许,但如果设为 false 则报错)。

**建议**:在每个工具的 outputSchema 中补充 `_meta` 字段定义,或在通用约定中声明"outputSchema 不含 _meta,由中间件统一注入"。

---

## 维度 4:规则冲突或矛盾

### 4.1 [P0] §5.1 PipelineState 片段与 FR2.3 PipelineState 完整定义不一致

**位置**:主 PRD §5.1(L1377-L1381)vs FR2.3(L662-L681)

**问题**:PipelineState 在两处定义:
- §5.1(L1378-L1381):仅 2 个字段(`artifact_refs`、`active_version`)
- FR2.3(L667-L681):13 个字段(`pipeline_status`、`participation`、`node_states`、`artifact_refs`、`active_version`、`draft_refs`、`draft_subscribers`、`events`、`pending_approvals`、`role_assignments`、`pending_prs`、`cascade_pending`、`external_health`)

§5.1 版本未引用 FR2.3,也未注明"完整定义见 FR2.3",形成同一数据结构的两个不一致定义。

**影响**:开发者可能以 §5.1 的 2 字段版本为准,遗漏 11 个字段。

**建议**:删除 §5.1 的 PipelineState 片段,改为"PipelineState 完整定义见 §FR2.3"。

---

### 4.2 [P0] §6.1 submit_artifact inputSchema 与深化 §9.1 严重不一致

**位置**:主 PRD §6.1(L1483-L1505)vs 深化 fr4-data-api.md §9.1(L1262-L1291)

**问题**:同一工具 `submit_artifact` 的 inputSchema 在两个文档中字段集差异巨大(详见维度 3 发现 3.8):
- 主 PRD §6.1 required: `["node_id", "repo", "branch", "path", "toolspec_framework", "artifact_kind", "artifact_qualifier", "classification"]`(8 个必填)
- 深化 §9.1 required: `["node_id", "repo", "branch", "path", "toolspec_framework", "version"]`(6 个必填)
- 主 PRD 有 `artifact_kind`/`artifact_qualifier`/`classification`/`external_repo`/`external_commit`,深化无
- 深化有 `version`,主 PRD 无
- §5.1 ArtifactRef 有 `version` 字段(L1350),支持主 PRD 应该也有,但 §6.1 缺失

**影响**:两个版本的必填字段集不同,实现时取哪个版本会导致行为不一致。特别是 `version` 字段:§5.1 ArtifactRef 有,深化 §9.1 有,但主 PRD §6.1 没有——如果按主 PRD 实现,产物可以无版本号提交,与多版本模型矛盾。

**建议**:统一 inputSchema,主 PRD §6.1 需补充 `version` 必填字段;深化 §9.1 需补充 `artifact_kind`/`artifact_qualifier`/`classification` 必填字段,对齐 D7 修正。

---

### 4.3 [P0] D11 的 current_owner / addenda / skipped 态修正未回写正文

**位置**:主 PRD §5.1(L1344-L1363)、§2 术语(L87)、FR2.1(L363)、FR2.3(L670);附录 D11(L2118-L2128)

**问题**:D11 声明了多项 P0 修正"影响章节",但正文未回写:

| D11 修正 | 声明影响章节 | 实际回写状态 | 证据 |
|---|---|---|---|
| P0-R5.9: current_owner 字段 | §5.1 | ❌ 未回写 | §5.1 ArtifactRef(L1344-L1363)无 current_owner |
| P0-R5.11: addendum 机制 | §FR1/§FR2 | ⚠️ 部分 | §FR2.5.1 有 addendum 机制,但 §5.1 ArtifactRef 无 addenda 字段 |
| P0-R5.17: skipped 态 + AC2.7 修正 | §FR2.1/AC2.7 | ❌ 未回写 | §2 术语(L87)仍说"10 态",FR2.1(L363)标题仍为"10 态",FR2.3(L670)注释仍说"10 态" |
| 状态机 10→11 态 | §FR2.1 | ❌ 未回写 | D11 L2128 声明"10 态 → 11 态",但正文未更新 |

**影响**:D11 的 P0 修正(skipped 态、current_owner、addenda)在正文中不存在,实现时遗漏。

**建议**:回写所有 D11 P0 修正:§2 术语和 FR2.1 改为"11 态";§5.1 ArtifactRef 补充 current_owner 和 addenda;AC2.7 补充 skipped 态处理。

---

### 4.4 [P0] Postgres artifact_ref 主键与 §5 多版本 ArtifactRef 模型直接矛盾

**位置**:深化 fr4-data-api.md §8.1(L961)vs 主 PRD §5.1(L1379)、FR2.3(L671)

**问题**:
- §5.1/FR2.3: `artifact_refs: dict[str, dict[str, ArtifactRef]]`(node_id → {version → ArtifactRef}),一个节点可有多个版本
- Postgres: `PRIMARY KEY (node_id, pipeline_id)`,一个节点只能有一行

这是数据模型设计与数据库 schema 的直接矛盾。D8 P0 修正 #2(L1937)明确要求多版本映射,但 schema 未修改。

**影响**:多版本共存无法实现,阻断 A14(契约 v2 不兼容共存)等场景。

**建议**:修改主键为 `PRIMARY KEY (node_id, pipeline_id, version)`,增加 `is_active BOOLEAN DEFAULT false` 列,通过应用层维护 `active_version` 映射。

---

### 4.5 [P0] Postgres audit_log 缺 hash 链字段,与 §5 AuditLogEntry 和 NFR15 矛盾

**位置**:深化 fr4-data-api.md §8.1 audit_log(L1074-L1089)vs 主 PRD §5.1 AuditLogEntry(L1408-L1409)、NFR15(L1627)

**问题**:
- §5.1 AuditLogEntry: 包含 `prev_hash`(L1408)和 `entry_hash`(L1409)
- NFR15: "审计日志采用 hash 链 + WORM 存储"
- AC7.6: "审计日志 hash 链可校验完整性"
- Postgres audit_log: 无 `prev_hash` 列,无 `entry_hash` 列

深化 §8.3(L1186-L1199)定义了 append-only 触发器(禁止 UPDATE/DELETE),但触发器只防修改,不实现 hash 链。hash 链字段在 DB 层完全缺失。

**影响**:hash 链无法存储,NFR15 和 AC7.6 无法实现。

**建议**:audit_log 表补充 `prev_hash TEXT` 和 `entry_hash TEXT NOT NULL` 列,应用层在 INSERT 时计算 hash 链。

---

### 4.6 [P0] Postgres pipeline status CHECK 与 §5 Pipeline status 不一致

**位置**:深化 fr4-data-api.md §8.1 pipeline 表(L917)vs 主 PRD §5.1 Pipeline(L1309)、FR2.7(L753-L759)

**问题**:
- §5.1 Pipeline(L1309): `status: "active" | "paused" | "cancelled" | "merged" | "completed"`(5 态)
- FR2.7(L753-L759): active / paused / cancelled / merged / completed(5 态)
- Postgres(L917): `CHECK (status IN ('active','paused','completed','archived'))`(4 态)

Postgres 缺少 `cancelled` 和 `merged`,多了 `archived`(TypedDict 和 FR2.7 中不存在)。

**影响**:管线取消(cancelled)和合并(merged)操作无法写入 DB,status CHECK 约束会拒绝;`archived` 状态在数据模型中不存在,可能产生无效状态。

**建议**:Postgres CHECK 改为 `IN ('active','paused','cancelled','merged','completed')`,移除 `archived`(或如果需要 archived,在 §5 和 FR2.7 中补充)。

---

### 4.7 [P0] Postgres node status CHECK 与 §2 状态机(10/11 态)不一致

**位置**:深化 fr4-data-api.md §8.1 node 表(L933-L935)vs 主 PRD §2(L87)、FR2.1(L363-L378)、D11(L2128)

**问题**:
- §2 术语(L87): "10 态状态机"(D8 修正后)
- FR2.1(L367-L378): 10 态(blocked, ready, pending_review, in_progress, review, done, changed, draft, deprecated, sunset)
- D11(L2128): "10 态 → 11 态(新增 skipped)"
- Postgres(L933-L935): `CHECK (status IN ('blocked','ready','in_progress','pending_review','review','done','changed'))` — 仅 7 态

Postgres 缺少 `draft`、`deprecated`、`sunset`(D8 新增)和 `skipped`(D11 新增),共缺 4 个状态。

**影响**:draft/deprecated/sunset/skipped 状态的节点无法写入 DB,CHECK 约束拒绝;状态机扩展(D8/D11 P0 修正)在 DB 层被阻断。

**建议**:Postgres CHECK 更新为全部 11 态:`IN ('blocked','ready','in_progress','pending_review','review','done','changed','draft','deprecated','sunset','skipped')`。

---

### 4.8 [P0] 深化 §9 声称"14 个工具"与 FR4 实际 34 个工具矛盾

**位置**:深化 fr4-data-api.md §0(L25)、§9 标题(L1250)vs 主 PRD FR4.1(L881-L901)、FR4.2(L902-L914)、FR4.3(L916-L944)

**问题**:深化 §0(L25)和 §9 标题(L1250)声称"14 个工具",但 FR4 实际声明:

| 来源 | 工具数 | 工具列表 |
|---|---|---|
| FR4.1 基础工具 | 16 | submit_artifact, soft_submit_artifact, subscribe_draft, unsubscribe_draft, update_progress, get_dependencies, get_pipeline_state, request_approval, approve, reject, set_gate_policy, add_addendum, reack_addendum, list_addenda, transfer_owner, revoke_human_token |
| FR4.2 审核工具 | 7 | list_pending_prs, get_pr_detail, review_artifact_pr, approve_pr, reject_pr, get_audit_log, export_compliance_report |
| FR4.3 新增工具 | 11 | cancel_pipeline, pause_pipeline, resume_pipeline, merge_pipelines, split_pipeline, report_consumption_status, report_generation_status, handle_security_incident, emergency_local_commit, sync_pending_artifacts, emergency_approve |
| **合计** | **34** | |

深化 §9 仅覆盖 14 个(§9.1-§9.14),附录 C1(L1750-L1752)也仅修正"13→14"。剩余 20 个工具无完整 schema。

此外,附录 C1 的修正本身基于错误的起点:它说"原误为 13",但 FR4 实际有 34 个工具,C1 只关注了 approve/reject 与 approve_pr/reject_pr 的区分,未考虑 FR4.1 和 FR4.3 新增的 20 个工具。

**影响**:20 个工具无规范,无法开发。

**建议**:深化 §9 覆盖全部 34 个工具;或明确分工(深化覆盖核心 14 个,其余在主 PRD §6 或单独深化中覆盖)。

---

### 4.9 [P1] §6.6 reject 参数与深化 §9.10 不一致

**位置**:主 PRD §6.6(L1587)vs 深化 fr4-data-api.md §9.10(L1710-L1712)

**问题**:
- §6.6(L1587): `approve` / `reject` | **node_id** | {ok, state} — reject 仅需 node_id
- 深化 §9.10(L1710-L1712): `reject` inputSchema required: `["node_id", "reason"]` — reject 需要 node_id **和 reason**

reject_pr(§6.4 L1555)也要求 reason(必填),但 §6.6 的 `reject`(approval 控制节点驳回)在主 PRD 中未要求 reason,深化要求 reason。

**影响**:reject 工具的必填参数不一致。

**建议**:统一 reject 必填参数为 `["node_id", "reason"]`,主 PRD §6.6 更新。

---

### 4.10 [P1] §6.6 request_approval 参数与深化 §9.8 不一致

**位置**:主 PRD §6.6(L1586)vs 深化 fr4-data-api.md §9.8(L1633)

**问题**:
- §6.6(L1586): `request_approval` | **node_id, approver** | {ok} — approver 为必填
- 深化 §9.8(L1633): `request_approval` inputSchema required: `["node_id"]` — approver 为**可选**(L1630 描述"可选,缺省用节点配置")

**影响**:approver 必填性不一致,主 PRD 要求必填但深化允许缺省。

**建议**:统一为深化版本(approver 可选,缺省用节点配置),主 PRD §6.6 更新。

---

### 4.11 [P1] branch pattern 与 D8 P0-4 路径修正矛盾

**位置**:深化 fr4-data-api.md §9.1(L1272)vs 主 PRD 附录 D8 P0-4(L1855)

**问题**:D8 P0-4(L1855)声明"产物路径改 `features/{pipeline_id}/...`",但深化 §9.1(L1272)的 branch pattern 仍为 `^feat/(product|server|design|client)/[a-z_]+-[0-9]+$`。D8 的修正未回写到深化文档的 schema 中。

此外,FR1.1(L188+)的分支保护规则和 PR 模板可能仍用旧路径(需交叉验证 FR1.1 正文)。

**影响**:分支/路径命名规范在 D8 P0-4 和深化 §9.1 之间矛盾,实现时路径冲突。

**建议**:统一为 D8 P0-4 的 `features/{pipeline_id}/...` 规范,更新深化 §9.1 的 pattern 和 FR1.1 的路径规则。

---

### 4.12 [P1] §7 NFR18(密钥本期落地)与 §1.4 一致但与 v2.0 原始声明矛盾

**位置**:主 PRD §1.4(L72)、NFR18(L1630);附录 C2(L1754-L1756)

**问题**:§1.4(L72)声明"密钥管理本期落地(NFR18)",NFR18(L1630)声明"MCP JWT 签名密钥、webhook HMAC、agent API Key 由 Vault 统一管理,永不硬编码"。附录 C2(L1754-L1756)记录了这一修正:"主 PRD 第 1.4 节将'密钥管理'划为 v3 范围外,但密钥管理是安全基线,应本期落地(新增 NFR18)"。

v3.1 版本中 §1.4 和 NFR18 已一致(本期落地),但:
- §1.4 的"不做"列仍保留"配额管理 v3 规划"——而深化文档已有配额设计(见发现 2.3)
- C2 修正记录本身仍存在于附录中,未标注"已回写"

**影响**:历史矛盾已修正但记录不清晰,附录 C2 未标注回写状态可能引起混淆。

**建议**:附录 C2 标注"已回写至 §1.4 和 NFR18";清理 §1.4 中配额管理的 v3 声明(见发现 2.3)。

---

### 4.13 [P1] §9 实施阶段 Phase 1 未包含认证/错误码/Postgres schema(P0 级)

**位置**:主 PRD §9 Phase 1(L1675-L1686)vs 深化 fr4-data-api.md §11(L1996-L2002)

**问题**:深化 §11(L1998)声明 Phase 1 MVP 包含:
- 错误码体系(§2)→ P0
- 认证授权(§3)→ P0
- Postgres schema 核心表(§8.1)→ P0
- ER 关系图(§7)→ P0
- langgraph_invoke 协议(§6)→ P0

但主 PRD §9 Phase 1(L1677-L1684)的任务列表仅包含:
- 产物仓库初始化 + 分支保护 + PR 模板
- LangGraph StateGraph
- MCP Server(submit/review/approve/reject/get_deps)
- 2 个 Constraint Skill
- 审核流程
- 基础可视化

**缺失**:认证授权(AuthMiddleware/AuthzMiddleware)、错误码体系、Postgres schema(含 audit_log)、langgraph_invoke 统一入口。这些在深化中为 P0,但主 PRD Phase 1 未列入。

此外,Phase 1(L1681)仅列 5 个 MCP 工具(submit/review/approve/reject/get_deps),但 NFR7(权限限制)和 NFR12(session token)是安全基线,无认证中间件无法满足。

**影响**:Phase 1 可能产出一个无认证、无错误码体系、无持久化 schema 的 MVP,不满足安全 NFR。

**建议**:§9 Phase 1 补充认证授权中间件、错误码体系、Postgres 核心表(含 audit_log)、langgraph_invoke 统一入口。

---

### 4.14 [P1] §9 Phase 3"LangGraph Postgres checkpointer"与 NFR3 矛盾

**位置**:主 PRD §9 Phase 3(L1706)vs NFR3(L1615)

**问题**:NFR3(L1615)声明"LangGraph checkpointer 持久化 state,重启可恢复"——这是可靠性基线需求。但 §9 将"LangGraph Postgres checkpointer"放在 **Phase 3**(L1706),Phase 1 和 Phase 2 使用什么 checkpointer 未说明。

如果 Phase 1/2 使用内存或 SQLite checkpointer,则 NFR3 在 Phase 1/2 不满足;如果 Phase 1 已使用 Postgres checkpointer,则 Phase 3 不应再列出此任务。

深化 fr4-data-api.md §1(L35)声明技术栈"Postgres ≥ 15",§8.1(L1103-L1106)提到 checkpointer 表由 SDK 自动创建,暗示 Postgres checkpointer 应在 Phase 1 就使用。

**影响**:Phase 1/2 的 state 持久化方案不明确,NFR3 的满足时机不清。

**建议**:明确 Phase 1 即使用 Postgres checkpointer(对齐 NFR3),Phase 3 删除该任务或改为"checkpointer 性能优化"。

---

### 4.15 [P2] §8.2 验收检查清单未覆盖 D8-D11 新增的验收标准

**位置**:主 PRD §8.2(L1653-L1669)vs 附录 C4(L1762-L1767)

**问题**:§8.2 的 15 项验收检查清单基于 v2.0 设计,未包含 D8-D11 新增的关键验收点:
- 多版本 ArtifactRef 共存验证
- addendum 附加 + must 级联 + 超时自动 changed
- owner 交接(transfer_owner)后审计记录
- 管线级生命周期操作(cancel/pause/resume/merge/split)
- hub 仓降级(emergency_*)+ 恢复后 sync
- 安全扫描阻断(secret/url/malware)
- 密级与 clearance 匹配
- hash 链完整性校验
- 外部依赖失效→deprecated→通知

附录 C4(L1762-L1767)声明"深化文档补充了 AC2.8~AC2.23、AC7.6/AC7.7、AC8.6~AC8.8",但这些 AC 未回写到 §8.2 检查清单。

**影响**:D8-D11 的验收标准在 §8.2 缺失,验收时可能遗漏。

**建议**:§8.2 补充 D8-D11 新增的验收检查项,或将 C4 声明的 AC 回写到正文。

---

## 关键发现汇总

### 最关键的 3 个发现

1. **[P0] Postgres schema 与 §5 TypedDict 全面脱节**(发现 1.8-1.12, 4.4-4.7)
   - artifact_ref 表主键不支持多版本,缺少 12+ 个关键字段(artifact_kind/classification/provenance/content_integrity_hash/current_owner/addenda 等)
   - audit_log 表缺少 hash 链字段(prev_hash/entry_hash),NFR15 无法实现
   - pipeline status CHECK 缺少 cancelled/merged,多了 archived
   - node status CHECK 仅 7 态,缺少 draft/deprecated/sunset/skipped(共 4 态)
   - agent 表与 RoleInstance 字段不一致,缺少 clearance/approvers 等
   - **这是最严重的发现:数据模型(TypedDict)与存储 schema(Postgres DDL)之间存在系统性脱节,D7-D11 的 P0 修正大多在 TypedDict 层回写但未传导到 schema 层**

2. **[P0] D11 修正未回写正文,current_owner/addenda/skipped 态缺失**(发现 1.4, 1.5, 4.3)
   - D11 P0-R5.9 声明 ArtifactRef 新增 current_owner → §5.1,但 §5.1 无此字段
   - D11 P0-R5.11 声明 addendum 机制 → §FR1/§FR2,FR2.5.1 有机制但 §5.1 ArtifactRef 无 addenda 字段
   - D11 P0-R5.17 声明状态机 10→11 态(新增 skipped),但 §2 术语、FR2.1、FR2.3 均仍为"10 态"
   - **D11 作为最新一轮压力测试修正,其 P0 项未回写正文意味着最新设计未落地**

3. **[P0] MCP 工具 schema 覆盖率严重不足,主 PRD §6 与深化 §9 矛盾**(发现 1.6, 4.2, 4.8)
   - FR4 共声明 34 个工具,深化 §9 仅覆盖 14 个,主 PRD §6 仅完整覆盖 5 个,约 20 个工具完全无 schema
   - 即使是已覆盖的 submit_artifact,主 PRD §6.1 和深化 §9.1 的 inputSchema 必填字段集不同(8 vs 6 个必填,字段集有交叉但不一致)
   - **工具规范是 MCP 接口层的核心,覆盖率和一致性不足直接阻断开发**

---

## 文件路径

- 评审报告:`/Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/reviews/review-part4-monitoring-data-nfr-appendix.md`
- 主 PRD:`/Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/coordination-platform-prd.md`
- 深化文档:`/Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/deep-dive/fr4-data-api.md`
