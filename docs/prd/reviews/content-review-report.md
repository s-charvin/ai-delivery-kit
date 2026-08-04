# PRD 内容完整性审核总报告

> **文档性质**:对《coordination-platform-prd.md》v3.0 的"内容/边界/细节/规则"四维度完整性审核汇总
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:待修复
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)
> **审核方法**:4 个并行 agent 分别审核 4 个部分,每个 agent 按"内容缺失/边界模糊/细节不足/规则冲突"四维度检查
> **分项报告**:
> - [review-part1-overview-roles-repo.md](./review-part1-overview-roles-repo.md)(§1-§3 + §FR1)
> - [review-part2-orchestration-crew.md](./review-part2-orchestration-crew.md)(§FR2 + §FR3)
> - [review-part3-mcp-skills-review.md](./review-part3-mcp-skills-review.md)(§FR4 + §FR5 + §FR6)
> - [review-part4-monitoring-data-nfr-appendix.md](./review-part4-monitoring-data-nfr-appendix.md)(§FR7 + §5-§8 + 附录)

---

## 1. 审核汇总

| Part | 范围 | 内容缺失 | 边界模糊 | 细节不足 | 规则冲突 | 合计 | P0 |
|---|---|---|---|---|---|---|---|
| Part 1 | §1-§3 + §FR1 | 16 | 10 | 14 | 16 | 56 | 13 |
| Part 2 | §FR2 + §FR3 | 7 | 6 | 9 | 7 | 29 | 8 |
| Part 3 | §FR4 + §FR5 + §FR6 | 7 | 5 | 7 | 6 | 25 | 10 |
| Part 4 | §FR7 + §5-§8 + 附录 | 19 | 9 | 14 | 14 | 56 | 22 |
| **合计** | **全文** | **49** | **30** | **44** | **43** | **166** | **53** |

---

## 2. 十大系统性问题(P0 级,按影响排序)

### S1. 状态机态数三重不一致(P0,Part 2+4)

| 文档位置 | 态数 | 缺失 |
|---|---|---|
| 主 PRD §FR2.1 | 10 态 | 缺 skipped |
| 附录 D11 | 11 态(新增 skipped) | 已声明但未回写正文 |
| fr2 深化 §2.1 | 7 态 | 缺 draft/deprecated/sunset/skipped |
| Postgres schema CHECK | 7 态 | 同上 |

**影响**:实现时无法判断以哪个为准,T1-T18 转移表未覆盖 draft/deprecated/sunset。

### S2. Postgres schema 与 §5 TypedDict 全面脱节(P0,Part 4)

- `artifact_ref` 表主键不支持多版本(与 `{version → ArtifactRef}` 矛盾)
- 缺 12+ 关键字段:artifact_kind/classification/provenance/content_integrity_hash/current_owner/addenda
- `audit_log` 表缺 hash 链字段(prev_hash/entry_hash)
- `pipeline.status` CHECK 缺 cancelled/merged
- `node.status` CHECK 仅 7 态(缺 draft/deprecated/sunset/skipped)

**影响**:D7-D11 的 P0 修正大多在 TypedDict 层回写但未传导到 schema 层。

### S3. D11 修正未回写正文(P0,Part 4)

- `current_owner` 字段(D11 P0-R5.9):§5.1 ArtifactRef 未更新
- `addenda` 字段(D11 P0-R5.11):§5.1 未更新(注:§FR2.5.1 已回写但 §5.1 未同步)
- `skipped` 态(D11 P0-R5.17):§2 术语/§FR2.1 未更新

### S4. 深化文档 manifest schema 与主 PRD 9 处冲突(P0,Part 1)

| 冲突点 | 主 PRD | 深化 fr1-fr6 |
|---|---|---|
| manifest 格式 | yaml | json |
| node_id 模式 | `{pipeline_id}.{local_id}` | `^n[0-9]+$` |
| node_type enum | 10+ 种 | 9 种(缺 derived_artifact) |
| role enum | 7 种(含 generator) | 6 种 |
| source.path | 含 features/{pipeline_id}/{qualifier}/ | 不含 |
| deps 字段 | 含 hub_ref/version_constraint/format_slot/strictness/presence/coupling | 缺这 6 个 |
| 必填字段 | 含 classification/artifact_kind/artifact_qualifier | 缺 |

### S5. 安全扫描规则族全空洞(P0,Part 3)

R_SECRET_SCAN/R_URL_SAFETY/R_MALWARE_SCAN/R_EXTERNAL_REF_OWNERSHIP/R_COMMIT_STABILITY/R_COMPLETENESS_CONTRACT 六个规则族在三份深化文档与主 PRD 中均无规则定义、无对应 op、无扫描内容。

**影响**:AC6.8/AC6.9 无法验收,安全门禁形同虚设。

### S6. skill.yaml 约束模型分裂(P0,Part 3)

主 PRD §FR5.2 与深化 fr3-fr5 用 `artifact_constraints`,深化 fr1-fr6 重构为 `review_rules`,两套并存且 6 个 skill.yaml 未改写。

### S7. submit_artifact schema 三处不一致(P0,Part 3+4)

| 位置 | 必填字段数 | 缺失字段 |
|---|---|---|
| §6.1 | 8 | — |
| §FR4.1 | 7 | classification |
| 深化 §9.1 | 6 | classification/artifact_kind/qualifier/external_repo/external_commit |

### S8. MCP 工具 schema 覆盖率严重不足(P0,Part 4)

FR4 声明 34 个工具,深化 §9 仅覆盖 14 个,主 PRD §6 仅完整覆盖 5 个,约 20 个工具完全无 inputSchema/outputSchema。

### S9. 硬预算数值矛盾(P0,Part 2)

| 层级 | 主 PRD §FR3.5 | fr3 深化 §2.3 |
|---|---|---|
| Task 级 | 20k token → 硬中断 | 10k token → warning |
| Agent 级 | $10/日 | $5/日 |
| 管线级 | $100 | $50 |

### S10. 节点类型清单未回写 D11 修正(P0,Part 1)

D11 明确将 client_logic/server_delivery/research_spike 列为 P0,但 §2.1 清单未列入,开发者无法判断本期是否实现。

---

## 3. 五大根因

| 根因 | 影响 | 涉及 P0 |
|---|---|---|
| **深化文档未随主 PRD 同步更新** | 主 PRD 已 v3.0,深化文档仍停留在 v2.0 设计 | S4/S5/S6/S7/S9 |
| **D11 修正只在附录记录,未回写正文** | 附录和正文不一致 | S3/S10 |
| **Postgres schema 未跟随 TypedDict 演进** | 数据层和模型层脱节 | S2 |
| **状态机演进(7→10→11)未全局同步** | 多处态数不一致 | S1 |
| **MCP 工具声明了但未定义 schema** | 20+ 工具无法实现 | S8 |

---

## 4. 修复计划

### Phase A:同步深化文档(P0,最高优先级)
1. fr1-fr6 manifest schema 对齐主 PRD(S4)
2. fr1-fr6 审核规则引擎补齐安全扫描 op(S5)
3. fr1-fr6 与 fr3-fr5 skill.yaml 统一为 review_rules 模型(S6)
4. fr4 MCP 工具 schema 补齐 20+ 工具(S8)
5. fr2 状态机从 7 态更新到 11 态(S1)
6. fr3 硬预算数值对齐主 PRD(S9)

### Phase B:回写正文(P0)
1. §2 术语:10 态 → 11 态(加 skipped)(S1)
2. §5.1 ArtifactRef:加 current_owner/addenda(S3)
3. §2.1 节点类型清单:加 client_logic/server_delivery/research_spike(S10)
4. §FR2.1 状态机:10 态 → 11 态(S1)

### Phase C:同步 Postgres schema(P0)
1. artifact_ref 表支持多版本(S2)
2. 补 12+ 字段(S2)
3. audit_log 表加 hash 链字段(S2)
4. pipeline/node status CHECK 对齐 11 态 + 5 态(S2)

### Phase D:统一 MCP 工具 schema(P0)
1. submit_artifact 三处统一(S7)
2. 20+ 工具补 inputSchema/outputSchema(S8)

---

## 5. 按优先级排序的 P0 清单(53 项)

详见各分项报告的 P0 清单:
- Part 1:13 项 P0(详见 [review-part1-overview-roles-repo.md](./review-part1-overview-roles-repo.md))
- Part 2:8 项 P0(详见 [review-part2-orchestration-crew.md](./review-part2-orchestration-crew.md))
- Part 3:10 项 P0(详见 [review-part3-mcp-skills-review.md](./review-part3-mcp-skills-review.md))
- Part 4:22 项 P0(详见 [review-part4-monitoring-data-nfr-appendix.md](./review-part4-monitoring-data-nfr-appendix.md))

---

## 6. 审核覆盖确认

| PRD 章节 | 审核状态 | 分项报告 |
|---|---|---|
| §1 产品概述 | ✅ 已审 | Part 1 |
| §2 术语 + 节点类型 | ✅ 已审 | Part 1 |
| §3 角色与权限 | ✅ 已审 | Part 1 |
| §FR1 产物仓库 | ✅ 已审 | Part 1 |
| §FR2 编排引擎 | ✅ 已审 | Part 2 |
| §FR3 CrewAI | ✅ 已审 | Part 2 |
| §FR4 MCP 接口 | ✅ 已审 | Part 3+4 |
| §FR5 约束技能 | ✅ 已审 | Part 3 |
| §FR6 审核机制 | ✅ 已审 | Part 3 |
| §FR7 监控 | ✅ 已审 | Part 4 |
| §FR8 Dashboard | ✅ 已审 | Part 4 |
| §5 数据模型 | ✅ 已审 | Part 4 |
| §6 接口规范 | ✅ 已审 | Part 4 |
| §7 NFR | ✅ 已审 | Part 4 |
| §8 验收标准 | ✅ 已审 | Part 4 |
| §9 实施阶段 | ✅ 已审 | Part 4 |
| 附录 D7-D11 | ✅ 已审 | Part 4 |

**全文已全覆盖审核。**
