# PRD 评审报告 Part 3:§FR4 MCP 接口层 + §FR5 约束技能 + §FR6 审核机制

> **评审对象**:`coordination-platform-prd.md` §FR4(行 877-961)、§FR5(行 964-1066)、§FR6(行 1069-1188)
> **交叉引用**:§2.1 节点类型(行 102-130)、§3.1-3.2 权限(行 133-178)、§FR1.2 分支保护(行 251-269)、§FR1.3 PR 模板(行 271-338)、§6 接口规范(行 1479-1606)
> **深化文档**:`fr1-fr6-artifact-review.md`、`fr3-fr5-crew-skills.md`、`fr4-data-api.md`
> **评审维度**:内容缺失 / 边界模糊 / 细节不足 / 规则冲突
> **日期**:2026-08-04

---

## 0. 评审结论摘要

| 维度 | 发现数 | P0 | P1 | P2 |
|---|---|---|---|---|
| 维度 1 内容缺失 | 7 | 4 | 2 | 1 |
| 维度 2 边界模糊 | 5 | 1 | 3 | 1 |
| 维度 3 细节不足 | 7 | 2 | 4 | 1 |
| 维度 4 规则冲突 | 6 | 3 | 2 | 1 |
| **合计** | **25** | **10** | **11** | **4** |

**结论**:§FR4/FR5/FR6 当前状态**不通过**,存在 10 个 P0 级阻断性问题,集中在"工具 schema 大面积缺失""安全扫描规则族无定义""skill 约束模型分裂"三处,需补全后方可进入 MVP 开发。

---

## 1. 维度 1:内容缺失

### D1-1【P0】25+ MCP 工具中 11+ 个完全无 inputSchema/outputSchema

**位置**:主 PRD §FR4.1(行 885-901)、§FR4.3(行 916-944);深化 `fr4-data-api.md` §9(行 1250-1947)

**问题**:
主 PRD §FR4.1 + §FR4.3 实际列出 **25+ 个工具**,但深化 `fr4-data-api.md` §9 仅给出 **14 个工具**的完整 schema。以下工具在主 PRD 与三份深化文档中**均无 inputSchema/outputSchema**:

| 类别 | 缺失工具 | 主 PRD 位置 |
|---|---|---|
| addendum 族 | `add_addendum`、`reack_addendum`、`list_addenda` | 行 896-898 |
| owner/ token | `transfer_owner`、`revoke_human_token` | 行 899-900 |
| 管线级 | `cancel_pipeline`、`pause_pipeline`、`resume_pipeline`、`merge_pipelines`、`split_pipeline` | 行 924-928 |
| 消费回传 | `report_consumption_status`、`report_generation_status` | 行 934-935 |
| 安全/降级 | `handle_security_incident`、`emergency_local_commit`、`sync_pending_artifacts`、`emergency_approve` | 行 941-944 |
| 审核 | `export_compliance_report` | 行 914 |

**影响**:`add_addendum`/`reack_addendum` 是第五轮 AC2.16-2.22(addendum 级联/超时/ack)的实现入口,无 schema 无法开发;`handle_security_incident` 是安全闭环(行 941)核心,无定义则 AC6.8 安全事件无法闭环。

**建议**:深化 `fr4-data-api.md` §9 补齐剩余 11+ 工具的 inputSchema/outputSchema,或在主 PRD §6.6 表格(行 1580-1605)逐工具展开。

---

### D1-2【P0】skill.yaml 缺正式 JSON Schema(对比 manifest 有完整 schema)

**位置**:主 PRD §FR5.2(行 989-1026);深化 `fr3-fr5-crew-skills.md` §6(行 671-924);对比 `fr1-fr6-artifact-review.md` §3.3(行 264-444)

**问题**:
- manifest 有完整可机器校验的 JSON Schema(深化 §3.3),但 skill.yaml **仅有 YAML 示例,无正式 JSON Schema**。
- `file_constraints` 下出现多种自定义约束字段无统一定义:
  - `requires_figma_link`(深化 §6.3 行 777)
  - `must_contain`(深化 §6.4 行 817)
  - `min_size_kb`(深化 §6.1 行 698)
  - 主 PRD §FR5.2(行 1008-1010)仅 `allowed_extensions` + `max_size_kb`
- 这些自定义约束是否纳入 CI 校验?校验 op 是什么?均未定义。

**建议**:为 skill.yaml 出具与 manifest 同等级别的 JSON Schema,明确 `file_constraints` 的扩展字段注册机制。

---

### D1-3【P0】审核规则引擎 op 清单不完整,无法覆盖安全扫描/completeness_contract

**位置**:深化 `fr1-fr6-artifact-review.md` §4.1.4(行 606-621)

**问题**:
§4.1.4 给出 11 个 op,但 §FR6.2(行 1094-1104)与 §FR6.1(行 1081-1082)提到的以下规则**无对应 op**:

| 规则族 | 需要的 op | 现状 |
|---|---|---|
| `R_SECRET_SCAN` | 密钥正则匹配/熵值检测 | 无 |
| `R_URL_SAFETY` | URL 黑名单/分类查询 | 无 |
| `R_MALWARE_SCAN` | 恶意特征扫描 | 无 |
| `R_COMPLETENESS_CONTRACT` | jsonpath 求值 + min_items | 无(主 PRD §FR5.2 行 1013-1017 用 jsonpath,但 op 清单无) |
| `R_EXTERNAL_REF_OWNERSHIP` | external_repo 白名单匹配 | 无 |
| `R_COMMIT_STABILITY` | commit 不可变校验 | 无 |

**影响**:规则引擎声称"可配置化"(深化 §4 开头),但 6 个核心规则无法用现有 op 表达,等于退化为硬编码,与"可演进"目标冲突。

**建议**:扩展 op 清单,至少新增 `secret_scan`、`url_safety_check`、`malware_scan`、`jsonpath_min_items`、`repo_in_whitelist`、`commit_immutable` 6 个 op。

---

### D1-4【P0】安全扫描规则族(R_SECRET_SCAN 等 6 个)具体扫描内容全文缺失

**位置**:主 PRD §FR6.1(行 1081)、§FR6.2(行 1103)、AC6.8(行 1185)、AC6.9(行 1186)

**问题**:
主 PRD 多处引用 6 个安全规则族,但**三份深化文档与主 PRD 均未定义任何一条规则的扫描内容**:

| 规则 | 应定义但缺失的内容 |
|---|---|
| `R_SECRET_SCAN` | 扫描哪些密钥模式(AWS AKIA/GitHub ghp_/私钥头/JWT/high-entropy)?用何引擎(gitleaks/truffleHog/自研)?扫描对象(产物文件本身?引用型产物指向的代码 commit?) |
| `R_URL_SAFETY` | 钓鱼/恶意/内网 URL 判定依据?黑名单来源? |
| `R_MALWARE_SCAN` | 产物为 YAML/JSON/MD 非二进制,何来恶意?是否扫描引用型产物指向的代码 commit?用何反病毒引擎? |
| `R_EXTERNAL_REF_OWNERSHIP` | 归属校验逻辑(对比 RoleInstance.`allowed_external_repos`?) |
| `R_COMMIT_STABILITY` | commit 不可变校验方式(查 git log?是否禁止 force push?) |
| `R_COMPLETENESS_CONTRACT` | 与 skill.yaml completeness_contract 的映射关系 |

**影响**:AC6.8"安全扫描检出密钥/恶意/钓鱼 URL 时阻断"无实现依据,无法验收;安全门禁形同虚设。

**建议**:新增"安全扫描规则族定义"章节,逐规则给出扫描模式/引擎/对象/阈值/误报处理。

---

### D1-5【P0】审计 hash 链算法细节缺失(payload/创世/锚定/降级衔接)

**位置**:主 PRD §FR6.5(行 1167-1172)、§FR7.2(行 1216);深化 `fr1-fr6-artifact-review.md` §8.3(行 1186-1199)

**问题**:
`entry_hash = SHA-256(prev_hash + action + actor + payload)`(行 1172)存在以下未定义项:

1. **payload 字段范围**:是整个 audit 记录(除 hash)还是子集?序列化格式(JSON canonical?字段顺序?)?
2. **创世记录**:第一条记录的 `prev_hash` 取值(全零?空串?)未定义。
3. **锚定频率**:主 PRD 与深化均未提"锚定频率"(是否定期锚定到外部时间戳/区块链?)。`export_compliance_report`(行 914)返回 `hash_chain_valid`,但校验算法未给。
4. **降级衔接**:§FR7.2(行 1216)"写入失败先持久化本地 WAL,恢复后补写 hash 链"——但 WAL 期间若有其他记录已写入主链,补写时 `prev_hash` 链如何衔接?链断裂风险未说明。

**建议**:明确 payload 规范化算法、创世 prev_hash、锚定策略、WAL 补写的链重建协议。

---

### D1-6【P1】get_dependencies 在深化中丢失 key_constraints / draft 字段(内容回退)

**位置**:主 PRD §FR4.1(行 891)、§6.5(行 1578);深化 `fr4-data-api.md` §9.5(行 1471-1518)

**问题**:
主 PRD §3.5(行 867-868)强调"`get_dependencies` 返回增加 `key_constraints` 字段,agent backstory 强制必须遵守 must 级约束"。但深化 §9.5 的 outputSchema(行 1489-1512)**返回结构无 `key_constraints`、无 `stability`**,参数也用 `include_content`/`max_content_kb` 取代了主 PRD 的 `include_draft`/`draft_version`。

**影响**:FR3.5 关键约束提取机制失去返回载体,agent 无法获取 must 级约束,行为护栏(行 868)落空。

**建议**:深化 §9.5 补回 `key_constraints[{level, text}]` 与 `stability` 字段,参数与主 PRD §6.5 对齐。

---

### D1-7【P1】review_artifact_pr outputSchema 缺安全扫描结果字段

**位置**:深化 `fr4-data-api.md` §9.2(行 1347-1372);主 PRD §FR7.1(行 1203)

**问题**:
§FR7.1 埋点表(行 1203)明确 `mcp.review_artifact_pr` span 含属性 `security_scan_results`,但深化 §9.2 的 outputSchema(行 1357-1365)只有 `checks{metadata, deps, file_format, file_exists}`,**无 `security_scan_results` / `completeness_contract` / `external_ref_ownership` 检查项**。

**影响**:审核结论不透明,人工审核者无法看到安全扫描明细;AC6.8 验收无结构化证据。

**建议**:outputSchema 的 `checks` 扩展为含 `security`、`completeness`、`ref_ownership` 子项。

---

## 2. 维度 2:边界模糊

### D2-1【P0】25+ 工具中 11+ 个无权限边界定义(调用方模糊)

**位置**:主 PRD §FR4.1(行 885-901)、§FR4.3(行 916-944);深化 `fr4-data-api.md` §3.3(行 264-305)

**问题**:
深化 §3.3 `ROLE_TOOLS` 白名单(行 268-275)仅覆盖 6 角色 × 14 个基础工具的权限映射,以下工具的调用权限**未定义**:

| 工具 | 主 PRD 标注调用方 | 模糊点 |
|---|---|---|
| `add_addendum` | current_owner / admin | "current_owner"如何界定?是产物提交者还是节点当前 owner?`transfer_owner` 后如何同步? |
| `subscribe_draft` | 各角色 agent | 能否订阅非自己上游的 draft? |
| `handle_security_incident` | admin / 安全监控 | "安全监控"是 agent 还是外部系统?如何认证? |
| `emergency_local_commit`/`emergency_approve` | admin | hub 仓宕机的自动判定条件?谁触发? |
| `reack_addendum` | 下游 node 的 owner | "下游 owner"如何解析?下游多 owner 时谁可 ack? |
| `report_consumption_status` | 外部 CI/CD | 外部系统如何认证(非 agent 非 human)? |

**影响**:MCP 鉴权层(AuthzMiddleware)无法对这些工具做角色校验,存在越权风险;ALR-14 越权告警(行 872)无基线。

**建议**:扩展 §3.3 `ROLE_TOOLS` 覆盖全部 25+ 工具,明确 current_owner/downstream_owner 的解析规则与外部系统的认证模型。

---

### D2-2【P1】skill"约束"(completeness_contract reject)与"引导"(guide 非强制)边界模糊

**位置**:主 PRD §FR5 目标(行 966)、§FR5.2(行 1012-1019)、§FR5.3(行 1038)

**问题**:
§FR5 目标声明"定义'交什么'(元数据约束)+ 引导'建议交什么'(guide)"。但 `completeness_contract`(行 1012)用 jsonpath 校验 `$.endpoints`/`$.errors` 并配 `on_fail: reject`——这实际是在**约束产物内容结构**,既非纯元数据约束,也非引导。三者边界:

- `required_fields`(元数据)→ 约束
- `file_constraints`(格式)→ 约束
- `completeness_contract`(内容结构)→ 约束还是引导?
- `guide.md`(内容建议)→ 引导

`completeness_contract` 与 `guide.md` 都涉及"内容",但一个 reject 一个非强制,边界未划清。

**建议**:明确分类:`required_fields`/`file_constraints`/`completeness_contract` 属"结构约束(强制)",`guide.md` 属"内容建议(非强制)";并澄清 completeness_contract 校验的是"结构存在性"而非"语义正确性"。

---

### D2-3【P1】on_fail=reject vs warn 的选择标准未定义(安全规则默认值缺失)

**位置**:深化 `fr1-fr6-artifact-review.md` §4.2.2(行 632-638)、§4.2.3(行 642-648)

**问题**:
§4.2.3 定义了 reject/needs_human/warn 的短路语义,§4.2.2 给出 P0-P4 优先级分层,但**未给出"什么类型的规则该用 reject 还是 warn"的选择标准**:

- `R_SECRET_SCAN` 应 reject(零容忍)还是 warn(可能误报)?未明确。
- `completeness_contract` 的 `on_fail` 可配 reject|warn(行 1018),但何时该 warn?结构缺失为何要容忍?
- P4"软提示"用 warn,但安全规则若误归 P4 会导致漏放。

**建议**:给出 on_fail 选择准则:安全类(密钥/恶意/钓鱼)默认 reject;格式/依赖类 reject;结构契约类按 skill 声明;仅"风格建议"类 warn。

---

### D2-4【P1】安全扫描"零容忍"与"告警"边界未划(假密钥/内网URL/开发URL)

**位置**:主 PRD AC6.8(行 1185);深化无对应章节

**问题**:
AC6.8"检出密钥/恶意/钓鱼 URL 时阻断"暗示零容忍,但实际场景需分级,文档无边界:

- **假密钥**:测试用占位符(如 `AKIAIOSFODNN7EXAMPLE`)是否告警?误报率高时如何白名单?
- **内网 URL**:`http://localhost`/`http://10.0.0.1` 是告警还是放行?
- **开发 URL**:`https://api.dev.internal` vs `https://api.internal` 如何区分?
- **引用型产物**:扫描产物文件本身(YAML/JSON)还是其指向的代码 commit?

**建议**:定义安全扫描分级矩阵(密钥/URL/恶意各分 critical/high/medium/low),明确各级 reject 还是 warn,以及白名单/误报申诉机制。

---

### D2-5【P2】"不解析内容"与 completeness_contract jsonpath 校验边界模糊

**位置**:主 PRD §FR5.2(行 1008 "不解析内容")vs 行 1012-1017(jsonpath 校验);深化 `fr1-fr6-artifact-review.md` §1.2(行 68)

**问题**:
"不解析内容"原则与 jsonpath 求值(`$.endpoints` min_items:1)的边界未划清:jsonpath 求值算"解析"还是"结构校验"?若算解析则违反原则(见 D4-4);若不算,需重新表述原则。此边界模糊导致实现者无所适从。

**建议**:原则修订为"不解析产物语义,但可校验结构契约(jsonpath 存在性/计数)",并明确 jsonpath 仅限 `exists`/`min_items`/`max_items` 三类,禁止值匹配。

---

## 3. 维度 3:细节不足

### D3-1【P0】submit_artifact required 字段三处不一致且深化缺安全审核必需字段

**位置**:主 PRD §6.1(行 1502)、§FR4.1(行 887);深化 `fr4-data-api.md` §9.1(行 1289)

**问题**:
三处 required 字段互不一致:

| 来源 | required 字段 |
|---|---|
| 主 PRD §6.1(行 1502) | node_id, repo, branch, path, toolspec_framework, **artifact_kind, artifact_qualifier, classification** |
| 主 PRD §FR4.1(行 887) | node_id, repo, branch, path, toolspec_framework, deps_decl, classification |
| 深化 §9.1(行 1289) | node_id, repo, branch, path, toolspec_framework, **version** |

深化 §9.1 的 required **缺失 `classification`/`artifact_kind`/`artifact_qualifier`/`external_repo`/`external_commit`**,而:
- AC6.9(行 1186)"引用型产物 external_repo 超出白名单被 reject"——无 `external_repo` 字段无法校验。
- §FR6.2(行 1098)"密级校验 classification 存在且 ≤ clearance"——无 `classification` 无法校验。
- §FR5.2(行 1003)required_fields 含 `classification`——与深化 §9.1 矛盾。

**建议**:以主 PRD §6.1 为权威,深化 §9.1 补齐 `artifact_kind`/`artifact_qualifier`/`classification`/`external_repo`/`external_commit`,并统一三处 required。

---

### D3-2【P1】get_dependencies 的 include_draft 返回结构细节不足

**位置**:主 PRD §6.5(行 1571-1578);深化 `fr4-data-api.md` §9.5(行 1471-1518)

**问题**:
主 PRD §6.5 有 `include_draft`/`draft_version` 参数,返回含 `stability`(stable|draft),但以下细节缺失:
- `draft_version` 格式:是 feat 分支名、commit hash 还是语义版本?
- 多下游订阅同一 draft 的版本协商机制(无)。
- `stability=draft` 的内容是否同样走 `classification` 密级过滤?§3.2(行 178)仅说"调用方 clearance 低于上游 classification 时拒绝返回内容",未区分 draft/stable。
- 深化 §9.5 直接删除了 `include_draft`/`draft_version`,改用 `include_content`/`max_content_kb`,draft 机制无 schema 支撑。

**建议**:统一参数命名,补 draft_version 格式、版本协商、draft 密级过滤规则。

---

### D3-3【P1】skill.yaml 的 deps 条件依赖(condition)语法缺失

**位置**:主 PRD §FR5.2(行 1004-1007);AC2.13(行 738)、AC2.14(行 739)

**问题**:
§FR5.2 `deps`/`min_version` 是静态声明,但第五轮 AC2.13"`no_design_client` 下 client_ui 不因缺 design_asset 被拒绝"、AC2.14"`tech_debt`/`design_only` 允许非 product 根"——隐含**条件依赖**(participation.profile 裁剪后 deps 动态调整)。skill.yaml 如何表达"当 profile=no_design_client 时 design_asset 依赖可选"?`deps` 是必须还是可选?`min_version` 的 condition 语法?主 PRD 与深化均未给出。

**影响**:AC2.13/AC2.14 无法通过 skill 约束实现,需硬编码例外,违背 skill 可配置化目标。

**建议**:为 `deps` 增加条件语法,如 `deps: [{node_type: design_asset, required_when: "profile != no_design_client"}]`。

---

### D3-4【P0】SkillRegistry 三级匹配算法未实现(深化代码仅精确匹配)

**位置**:主 PRD §FR5.3(行 1034)、§2.1(行 106);深化 `fr3-fr5-crew-skills.md` §8.1(行 995-1016)

**问题**:
主 PRD §FR5.3/§2.1 声明三级匹配:"精确 → 角色通配(`client.*`) → 通用(`*`)"。但深化 §8.1 `SkillRegistry.build_index`(行 1004-1012)的 `match_skill`(行 1014-1016)仅 `return self.index.get(node_type)`——**纯精确匹配,未实现角色通配与通用通配**。

且通配匹配的算法细节未定义:
- 若 `client.ui`、`client.*`、`*` 三个 skill 同时存在,优先级如何判定?
- 冲突时(两个 skill 都匹配 `client.ui`)如何处理?深化代码遇 `node_type` 重复直接 `raise`(行 1010),但通配本就会产生"重复匹配",该逻辑与三级匹配不兼容。
- `design-handoff-skill` 的 `trigger.node_type: [design_proto, design_asset]`(深化 §6.3 行 759)是列表,与通配 `client.*` 语法如何区分?

**影响**:AC5.1"节点 ready 时自动匹配正确 skill"无法通过;新节点类型无精确 skill 时无法兜底。

**建议**:实现三级匹配算法,明确通配优先级(精确 > 角色通配 > 通用)、冲突仲裁规则、列表型 node_type 与通配的语法区分。

---

### D3-5【P1】审核规则 priority 同级冲突处理 + 规则组优先级与独立规则排序矛盾

**位置**:深化 `fr1-fr6-artifact-review.md` §4.2.1(行 625-628)、§4.4.1(行 696-737)

**问题**:
1. §4.2.1"同优先级按 YAML 声明顺序"——但跨 skill 合并规则后(若多个 skill 同时激活),声明顺序如何确定?未定义。
2. §4.4.1 伪码(行 703-727)先按 priority 降序跑独立规则(行 705-716),**再**跑规则组 group(行 718-722)——意味着 group 总是在所有独立规则之后,与"按 priority 统一排序"矛盾。group 的优先级如何与独立规则比较?
3. `R_SECRET_SCAN` 等安全规则的 priority 未在 §4.2.2 分层(行 632-638)中列出(应归 P0 90-100,但表内仅列 `R_META_REQUIRED`/`R_NO_PATH_TRAVERSAL`)。

**建议**:统一独立规则与 group 的排序模型(建议 group 也有 priority,纳入统一排序);明确安全规则优先级。

---

### D3-6【P1】R_SECRET_SCAN 具体密钥模式与引擎未定

**位置**:主 PRD §FR6.2(行 1103);深化无

**问题**:
(关联 D1-4)R_SECRET_SCAN 应扫描哪些密钥模式未定。需明确:
- 云厂商:AWS(AKIA/ASIA)、GCP、Azure
- 代码托管:GitHub PAT(`ghp_`)、GitLab、Bitbucket
- 通用:私钥头(`-----BEGIN`)、JWT、high-entropy 字符串
- 引擎选型:gitleaks / truffleHog / 自研正则
- 扫描对象:产物文件本身?引用型产物指向的代码 commit?manifest 元数据?

**建议**:给出密钥模式清单 + 引擎选型 + 扫描对象矩阵。

---

### D3-7【P2】hash 链锚定频率与 WORM 存储接口细节不足

**位置**:主 PRD §FR6.5(行 1144);深化 `fr1-fr6-artifact-review.md` §8.3(行 1186-1199)

**问题**:
(关联 D1-5)
- **锚定频率**:无定义(每条?每小时?外部锚定?)。
- **WORM 接口**:主 PRD 说"写入 WORM 表,只允许 INSERT"(行 1144),深化 §8.3 用 Postgres 触发器禁止 UPDATE/DELETE(行 1186-1199)——但 Postgres 触发器可被 superuser 禁用/绕过,**非真 WORM**。真正的 WORM(S3 Object Lock / 专用 WORM 设备)接口未定义。合规场景(如金融)可能不认可 Postgres 触发器为 WORM。

**建议**:明确锚定策略(如每日锚定到外部时间戳服务);WORM 存储升级为 S3 Object Lock 或声明 Postgres 触发器的合规边界。

---

## 4. 维度 4:规则冲突或矛盾

### D4-1【P0】§FR4 工具清单 vs §6 接口规范 vs 深化§9 三处不一致

**位置**:主 PRD §FR4.1/§FR4.3(行 885-944)、§6(行 1479-1606);深化 `fr4-data-api.md` §9(行 1250-1947)、§0(行 25)

**问题**:
1. **工具数量矛盾**:深化 §0(行 25)称"实为 14 个",但主 PRD §FR4.1+§FR4.3 实际列 25+ 工具(含 addendum/管线/消费/安全/降级族)。深化的"14 个"统计已过时,遗漏 11+ 工具。
2. **submit_artifact required 三处不同**(见 D3-1)。
3. **get_dependencies 参数名不同**:主 PRD `include_draft`/`draft_version`(行 1571-1572) vs 深化 `include_content`/`max_content_kb`(行 1475-1476)。
4. **approve_pr 返回字段不同**:§6.3(行 1541)`{ok, merged, node_id, state}` vs 深化 §9.3(行 1403-1414)`{merged, pr_id, node_id, merge_commit, state, cascaded}`。
5. **review_artifact_pr 返回字段不同**:§6.2(行 1523)`{verdict, reason}` vs 深化 §9.2(行 1354-1368)`{pr_id, verdict, reason, checks{...}, skill_used}`。

**影响**:开发时以哪份为准不明确,实现与验收标准脱节。

**建议**:明确主 PRD §6 与深化 §9 的权威关系(建议深化为准但主 PRD 同步修订),统一所有工具的 required/返回字段。

---

### D4-2【P0】§FR5 skill 清单(7个) vs §2.1 节点类型(10种) vs 深化skill(6个)不一致 + manifest enum 缺 derived_artifact

**位置**:主 PRD §2.1(行 104-119)、§FR5.1(行 970-983)、§FR5.4(行 1044-1052);深化 `fr3-fr5-crew-skills.md` §6(行 671-924)、`fr1-fr6-artifact-review.md` §3.3(行 302-312)、§10.3(行 1484)、§8.1(行 1092-1101)

**问题**:
1. **skill 数量矛盾**:§FR5.1/§FR5.4 说 **7 个 skill**(含 `derived-artifact-skill`,行 982、1052);深化 `fr3-fr5` §6 只给 **6 个**(无 derived-artifact-skill);深化 `fr1-fr6` §10.3(行 1484)说"Constraint Skill 6 个"。`derived_artifact` 节点(§2.1 行 119)的 skill 约束**完全缺失**。
2. **manifest node_type enum 缺 derived_artifact**:深化 `fr1-fr6` §3.3(行 302-312)enum 列 9 种(product_spec...client_delivery),**缺 `derived_artifact`** —— 与 §2.1 的 10 种矛盾,`derived_artifact` 产物 manifest 无法通过 schema 校验。
3. **DB UNIQUE 约束与多 node_type skill 冲突**:深化 §8.1 `skill` 表 `node_type TEXT NOT NULL UNIQUE`(行 1095),但 `design-handoff-skill` 一个 skill 覆盖 `design_proto`+`design_asset`(深化 `fr3-fr5` §6.3 行 759)——一个 skill 行无法存两个 node_type,与 UNIQUE 约束冲突。

**影响**:`derived_artifact` 节点(generator agent 产出,§3.1 行 143)无法提交/校验;design-handoff-skill 无法入库。

**建议**:补 `derived-artifact-skill`;manifest enum 补 `derived_artifact`;`skill` 表 `node_type` 改为非 UNIQUE 或拆为 `skill_node_type` 关联表。

---

### D4-3【P1】§FR6 审核规则与 §FR1.2 分支保护 CI 校验重复(未明确分工)

**位置**:主 PRD §FR1.2(行 259)、§FR6.1(行 1080-1082)、§FR6.2(行 1094-1104);深化 `fr1-fr6-artifact-review.md` §8.1.1(CI-1~CI-11)、§8.1.2(行 1130-1161)

**问题**:
- §FR1.2(行 259)CI 校验 = manifest schema + skill 约束 + 安全扫描规则族。
- §FR6.1(行 1080-1082)管理方审核也校验元数据 + 依赖完整性 + 文件格式 + completeness_contract + 安全扫描。
- 文字层面重复,主 PRD 未明确分工边界。

深化 `fr1-fr6` §8.1.1/§8.1.2 做了分工(CI 校格式/结构,管理方校业务/依赖),但仍有重叠:
- CI-5"扩展名白名单"(行 1138)与 `R_FILE_FORMAT` 的 `extensions_in` 重复。
- CI-6"文件大小"(行 1139)与 `R_FILE_FORMAT` 的 `size_le` 重复。
- CI-4"manifest schema"(行 1137)与 `R_META_REQUIRED` 部分重复。

**影响**:双重校验增加维护成本;规则变更时两处不同步导致行为漂移。

**建议**:主 PRD §FR1.2 明确"CI 仅校验仓库级格式/结构,业务/依赖/安全由 §FR6 管理方规则引擎校验",消除重叠项的重复定义。

---

### D4-4【P0】completeness_contract 与"不解析内容"原则直接矛盾

**位置**:主 PRD §FR5 目标(行 966)、§FR5.2(行 1008 "不解析内容"、行 1012-1017 jsonpath 校验);深化 `fr1-fr6-artifact-review.md` §1.2(行 68)、§FR6.2(行 1102)

**问题**:
- §FR5 目标(行 966)"不限制'怎么交'"。
- §FR5.2 `file_constraints`(行 1008)标注"不解析内容"。
- 但同节 `completeness_contract`(行 1012-1017)用 `jsonpath: "$.endpoints"` + `min_items: 1` 校验——**明确在解析产物内容并求值**。
- 深化 §1.2(行 68)"管理方不解析产物内容,只校验元数据 + 文件格式"与 §FR6.2(行 1102)"completeness_contract 中 required_structures 满足"**直接矛盾**。

这是原则性冲突:`completeness_contract` 要么违反"不解析内容"原则(应删除或改为元数据约束),要么原则需重新表述。当前实现者无法判断 jsonpath 求值是否允许。

**建议**:
- 方案 A(推荐):修订原则为"不解析产物语义,但可校验结构契约",并限制 jsonpath 仅 `exists`/`min_items`/`max_items`。
- 方案 B:删除 `completeness_contract`,改为 `guide.md` 引导 + `required_fields` 元数据约束。
明确选择其一并同步修订 §FR5 目标、§FR5.2、深化 §1.2。

---

### D4-5【P0】artifact_constraints(主PRD/深化fr3-fr5) vs review_rules(深化fr1-fr6)两套模型并存矛盾

**位置**:主 PRD §FR5.2(行 995-1026);深化 `fr1-fr6-artifact-review.md` §4.1.1(行 489-571)、§10.2(行 1466);深化 `fr3-fr5-crew-skills.md` §6(行 671-924)

**问题**:
- 主 PRD §FR5.2 用 `artifact_constraints`(required_fields/deps/min_version/file_constraints/completeness_contract)。
- 深化 `fr1-fr6` §4.1.1 将其**重构为 `review_rules`**(规则引擎),§10.2(行 1466)明确"FR5.2 skill.yaml 的 artifact_constraints 重构为 review_rules"。
- 但深化 `fr3-fr5` §6 的 6 个 skill.yaml **仍用 `artifact_constraints`**,未用 `review_rules`!

两份深化文档对 skill.yaml 的字段定义互相矛盾,且:
- 主 PRD §FR5.5 AC5.2-5.4(行 1059-1061)按 `required_fields`/`deps`/`allowed_extensions` 验收——与 review_rules 模型不匹配。
- 深化 `fr1-fr6` §4.4.3(行 750-762)给出映射表,但 `fr3-fr5` §6 未按映射改写。

**影响**:开发时 skill.yaml 到底用哪套字段?审核引擎按 review_rules 还是 artifact_constraints 实现?两套并存导致实现分裂。

**建议**:明确权威模型(建议 review_rules 为准),主 PRD §FR5.2 与 `fr3-fr5` §6 同步迁移,给出 `artifact_constraints` → `review_rules` 的完整改写。

---

### D4-6【P1】design-handoff-skill 统一 requires_human_review=true 与 §FR6.4(design_proto 不需人工)矛盾

**位置**:主 PRD §FR5.4(行 1048)、§FR6.4(行 1131-1132);深化 `fr3-fr5-crew-skills.md` §6.3(行 778)

**问题**:
- 深化 §6.3 `design-handoff-skill` 的 `requires_human_review: true`(行 778),且该 skill 覆盖 `design_proto` + `design_asset`(行 759)。
- 但 §FR6.4(行 1131-1132):`design_proto` 人工审核 ❌,`design_asset` 人工审核 ✅。
- 一个 skill 对两种节点统一 `requires_human_review=true`,会导致 **`design_proto` 也被强制人工审**,与 §FR6.4 矛盾。

§FR5.4(行 1048)也写"design-handoff-skill ... requires_human_review: true(design_asset)"——括号标注 design_asset,但 skill.yaml 字段是 skill 级而非 node_type 级,无法区分。

**影响**:`design_proto` 节点被错误强制人工审核,增加无谓延迟,违反 §FR6.4 矩阵。

**建议**:`requires_human_review` 改为支持 per-node-type 声明(如 `{design_proto: false, design_asset: true}`),或拆分为 `design-proto-skill` + `design-asset-skill` 两个 skill。

---

## 5. 最关键的 3 个发现(重申)

1. **【D1-4 / D1-3】安全扫描规则族(R_SECRET_SCAN/R_URL_SAFETY/R_MALWARE_SCAN/R_EXTERNAL_REF_OWNERSHIP/R_COMMIT_STABILITY/R_COMPLETENESS_CONTRACT)全文无任何规则定义、无 op、无扫描内容** —— AC6.8/AC6.9 无法验收,安全门禁形同虚设。这是整个 §FR6 安全闭环的最大空洞。

2. **【D4-5】skill.yaml 约束模型分裂:主 PRD + 深化 fr3-fr5 用 `artifact_constraints`,深化 fr1-fr6 重构为 `review_rules`,两套并存且 6 个 skill.yaml 未用 review_rules,未声明权威** —— 审核引擎无法落地,AC5.2-5.7 验收基线不明。

3. **【D3-1 / D4-1】submit_artifact 的 inputSchema 三处不一致(§6.1 / §FR4.1 / 深化§9.1 required 字段各异),且深化§9.1 缺 classification / artifact_kind / qualifier / external_repo 等安全审核必需字段** —— L3 external_repo 校验(AC6.9)与密级校验(§FR6.2)无字段支撑,安全审核可被绕过。

---

## 6. 修复优先级建议

### P0(阻断 MVP,必须先修)
1. D1-4 + D1-3:补全安全扫描规则族定义与 op 清单
2. D4-5:统一 skill.yaml 约束模型(artifact_constraints vs review_rules)
3. D3-1 + D4-1:统一 submit_artifact schema,补齐安全字段
4. D1-1:补全 11+ 工具的 inputSchema/outputSchema
5. D4-2:补 derived-artifact-skill + manifest enum + 修 skill 表 UNIQUE
6. D4-4:决策 completeness_contract 与"不解析内容"原则的取舍
7. D3-4:实现 SkillRegistry 三级匹配算法
8. D4-6:修 design-handoff-skill 的 requires_human_review 粒度
9. D1-5:明确 hash 链 payload/创世/锚定/WORM
10. D2-1:补全 25+ 工具的权限边界

### P1(应修,不阻断 MVP 但影响完整性)
D1-6、D1-7、D2-2、D2-3、D2-4、D3-2、D3-3、D3-5、D3-6、D4-3

### P2(可后续迭代)
D2-5、D3-7

---

**评审结束。** §FR4/FR5/FR6 需补全 10 个 P0 项后方可进入 MVP 开发。
