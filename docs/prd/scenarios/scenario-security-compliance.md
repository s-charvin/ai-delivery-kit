# 第四轮压力测试:安全与合规场景

> **文档性质**:对《coordination-platform-prd.md》v2.0 + 第三轮修正的第四轮压力测试
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:架构评审输入
> **测试方法**:选取 4 个安全合规真实场景(A17-A20),逐步走查 PRD 能否处理
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)
> **核心张力**:管理方"不解析内容"原则 vs 安全扫描/合规审计的刚性需求

---

## 0. 测试方法说明

### 0.1 本轮聚焦:安全与合规(前三轮未覆盖)

前三轮共 48 场景、279 缺陷(196 + 83),覆盖大文件/错误引用/热重载/契约变更/多格式/版本共存/hotfix/审批缺席/agent 故障/逆向打回/跨团队/全链路回滚/多 feature 并行/设计稿延迟/mock/跨管线共享/并发竞争/跨仓库引用/演进迁移/运维操作/草案产物/单一 hub 仓/代码产物合一/管线模板复用。**但"产物内容安全"和"仓库安全"几乎空白**——管理方"不解析内容"原则与"安全扫描"存在根本张力,真实开发中这是阻断性风险。

### 0.2 本轮 4 个场景

| 场景 | 主题 | 核心矛盾 |
|---|---|---|
| A17 | 产物中意外包含密钥/凭证 | 不解析内容 → 密钥泄露到 hub 仓,git 历史不可变 |
| A18 | 恶意提交/供应链攻击 | 不解析内容 → 恶意内容/钓鱼链接/SSRF payload 无检测 |
| A19 | 不同密级产物混入同一 hub 仓 | 单一 hub 仓 + 扁平权限模型 → 涉密产物被无权限人看到 |
| A20 | 产物合规审计与溯源 | 事件流 in-memory + 审计无 hash 链 → 合规不可篡改/导出缺失 |

### 0.3 核心张力的解法(贯穿全文)

**问题**:管理方"不解析内容"(主 PRD §1.4 行 69、FR1 行 180)与安全扫描(需读内容)矛盾。

**解法——区分两类"看内容"**:

| 类别 | 定义 | 是否在范围内 | 先例 |
|---|---|---|---|
| **内容解析(业务语义)** | 理解/判断产物的业务含义(如 API 设计好坏、schema 正确性、方法论优劣) | **范围外**(需求 9 自由) | 管理方不校验 YAML/JSON 内容格式(行 69) |
| **安全约束(仓库安全)** | 扫描内容的安全特征(密钥模式、恶意特征、路径穿越),不理解业务语义 | **范围内**(管理约束) | `R_NO_PATH_TRAVERSAL` 已扫描 `source.path` 内容查 `..`(fr1-fr6 §4.1.4 行 620、附录 A 行 1510) |

**判据**:扫描是否"理解业务语义"?否 → 是管理约束(同文件大小/扩展名/路径安全);是 → 是内容解析(出范围)。

**结论**:secret scanning(匹配 AWS key/私钥头模式)、URL safety(校验链接可达性/域名)、content hash(sha256 运算)均**不理解业务语义**,属于"管理约束",不破坏管理方中立性。`R_NO_PATH_TRAVERSAL` 是"扫描内容做安全约束"的既有先例,本轮将其扩展为安全规则族 `R_SECURITY_*`。

---

## 1. 场景 A17:产物中意外包含密钥/凭证(secret leakage)

### 1.1 场景描述

**真实情境**:服务端 agent 提交 `api_contract` 产物,JSON 中意外包含数据库连接串 `postgres://user:pwd@db.internal:5432/prod`、第三方 API key `sk-live-xxx`、OAuth token(从 config 文件复制示例时带入)。

**关键矛盾**:
- 管理方"不解析内容"(行 180)→ 密钥扫描无人做
- hub 仓是单一信息枢纽(附录 D7),所有有仓权限的人可见密钥
- git 历史不可变,squash merge(行 189)后即使新 commit 删除密钥,旧 commit 历史仍可 `git log -p` 访问
- 密钥泄露是时间敏感事件:每多一分钟,泄露面扩大

### 1.2 PRD 走查

| 走查点 | PRD 章节(行号) | 结论 |
|---|---|---|
| 管理方不解析内容 → 密钥扫描谁做? | FR1 行 180"只校验文件存在性 + 扩展名/大小";fr1-fr6 §8.1 CI-1~CI-11(行 1132-1144)全格式/结构 | ❌ **无 secret scanning**。CI-1~CI-11 覆盖目录白名单/命名/manifest schema/扩展名/大小/路径安全/seq/节点类型,无密钥扫描项 |
| CI 有无 secret scanning? | fr1-fr6 §8.1.1 仓库级 CI(行 1130)、§8.1.2 管理方审核(行 1146) | ❌ 两类检查均无密钥扫描规则。规则引擎 8 条(fr1-fr6 §4、附录 A 行 1499-1510)无 `R_SECRET_SCAN` |
| hub 仓 git 历史如何清理? | FR1.2 行 189"squash merge,每产物一个 commit,便于追溯";FR1.2 行 186"main 禁止直接 push" | ❌ squash merge 强调"便于追溯"(不可变),与"清理密钥需 force-push 重写历史"直接冲突。无 history rewrite 规范 |
| 已 clone 的人怎么办? | FR1 无 clone 注册;fr4 §9.5 get_dependencies 用 `git show`(行 1462)拉内容 | ❌ 无 clone/fetch 注册表,无法知道谁已 clone,无法通知清理 |
| 密钥泄露事件如何通知? | fr4 §2 错误码(行 111-148)37 个,无 `SECURITY_*` 域;FR2.5 notify 节点(行 295)只触发飞书/Slack 通用通知 | ❌ 无安全事件错误码/工具/升级链。notify 节点是通用通知,非安全事件响应 |
| 责任人如何追溯? | FR6.5 审计日志(行 534-557)有 submitter/reviewer/merge_commit | ⚠️ 部分支持:audit_log 记 submitter,但无"安全事件"action 类型,无事件关联链 |

### 1.3 设计缺陷

| 编号 | 缺陷 | PRD 定位 | 严重度 |
|---|---|---|---|
| **DA17-R4.1** | CI 无 secret scanning:CI-1~CI-11 与规则引擎 8 条均无密钥扫描,密钥直入 hub 仓 main | fr1-fr6 §8.1(行 1130)、§4(行 481) | **Critical** |
| **DA17-R4.2** | 无安全事件响应机制:无 `SECURITY_SECRET_DETECTED` 错误码、无 `handle_security_incident` 工具、无升级链 | fr4 §2(行 111)、§9(行 1250)、fr1-fr6 §6(行 894) | **High** |
| **DA17-R4.3** | git 历史清理与"不可变追溯"冲突无规范:squash merge 强调不可变,但密钥清理需 force-push,无 policy | FR1.2(行 186-189) | **High** |
| **DA17-R4.4** | 已 clone 用户通知机制缺失:无 clone/fetch 注册表,泄露后无法定位通知对象 | FR1(行 148)、fr4 §9.5(行 1462) | **Medium** |
| **DA17-R4.5** | 密钥泄露责任人追溯断链:audit_log 无 `security_incident` action,无法关联事件链 | FR6.5(行 534)、fr4 §8.1 audit_log(行 1074) | **Medium** |

### 1.4 修正方案

#### 1.4.1 新增安全扫描规则 `R_SECRET_SCAN`(定位为管理约束,非内容解析)

```yaml
# skills/api-contract-skill/skill.yaml 的 review_rules 新增
review_rules:
  - id: R_SECRET_SCAN
    name: 密钥泄露扫描
    priority: 98                    # P0 安全层,仅次于 R_META_REQUIRED(100)
    combinators: AND
    on_fail: reject                 # 命中即 reject,阻止入 main
    checks:
      - field: __files__
        op: secret_scan             # 新增 op:扫描文件内容匹配密钥模式
        value:
          detectors:                # 内置密钥检测器(不理解业务,只匹配特征)
            - aws_access_key        # AKIA[0-9A-Z]{16}
            - aws_secret            # 40 字符 base64 私钥模式
            - private_key_header    # -----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----
            - db_connection_string  # (postgres|mysql|mongodb)://user:pwd@host
            - github_token          # ghp_[a-zA-Z0-9]{36}
            - generic_high_entropy  # 熵值 > 4.5 的长字符串(启发式)
          allowlist_path: .secret-allowlist.yaml  # 误报白名单(如测试用假密钥)
          max_findings: 0           # 0 表示零容忍,任一命中即 reject
```

**`.secret-allowlist.yaml` 示例**(误报白名单,管理方审计):
```yaml
# 已知安全的字符串(如测试 fixture 中的假密钥)
allowlist:
  - pattern: "AKIATESTEXAMPLE000"   # 测试用占位 key
    reason: "测试 fixture,非真实凭证"
    approved_by: admin
    expires_at: "2026-12-31"
```

**新增 op `secret_scan`**(fr1-fr6 §4.1.4 操作符清单补充):
| op | 适用 field | 说明 |
|---|---|---|
| `secret_scan` | `__files__` | 扫描文件内容匹配密钥检测器,不理解业务语义,仅模式匹配 |

#### 1.4.2 新增安全事件错误码与工具

fr4 §2 错误码新增 `SECURITY_*` 域:

| 错误码 | HTTP | 含义 | retryable |
|---|---|---|---|
| `SECURITY_SECRET_DETECTED` | 422 | 产物包含疑似密钥,被 R_SECRET_SCAN 拦截 | false |
| `SECURITY_INCIDENT_EXISTS` | 409 | 该产物已关联未闭环安全事件,禁止操作 | false |

fr4 §9 新增 MCP 工具 `handle_security_incident`(仅 admin):

```json
{
  "name": "handle_security_incident",
  "version": "1.0.0",
  "description": "安全事件响应:密钥泄露/恶意内容事件的处置(仅 admin)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "incident_id": {"type": "string"},
      "action": {"type": "string", "enum": ["acknowledge", "rotate_secret", "quarantine_artifact", "notify_cloned", "close"]},
      "affected_commit": {"type": "string", "description": "含密钥的 commit hash"},
      "rotation_ref": {"type": "string", "description": "密钥轮换工单链接(action=rotate_secret 时必填)"},
      "note": {"type": "string"}
    },
    "required": ["incident_id", "action"],
    "additionalProperties": false
  }
}
```

#### 1.4.3 git 历史清理策略(与 A20 不可篡改审计的冲突调和)

**核心矛盾**:A17 需重写 git 历史清理密钥,但 A20 需 git 历史不可变做审计。**解法:不重写历史,改用"密钥轮换 + 标记 compromised"**。

```yaml
# HubRepoConfig 新增(扩展 fr1-fr6 §3.5 / round3 §3.5)
hub_repo:
  security:
    history_policy: immutable         # immutable(默认,不 force-push) | rewrite_allowed(高危场景)
    secret_cleanup_strategy: rotate   # rotate(轮换密钥,历史保留但标记) | tombstone(新 commit 替换为 REDACTED)
    compromised_commit_retention: 365 # compromised commit 标记保留天数(审计需要)
```

**`tombstone` 策略流程**(不 force-push,保审计):
1. 密钥泄露 commit 不删除,标记为 `compromised`(audit_log 记录)
2. 新 commit 将密钥替换为 `REDACTED_SECRET_<incident_id>`(内容层清理)
3. 密钥在源头轮换(Vault),旧密钥作废 → 历史 commit 中的密钥失效
4. audit_log 完整记录"泄露→轮换→tombstone"链,git 历史不可变(满足 A20)

#### 1.4.4 clone 注册表与通知

fr4 §8.1 新增 `clone_registry` 表:

```sql
CREATE TABLE clone_registry (
    clone_id     BIGSERIAL PRIMARY KEY,
    agent_id     TEXT,                    -- clone 的 agent(null 表示人工)
    user_id      TEXT,                    -- clone 的人员
    clone_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_fetch   TIMESTAMPTZ,             -- 最近 git fetch 时间
    clone_type   TEXT NOT NULL            -- full | partial | shallow
);
-- 每次 get_dependencies / git clone / git fetch 时记录
```

`handle_security_incident(action=notify_cloned)` 查 `clone_registry` 批量通知已 clone 的人清理本地缓存 + 轮换密钥。

### 1.5 Mermaid 设计图:密钥泄露检测与响应流程

```mermaid
flowchart TD
    SUBMIT["server agent 提交 api_contract<br/>JSON 含 db连接串 sk-live-xxx"]
    SUBMIT --> CI{"仓库 CI<br/>CI-1~CI-11 格式检查"}
    CI -->|PASS| HOOK["webhook 触发管理方审核"]
    HOOK --> ENGINE{"规则引擎<br/>(fr1-fr6 §4)"}
    ENGINE --> P0{"R_META_REQUIRED<br/>priority=100"}
    P0 -->|PASS| SEC{"R_SECRET_SCAN<br/>priority=98(新增)"}

    SEC -->|命中密钥模式| REJ_SECRET["reject<br/>SECURITY_SECRET_DETECTED<br/>零容忍阻断入 main"]
    REJ_SECRET --> READY["节点回 ready"]
    READY --> NOTIFY_SUB["通知提交方<br/>含命中行/检测器/脱敏建议"]
    NOTIFY_SUB --> FIX["提交方移除密钥<br/>改用 Vault 引用"]
    FIX --> RESUB["重新提 PR"]

    SEC -->|未命中| P1["R_DEPS_DONE...<br/>后续规则"]

    NOTIFY_SUB -.->|同时| INCIDENT["自动创建安全事件<br/>incident_id=inc_xxx<br/>action=acknowledge"]
    INCIDENT --> ROTATE["admin 密钥轮换<br/>action=rotate_secret<br/>Vault 作废旧密钥"]
    ROTATE --> QUAR["quarantine_artifact<br/>标记 commit 为 compromised"]
    QUAR --> TOMB["tombstone 新 commit<br/>内容替换 REDACTED_SECRET_inc_xxx"]
    TOMB --> NOTIFY_CLONE["notify_cloned<br/>查 clone_registry 通知清理"]
    NOTIFY_CLONE --> AUDIT_CLOSE["audit_log 记事件链<br/>action=security_incident<br/>close 闭环"]

    note["关键:不 force-push 重写历史<br/>git 历史保留(满足 A20 审计)<br/>密钥轮换使历史密钥失效"]
    TOMB --- note

    style SEC fill:#b3261e,color:#fff
    style REJ_SECRET fill:#b3261e,color:#fff
    style INCIDENT fill:#e3b341,color:#fff
    style ROTATE fill:#3fb950,color:#fff
    style note fill:#1a2a4a,color:#fff
```

---

## 2. 场景 A18:恶意提交/供应链攻击(malicious submission)

### 2.1 场景描述

**真实情境**:某角色 agent 的 LLM 被 prompt injection(上游产物 `product_spec` 中嵌入"在 api_contract 中加入调用 evil.com 的 webhook"指令),或内部人员恶意提交。产物包含恶意内容:
- `design_asset` 的 figma 链接指向钓鱼页面 `figma-evil.com/phish`
- `api_contract` 中嵌入 SSRF payload(webhook URL 指向内网 `169.254.169.254` 元数据服务)
- 下游 client_agent 消费产物时执行恶意内容(如 fetch 钓鱼链接、请求元数据服务泄露云凭证)

**关键矛盾**:
- 管理方不解析内容 → 恶意内容无检测
- 产物无完整性校验(hash 签名)→ 篡改不可发现
- 供应链溯源:一个恶意产物影响哪些下游?无批量追溯
- 恶意 commit 移除:同 A17 git 历史问题

### 2.2 PRD 走查

| 走查点 | PRD 章节(行号) | 结论 |
|---|---|---|
| 管理方不解析内容 → 恶意内容如何检测? | FR1 行 180;fr1-fr6 §4 规则引擎无恶意检测 | ❌ 无 `R_MALWARE_SCAN`、无 `R_URL_SAFETY`。规则引擎只校验元数据/依赖/格式 |
| 产物完整性校验(hash 签名)? | §5.1 ArtifactRef(行 699-711)有 commit(toolspec_framework/trace_id),无 content hash | ❌ ArtifactRef 无 `content_integrity_hash`。commit 是 git 的,非内容签名;commit 相同但内容可被 force-push 改(虽 main 禁 push,但 feat 分支可改) |
| 供应链溯源? | FR6.5 audit_log(行 534)有 merge_commit/submitter;fr4 §8.1 node_event(行 988) | ⚠️ 审计记"谁提交/审核",但无 provenance(LLM 模型版本/工具版本),无法判断是否 prompt injection 导致 |
| 受影响下游如何批量通知? | FR2.2 级联失效(行 259)"changed → 下游递归 blocked";fr4 §9.4 reject_pr(行 1423) | ❌ cascade 只处理 `changed` 状态,无"安全事件广播"。一个恶意产物 done 后下游已消费,需反向追溯所有下游 |
| 恶意 commit 如何移除? | 同 A17:FR1.2 行 189 不可变 | ❌ 同 DA17-R4.3 |
| 外部链接产物安全校验? | round3 §3.18(外部链接 url_reachable op);design_asset 含 figma 链接(行 102) | ⚠️ round3 提 `url_reachable` op 仅校验"可达",不校验"安全"(钓鱼域名/内网 IP) |

### 2.3 设计缺陷

| 编号 | 缺陷 | PRD 定位 | 严重度 |
|---|---|---|---|
| **DA18-R4.1** | 产物完整性校验缺失:ArtifactRef 无 content_integrity_hash,内容篡改不可发现 | §5.1(行 699)、fr4 §8.1 artifact_ref(行 951) | **High** |
| **DA18-R4.2** | 恶意内容/URL 安全检测无机制:无 R_URL_SAFETY、无 R_MALWARE_SCAN,钓鱼链接/SSRF payload 直入 | fr1-fr6 §4(行 481)、round3 url_reachable(§3.18) | **High** |
| **DA18-R4.3** | 供应链 provenance 断链:无 LLM 模型版本/工具版本字段,无法追溯恶意产物是否 prompt injection | §5.1 ArtifactRef(行 699)、fr4 §8.1(行 951) | **High** |
| **DA18-R4.4** | 受影响下游批量通知缺失:cascade 只处理 changed,无 security_incident_broadcast 反向追溯 | FR2.2(行 259)、fr4 §9(行 1250) | **Medium** |
| **DA18-R4.5** | prompt injection 防护定位空白:agent LLM 被注入属执行层问题,管理方无隔离/检测 | FR3(行 308)、范围边界(行 64) | **Medium** |

### 2.4 修正方案

#### 2.4.1 ArtifactRef 增 content_integrity_hash + provenance

```python
class ArtifactRef(TypedDict):
    # ... 既有字段 ...
    content_integrity_hash: str       # 新增:产物内容 sha256(合并时计算,防篡改)
    provenance: Provenance            # 新增:溯源信息

class Provenance(TypedDict):
    generator_type: str               # "agent" | "human" | "import"(round3 存量迁移)
    agent_id: str | None              # 生成 agent
    llm_model: str | None             # LLM 模型版本(如 "glm-5.2")—追溯 prompt injection
    toolspec_framework: str           # 生成工具(已有)
    toolspec_version: str | None      # 工具版本
    generated_at: str                 # 生成时间(ISO 8601)
```

**完整性校验**:合并时计算 `content_integrity_hash = sha256(file_content)`,存 audit_log + ArtifactRef。下游消费时(`get_dependencies`)可重算 hash 校验内容未被中途篡改(feat 分支 push 新 commit 后 hash 变化,触发重审)。

#### 2.4.2 新增 R_URL_SAFETY + R_MALWARE_SCAN 规则

```yaml
review_rules:
  - id: R_URL_SAFETY
    name: 外部链接安全校验
    priority: 97
    combinators: AND
    on_fail: reject
    checks:
      - field: __files__
        op: url_safety_scan          # 新增 op:提取 URL 并校验安全
        value:
          url_fields: ["figma_url", "webhook_url", "external_refs"]  # 待校验字段
          block_private_ip: true     # 拦截 169.254.169.254/10.x/172.16.x/192.168.x(SSRF)
          block_phishing_domain: true # 对接钓鱼域名库
          require_https: true        # 强制 https
          allowlist_path: .url-allowlist.yaml

  - id: R_MALWARE_SCAN
    name: 恶意特征扫描
    priority: 96
    combinators: AND
    on_fail: needs_human             # 命中转人工复核(避免误报阻断)
    checks:
      - field: __files__
        op: malware_scan             # 新增 op:扫描已知恶意特征
        value:
          signature_db: clamav       # 对接 ClamAV 签名库
          yara_rules: true           # YARA 规则匹配
          max_filesize_mb: 10        # 超过不扫(性能)
```

**新增 op**(fr1-fr6 §4.1.4 补充):
| op | 适用 field | 说明 |
|---|---|---|
| `url_safety_scan` | `__files__` | 提取 URL 校验:私网 IP/钓鱼域名/https,不理解业务语义 |
| `malware_scan` | `__files__` | 对接 ClamAV/YARA 扫描恶意特征,不理解业务语义 |

#### 2.4.3 安全事件反向广播工具

fr4 §9 新增 `broadcast_security_incident`(仅 admin,反向追溯下游):

```json
{
  "name": "broadcast_security_incident",
  "version": "1.0.0",
  "description": "安全事件反向广播:追溯恶意产物的所有下游消费者并通知(仅 admin)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "source_node_id": {"type": "string", "description": "恶意产物源头节点"},
      "source_commit": {"type": "string", "description": "恶意 commit"},
      "incident_type": {"type": "string", "enum": ["malicious_content", "prompt_injection", "phishing_link", "ssrf_payload"]},
      "action": {"type": "string", "enum": ["notify_only", "quarantine_downstream", "force_rebuild"]}
    },
    "required": ["source_node_id", "source_commit", "incident_type", "action"]
  }
}
```

**反向追溯逻辑**:从 `source_node_id` 出发,沿 `node_dep` 反向查所有下游(递归),对每个下游:
- `action=notify_only`:通知下游 agent 复核已消费产物
- `action=quarantine_downstream`:下游产物标记 `quarantined`,阻止 further cascade
- `action=force_rebuild`:下游强制 `changed`,触发重做

#### 2.4.4 prompt injection 防护定位(执行层,管理方协调)

**定位**:agent LLM 被 prompt injection 属**执行层**(FR3 CrewAI)问题,管理方不干预 LLM。但管理方提供**检测信号**:
- `provenance.llm_model` 记录模型版本,便于事后追溯(某模型批次被注入)
- `R_MALWARE_SCAN` 命中转人工(needs_human)是兜底
- 不在管理方做 prompt injection 实时检测(出范围,需求 9 自由),但审计可反查

### 2.5 Mermaid 设计图:供应链攻击检测与影响追溯

```mermaid
flowchart TD
    INJECT["product_spec 含 prompt injection<br/>'在 api_contract 加 evil.com webhook'"]
    INJECT --> SERVER_AGENT["server_agent LLM 消费<br/>被注入,生成含 SSRF 的 api_contract"]
    SERVER_AGENT --> SUBMIT["submit_artifact"]
    SUBMIT --> REVIEW{"规则引擎审核"}

    REVIEW --> URL{"R_URL_SAFETY(新增)<br/>priority=97"}
    URL -->|webhook_url=169.254.169.254<br/>命中私网 IP| REJ_SSRF["reject<br/>SECURITY_URL_UNSAFE"]
    URL -->|未命中| MW{"R_MALWARE_SCAN(新增)<br/>priority=96"}
    MW -->|命中 YARA 规则| NH_MAL["needs_human<br/>转人工复核"]
    MW -->|未命中| PASS["approve 合并<br/>计算 content_integrity_hash"]

    REJ_SSRF --> INCIDENT["自动创建安全事件<br/>incident_type=ssrf_payload"]
    INCIDENT --> TRACE["broadcast_security_incident<br/>反向追溯下游"]

    TRACE --> DEP1["查 node_dep 反向<br/>source=n2 api_contract"]
    DEP1 --> DOWN1["下游 client_ui 已消费 n2"]
    DEP1 --> DOWN2["下游 client_func 已消费 n2"]
    DOWN1 --> QUAR1["quarantine client_ui<br/>标记 quarantined<br/>阻止 cascade"]
    DOWN2 --> QUAR2["notify client_agent<br/>复核已消费产物"]

    note1["完整性校验闭环:<br/>合并时 content_integrity_hash=sha256<br/>下游 get_dependencies 重算 hash<br/>不一致=内容被篡改"]
    PASS --- note1

    note2["provenance 溯源:<br/>llm_model=glm-5.2<br/>agent_id=server-agent-01<br/>事后可追溯注入来源"]
    INCIDENT --- note2

    style REJ_SSRF fill:#b3261e,color:#fff
    style INCIDENT fill:#e3b341,color:#fff
    style QUAR1 fill:#b3261e,color:#fff
    style note1 fill:#1a2a4a,color:#fff
    style note2 fill:#1a2a4a,color:#fff
```

---

## 3. 场景 A19:不同密级产物混入同一 hub 仓(classification mixing)

### 3.1 场景描述

**真实情境**:企业中部分产物涉密(如核心推荐算法 spec、内部架构图、未公开财报数据引用),部分可公开(如开放 API 文档、开源 SDK 文档)。单一 hub 仓模型(附录 D7)下,所有产物混在一个仓库,权限模型只有"角色→node_type"(§3.2 行 132),无"产物密级"概念。涉密产物可能被无权限人员(如外包 client_agent、外部 reviewer)通过 `git clone` 或 `get_dependencies` 看到。

**关键矛盾**:
- 单一 hub 仓是"信息枢纽"(round3 §6),所有产物物理共存
- 权限模型扁平(§3.2 只有 role→tool/role→node_type),无密级维度
- `get_dependencies`(fr4 §9.5 行 1462)任何角色可调,`git show` 拉上游内容无密级过滤
- round3 RoleInstance(§3.8)实例化了团队,但无密级 clearance

### 3.2 PRD 走查

| 走查点 | PRD 章节(行号) | 结论 |
|---|---|---|
| hub 仓权限模型是否支持密级? | §3.2 权限矩阵(行 132-142):role→tool/role→node_type;round3 §3.8 RoleInstance | ❌ 无 classification 维度。RoleInstance 有 allowed_external_repos,无 clearance 字段 |
| 目录级权限? | FR1.1(行 154-174)按 node_type 扁平目录;CODEOWNERS(round3 §3.10 get_codeowners) | ⚠️ CODEOWNERS 可按路径,但无密级 ACL。涉密产物与公开产物同目录混存 |
| 产物标记密级(classification field)? | fr1-fr6 §3.3 manifest schema(行 266-444) | ❌ manifest 有 node_id/version/source/toolspec/deps,无 classification 字段 |
| 下游依赖密级校验? | fr1-fr6 §4 规则引擎 R_DEPS_*(行 513-529) | ❌ R_DEPS_DONE 只查状态,R_DEPS_MIN_VERSION 只查版本,无密级一致性校验 |
| 跨密级引用管控? | round3 §3.13 hub:// 协议(行 333);get_dependencies(行 1462) | ❌ hub:// 无密级校验;get_dependencies 无 caller clearance 过滤 |

### 3.3 设计缺陷

| 编号 | 缺陷 | PRD 定位 | 严重度 |
|---|---|---|---|
| **DA19-R4.1** | 产物无密级标记:manifest schema 无 classification 字段,涉密产物与公开产物无区分 | fr1-fr6 §3.3(行 266) | **High** |
| **DA19-R4.2** | hub 仓权限模型无密级:RoleInstance 无 clearance,CODEOWNERS 无密级 ACL | §3.2(行 132)、round3 §3.8(行 252) | **High** |
| **DA19-R4.3** | 跨密级依赖校验缺失:公开产物可依赖涉密产物,R_DEPS_* 无密级一致性规则 | fr1-fr6 §4(行 513) | **High** |
| **DA19-R4.4** | get_dependencies 无密级过滤:任何角色 git show 拉取上游内容无 clearance 校验,涉密产物泄露 | fr4 §9.5(行 1462) | **Critical** |
| **DA19-R4.5** | 跨管线 hub:// 引用无密级管控:round3 hub:// 协议绕过本管线校验,跨管线密级泄露 | round3 §3.13(行 333) | **Medium** |

### 3.4 修正方案

#### 3.4.1 manifest 增 classification 字段 + ArtifactRef 透传

fr1-fr6 §3.3 manifest schema 新增:

```json
{
  "classification": {
    "type": "string",
    "description": "产物密级",
    "enum": ["public", "internal", "confidential", "restricted"],
    "default": "internal"
  }
}
```

密级语义(对齐企业通用分级):

| 密级 | 含义 | 可见范围 |
|---|---|---|
| `public` | 可公开(开源 API 文档) | 所有人 + 外部 |
| `internal` | 内部(默认,常规 spec) | 全公司员工 |
| `confidential` | 机密(核心算法 spec、未公开架构) | 授权项目组 |
| `restricted` | 限制(未公开财报、合规敏感) | 明确名单 |

ArtifactRef 透传 classification(§5.1):
```python
class ArtifactRef(TypedDict):
    # ... 既有 ...
    classification: str    # 新增:public|internal|confidential|restricted
```

#### 3.4.2 RoleInstance 增 clearance 字段

round3 §3.8 RoleInstance 扩展:

```python
class RoleInstance(TypedDict):
    # ... 既有 ...
    clearance: str                   # 新增:该实例最高可见密级 public|internal|confidential|restricted
    allowed_classifications: list[str]  # 新增:可产出的密级(如外包 instance 仅 public)
```

**校验时机**:
- `submit_artifact`:产物 classification 必须在 RoleInstance.allowed_classifications 内(外包不能提 confidential)
- `get_dependencies`:上游产物 classification 必须 ≤ caller RoleInstance.clearance(否则脱敏或拒绝)

#### 3.4.3 新增 R_CLASSIFICATION_CONSISTENCY 规则

```yaml
review_rules:
  - id: R_CLASSIFICATION_CONSISTENCY
    name: 跨密级依赖一致性
    priority: 88                     # P1 依赖层
    combinators: AND
    on_fail: reject
    checks:
      - field: deps
        op: classification_ge_self    # 新增 op:所有依赖密级 >= 本产物密级
        # 逻辑:public 产物可依赖 internal(更严),但 internal 不能依赖 public? 
        # 反向:本产物密级必须 >= 所有依赖密级(低密级不能承载高密级内容)
        # 即 confidential 产物可依赖 public/internal,但 public 产物不能依赖 confidential
```

**新增 op**(fr1-fr6 §4.1.4):
| op | 适用 field | 说明 |
|---|---|---|
| `classification_ge_self` | `deps` | 所有依赖产物的 classification 密级 ≤ 本产物密级(低密级产物不能依赖高密级) |

**密级偏序**:`public < internal < confidential < restricted`。本产物密级必须 ≥ 所有依赖密级,否则 reject(防止"公开产物嵌入涉密内容")。

#### 3.4.4 get_dependencies 增密级过滤

fr4 §9.5 get_dependencies 升级:

```json
{
  "name": "get_dependencies",
  "version": "1.2.0",
  "inputSchema": {
    "properties": {
      "node_id": {"type": "string"},
      "include_content": {"type": "boolean", "default": true},
      "max_content_kb": {"type": "integer", "default": 512},
      "classification_filter": {"type": "string", "enum": ["auto", "metadata_only"], "default": "auto"}
    }
  }
}
```

**过滤逻辑**:
- `classification_filter=auto`:上游产物 classification > caller clearance 时,返回 metadata(引用)但**拒绝返回 content**,响应含 `redacted_reason: "classification_confidential_exceeds_clearance"`
- `classification_filter=metadata_only`:只返回引用元数据,不拉内容(敏感场景)

新增错误码:
| 错误码 | HTTP | 含义 |
|---|---|---|
| `CLASSIFICATION_EXCEEDS_CLEARANCE` | 403 | 产物密级超过调用方 clearance,内容拒绝返回 |

#### 3.4.5 hub:// 协议增密级校验

round3 §3.13 hub_ref 扩展:
```python
class DepDeclaration(TypedDict):
    node_id: str | None
    hub_ref: str | None           # "hub://{pipeline_id}/{node_id}@{version}"
    # 新增:跨管线引用时声明预期密级(校验对方产物密级 <= 本产物密级)
    expected_classification: str | None
```

解析 hub_ref 时,查目标产物 classification,与 `expected_classification` 校验一致性。

### 3.5 Mermaid 设计图:密级模型与依赖一致性校验

```mermaid
flowchart TD
    subgraph CLEARANCE["密级偏序 public < internal < confidential < restricted"]
        PUB["public<br/>开源 API 文档"]
        INT["internal<br/>常规 spec(默认)"]
        CONF["confidential<br/>核心算法 spec"]
        REST["restricted<br/>未公开财报引用"]
        PUB --> INT --> CONF --> REST
    end

    SUBMIT["client_agent(外包)<br/>clearance=internal<br/>allowed_classifications=public"]
    SUBMIT --> CHECK1{"submit_artifact 校验<br/>产物 classification 在<br/>allowed_classifications 内?"    }
    CHECK1 -->|产物=confidential<br/>不在 allowed| REJ1["reject<br/>PERMISSION_ROLE_MISMATCH<br/>外包不能提 confidential"]

    GETDEP["server_agent(正式)<br/>clearance=confidential<br/>调 get_dependencies(n_core_algo)"]
    GETDEP --> CHECK2{"上游 classification<br/><= caller clearance?"}
    CHECK2 -->|n_core_algo=confidential<br/><= clearance=confidential| OK1["返回 content"]
    CHECK2 -->|n_core_algo=restricted<br/>> clearance=confidential| REDACT["返回 metadata only<br/>redacted_reason=<br/>classification_exceeds_clearance"]

    DEPCHK["api_contract(classification=public)<br/>deps: [product_spec(confidential)]"]
    DEPCHK --> RULE{"R_CLASSIFICATION_CONSISTENCY<br/>本产物密级 >= 所有依赖密级?"}
    RULE -->|public >= confidential? 否| REJ2["reject<br/>公开产物不能依赖涉密产物<br/>防止涉密内容泄露到公开产物"]

    style REJ1 fill:#b3261e,color:#fff
    style REDACT fill:#e3b341,color:#fff
    style REJ2 fill:#b3261e,color:#fff
    style CLEARANCE fill:#1a2a4a,color:#fff
```

---

## 4. 场景 A20:产物合规审计与溯源(compliance audit)

### 4.1 场景描述

**真实情境**:监管(SOC 2 / GDPR / 行业合规)要求追溯"某产物在什么时候被谁创建/修改/审核/合并,下游影响哪些产物,内容是否被篡改"。PRD 有 events 事件流(§FR2.3 行 268)和 get_audit_log(fr4 §9.14),但:
- events 是 PipelineState 的 in-memory `Annotated[Sequence[dict], operator.add]`(行 268),管线结束/重启后是否丢失?
- 审计日志如何持久化?(fr4 §8.1 有 node_event + audit_log 表,但与 PipelineState.events 关系未明)
- 合规导出?(get_audit_log 只返回原始记录,无结构化 provenance chain 导出)
- 不可篡改?(fr4 §8.3 append-only 触发器防应用层 UPDATE/DELETE,但 DBA 可绕过,无 hash 链)

### 4.2 PRD 走查

| 走查点 | PRD 章节(行号) | 结论 |
|---|---|---|
| 事件流持久化? | FR2.3 PipelineState.events(行 268)in-memory;fr4 §8.1 node_event 表(行 988)持久化;NFR3(行 863)checkpointer 持久化 | ⚠️ **部分支持**:node_event 表持久化事件,但 PipelineState.events 与 node_event 表谁是权威源未明确。checkpointer 持久化 state(含 events),但 state 可被 langgraph_invoke 覆盖,events 是否累积未明 |
| 审计日志不可篡改? | fr4 §8.3(行 1186-1199)append-only 触发器防 UPDATE/DELETE | ⚠️ **部分支持**:触发器防应用层,但 DBA 有 superuser 可绕过触发器。无 hash 链/签名,内部威胁无防护。NFR9(行 869)"不可篡改"未落地机制 |
| 合规导出? | fr4 §9.14 get_audit_log(行 1882)返回 entries 列表 | ❌ 只返回扁平记录,无结构化合规报告(某产物的完整 provenance chain:创建→修改→审核→合并→下游影响) |
| 审计与产物内容关联? | fr4 §8.1 audit_log.merge_commit(行 1083);ArtifactRef.commit(行 956) | ⚠️ merge_commit 关联 git,但无 content_integrity_hash(A18 缺陷),产物被 force-push 改后审计失真 |
| 跨管线审计? | fr4 §9.14 get_audit_log 无 pipeline_id 必填(行 1893) | ✅ 支持跨管线查询(不强制 pipeline_id)。但 round3 hub:// 跨管线引用的审计关联未明 |
| 保留策略? | NFR9(行 869)"保留 ≥ 1 年";fr4 §8.4(行 1224)audit_log 月分区,保留 ≥12 月 | ⚠️ 1 年不满足金融(7 年)/医疗(6 年)合规。无 configurable retention per compliance regime |

### 4.3 设计缺陷

| 编号 | 缺陷 | PRD 定位 | 严重度 |
|---|---|---|---|
| **DA20-R4.1** | 审计日志无 hash 链:append-only 触发器防应用层,但 DBA superuser 可绕过,无 hash chaining/签名,内部威胁无防护 | fr4 §8.3(行 1186)、NFR9(行 869) | **High** |
| **DA20-R4.2** | 无合规导出工具:get_audit_log 只返回扁平记录,无 export_compliance_report 结构化 provenance chain | fr4 §9.14(行 1882) | **Medium** |
| **DA20-R4.3** | 审计与产物内容完整性关联断链:audit_log 无 content_integrity_hash,force-push 改内容后审计失真 | fr4 §8.1 audit_log(行 1074)、§5.1 ArtifactRef(行 699) | **High** |
| **DA20-R4.4** | 保留策略不可配置:NFR9 固定 1 年,金融/医疗合规需 7/6 年,无 per-regime retention | NFR9(行 869)、fr4 §8.4(行 1224) | **Medium** |
| **DA20-R4.5** | PipelineState.events 与 node_event 表权威源未明确:state 可被覆盖,事件可能丢失 | FR2.3(行 268)、fr4 §8.1(行 988) | **Medium** |

### 4.4 修正方案

#### 4.4.1 审计日志 hash 链(防内部篡改)

fr4 §8.1 audit_log 表新增 `prev_hash` + `entry_hash` 字段:

```sql
ALTER TABLE audit_log
    ADD COLUMN prev_hash  TEXT,      -- 上一条 entry_hash(链式)
    ADD COLUMN entry_hash TEXT NOT NULL,  -- 本条 hash = sha256(prev_hash || canonical_json(entry))
    ADD COLUMN signer     TEXT;      -- 签名者(管理方 bot key_id)

-- 插入时计算(应用层):
-- entry_hash = sha256(prev_hash || json_stable_sort(entry_fields))
-- 定期可由独立 KMS 对最新 entry_hash 签名,锚定到外部(如 WORM 存储)
```

**校验机制**:定时任务(每小时)从最早记录重算 hash 链,任一 `entry_hash` 不匹配 → 告警 admin(SOC 2 控制)。定期将最新 `entry_hash` 锚定到外部 WORM(Write Once Read Many)存储或区块链,防 DBA 篡改整链。

```mermaid
flowchart LR
    E1["entry_1<br/>entry_hash=h1<br/>prev_hash=genesis"] --> E2["entry_2<br/>entry_hash=h2<br/>prev_hash=h1"]
    E2 --> E3["entry_3<br/>entry_hash=h3<br/>prev_hash=h2"]
    E3 --> ANCHOR["每小时锚定<br/>最新 h3 → WORM 存储<br/>DBA 无法篡改 WORM"]
    ANCHOR --> VERIFY["定时校验<br/>重算 h1→h2→h3<br/>不匹配告警 SOC2"]
```

#### 4.4.2 新增 export_compliance_report 工具

fr4 §9 新增(仅 reviewer/admin):

```json
{
  "name": "export_compliance_report",
  "version": "1.0.0",
  "description": "合规审计导出:某产物的完整 provenance chain(创建/修改/审核/合并/下游影响/完整性)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {"type": "string", "description": "目标产物节点"},
      "pipeline_id": {"type": "string"},
      "ts_from": {"type": "string", "format": "date-time"},
      "ts_to": {"type": "string", "format": "date-time"},
      "include_downstream": {"type": "boolean", "default": true, "description": "是否含下游影响链"},
      "format": {"type": "string", "enum": ["json", "pdf"], "default": "json"}
    },
    "required": ["node_id", "pipeline_id"]
  }
}
```

**报告结构**:
```json
{
  "artifact": {
    "node_id": "n2", "node_type": "api_contract",
    "current_version": "1.2.0", "classification": "internal",
    "content_integrity_hash": "sha256:abc...", "merge_commit": "a1b2c3"
  },
  "provenance_chain": [
    {"ts": "...", "action": "submit_artifact", "actor": "server-agent-01", "provenance": {"llm_model": "glm-5.2"}},
    {"ts": "...", "action": "review_artifact_pr", "verdict": "approve", "rules_version": "1.1"},
    {"ts": "...", "action": "approve_pr", "reviewer": "mgmt-bot", "merge_commit": "a1b2c3"}
  ],
  "downstream_impact": [
    {"node_id": "n5", "pipeline_id": "...", "status": "done", "consumed_at": "..."}
  ],
  "integrity_verification": {
    "content_hash_matches": true,
    "audit_hash_chain_valid": true,
    "last_anchored_at": "..."
  }
}
```

#### 4.4.3 审计与产物完整性关联

audit_log 表新增 `content_integrity_hash`(关联 A18):

```sql
ALTER TABLE audit_log
    ADD COLUMN content_integrity_hash TEXT;  -- 合并时产物的 sha256(关联 ArtifactRef)
```

**闭环**:audit_log 记录合并时的 content_integrity_hash → 合规导出时重算当前产物 hash → 比对 → 不一致即"内容被篡改"(force-push 或人为改)。与 A17 tombstone 策略协同:密钥清理的 tombstone commit 是新 hash,audit_log 记录 `security_incident` action 链,历史 hash 保留可追溯。

#### 4.4.4 可配置保留策略

NFR9 升级 + fr4 §8.4 分区策略:

```yaml
# 合规保留配置(扩展 fr4 §8.4)
compliance_retention:
  default_months: 12              # 默认 1 年
  regimes:
    - name: financial             # 金融合规
      retention_months: 84        # 7 年
      node_types: [api_contract, server_impl]  # 仅涉财务接口产物
    - name: healthcare            # 医疗合规
      retention_months: 72        # 6 年
      classifications: [confidential, restricted]  # 仅机密+
  archive_target: s3_worm         # 归档到 WORM 冷存储
```

分区保留由 pg_partman 按配置自动保留/归档,而非统一 12 月。

#### 4.4.5 events 权威源明确

明确:**node_event 表为权威源**,PipelineState.events 为运行时缓存。

- 所有状态变更必须先写 `node_event` 表(append-only),再更新 PipelineState.events
- 管线重启时从 `node_event` 表重放重建 PipelineState.events(事件溯源)
- PipelineState.events 可被覆盖/丢失,但 node_event 永不丢

### 4.5 Mermaid 设计图:合规审计 hash 链与导出

```mermaid
sequenceDiagram
    autonumber
    participant AG as Agent
    participant MCP as MCP Server
    participant LG as LangGraph
    participant NE as node_event 表(权威源)
    participant AL as audit_log 表(hash 链)
    participant WORM as WORM 锚定存储
    participant AUD as reviewer/admin

    AG->>MCP: approve_pr(pr_id=42)
    MCP->>LG: langgraph_invoke(set_done)
    LG->>NE: INSERT node_event(state_change, n2, ready→done)
    LG-->>MCP: state=done
    MCP->>MCP: 计算 content_integrity_hash=sha256
    MCP->>AL: INSERT audit_log(action=approve_pr, merge_commit, content_integrity_hash, prev_hash=上条entry_hash, entry_hash=sha256(...))

    Note over AL,WORM: 每小时锚定
    AL->>WORM: 锚定最新 entry_hash 到 WORM(不可改)

    Note over AUD: 合规审计请求
    AUD->>MCP: export_compliance_report(node_id=n2)
    MCP->>NE: 查 n2 全部 node_event
    MCP->>AL: 查 n2 全部 audit_log(含 hash 链)
    MCP->>MCP: 重算 hash 链校验(entry_hash 连续性)
    MCP->>MCP: 重算当前产物 content_integrity_hash 比对 audit 记录
    alt hash 链断裂 或 内容 hash 不匹配
        MCP-->>AUD: 报告标记 integrity_compromised + 告警
    else 校验通过
        MCP-->>AUD: 完整 provenance_chain + downstream_impact + integrity_verification
    end
```

---

## 5. 缺陷汇总表

### 5.1 缺陷统计

| 场景 | Critical | High | Medium | Low | 合计 |
|---|---|---|---|---|---|
| A17 密钥泄露 | 1 | 2 | 2 | 0 | 5 |
| A18 恶意提交 | 0 | 3 | 2 | 0 | 5 |
| A19 密级混入 | 1 | 3 | 1 | 0 | 5 |
| A20 合规审计 | 0 | 2 | 3 | 0 | 5 |
| **合计** | **2** | **10** | **8** | **0** | **20** |

### 5.2 缺陷明细

| 编号 | 场景 | 缺陷 | 严重度 | PRD 定位 |
|---|---|---|---|---|
| DA17-R4.1 | A17 | CI 无 secret scanning | Critical | fr1-fr6 §8.1、§4 |
| DA17-R4.2 | A17 | 无安全事件响应机制 | High | fr4 §2、§9、fr1-fr6 §6 |
| DA17-R4.3 | A17 | git 历史清理与不可变追溯冲突 | High | FR1.2 |
| DA17-R4.4 | A17 | 已 clone 用户通知缺失 | Medium | FR1、fr4 §9.5 |
| DA17-R4.5 | A17 | 密钥泄露责任人追溯断链 | Medium | FR6.5、fr4 §8.1 |
| DA18-R4.1 | A18 | 产物完整性校验缺失(content hash) | High | §5.1、fr4 §8.1 |
| DA18-R4.2 | A18 | 恶意内容/URL 安全检测无机制 | High | fr1-fr6 §4 |
| DA18-R4.3 | A18 | 供应链 provenance 断链(LLM 模型版本) | High | §5.1、fr4 §8.1 |
| DA18-R4.4 | A18 | 受影响下游批量通知缺失 | Medium | FR2.2、fr4 §9 |
| DA18-R4.5 | A18 | prompt injection 防护定位空白 | Medium | FR3、§1.4 |
| DA19-R4.1 | A19 | 产物无密级标记(classification) | High | fr1-fr6 §3.3 |
| DA19-R4.2 | A19 | hub 仓权限模型无密级(clearance) | High | §3.2、round3 §3.8 |
| DA19-R4.3 | A19 | 跨密级依赖校验缺失 | High | fr1-fr6 §4 |
| DA19-R4.4 | A19 | get_dependencies 无密级过滤 | Critical | fr4 §9.5 |
| DA19-R4.5 | A19 | hub:// 跨管线引用无密级管控 | Medium | round3 §3.13 |
| DA20-R4.1 | A20 | 审计日志无 hash 链(内部威胁) | High | fr4 §8.3、NFR9 |
| DA20-R4.2 | A20 | 无合规导出工具 | Medium | fr4 §9.14 |
| DA20-R4.3 | A20 | 审计与产物内容完整性关联断链 | High | fr4 §8.1、§5.1 |
| DA20-R4.4 | A20 | 保留策略不可配置(金融/医疗) | Medium | NFR9、fr4 §8.4 |
| DA20-R4.5 | A20 | events 权威源未明确 | Medium | FR2.3、fr4 §8.1 |

### 5.3 P0 修正项(Phase 1 必做,共 8 项)

| 编号 | 修正项 | 影响 | 章节 |
|---|---|---|---|
| **P0-R4.1** | 新增 R_SECRET_SCAN 规则 + secret_scan op(CI 密钥扫描) | DA17-R4.1 | fr1-fr6 §4/§8 |
| **P0-R4.2** | ArtifactRef 增 content_integrity_hash + provenance | DA18-R4.1/4.3、DA20-R4.3 | §5.1、fr4 §8.1 |
| **P0-R4.3** | manifest 增 classification 字段 + RoleInstance 增 clearance | DA19-R4.1/4.2 | fr1-fr6 §3.3、round3 §3.8 |
| **P0-R4.4** | get_dependencies 增密级过滤 + CLASSIFICATION_EXCEEDS_CLEARANCE 错误码 | DA19-R4.4 | fr4 §9.5、§2 |
| **P0-R4.5** | 新增 R_URL_SAFETY + R_MALWARE_SCAN 规则 | DA18-R4.2 | fr1-fr6 §4 |
| **P0-R4.6** | 新增 SECURITY_* 错误码域 + handle_security_incident 工具 | DA17-R4.2、DA18-R4.4 | fr4 §2、§9 |
| **P0-R4.7** | audit_log 增 hash 链(prev_hash/entry_hash)+ WORM 锚定 | DA20-R4.1 | fr4 §8.3、NFR9 |
| **P0-R4.8** | 新增 export_compliance_report 工具 + 可配置保留策略 | DA20-R4.2/4.4 | fr4 §9、§8.4 |

### 5.4 根因归类(4 大根因)

| 根因 | 影响缺陷 | 核心问题 | 影响范围 |
|---|---|---|---|
| **R1. 安全扫描定位空白** | DA17-R4.1/4.2、DA18-R4.2/4.5 | "不解析内容"被过度解读为"不做任何内容扫描",忽略 R_NO_PATH_TRAVERSAL 已有先例;安全规则族 R_SECURITY_* 缺失 | fr1-fr6 §4/§8 + fr4 §2 |
| **R2. 产物完整性/provenance 缺失** | DA18-R4.1/4.3/4.4、DA20-R4.3 | ArtifactRef 无 content_integrity_hash、无 provenance(LLM 模型版本),篡改不可发现、供应链不可溯 | §5.1 + fr4 §8.1 |
| **R3. 权限模型无密级维度** | DA19-R4.1~4.5 | 单一 hub 仓 + 扁平 role→node_type 权限,无 classification/clearance,涉密产物泄露 | §3.2 + fr1-fr6 §3.3 + fr4 §9.5 |
| **R4. 审计防篡改与导出不完整** | DA20-R4.1~4.5、DA17-R4.5 | append-only 触发器防不住 DBA,无 hash 链;无合规导出;保留策略僵化 | fr4 §8 + NFR9 |

---

## 6. 关键认知与设计张力

### 6.1 核心张力的解决(贯穿 4 场景)

**管理方"不解析内容"原则 vs 安全扫描的刚性需求**,通过以下分层解决:

1. **内容解析(业务语义)= 范围外**:不判断 API 设计好坏、schema 正确性(需求 9 自由)
2. **安全约束(仓库安全)= 范围内**:扫描安全特征(密钥/恶意/URL/路径),不理解业务语义
3. **先例**:R_NO_PATH_TRAVERSAL(fr1-fr6 §4.1.4 行 620)已扫描 `source.path` 内容查 `..`——这就是"扫描内容做安全约束"的既有先例
4. **扩展**:本轮将单条 R_NO_PATH_TRAVERSAL 扩展为安全规则族 `R_SECRET_SCAN`/`R_URL_SAFETY`/`R_MALWARE_SCAN`,均定位为管理约束,不破坏中立性

### 6.2 A17 与 A20 的设计冲突调和

**冲突**:A17(密钥泄露)需重写 git 历史清理密钥;A20(合规审计)需 git 历史不可变做审计。

**解法**:不 force-push 重写历史,改用"密钥轮换 + tombstone + compromised 标记":
- 历史 commit 保留(满足 A20 不可变审计)
- 密钥在源头轮换(Vault 作废),历史密钥失效(消除 A17 泄露风险)
- 新 commit 替换为 REDACTED(内容层清理)
- audit_log 完整记录事件链(满足 A20 可追溯)

### 6.3 单一 hub 仓的安全边界

round3 §6 确立"单一 hub 仓是信息枢纽而非权限枢纽"。本轮 A19 进一步:即使物理共存,需在 RoleInstance clearance + manifest classification + get_dependencies 过滤三层实现逻辑密级隔离。hub 仓物理单点,但逻辑权限分层——这与 round3"权限隔离需在 RoleInstance + CODEOWNERS 层补充"一致,classification 是该方向的深化。

### 6.4 与前三轮的关系

| 前三轮修正 | 本轮深化 |
|---|---|
| round3 §3.7 R_EXTERNAL_REF_OWNERSHIP(引用归属) | DA18-R4.2 扩展为 R_URL_SAFETY(链接安全)+ R_MALWARE_SCAN |
| round3 §3.8 RoleInstance(实例化) | DA19-R4.2 增 clearance 字段 |
| round3 §3.13 hub:// 协议 | DA19-R4.5 增密级校验 |
| round3 §3.18 url_reachable | DA18-R4.2 升级为 url_safety_scan(安全而非仅可达) |
| fr4 §8.3 audit_log append-only 触发器 | DA20-R4.1 增 hash 链防内部篡改 |

---

## 7. 修正优先级矩阵

| 优先级 | 修正项 | 影响缺陷 | 阶段 |
|---|---|---|---|
| **P0** | R_SECRET_SCAN + secret_scan op(§1.4.1) | DA17-R4.1 | Phase 1 |
| **P0** | ArtifactRef content_integrity_hash + provenance(§2.4.1) | DA18-R4.1/4.3、DA20-R4.3 | Phase 1 |
| **P0** | manifest classification + RoleInstance clearance(§3.4.1/3.4.2) | DA19-R4.1/4.2 | Phase 1 |
| **P0** | get_dependencies 密级过滤(§3.4.4) | DA19-R4.4 | Phase 1 |
| **P0** | R_URL_SAFETY + R_MALWARE_SCAN(§2.4.2) | DA18-R4.2 | Phase 1 |
| **P0** | SECURITY_* 错误码 + handle_security_incident(§1.4.2) | DA17-R4.2、DA18-R4.4 | Phase 1 |
| **P0** | audit_log hash 链 + WORM 锚定(§4.4.1) | DA20-R4.1 | Phase 1 |
| **P0** | export_compliance_report + 可配置保留(§4.4.2/4.4.4) | DA20-R4.2/4.4 | Phase 1 |
| **P1** | R_CLASSIFICATION_CONSISTENCY 依赖密级校验(§3.4.3) | DA19-R4.3 | Phase 2 |
| **P1** | broadcast_security_incident 反向追溯(§2.4.3) | DA18-R4.4 | Phase 2 |
| **P1** | hub:// 密级校验(§3.4.5) | DA19-R4.5 | Phase 2 |
| **P1** | clone_registry + notify_cloned(§1.4.4) | DA17-R4.4 | Phase 2 |
| **P2** | git 历史清理 policy(tombstone 策略)(§1.4.3) | DA17-R4.3 | Phase 3 |
| **P2** | events 权威源明确(node_event)(§4.4.5) | DA20-R4.5 | Phase 3 |
| **P2** | prompt injection 防护定位(§2.4.4) | DA18-R4.5 | Phase 3 |

---

## 8. 主 PRD 修正建议(回写章节)

| PRD 章节 | 修正内容 | 关联缺陷 |
|---|---|---|
| §1.4 范围边界 | "不解析内容"澄清为"不解析业务语义";安全扫描属管理约束(扩 R_NO_PATH_TRAVERSAL 先例) | 全部(张力解法) |
| §3.2 权限矩阵 | RoleInstance 增 clearance/allowed_classifications | DA19-R4.2 |
| §5.1 ArtifactRef | 增 content_integrity_hash/provenance/classification | DA18-R4.1/4.3、DA19-R4.1 |
| §FR1.2 分支保护 | 增 history_policy/secret_cleanup_strategy(tombstone) | DA17-R4.3 |
| §FR2.3 PipelineState | 明确 node_event 为权威源,events 为缓存 | DA20-R4.5 |
| §FR6.2 审核逻辑 | 增 R_SECRET_SCAN/R_URL_SAFETY/R_MALWARE_SCAN/R_CLASSIFICATION_CONSISTENCY | DA17-R4.1、DA18-R4.2、DA19-R4.3 |
| fr1-fr6 §3.3 manifest | 增 classification 字段 | DA19-R4.1 |
| fr1-fr6 §4 规则引擎 | 增安全规则族 R_SECURITY_* + op(secret_scan/url_safety_scan/malware_scan/classification_ge_self) | DA17/18/19 |
| fr1-fr6 §8 CI | CI 新增 CI-12 secret_scan/CI-13 url_safety/CI-14 classification | DA17-R4.1、DA18-R4.2 |
| fr4 §2 错误码 | 增 SECURITY_*/CLASSIFICATION_* 域 | DA17-R4.2、DA19-R4.4 |
| fr4 §8.1 audit_log | 增 prev_hash/entry_hash/content_integrity_hash/signer + clone_registry 表 | DA20-R4.1/4.3、DA17-R4.4 |
| fr4 §8.3 append-only | 增 hash 链 + WORM 锚定校验 | DA20-R4.1 |
| fr4 §8.4 保留策略 | 改可配置 per compliance regime | DA20-R4.4 |
| fr4 §9 MCP 工具 | 新增 handle_security_incident/broadcast_security_incident/export_compliance_report;get_dependencies 增 classification_filter | DA17-R4.2、DA18-R4.4、DA20-R4.2、DA19-R4.4 |
| NFR9 审计 | 升级:hash 链 + WORM 锚定 + 可配置保留 | DA20-R4.1/4.4 |
| 附录 D(新增 D9) | 第四轮压力测试修正记录 | 全部 |

---

**文档结束。** 本轮 4 场景 20 缺陷(2 Critical / 10 High / 8 Medium),归因 4 大根因(安全扫描定位空白/完整性 provenance 缺失/权限无密级/审计防篡改不完整),提出 8 项 P0 修正。核心张力通过"安全约束≠内容解析"分层解决,以 R_NO_PATH_TRAVERSAL 为先例扩展 R_SECURITY_* 规则族,不破坏管理方中立性。
