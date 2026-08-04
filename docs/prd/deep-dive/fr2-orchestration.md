# FR2 管理编排引擎(LangGraph)深化设计

> **文档性质**:对《coordination-platform-prd.md》FR2 章节的深化补充
> **版本**:v3.0 | **日期**:2026-08-04 | **状态**:待评审
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)(v3.0,权威源)
> **调研依据**:[ai-multi-agent-dev-dashboard-research.md](../../research/ai-multi-agent-dev-dashboard-research.md) 第17章 LangGraph 设计

## Changelog

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v2.0 | 2026-07 | 初版:9 个薄弱点深化(7 态状态机 + T1-T18 转移表) |
| v2.1 | 2026-08-04 | 微调:幂等键 / 退避参数 |
| **v3.0** | **2026-08-04** | **S1 修复:状态机 7 态 → 11 态(对齐主 PRD v3.0 §FR2.1 + 附录 D11);新增 D1-D12 + S1-S2 转移条目;非法转移防护表覆盖 11 态;§7 补 ParticipationProfile + optional 依赖 DAG 校验;新增 §13 管线级生命周期 5 态;新增 §14 addendum 级联机制** |

> **本版同步依据**:主 PRD v3.0 §FR2.1(11 态定义)、§FR2.2(DAG 规则 + DepDeclaration + ParticipationProfile)、§FR2.5.1(addendum 机制)、§FR2.7(管线级生命周期)、附录 D11(第五轮 P0-R5.17 skipped 态扩展)。

---

## 0. 文档范围与补全说明

本文针对 PRD v3.0 FR2 章节的以下薄弱点进行深化(v3.0 已合并第五轮 D10/D11 修正):

| # | 薄弱点 | 深化章节 |
|---|---|---|
| 1 | 状态机边界条件(11 态/多变更/非法跳转/幂等) | §2 |
| 2 | 并发提交处理(同节点/异节点/LangGraph 并发模型) | §3 |
| 3 | PR 冲突处理(多 PR 合并/产物路径冲突) | §4 |
| 4 | 错误恢复与重试(节点失败/MCP/git) | §5 |
| 5 | checkpointer 配置(Postgres schema/频率/恢复点) | §6 |
| 6 | 管线加载与校验(DAG 无环/引用完整/ParticipationProfile/optional 依赖/热重载) | §7 |
| 7 | 控制节点完整边界条件(gate/approval/fork/switch/notify) | §8 |
| 8 | LangGraph 配置细节(编译/interrupt/recursion/fan-out) | §9 |
| 9 | 事件溯源(events 累积/回放/审计/state 重建) | §10 |
| 10 | 管线级生命周期 5 态(active/paused/cancelled/merged/completed) | §13 |
| 11 | addendum 级联机制(must/should/info + 超时) | §14 |

**最少 4 张 Mermaid 设计图**:`图 2-1` 完整状态机含 guard、`图 3-1` 并发提交时序、`图 5-1` 错误恢复流程、`图 6-1` checkpoint 恢复;另含 `图 7-1` 管线加载校验流程、`图 10-1` 事件回放流程。

**技术栈约束**:LangGraph ≥ 0.2 + CrewAI ≥ 0.4 + Langfuse ≥ 3.0 + Postgres ≥ 15 + Python 3.11+。

---

## 1. 编排引擎定位回顾

LangGraph StateGraph 是管理/编排层的"心脏",承担 4 项职责:

| 职责 | 实现机制 |
|---|---|
| 节点状态机(**11 态**) | `node_states` dict + 状态转移 guard(对齐主 PRD v3.0 §FR2.1) |
| 依赖 DAG | `deps` 推导边 + `cascade_node` / `invalidate_node` + ParticipationProfile materialize |
| 条件推进 | `add_conditional_edges` 声明式路由 |
| 变更级联 | done→下游 ready / changed→下游 blocked(递归);addendum→下游 must/should/info 弱级联(§14) |

**本深化的 5 条设计原则:**

| 原则 | 含义 | 落地 |
|---|---|---|
| **状态严格性** | 状态转移必须经 guard 校验,非法跳转拒绝 | §2.2 非法转移表 |
| **并发安全性** | 同节点并发变更串行化,异节点并行 fan-out | §3 锁机制 |
| **可恢复性** | 任意节点失败 / 进程崩溃可从最后 checkpoint 恢复 | §5 + §6 |
| **可观测性** | 每次状态变更产 event,事件流可回放重建 state | §10 |
| **幂等性** | 同一 MCP 调用重放结果一致,无副作用叠加 | §2.4 + §3.3 |

---

## 2. 状态机深化设计

### 2.1 完整状态转移表(所有合法转移)

PRD v3.0 §FR2.1 定义 11 态状态机,本节穷举所有合法转移及其 guard / 副作用。状态枚举(11 态,对齐主 PRD §FR2.1 + 附录 D11 P0-R5.17):

| 状态 | 含义 | 类别 |
|---|---|---|
| `blocked` | 依赖未满足 | 初始/中间态 |
| `ready` | 依赖满足,待产出 | 中间态 |
| `pending_review` | PR 已提交,待审核 | 中间态 |
| `in_progress` | 开发中(进度更新)/门禁失败打回 | 中间态(产物节点) |
| `review` | 审批门等待审批 | 中间态(approval 控制节点) |
| `done` | 产物已合并生效 | 终态(可被 changed/deprecated 打破) |
| `changed` | 已 done 产物被重新提交(变更) | 中间态 |
| `draft` | 草案(未完成但可共享) | 中间态 |
| `deprecated` | 已废弃(仍存在但不推荐新依赖) | 中间态(向 sunset 演进) |
| `sunset` | 已下线(不可被任何新管线依赖) | 终态 |
| `skipped` | 可选节点未交付且管线将完成 | 终态(可人工转回 ready) |

> **addendum 不引入新状态**:addendum 是 done 态上的"附加层",节点状态保持 done。详见 §14。

#### 2.1.1 基础转移表(T1-T18,7 态原版)

| # | 源状态 | 目标状态 | 触发事件 | 前置 Guard | 副作用(Side Effect) | 备注 |
|---|---|---|---|---|---|---|
| T1 | `(初始)` | `blocked` | `bootstrap_node` | 节点有 required deps 且至少一个未满足(strictness=strict 时需 done;accepts_draft 时需 done 或 draft) | 写 `node_states[nid]=blocked`,发 `BLOCKED` event | 默认初始态 |
| T2 | `(初始)` | `ready` | `bootstrap_node` | 节点无 required deps(根节点)或所有 required deps 已满足 | 写 `node_states[nid]=ready`,发 `READY` event,触发 CrewAI 分配 | AC2.1 |
| T3 | `blocked` | `ready` | `cascade_node` required deps 全满足 | `all(satisfied(dep) for dep in deps(nid) if dep.presence==required)`,其中 `satisfied(strict)=done`、`satisfied(accepts_draft)∈{done,draft}` | 写 ready,发 `READY` event,CrewAI 分配 | 级联解锁;optional dep 不参与判定(附录 E.2) |
| T4 | `ready` | `in_progress` | `update_progress(status=in_progress)` | 调用方为 `role_assignments[nid]` 对应 agent 或 admin;节点类型为产物节点 | 发 `IN_PROGRESS` event,Langfuse span 开始 | 进度更新 |
| T5 | `ready` | `pending_review` | `submit_artifact` 开 PR | `skill` 元数据 + 依赖完整性预校验通过;`pending_prs[nid]` 为空 | 写 `pending_prs[nid]=pr_id`,发 `PENDING_REVIEW` event | AC2.7 |
| T6 | `in_progress` | `pending_review` | `submit_artifact` 开 PR | 同 T5;且当前 `role_assignments[nid]` 持有者调用 | 同 T5 | 修复后提 PR |
| T7 | `pending_review` | `done` | `approve_pr` 合并 | PR 已 squash merge;构造 `ArtifactRef` | 写 `artifact_refs[nid]`,清 `pending_prs[nid]`,发 `DONE` event,触发 `cascade_node` | 合并即生效 |
| T8 | `pending_review` | `ready` | `reject_pr` | PR 已关闭未合并 | 清 `pending_prs[nid]`,发 `REJECT` event,通知提交方 | 驳回 |
| T9 | `pending_review` | `pending_review` | 重提新 PR(同一节点) | 旧 PR 已 close;`pending_prs[nid]` 被新 pr_id 覆盖 | 替换 `pending_prs[nid]`,发 `RE_SUBMIT` event | 见 §4.1 |
| T10 | `done` | `changed` | `submit_artifact` 重提已 done 节点的 PR(modification_type=changed) | `artifact_refs[nid]` 已存在;新 commit ≠ 旧 commit;`change_class` 已声明 | 发 `CHANGED` event,触发 `invalidate_node` 按 coupling×change_class 分级失效下游 | AC2.4 |
| T11 | `done` | `done` | 同 commit 重提 | 新 commit == 旧 commit | 幂等返回,不发 `CHANGED`,不级联 | 幂等,见 §2.4 |
| T12 | `changed` | `pending_review` | 重提 PR | 同 T5 | 写 `pending_prs[nid]`,发 `PENDING_REVIEW` event | 变更后重审 |
| T13 | `changed` | `done` | 直接 approve(变更已合并) | PR 合并 commit 已是最新 | 写 `artifact_refs[nid]`(新 commit),发 `DONE` event,触发 `cascade_node` 解锁下游 | 变更生效 |
| T14 | `review` | `done` | `approve`(approval 控制节点) | `pending_approvals[nid]` 已 approve(多审批人时全部 approve) | 清 `pending_approvals[nid]`,发 `DONE` event,cascade | 控制节点 |
| T15 | `review` | `changed` | `reject`(approval 控制节点) | 上游最近产物节点存在(沿 deps 反向遍历跳过 control 节点;若无,标记 `NO_ARTIFACT_UPSTREAM`) | 上游产物节点置 `changed`(递归),发 `REJECT` event | AC2.6 |
| T16 | `blocked`/`ready`/`in_progress`/`pending_review`/`draft`/`done`(strict 下游)/`review` | `blocked` | 下游 cascade 失效(上游 changed breaking + coupling=hard 递归) | 本节点是某 changed 节点的下游可达节点,且 dep.coupling=hard;按 `breaking+hard→hard_invalidate` 分级(见 §2.6 级联矩阵) | 清 `artifact_refs[nid]`/`draft_refs[nid]`,清 `pending_prs[nid]`,发 `INVALIDATED` event;pending_review 时 PR 自动 reject | 递归失效;visited set 防环 |
| T17 | `done`(控制节点) | `done` | 控制节点透传(fork/notify) | 控制节点上游全 done | 发 `DONE` event,cascade | 透传 |
| T18 | `in_progress` | `ready` | `gate` 失败打回 | gate policy 校验失败 | 发 `GATE_FAIL` event,通知提交方修复 | AC2.5 |

#### 2.1.2 draft / 草案转移表(D1-D4)

> 修正来源:主 PRD §FR2.1(行 384)、§FR2.5.1(行 530 草案迭代光谱)。draft 是"未完成但可共享"中间态,不触发 cascade,可作为下游 `strictness=accepts_draft` 的可选依赖。

| # | 源状态 | 目标状态 | 触发事件 | 前置 Guard | 副作用(Side Effect) | 备注 |
|---|---|---|---|---|---|---|
| D1 | `ready` | `draft` | `soft_submit_artifact` | 节点类型为产物节点;调用方为 assignee 或 admin;feat 分支 commit 已存在 | 写 `draft_refs[nid]`,发 `DRAFT_CREATED` event,通知 `draft_subscribers[nid]`;**不触发 cascade** | AC2.8 |
| D2 | `draft` | `draft` | feat 分支 push 新 commit | 新 commit ≠ 旧 commit | 更新 `draft_refs[nid]`,发 `DRAFT_UPDATED` event,通知订阅者 | 草案迭代;AC2.9 |
| D3 | `draft` | `pending_review` | `submit_artifact`(转正式) | 同 T5 guard;`draft_refs[nid]` 存在 | 清 `draft_refs[nid]`,写 `pending_prs[nid]`,发 `PENDING_REVIEW` event | 草案转正式 |
| D4 | `draft` | `ready` | `abandon_draft` | 调用方为 assignee 或 admin | 清 `draft_refs[nid]`,发 `DRAFT_ABANDONED` event,通知订阅者 | 放弃草案 |

> **draft vs in_progress 边界**:draft 是独立状态(非 in_progress 子状态)。`in_progress` 时**不能** soft_submit(否则状态冲突);需先回 ready(T18 gate 失败 / 手动)再 D1 进 draft,或直接 T5/T6 提正式 PR。

#### 2.1.3 deprecated / sunset 转移表(D5-D10)

> 修正来源:主 PRD §FR2.1(行 385-386)、§FR2.2(行 467-470 外部依赖持续监控)、附录 D9 修正项 5(外部依赖监控)。

| # | 源状态 | 目标状态 | 触发事件 | 前置 Guard | 副作用(Side Effect) | 备注 |
|---|---|---|---|---|---|---|
| D5 | `done` | `deprecated` | 管理方标记废弃 / 版本 superseded | 调用方为 admin;`artifact_refs[nid]` 存在 | 发 `DEPRECATED` event,通知 CrossPipelineReferenceRegistry 中所有引用方;`deprecated_at` 时间戳写入 | 主动废弃 |
| D6 | `deprecated` | `sunset` | deprecated 后 N 天(NFR 可配,默认 30) | `now - deprecated_at >= N 天` | 发 `SUNSET` event,强制所有下游 → blocked(递归 hard_invalidate);从 `active_version` 移除 | 终态下线 |
| D7 | `done` | `deprecated` | ExternalHealthMonitor 检测到外部 URL 失效 | `external_health[nid].status = unreachable`;产物 manifest 声明 `external_resources` | 同 D5;附 `reason=external_url_invalid` | AC2.10 |
| D8 | `done` | `deprecated` | 第三方 API 变更(破坏性) | ExternalHealthMonitor 检测到 API schema 不兼容 | 同 D5;附 `reason=third_party_api_breaking` | 外部依赖失效 |
| D9 | `done` | `deprecated` | CVE 漏洞披露 | 安全扫描规则族 R_MALWARE_SCAN / 外部 CVE feed 命中 | 同 D5;附 `reason=cve_vulnerability`;触发 `handle_security_incident` | 安全合规 |
| D10 | (跨管线) | (通知) | 跨管线 deprecated 通知 | 上游跨管线 hub:// 引用节点 deprecated | 查 CrossPipelineReferenceRegistry,向所有引用方发 `DEPRECATED_NOTIFY` event;引用方可选择升级或保持(有限期) | 跨管线级联,不改本管线状态 |

> **deprecated 期间下游行为**:deprecated 节点的下游**保持原状态**(不立即 blocked),但收到 `DEPRECATED_NOTIFY`;下游 owner 需在 sunset 前完成升级。sunset 时强制下游 blocked(D6 副作用)。

#### 2.1.4 skipped 转移表(S1-S2)

> 修正来源:主 PRD §FR2.1(行 387)、附录 D11 P0-R5.17(skipped 态扩展)。skipped 用于 optional 节点未交付但管线 core 节点已全 done 的场景,不阻塞 completed。

| # | 源状态 | 目标状态 | 触发事件 | 前置 Guard | 副作用(Side Effect) | 备注 |
|---|---|---|---|---|---|---|
| S1 | `blocked`/`ready`/`in_progress` | `skipped` | `skip_finalize_node`(core 节点全 done 时扫 optional 未 done)/ 显式 `skip_node` | 节点 `presence=optional` 或在 `completion.optional_node_types` 中;管线 `core_nodes_done` 谓词即将满足 | 写 `node_states[nid]=skipped`,发 `SKIPPED` event,记 skip 原因;**不阻塞 completed** | AC2.7 修正 |
| S2 | `skipped` | `ready` | 人工反悔 `reactivate_node` / 后到依赖触发 `OPTIONAL_DEP_ARRIVED` | 调用方为 admin;管线未进入 completed/cancelled 终态 | 写 `node_states[nid]=ready`,发 `REACTIVATED` event,CrewAI 重新分配 | 可逆终态 |
| S3 | `skipped` | `skipped` | 后到依赖到达但 owner 选择继续 skip | `OPTIONAL_DEP_ARRIVED` 后 owner 显式 `keep_skipped` | 发 `SKIP_MAINTAINED` event,不改变状态 | 幂等 |

> **skipped 与 completed 的关系**(对齐 AC2.7 修正):管线 `core 节点全 done 且 optional 节点全 done 或 skipped` 时进入 `completed`。optional 节点失败只告警不挡完成(自动 skipped)。

#### 2.1.5 转移表汇总说明

**状态类别边界:**
- `review` 状态仅 `approval` 控制节点进入;产物节点不进 `review`,产物节点走 `pending_review`。
- `in_progress` 仅产物节点会进入(由 `update_progress`);控制节点不进 `in_progress`。
- `draft` 仅产物节点可进入(soft_submit);控制节点不进 draft。
- `deprecated`/`sunset` 仅 `done` 态可进入(已生效产物才可废弃)。
- `skipped` 仅 optional 节点可进入(required 节点不可 skip)。

**幂等性要点:**
- T11 是幂等转移,不发 `CHANGED` 避免 cascade 风暴。
- D2 草案 push 同 commit 重放幂等(不发 `DRAFT_UPDATED`)。
- S3 保持 skip 幂等。

**递归防护:**
- T16 递归失效需用 visited set 防环(虽然 DAG 无环,但跨管线引用需防护)。
- D6 sunset 触发的下游 blocked 复用 T16 递归逻辑。

### 2.2 非法转移防护表

以下转移被 Guard 拒绝,返回 `INVALID_TRANSITION` 错误(对齐 FR4 错误码体系)。本表覆盖 11 态之间的所有非法转移组合。

#### 2.2.1 基础 7 态非法转移(原版保留)

| 源状态 | 目标状态 | 拒绝原因 | 错误码 |
|---|---|---|---|
| `blocked` | `pending_review` | 依赖未满足不能提 PR | `INVALID_TRANSITION` + `DEPS_NOT_DONE` |
| `blocked` | `done` | 跳过产出/审核 | `INVALID_TRANSITION` |
| `blocked` | `changed` | 未 done 不能 changed | `INVALID_TRANSITION` + `NOT_DONE` |
| `ready` | `done` | 跳过 pending_review | `INVALID_TRANSITION` |
| `ready` | `review` | review 仅 approval 控制节点可进 | `INVALID_TRANSITION` + `NOT_APPROVAL_NODE` |
| `ready` | `blocked`(非 cascade 路径) | 仅 T16 cascade 可回 blocked | `INVALID_TRANSITION` |
| `pending_review` | `in_progress` | 审核中不可改进度 | `INVALID_TRANSITION` + `REVIEW_IN_PROGRESS` |
| `pending_review` | `ready`(非 reject 路径) | 仅 `reject_pr` 可回 ready | `INVALID_TRANSITION` |
| `pending_review` | `review` | 产物节点不进 review | `INVALID_TRANSITION` |
| `pending_review` | `done`(无 PR 合并) | 审核必须经 PR 合并 | `INVALID_TRANSITION` + `NO_MERGE_COMMIT` |
| `pending_review` | `changed` | 审核中不能直接 changed,需先 done 再重提 | `INVALID_TRANSITION` |
| `done` | `ready` | 已生效不能直接回 ready,需走 changed | `INVALID_TRANSITION` + `USE_CHANGED_PATH` |
| `done` | `blocked` | 已生效不能直接 blocked,需先 changed 或 deprecated | `INVALID_TRANSITION` |
| `done` | `in_progress` | 已生效不能回开发,需走 changed 重审 | `INVALID_TRANSITION` |
| `done` | `pending_review`(非重提路径) | 需走 T10 changed 再 T12 pending_review | `INVALID_TRANSITION` |
| `done` | `review` | done 不回 review,approval 驳回走 T15 上游 changed | `INVALID_TRANSITION` |
| `changed` | `ready` | changed 必须经 pending_review 重审 | `INVALID_TRANSITION` |
| `changed` | `done`(无 PR 合并) | 变更必须经审核 | `INVALID_TRANSITION` + `NO_MERGE_COMMIT` |
| `changed` | `blocked` | changed 不直接 blocked,需经 T12→T7 重审或上游再 cascade | `INVALID_TRANSITION` |
| `review` | `ready` | approval 节点驳回走 changed,不回 ready | `INVALID_TRANSITION` |
| `review` | `pending_review` | review 与 pending_review 不互通 | `INVALID_TRANSITION` |
| `review` | `in_progress` | approval 节点不进 in_progress | `INVALID_TRANSITION` |
| `review` | `blocked` | approval 不直接 blocked,驳回走 T15 | `INVALID_TRANSITION` |
| 任意 | `in_progress`(非产物节点) | 控制节点不进 in_progress | `INVALID_TRANSITION` + `CONTROL_NODE_NO_PROGRESS` |
| 任意 | `review`(非 approval 控制节点) | 仅 approval 控制节点可进 review | `INVALID_TRANSITION` + `NOT_APPROVAL_NODE` |

#### 2.2.2 新增 4 态(draft/deprecated/sunset/skipped)非法转移

| 源状态 | 目标状态 | 拒绝原因 | 错误码 |
|---|---|---|---|
| `blocked`/`pending_review`/`review`/`changed`/`deprecated`/`sunset`/`skipped` | `draft` | 仅 `ready` 可经 D1 进 draft | `INVALID_TRANSITION` + `NOT_READY` |
| `in_progress` | `draft` | in_progress 不能直接 soft_submit,需先回 ready | `INVALID_TRANSITION` + `IN_PROGRESS_NO_DRAFT` |
| `draft` | `done` | draft 不能直接 done,需 D3 转正式 PR 再 T7 | `INVALID_TRANSITION` |
| `draft` | `in_progress` | draft 不回 in_progress,需先 D4 abandon 回 ready | `INVALID_TRANSITION` |
| `draft` | `review` | draft 不进 review(非 approval 节点) | `INVALID_TRANSITION` |
| `draft` | `changed` | draft 未 done 不能 changed,需先 D3 转正式 | `INVALID_TRANSITION` |
| `draft` | `deprecated` | draft 未生效不能 deprecated,需先 D3→T7 done | `INVALID_TRANSITION` |
| `draft` | `skipped` | draft 已有草案产出,不能 skip(需先 D4 abandon) | `INVALID_TRANSITION` + `DRAFT_EXISTS` |
| `draft` | `sunset` | draft 未生效不能 sunset | `INVALID_TRANSITION` |
| 非 `done` | `deprecated` | 仅 done 可 deprecated(已生效才可废弃) | `INVALID_TRANSITION` + `NOT_DONE` |
| `deprecated` | `done` | deprecated 不可恢复 done(废弃不可逆,需重做走新版本) | `INVALID_TRANSITION` + `DEPRECATED_IRREVERSIBLE` |
| `deprecated` | `ready` | deprecated 不可回 ready(需新版本节点) | `INVALID_TRANSITION` |
| `deprecated` | `pending_review` | deprecated 不可提 PR(需新版本节点) | `INVALID_TRANSITION` |
| `deprecated` | `changed` | deprecated 不可 changed(需新版本节点) | `INVALID_TRANSITION` |
| `deprecated` | `draft` | deprecated 不可回 draft | `INVALID_TRANSITION` |
| `deprecated` | `in_progress` | deprecated 不可回开发 | `INVALID_TRANSITION` |
| `deprecated` | `review` | deprecated 不可回审批 | `INVALID_TRANSITION` |
| `deprecated` | `skipped` | deprecated 不可转 skipped(语义不同) | `INVALID_TRANSITION` |
| `sunset` | (任意非终态) | sunset 是终态,不可转出 | `INVALID_TRANSITION` + `SUNSET_TERMINAL` |
| `sunset` | `sunset` | sunset 自环无意义(非幂等场景) | `INVALID_TRANSITION` |
| `done` | `skipped` | done 节点不可 skip(已交付) | `INVALID_TRANSITION` + `DONE_NOT_SKIPPABLE` |
| `changed` | `skipped` | changed 节点不可 skip(变更需重审) | `INVALID_TRANSITION` |
| `deprecated`/`sunset` | `skipped` | 废弃/下线节点不可 skip | `INVALID_TRANSITION` |
| `skipped` | `done` | skipped 不能直接 done(需 S2 回 ready 再走完整流程) | `INVALID_TRANSITION` |
| `skipped` | `pending_review` | skipped 不能直接提 PR(需 S2 回 ready) | `INVALID_TRANSITION` |
| `skipped` | `in_progress` | skipped 不能直接开发(需 S2 回 ready) | `INVALID_TRANSITION` |
| `skipped` | `changed` | skipped 未 done 不能 changed | `INVALID_TRANSITION` |
| `skipped` | `draft` | skipped 不能直接 soft_submit(需 S2 回 ready) | `INVALID_TRANSITION` |
| `skipped` | `deprecated` | skipped 未生效不能 deprecated | `INVALID_TRANSITION` |
| `skipped` | `sunset` | skipped 未生效不能 sunset | `INVALID_TRANSITION` |
| `skipped` | `review` | skipped 不进 review | `INVALID_TRANSITION` |
| `skipped` | `blocked` | skipped 不回 blocked(需 S2 回 ready 或保持终态) | `INVALID_TRANSITION` |
| 任意 | `sunset`(非 deprecated 源) | 仅 deprecated 可经 D6 进 sunset | `INVALID_TRANSITION` + `NOT_DEPRECATED` |
| 任意(required 节点) | `skipped` | required 节点不可 skip(仅 optional 可 skip) | `INVALID_TRANSITION` + `REQUIRED_NOT_SKIPPABLE` |

#### 2.2.3 防护表覆盖度汇总

| 状态 | 合法出转移数 | 合法入转移数 | 非法转移防护条目 |
|---|---|---|---|
| `blocked` | 2(T3 ready / S1 skipped)+T16 自环 | 5(初始 / T16 from 5 态 / D6 触发) | 3 |
| `ready` | 5(T4/T5/D1/T18/S1)+T16 | 4(T2/T3/T8/T15/D4/S2) | 3 |
| `pending_review` | 3(T7/T8/T9)+T16 | 4(T5/T6/T9/T12/D3) | 6 |
| `in_progress` | 2(T6/T18)+T16 | 1(T4) | 1 |
| `review` | 2(T14/T15)+T16 | 1(approval 节点依赖满足) | 4 |
| `done` | 4(T10/T11/D5/D7/D8/D9)+T17 | 2(T7/T13) | 5 |
| `changed` | 2(T12/T13) | 1(T10/T15) | 3 |
| `draft` | 3(D2/D3/D4)+T16 | 1(D1) | 7 |
| `deprecated` | 1(D6) | 4(D5/D7/D8/D9) | 7 |
| `sunset` | 0(终态) | 1(D6) | 2(全拒绝出转移) |
| `skipped` | 2(S2/S3) | 1(S1) | 10 |
| **合计** | — | — | **51 条非法转移防护** |

**Guard 实现要点:**
- Guard 在 LangGraph 节点入口校验,失败时**不修改 state**,直接返回错误 event 并终止该次 invoke。
- Guard 校验用纯函数 `guard_transition(from_state, to_state, event, node_type, participation) -> (ok, reason)`,便于单测覆盖上表全部分支。
- Guard 拒绝的 event 仍入 `events` 流(标记 `rejected=true`),供审计与回放。
- 新增 4 态的 Guard 需额外校验节点类别(产物/控制)和 participation(optional 标记),见 §2.3。

### 2.3 状态机 Guard 设计

每个 LangGraph 节点入口包含三层 Guard(11 态扩展版):

```python
def guard_transition(
    state: PipelineState,
    node_id: str,
    target: NodeStatus,  # 11 态枚举
    event: str,
    caller: str,
) -> TransitionVerdict:
    """三层 Guard:身份 / 前置状态 / 上下文(11 态扩展)"""
    current = state["node_states"].get(node_id)
    node = get_node_def(node_id)
    participation = state["participation"]

    # L1: 身份 Guard — 调用方是否有权操作此节点
    if not authorize(caller, node, event):
        return TransitionVerdict(ok=False, code="FORBIDDEN",
                                  reason=f"{caller} 无权对 {node_id} 执行 {event}")

    # L2: 前置状态 Guard — 源→目标转移是否合法(查 §2.2 表,含 11 态)
    #   额外校验:target=skipped 时节点必须 optional(participation.completion.optional_node_types 或 dep.presence=optional)
    #   target=draft 时节点必须为产物节点
    #   target=review 时节点必须为 approval 控制节点
    if not is_legal_transition_11state(current, target, event, node, participation):
        return TransitionVerdict(ok=False, code="INVALID_TRANSITION",
                                  reason=f"{current}→{target} via {event} 非法")

    # L3: 上下文 Guard — 业务前置条件(依赖全 done / PR 已合并 / commit 不同等)
    #   含 draft/deprecated/sunset/skipped 的上下文校验:
    #   - D1: draft_refs[nid] 不存在(防重复草案)
    #   - D5/D7/D8/D9: artifact_refs[nid] 存在(已生效才能废弃)
    #   - D6: now - deprecated_at >= N 天
    #   - S1: core_nodes_done 谓词即将满足
    #   - S2: 管线未进入 completed/cancelled 终态
    ctx_ok, ctx_reason = check_context_11state(state, node_id, target, event)
    if not ctx_ok:
        return TransitionVerdict(ok=False, code="CONTEXT_FAIL", reason=ctx_reason)

    return TransitionVerdict(ok=True)
```

### 2.4 状态幂等性

**幂等键设计**:每次 MCP 工具调用携带 `idempotency_key`(由 agent 生成 UUID,首次失败重试复用同一 key)。LangGraph 入口节点查 `idempotency_keys` 表:

| 场景 | 幂等键 | 行为 |
|---|---|---|
| 重复 `submit_artifact`(同 node_id + 同 commit) | `submit:{node_id}:{commit}` | 直接返回首次的 `pr_id`,不重复开 PR |
| 重复 `approve_pr`(同 pr_id) | `approve:{pr_id}` | 直接返回首次结果,不重复合并 |
| 重复 `reject_pr`(同 pr_id) | `reject:{pr_id}` | 直接返回,不重复关 PR |
| 重复 `update_progress`(同 node_id + 同 note hash) | `progress:{node_id}:{note_hash}` | 直接返回 ok,不重复写 event |
| 重复 `approve`(同 approval 节点 + 同 approver) | `approval:{node_id}:{approver}` | 直接返回,不重复 cascade |
| 重复 `soft_submit_artifact`(同 node_id + 同 commit) | `soft_submit:{node_id}:{commit}` | 直接返回首次 `draft_ref`,不重复写 `draft_refs`(第五轮新增) |
| 重复 `add_addendum`(同 node_id + 同 content hash) | `addendum:{node_id}:{content_hash}` | 直接返回首次 `addendum_id`,不重复附加(第五轮新增) |
| 重复 `reack_addendum`(同 addendum_id + 同 ack_status) | `reack:{addendum_id}:{ack_status}` | 直接返回,不重复写 `reacks`(第五轮新增) |
| 重复 `transfer_owner`(同 node_id + 同 new_owner) | `transfer:{node_id}:{new_owner}` | 直接返回,不重复写 `current_owner`(第五轮新增) |
| 重复 `skip_node`(同 node_id) | `skip:{node_id}` | 直接返回,不重复发 `SKIPPED` event(第五轮新增) |

**幂等键存储**:`idempotency_keys(key, response_json, expires_at)` 表, TTL 7 天。重复命中时返回首次响应原文,保证客户端语义等价。

**T11 同 commit 重提**:`submit_artifact` 检测到 `artifact_refs[nid].commit == new_commit` 时,不进 `changed`,直接返回 `{"ok": true, "idempotent": true, "state": "done"}`。

**D2 同 commit 重放**:feat 分支 push 检测到 `draft_refs[nid].commit == new_commit` 时,不更新 `draft_refs`,不发 `DRAFT_UPDATED`。

### 2.5 完整状态机含 Guard(图 2-1,11 态)

```mermaid
stateDiagram-v2
    direction TB
    [*] --> blocked : T1 bootstrap(required deps未满足)
    [*] --> ready : T2 bootstrap(根节点/required deps全满足)

    blocked --> ready : T3 cascade\\n[guard: required deps全满足]
    blocked --> skipped : S1 skip_finalize(core全done+optional未做)\\n[guard: 节点optional]

    ready --> in_progress : T4 update_progress\\n[guard: caller=assignee+产物节点]
    ready --> pending_review : T5 submit_artifact\\n[guard: skill校验+required deps满足]
    ready --> draft : D1 soft_submit_artifact\\n[guard: 产物节点+feat分支commit存在]
    ready --> skipped : S1 skip_finalize\\n[guard: 节点optional]
    in_progress --> pending_review : T6 submit_artifact\\n[guard: 同T5]
    in_progress --> ready : T18 gate失败打回\\n[guard: gate policy失败]

    draft --> draft : D2 草案push新commit\\n[guard: 新commit≠旧commit]
    draft --> pending_review : D3 submit_artifact转正式\\n[guard: 同T5]
    draft --> ready : D4 abandon_draft\\n[guard: caller=assignee/admin]

    pending_review --> done : T7 approve_pr合并\\n[guard: PR已merge]
    pending_review --> ready : T8 reject_pr\\n[guard: PR已close未merge]
    pending_review --> pending_review : T9 重提新PR\\n[guard: 旧PR已close]

    done --> changed : T10 重提且commit不同(modification=changed)\\n[guard: 新commit≠旧commit]
    done --> done : T11 同commit重提(幂等)\\n[guard: commit相同]
    done --> done : T17 控制节点透传(fork/notify)\\n[guard: 上游全done]
    done --> deprecated : D5 管理方标记/superseded\\n[guard: caller=admin]
    done --> deprecated : D7 外部URL失效\\n[guard: external_health=unreachable]
    done --> deprecated : D8 第三方API破坏性变更\\n[guard: API schema不兼容]
    done --> deprecated : D9 CVE漏洞披露\\n[guard: R_MALWARE_SCAN/CVE feed命中]

    changed --> pending_review : T12 重提PR\\n[guard: 同T5]
    changed --> done : T13 变更approve合并\\n[guard: PR已merge]

    review --> done : T14 approve(approval节点)\\n[guard: pending_approvals全approve]
    review --> changed : T15 reject(approval节点)\\n[guard: 上游最近产物节点存在]

    deprecated --> sunset : D6 deprecated后N天\\n[guard: now-deprecated_at>=N天]

    skipped --> ready : S2 人工反悔/OPTIONAL_DEP_ARRIVED\\n[guard: caller=admin+管线未终态]
    skipped --> skipped : S3 keep_skipped(幂等)\\n[guard: owner选择继续skip]

    blocked --> blocked : T16 cascade失效(自环)
    ready --> blocked : T16 cascade失效\\n[guard: 上游changed+coupling=hard]
    in_progress --> blocked : T16 cascade失效
    pending_review --> blocked : T16 cascade失效\\n[guard: 清pending_prs+artifact_refs]
    draft --> blocked : T16 cascade失效\\n[guard: 清draft_refs]
    review --> blocked : T16 cascade失效
    done --> blocked : T16 cascade失效(strict下游)\\n[guard: 清artifact_refs]
    deprecated --> blocked : D6 sunset触发(下游hard_invalidate)

    note right of draft
        draft 边界:
        - 仅 ready 可进 draft
        - in_progress 不能直接 soft_submit
        - draft 不触发 cascade
        - draft 可作为 accepts_draft 下游依赖
    end note

    note right of deprecated
        deprecated 边界:
        - 仅 done 可进 deprecated
        - deprecated 不可逆(不能回 done)
        - 下游保持原状态但收到 DEPRECATED_NOTIFY
        - sunset 后下游强制 blocked
    end note

    note right of skipped
        skipped 边界:
        - 仅 optional 节点可 skip
        - required 节点不可 skip
        - skipped 不阻塞 completed
        - skipped 可经 S2 回 ready(可逆)
    end note

    note right of sunset
        sunset 是终态:
        - 不可转出任何状态
        - 不可被任何新管线依赖
    end note
```

### 2.6 级联失效矩阵(coupling × change_class)

> 对齐主 PRD §FR2.2.1(行 515)。T16 递归失效按此矩阵分级处理。

| coupling \ change_class | breaking(破坏性) | compatible(兼容) | docs_only(仅文档) |
|---|---|---|---|
| `hard`(强耦合) | **hard_invalidate**:下游 → blocked(递归传播),清 `artifact_refs`/`draft_refs`,PR 自动 reject | **soft_invalidate**:下游保持 + ack required(7 天) | cascade_skip(通知) |
| `soft`(弱耦合) | **soft_invalidate**:下游保持 + ack required | cascade_skip(通知) | cascade_skip(通知) |
| `informational`(信息性) | cascade_skip(通知,不传播) | cascade_skip(通知) | cascade_skip(通知) |

**递归传播规则**:
- `hard + breaking` → 下游 blocked,继续向下游的下游传播(按其 coupling 判定)
- `soft / informational` → 不递归传播(终止于本节点)
- `visited set` 防环(跨管线 hub:// 引用场景)

**addendum 级联**(独立类型,见 §14):
- 不改节点状态(done 保持 done)
- must 级:下游若 `incompatible_with` 命中则 → changed(委托 invalidate_node);超时 7 天 → changed
- should 级:通知 + warning,不改状态
- info 级:仅记录

---

## 3. 并发处理模型

### 3.1 LangGraph Annotated 累积策略详解

PRD v3.0 §FR2.3 给出了 `PipelineState` 雏形(13 字段),本节明确每个字段的合并策略(11 态扩展版):

| 字段 | 类型 | 合并策略 | 理由 |
|---|---|---|---|
| `pipeline_status` | `PipelineStatus`(5 态) | last-write-wins | 管线级状态(§13) |
| `participation` | `ParticipationProfile` | last-write-wins(bootstrap 时固定) | 角色参与拓扑(§7.3) |
| `node_states` | `dict[str, NodeStatus]`(11 态) | **last-write-wins + 版本号** | 状态是"当前态",覆盖语义;用 `version` 防 lost update |
| `artifact_refs` | `dict[str, dict[str, ArtifactRef]]` | **last-write-wins + 版本号** | 引用是"当前态",覆盖语义;多版本共存 |
| `active_version` | `dict[str, str]` | last-write-wins | 当前生效版本 |
| `draft_refs` | `dict[str, DraftRef]` | last-write-wins | 草案引用(feat 分支 commit) |
| `draft_subscribers` | `dict[str, list[str]]` | **`Annotated[..., list_extend]`** 列表合并 | 订阅者列表,多分支订阅自动合并 |
| `events` | `Sequence[dict]` | **`Annotated[..., operator.add]`** 累积追加 | 事件是"日志",追加语义,多节点并发写自动合并 |
| `pending_approvals` | `dict[str, str]` | last-write-wins | 当前态 |
| `role_assignments` | `dict[str, str]` | last-write-wins | 当前态 |
| `pending_prs` | `dict[str, str]` | last-write-wins | 当前态 |
| `cascade_pending` | `list[dict]` | **`Annotated[..., operator.add]`** 累积 | paused 时挂起的级联事件,resume 时清空 |
| `external_health` | `dict[str, ExternalHealthStatus]` | last-write-wins | 外部依赖健康状态 |
| `node_versions` | `dict[str, int]` | **`Annotated[..., max]`** 取最大 | 单调递增版本号,防并发覆盖 |
| `idempotency_seen` | `set[str]` | **`Annotated[..., operator.or_]`** 并集 | 幂等键集合,多分支合并取并集 |

**TypedDict 定义(对齐主 PRD v3.0 §FR2.3):**

```python
from typing import Annotated
import operator

def list_extend(a: list, b: list) -> list:
    return a + [x for x in b if x not in a]

class PipelineState(TypedDict):
    pipeline_status: PipelineStatus                              # 管线级 5 态(§13)
    participation: ParticipationProfile                          # 角色参与拓扑(§7.3)
    node_states: dict[str, NodeStatus]                           # node_id -> 11 态
    artifact_refs: dict[str, dict[str, ArtifactRef]]             # node_id -> {version -> ArtifactRef}
    active_version: dict[str, str]                               # node_id -> 当前生效版本
    draft_refs: dict[str, DraftRef]                              # node_id -> 草案引用
    draft_subscribers: dict[str, list[str]]                      # node_id -> 订阅下游
    events: Annotated[Sequence[dict], operator.add]              # 事件流(累积追加)
    pending_approvals: dict[str, str]                            # node_id -> approver
    role_assignments: dict[str, str]                             # node_id -> instance_id
    pending_prs: dict[str, str]                                  # node_id -> pr_id
    cascade_pending: Annotated[list[dict], operator.add]         # paused 时挂起的级联事件
    external_health: dict[str, ExternalHealthStatus]             # node_id -> 外部依赖健康
    node_versions: Annotated[dict[str, int], lambda a, b: {**a, **b,
        **{k: max(a.get(k, 0), b.get(k, 0)) for k in b}}]        # per-key max
    idempotency_seen: Annotated[set[str], operator.or_]          # 并集
    last_checkpoint_ts: str                                      # ISO8601
```

**字段初始值**(bootstrap 时):
- `pipeline_status`: `active`
- `participation`: 从 pipeline.yaml 读取
- `node_states`: 按 required deps 判定(根节点 ready,非根 blocked)
- `artifact_refs`/`draft_refs`/`draft_subscribers`/`pending_approvals`/`pending_prs`/`cascade_pending`: 空 dict/list
- `active_version`: 空 dict
- `external_health`: 空 dict(首次 ExternalHealthMonitor 轮询后填充)

**为什么 `events` 用累积追加**:LangGraph 在并行 fan-out 时,多个分支节点可能同时产 event;`operator.add` 让分支汇聚时 event 自动拼接,无需手动协调。这是调研报告第3章强调的"LangGraph 精髓"。

### 3.2 锁机制(Postgres Advisory Lock)

**并发问题**:多个 MCP 调用同时对**同一节点**触发状态变更时,若直接读-改-写 `node_states`,会丢失更新(lost update)。

**方案**:节点级 Postgres advisory lock,Lock Key = hash(node_id)。所有状态变更节点入口先抢锁,串行化同节点操作;异节点操作无锁,真并行。

```python
import hashlib
from psycopg2.extensions import AsIs

def node_lock_key(node_id: str) -> int:
    """node_id → int64 advisory lock key(稳定哈希)"""
    h = hashlib.blake2b(node_id.encode(), digest_size=8).digest()
    return int.from_bytes(h, "big", signed=True) & ((1 << 63) - 1)

async def with_node_lock(node_id: str, fn):
    """节点级串行化包装器。同节点并发调用排队,异节点并行。"""
    key = node_lock_key(node_id)
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock($1)", key)
            return await fn(conn)
```

**锁粒度矩阵:**

| 操作 | 锁对象 | 锁 Key | 持锁时长 |
|---|---|---|---|
| `submit_artifact` | node_id | `hash(node_id)` | 整个开 PR + state 写入 |
| `approve_pr` | node_id + 下游节点集 | `hash(node_id)` + 下游 `hash(downstream_id)` 依次抢 | 合并 + cascade 整体 |
| `reject_pr` | node_id | `hash(node_id)` | 关 PR + state 写入 |
| `cascade_node`(同节点 done) | node_id + 所有下游 | 同上 | cascade 全程 |
| `invalidate_node` | node_id + 所有下游(递归) | 递归抢下游锁(按拓扑序) | 递归失效全程 |
| `approve`(approval 控制节点) | node_id + 上游产物节点 | `hash(node_id)` + `hash(upstream_artifact_node)` | approve + cascade |

**死锁防护:**
- 所有需要多锁的操作,按 node_id 字典序抢锁(规范化加锁顺序)。
- `invalidate_node` 递归失效时按 DAG 拓扑序下游方向加锁,避免反向等待。
- 单锁持有上限 30s,超时自动释放并写 `LOCK_TIMEOUT` event。

### 3.3 同一节点同时收到多个状态变更

**场景示例**:节点 n2 处于 `pending_review`,同时收到 `reject_pr`(来自 reviewer)和 `update_progress`(来自 agent)。

**处理规则(在 `with_node_lock` 串行化下):**

| 时序 | 行为 |
|---|---|
| 先 reject 后 progress | reject 成功:n2→ready;progress 因 guard `pending_review→in_progress 非法` 被拒,返回 `INVALID_TRANSITION` |
| 先 progress 后 reject | progress 因 guard 被拒;reject 成功:n2→ready |
| 同时到达 | advisory lock 串行化,二者其一先执行,另一个按上表 |

**关键**:Guard 是状态变更的"看门人",所有并发竞态由 Guard 兜底——即使锁内顺序不确定,非法转移也会被拒绝,不会破坏状态机不变量。

### 3.4 LangGraph 并发模型

LangGraph 原生支持两种并发:

| 模式 | 实现 | 用途 |
|---|---|---|
| **并行 fan-out** | `Send(node, state)` API + `add_conditional_edges` 返回 list[Send] | 多个 ready 节点同时分配 CrewAI Task |
| **累积分支合并** | `Annotated[..., operator.add]` | 多分支产 event 自动合并 |

**异节点并发提交模型**:

- 多个 agent 同时调 `submit_artifact` 不同 node_id → 不同 advisory lock → 真并行
- 每个 MCP 调用独立 `langgraph.invoke()`,LangGraph checkpointer 用 `thread_id = pipeline_id` 保证 state 跨调用累积
- checkpointer 自身用 Postgres 行锁 + `Annotated` 合并策略,自动协调多 invoke 的 state 写入

### 3.5 并发提交时序(图 3-1)

```mermaid
sequenceDiagram
    participant A1 as Server Agent
    participant A2 as Design Agent
    participant A3 as Client Agent
    participant MCP as MCP Server
    participant LOCK as Postgres<br/>Advisory Lock
    participant LG as LangGraph
    participant CKPT as Checkpointer

    Note over A1,A3: 异节点并发(真并行)
    par Server Agent 提交 n2
        A1->>MCP: submit_artifact(n2, ...)
        MCP->>LOCK: pg_advisory_xact_lock(hash(n2))
        LOCK-->>MCP: acquired
        MCP->>LG: invoke({submit: n2})
        LG->>CKPT: load thread=pipeline_id
        CKPT-->>LG: state(v=5)
        LG->>LG: guard(n2: ready→pending_review) ✓
        LG->>CKPT: save state(v=6)
        LG-->>MCP: ok, pending_review
        MCP-->>A1: pr_id=42
    and Design Agent 提交 n3
        A2->>MCP: submit_artifact(n3, ...)
        MCP->>LOCK: pg_advisory_xact_lock(hash(n3))
        LOCK-->>MCP: acquired
        MCP->>LG: invoke({submit: n3})
        LG->>CKPT: load thread=pipeline_id
        CKPT-->>LG: state(v=5)
        LG->>LG: guard(n3: ready→pending_review) ✓
        LG->>CKPT: save state(v=7) (合并 v=6 的 n2 变更)
        LG-->>MCP: ok, pending_review
        MCP-->>A2: pr_id=43
    end

    Note over A1,A3: 同节点并发(串行化)
    A1->>MCP: approve_pr(42)
    A3->>MCP: update_progress(n2, in_progress)
    par approve 先抢到锁
        MCP->>LOCK: pg_advisory_xact_lock(hash(n2))
        LOCK-->>MCP: acquired by approve
        MCP->>LG: invoke({approve: n2})
        LG->>LG: guard(n2: pending_review→done) ✓
        LG->>CKPT: save state(v=8)
        MCP-->>A1: done
    and progress 排队
        MCP->>LOCK: pg_advisory_xact_lock(hash(n2))
        Note right of LOCK: 等待 approve 释放
        LOCK-->>MCP: acquired by progress
        MCP->>LG: invoke({progress: n2})
        LG->>LG: guard(n2: done→in_progress) ✗ INVALID_TRANSITION
        LG-->>MCP: 拒绝
        MCP-->>A3: error INVALID_TRANSITION
    end
```

---

## 4. PR 冲突处理

### 4.1 同节点多个 PR 处理

**场景**:节点 n2 已有 PR #42 在 `pending_review`,同一 agent 或另一 agent 又开了 PR #43。

**处理策略:一次只允许一个活跃 PR**(`pending_prs[nid]` 单值约束):

| 时序 | 行为 |
|---|---|
| PR #42 在审,新开 PR #43 | MCP 检测 `pending_prs[n2]` 非空 → 拒绝开 PR #43,返回 `PR_ALREADY_PENDING` 错误,提示先 close #42 |
| PR #42 被 reject(close),新开 PR #43 | 允许,T9 转移:`pending_prs[n2]` 更新为 43,n2 保持 ready→pending_review |
| PR #42 在审,人为直接 close #42(不经 reject_pr) | webhook 通知 MCP,MCP 清 `pending_prs[n2]`,n2 回 `ready`,发 `PR_CLOSED` event |

**实现**:`submit_artifact` 入口 guard 增加 `pending_prs[nid] is None` 检查(T5/T6 guard 的上下文条件)。

### 4.2 产物路径冲突

**场景**:两个不同节点 PR 提交到同一产物路径 `api_contract/001.yaml`。

**根因**:节点 ID 与产物路径未强绑定,管理方 PR 模板只声明 `node_id` + `artifact.path`,未校验路径唯一性。

**防护方案**:

1. **路径注册表**:新增 `node_path_registry(node_id, artifact_path, commit)` 表,PR 审核时校验路径占用。
2. **审核校验**:`review_artifact_pr` 增加 `path_conflict_check`:
   - 若 `artifact_path` 已被其他 node_id 注册且该 node 处于 `done`/`pending_review` → 拒绝,返回 `PATH_CONFLICT` + 占用方 node_id
   - 若 `artifact_path` 是本 node_id 已注册路径 → 允许(变更场景)
3. **路径命名规范**(建议,非强制):`{node_type}/{node_id}_{seq}.{ext}`,如 `api_contract/n2_001.yaml`,从源头避免冲突。

### 4.3 合并冲突 rebase

**场景**:PR #42 基于的 main commit 已被 PR #41 合并推进,PR #42 合并时 git 报冲突。

**处理流程:**

| 步骤 | 动作 | 失败处理 |
|---|---|---|
| 1 | `approve_pr` 触发 `git merge --squash` | 冲突 → 进步骤 2 |
| 2 | 尝试 `git rebase main` 自动重放 | 仍冲突 → 进步骤 3 |
| 3 | 标记 PR `needs_rebase`,通知提交方 | 提交方本地 rebase 后 force push |
| 4 | 提交方 force push 后,webhook 重新触发 review | 重新走 §4.3 步骤 1 |

**幂等保护**:rebase + force push 产生新 commit,`idempotency_key` 用 `submit:{node_id}:{new_commit}`,不复用旧 key,允许重新走流程。

**重试上限**:同一 PR rebase 失败 3 次后,自动 reject 并标记 `REBASE_GIVE_UP`,要求人工介入。

---

## 5. 错误恢复与重试策略

### 5.1 错误分类与处理矩阵

| 错误类别 | 典型错误 | 影响范围 | 处理策略 | 重试上限 |
|---|---|---|---|---|
| **LangGraph 节点异常** | `cascade_node` 抛 KeyError(节点定义缺失) | 当前 invoke 失败 | 指数退避重试 → 死信队列 | 3 次 |
| **MCP 调用失败** | `submit_artifact` 校验产物引用超时 | 单次 MCP 调用失败 | 指数退避重试 → 返回错误给 agent | 3 次 |
| **git 操作失败** | `git merge` 冲突 / `git ls-file` 超时 | approve_pr 或 verify 失败 | rebase(§4.3)或退避重试 → 死信 | 3 次 |
| **Checkpointer 失败** | Postgres 连接断开 | state 持久化失败 | 退避重试 → 降级内存 checkpoint + 告警 | 5 次 |
| **Guard 拒绝** | 非法状态转移 | 当前 invoke 拒绝 | **不重试**(语义错误,重试无用) | 0 次 |
| **Langfuse 失败** | trace 写入超时 | 监控数据丢失 | **降级本地日志**,主流程继续 | 不重试 |
| **CrewAI 分配失败** | agent 离线 | Task 未派发 | 重新选 agent → 退避重试 → 标记 `NO_AGENT` | 3 次 |

### 5.2 指数退避

**通用退避函数:**

```python
import asyncio
import random

async def retry_with_backoff(
    fn,
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (TimeoutError, ConnectionError, GitError),
):
    """指数退避 + 抖动。Guard 拒绝等语义错误不重试。"""
    attempt = 0
    last_exc = None
    while attempt < max_attempts:
        try:
            return await fn()
        except retryable_exceptions as e:
            last_exc = e
            attempt += 1
            if attempt >= max_attempts:
                break
            delay = min(max_delay, base_delay * (2 ** attempt)) * (0.5 + 0.5 * random.random())
            await asyncio.sleep(delay)
    # 重试耗尽 → 抛给上层入死信队列
    raise RetryExhausted(attempt=attempt, last_exc=last_exc)
```

**参数矩阵:**

| 操作 | max_attempts | base_delay | max_delay | retryable |
|---|---|---|---|---|
| `submit_artifact`(verify ref) | 3 | 1s | 10s | TimeoutError, ConnectionError |
| `approve_pr`(git merge) | 3 | 2s | 30s | GitError, TimeoutError |
| `langgraph.invoke` | 3 | 1s | 15s | LangGraphRuntimeError |
| checkpointer save | 5 | 0.5s | 5s | psycopg2.OperationalError |
| CrewAI dispatch | 3 | 5s | 60s | AgentOfflineError |

### 5.3 死信队列(DLQ)

**死信表 schema(Postgres):**

```sql
CREATE TABLE dlq (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pipeline_id TEXT NOT NULL,
    node_id TEXT,
    operation TEXT NOT NULL,              -- submit_artifact / approve_pr / cascade_node ...
    payload JSONB NOT NULL,               -- 原始请求 + 上下文
    last_error TEXT NOT NULL,
    attempts INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending / processing / resolved / abandoned
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,                      -- admin / auto-replay
    resolution_note TEXT
);
CREATE INDEX idx_dlq_status_pipeline ON dlq(status, pipeline_id);
```

**入队规则:**
- `retry_with_backoff` 耗尽 → 写入 DLQ,`status=pending`
- LangGraph 节点异常 → 直接入 DLQ(不经退避,语义错误)
- DLQ 写入后发 `DLQ_ENQUEUED` event,通知 admin

**处理方式:**
- admin 通过 `get_audit_log(filter=dlq)` 查看 DLQ
- 修复根因后调 `replay_dlq(id)` 重放:从 payload 重新 invoke LangGraph
- 重放成功 → `status=resolved`;重放仍失败 → 保持 `pending`,attempts++
- 连续 3 次重放失败 → `status=abandoned`,需人工介入

### 5.4 错误恢复流程(图 5-1)

```mermaid
flowchart TD
    INVOKE[LangGraph 节点执行] --> TRY{执行}
    TRY -->|成功| OK[写 state + event<br/>checkpoint]
    TRY -->|异常| CLASS{错误分类}

    CLASS -->|语义错误<br/>Guard拒绝/校验失败| REJECT[返回错误给调用方<br/>不重试,写rejected event]
    CLASS -->|瞬态错误<br/>超时/连接断| BACKOFF[指数退避重试]

    BACKOFF --> SLEEP{sleep<br/>delay=base*2^attempt}
    SLEEP --> INVOKE

    BACKOFF -->|attempts < max| INVOKE
    BACKOFF -->|attempts >= max| DLQ[入死信队列<br/>status=pending]

    DLQ --> NOTIFY[通知 admin<br/>发 DLQ_ENQUEUED event]
    NOTIFY --> WAIT[等待人工或自动重放]

    WAIT --> REPLAY[replay_dlq id]
    REPLAY --> INVOKE2[从 payload 重新 invoke]
    INVOKE2 -->|成功| RESOLVED[status=resolved]
    INVOKE2 -->|失败 3 次| ABANDON[status=abandoned<br/>人工介入]

    OK --> CKPT[checkpointer save]
    CKPT -->|成功| DONE[流程继续]
    CKPT -->|失败| CKPT_RETRY[退避重试 5 次]
    CKPT_RETRY -->|成功| DONE
    CKPT_RETRY -->|失败| FALLBACK[降级内存 checkpoint<br/>告警 admin]

    style REJECT fill:#b3261e,color:#fff
    style DLQ fill:#d29922,color:#fff
    style RESOLVED fill:#3fb950,color:#fff
    style ABANDON fill:#b3261e,color:#fff
    style FALLBACK fill:#d29922,color:#fff
```

---

## 6. Checkpointer 配置

### 6.1 Postgres Schema

LangGraph 0.2+ 内置 `AsyncPostgresSaver`,自动管理 checkpoint 表。本节给出完整 schema(含 LangGraph 内置表 + 平台扩展表)。

**LangGraph 内置表(由 `AsyncPostgresSaver.setup()` 自动创建):**

```sql
-- LangGraph checkpointer 内置表(简化,实际由 SDK 管理)
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BYTEA,                     -- 序列化后的 PipelineState
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id, checkpoint_ns, checkpoint_id);

CREATE TABLE writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INT NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel)
);
```

**平台扩展表(自行管理):**

```sql
-- 幂等键表
CREATE TABLE idempotency_keys (
    key TEXT PRIMARY KEY,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_idem_expires ON idempotency_keys(expires_at);

-- 节点路径注册表(§4.2)
CREATE TABLE node_path_registry (
    node_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    commit TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pipeline_id, node_id),
    UNIQUE (pipeline_id, artifact_path)   -- 路径全局唯一
);

-- 死信队列(§5.3)
-- 见 §5.3 schema

-- 审计日志(独立表,与 FR6.5 对齐)
CREATE TABLE audit_log (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    pr_id BIGINT,
    node_id TEXT,
    node_type TEXT,
    artifact_path TEXT,
    merge_commit TEXT,
    reviewer TEXT,
    submitter TEXT,
    skill_used TEXT,
    skill_verdict TEXT,
    deps_at_review JSONB,
    note TEXT,
    trace_id TEXT,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_node ON audit_log(node_id, ts);
CREATE INDEX idx_audit_reviewer ON audit_log(reviewer, ts);
CREATE INDEX idx_audit_action ON audit_log(action, ts);

-- 锁状态监控(可选,advisory lock 本身无表)
CREATE TABLE lock_wait_log (
    id BIGSERIAL PRIMARY KEY,
    node_id TEXT NOT NULL,
    waiter_op TEXT NOT NULL,
    wait_ms INT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 6.2 Checkpoint 频率

| 触发点 | 是否 checkpoint | 理由 |
|---|---|---|
| `bootstrap_node` 完成 | ✅ | 初始 state 必须落盘 |
| 每次状态转移(T1-T18) | ✅ | state 变更点必须可恢复 |
| `cascade_node` / `invalidate_node` 每跳 | ✅(每跳) | 递归失效中途崩溃可从上一跳恢复 |
| `events` 追加 | ✅(随 state 一起) | event 与 state 同 checkpoint |
| Guard 拒绝 | ✅ | rejected event 也要持久化审计 |
| Langfuse trace | ❌ | 旁路,不阻塞,失败降级 |
| 长时间 `wait_node` | ❌(无 state 变更) | 无变更不 checkpoint |

**频率权衡**:checkpoint 每次状态变更必做,保证强一致性;Postgres WAL + 同步提交(`synchronous_commit=on`)确保不丢。性能瓶颈期可改 `synchronous_commit=remote_apply` 在主从间平衡。

### 6.3 恢复点选择

**thread_id 设计**:`thread_id = pipeline_id`(一个管线一个 thread),`checkpoint_ns = ""`(本平台不嵌套 subgraph)。

**恢复流程:**

1. 进程启动 → 加载 `pipeline.yaml` → 校验 DAG(§7)
2. 对每个 `pipeline_id` 调 `graph.aget_state(thread_id=pipeline_id)`
3. 若存在 checkpoint → 从最新 checkpoint 恢复 `PipelineState`
4. 若不存在 → 调 `bootstrap_node` 初始化
5. 恢复后校验:`state.node_states` 键集 == `pipeline.nodes` 键集;不一致则补缺失节点为 `blocked` 并发 `STATE_RECOVERED` event
6. 恢复 DLQ 中 `status=pending` 的记录,提示 admin 决定是否重放

**部分恢复策略**:
- 若最新 checkpoint 标记 `in_flight=True`(节点执行中崩溃)→ 该节点状态回退到上一 checkpoint 的状态,标记 `RECOVERY_RETRY`,允许重新 invoke
- 若 checkpoint 解码失败(state schema 版本不兼容)→ 回退到上一个能解码的 checkpoint,发 `CHECKPOINT_DECODE_FAIL` 告警

### 6.4 Checkpoint 恢复(图 6-1)

```mermaid
sequenceDiagram
    participant MAIN as main.py 启动
    participant LG as LangGraph Runtime
    participant CKPT as Postgres<br/>Checkpointer
    participant DLQ as 死信队列
    participant ADMIN as Admin

    MAIN->>LG: 加载 pipeline.yaml + DAG 校验
    MAIN->>LG: 为每个 pipeline_id 调 aget_state

    alt 存在 checkpoint
        LG->>CKPT: SELECT checkpoint ORDER BY checkpoint_id DESC LIMIT 1
        CKPT-->>LG: state(v=N, in_flight=?)
        LG->>LG: 解码 state
        alt 解码成功
            LG->>LG: 校验 node_states 键集 == pipeline.nodes
            alt 键集一致
                LG->>LG: 恢复 state
            else 键集不一致(管线变更)
                LG->>LG: 补缺失节点为 blocked<br/>发 STATE_RECOVERED event
            end
            opt in_flight=True(崩溃中)
                LG->>LG: 该节点回退到 v=N-1 状态<br/>标记 RECOVERY_RETRY
            end
        else 解码失败
            LG->>CKPT: 回退到上一个可解码 checkpoint
            LG->>ADMIN: 告警 CHECKPOINT_DECODE_FAIL
        end
    else 无 checkpoint
        LG->>LG: 调 bootstrap_node 初始化
        LG->>CKPT: save checkpoint(v=1)
    end

    LG->>DLQ: 查询 status=pending
    DLQ-->>LG: [dlq entries]
    LG->>ADMIN: 通知待处理 DLQ 条目

    MAIN->>LG: graph.astream(events 恢复执行)

    Note over LG,CKPT: 后续每次状态变更<br/>自动 checkpoint
```

---

## 7. 管线加载与校验

### 7.1 加载流程

```mermaid
flowchart TD
    FILE[读取 pipeline.yaml] --> PARSE[解析 YAML → Pipeline 对象]
    PARSE --> PARTICIPATION[ParticipationProfile 校验<br/>roles_present/roles_absent]
    PARSE --> CYCLE[DAG 无环校验 Kahn]
    PARSE --> REF[节点引用完整性]
    PARSE --> CTRL[控制节点配置校验]
    PARSE --> ROLE[角色/工具权限校验]
    PARSE --> OPT[optional 依赖 DAG 校验<br/>presence/strictness/coupling]

    PARTICIPATION -->|profile 非法| FAIL0[拒绝加载<br/>error: INVALID_PROFILE]
    CYCLE -->|有环| FAIL1[拒绝加载<br/>error: CYCLE_DETECTED]
    REF -->|引用缺失| FAIL2[拒绝加载<br/>error: DANGLING_REF]
    CTRL -->|配置非法| FAIL3[拒绝加载<br/>error: INVALID_CONTROL_NODE]
    ROLE -->|角色不匹配| FAIL4[拒绝加载<br/>error: ROLE_MISMATCH]
    OPT -->|optional 配置矛盾| FAIL5[拒绝加载<br/>error: OPTIONAL_DEP_CONFLICT]

    PARTICIPATION -->|合法| OK0
    CYCLE -->|无环| OK1
    REF -->|完整| OK2
    CTRL -->|合法| OK3
    ROLE -->|匹配| OK4
    OPT -->|一致| OK5

    OK0 & OK1 & OK2 & OK3 & OK4 & OK5 --> MAT[materialize<br/>裁剪 roles_absent 节点<br/>删除指向已裁剪节点的 deps]
    MAT --> BUILD[构建 StateGraph<br/>add_node + add_conditional_edges]
    BUILD --> COMPILE[graph.compile checkpointer/interrupt]
    COMPILE --> LOAD_DB[写入 pipeline_registry 表]
    LOAD_DB --> READY[就绪,等待 invoke]

    style FAIL0 fill:#b3261e,color:#fff
    style FAIL1 fill:#b3261e,color:#fff
    style FAIL2 fill:#b3261e,color:#fff
    style FAIL3 fill:#b3261e,color:#fff
    style FAIL4 fill:#b3261e,color:#fff
    style FAIL5 fill:#b3261e,color:#fff
    style MAT fill:#58a6ff,color:#fff
    style READY fill:#3fb950,color:#fff
```

### 7.2 DAG 无环校验(Kahn 算法,含跨管线环检测)

```python
def validate_dag_acyclic(nodes: list[NodeDef]) -> tuple[bool, list[str]]:
    """Kahn 拓扑排序判环。返回 (无环?, 环路径若存在)"""
    in_degree = {n["id"]: 0 for n in nodes}
    adj = {n["id"]: [] for n in nodes}
    for n in nodes:
        for dep in n.get("deps", []):
            dep_id = dep["node_id"] or dep["hub_ref"]
            if dep_id not in adj:
                return False, [f"DANGLING_REF: {n['id']} 依赖不存在的 {dep_id}"]
            adj[dep_id].append(n["id"])
            in_degree[n["id"]] += 1
    queue = [nid for nid, d in in_degree.items() if d == 0]
    visited = 0
    while queue:
        cur = queue.pop(0)
        visited += 1
        for nxt in adj[cur]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    if visited != len(nodes):
        cycle_nodes = [nid for nid, d in in_degree.items() if d > 0]
        return False, cycle_nodes
    return True, []


def validate_cross_pipeline_acyclic(registry: CrossPipelineReferenceRegistry) -> tuple[bool, list[str]]:
    """跨管线环检测:构建全局依赖图(hub:// 引用),Kahn 校验。

    单管线校验无法检测跨管线环(A.n1 → B.n2 → A.n1)。
    注册 hub:// 引用时调用本函数。
    """
    # 构建 全局 node_id 集 + 全局 adj
    global_nodes = set()
    global_adj = {}
    global_in_degree = {}
    for ref in registry.all_references():
        src, dst = ref["from_node"], ref["to_node"]  # src 依赖 dst
        global_nodes.add(src)
        global_nodes.add(dst)
        global_adj.setdefault(dst, []).append(src)
        global_in_degree[src] = global_in_degree.get(src, 0) + 1
        global_in_degree.setdefault(dst, 0)
    queue = [n for n in global_nodes if global_in_degree.get(n, 0) == 0]
    visited = 0
    while queue:
        cur = queue.pop(0)
        visited += 1
        for nxt in global_adj.get(cur, []):
            global_in_degree[nxt] -= 1
            if global_in_degree[nxt] == 0:
                queue.append(nxt)
    if visited != len(global_nodes):
        cycle = [n for n in global_nodes if global_in_degree.get(n, 0) > 0]
        return False, cycle
    return True, []
```

### 7.3 ParticipationProfile materialize(角色参与拓扑)

> 对齐主 PRD v3.0 §FR2.2.1。需求 1 要求"设计/服务端/客户端可能无",平台必须认识拓扑变体。

**支持的 profile:**

| profile | roles_present(典型) | 说明 |
|---|---|---|
| `fullstack` | product,server,design,client | 默认登录类全链路 |
| `server_only` | product,server | 内部 API / 计费等无 UI |
| `no_design_client` | product,server,client | Admin/组件库拼装,永久无 Figma |
| `design_only` | design(+product?) | 设计系统/视觉改版;`allow_non_product_root` 可 true |
| `tech_debt` | server | 无产品规格热修;强制更高人工审批 |
| `custom` | 显式列表 | 自由组合,须通过无环 + 无悬空 deps 校验 |

**materialize 规则**(LangGraph bootstrap 时执行):

```python
def materialize_pipeline(template: PipelineTemplate, profile: ParticipationProfile) -> MaterializedPipeline:
    """按 ParticipationProfile 裁剪管线。"""
    nodes = template["nodes"]
    roles_absent = set(profile["roles_absent"])

    # 1. 按 roles_absent / condition 裁剪节点
    materialized_nodes = [
        n for n in nodes
        if n.get("role") not in roles_absent
        and evaluate_condition(n.get("condition"), profile)
    ]
    materialized_ids = {n["id"] for n in materialized_nodes}

    # 2. 删除指向已裁剪节点的 deps(禁止 dangling)
    for n in materialized_nodes:
        n["deps"] = [
            dep for dep in n.get("deps", [])
            if (dep.get("node_id") in materialized_ids) or dep.get("hub_ref")
        ]

    # 3. CrewAI 仅为 roles_present 建 RoleInstance(见 §FR3)
    role_instances = {
        role: RoleInstance(role=role, ...)
        for role in profile["roles_present"]
    }

    # 4. completed 使用 core_nodes_done;optional 节点失败只告警不挡完成
    completion = profile["completion"]  # mode + core_node_types + optional_node_types

    return MaterializedPipeline(
        nodes=materialized_nodes,
        role_instances=role_instances,
        participation=profile,
        completion=completion,
    )
```

**materialize 后的 ready 谓词**(对齐主 PRD 附录 E.2):

```python
def is_ready(node_id: str, state: PipelineState) -> bool:
    """ready 谓词:仅 required deps 参与 AND;optional 不参与。"""
    node = get_node_def(node_id)
    for dep in node["deps"]:
        if dep.get("presence") == "optional":
            continue  # optional dep 不参与 ready 判定
        if dep.get("presence") == "if_present":
            # 仅当 dep 节点在 materialized 管线中存在时才成为 required 依赖
            if dep["node_id"] not in state["node_states"]:
                continue  # 节点不存在,deps 边已删除
        # required 依赖:按 strictness 判定
        dep_state = state["node_states"].get(dep["node_id"])
        if dep["strictness"] == "strict":
            if dep_state != "done":
                return False
        elif dep["strictness"] == "accepts_draft":
            if dep_state not in ("done", "draft"):
                return False
    return True
```

> **roles_absent 裁剪 vs DepDeclaration.optional 关系**(对齐评审 P1-2.4):
> - `roles_absent` 是**管线级裁剪**(materialize 时删除节点 + deps 边),针对"角色缺位"场景。
> - `DepDeclaration.presence=optional` 是**依赖级标记**(节点存在但依赖关系弱),针对"可选依赖"场景。
> - 两者正交:roles_absent 裁剪后,剩余节点的 deps 中若指向已裁剪节点,该 deps 边删除(不降级为 optional)。
> - `completion.optional_node_types` 是**完成谓词级**标记(optional 节点未 done 时可 skip,不挡 completed),与 presence=optional 语义一致但作用层不同。

### 7.4 optional 依赖 DAG 校验

> 对齐主 PRD v3.0 §FR2.2 DepDeclaration + 附录 D11 P0-R5.15/P0-R5.16。optional 依赖不参与 ready 判定,但需校验配置一致性。

**DepDeclaration 字段**(规范化):

```python
class DepDeclaration(TypedDict):
    node_id: str | None
    hub_ref: str | None
    version_constraint: str          # 默认 "*"
    format_slot: str | None
    strictness: str                  # strict | accepts_draft(默认 strict)
    presence: str                    # required | optional | if_present(默认 required)
    coupling: str                    # hard | soft | informational(默认 hard)
    # 兼容: optional: true → 写入时规范化为 presence=optional
```

**optional 依赖校验规则:**

| 校验项 | 规则 | 失败错误码 |
|---|---|---|
| `presence=optional` 的 dep 指向 required 节点 | 允许(optional 标记在依赖方,不影响被依赖方) | — |
| `presence=if_present` 的 dep 指向 materialized 中不存在的节点 | 允许(裁剪后 deps 边删除) | — |
| `presence=required` 的 dep 指向 materialized 中不存在的节点 | **拒绝**(required 依赖不能悬空) | `OPTIONAL_DEP_CONFLICT` + `REQUIRED_DEP_DANGLING` |
| `strictness=accepts_draft` 但上游节点类型不支持 draft | 上游必须是产物节点(控制节点不进 draft) | `INVALID_STRICTNESS` |
| `coupling=informational` 的 dep 同时 `presence=required` | 允许(参与 ready 判定但不级联) | — |
| optional 节点的下游 deps 全是 optional | 允许(该节点可被 skip 不影响下游) | — |
| required 节点的某 dep 是 optional | 允许(optional dep 不参与 ready 判定) | — |
| `presence=optional` 节点在 `completion.core_node_types` 中 | **拒绝**(core 节点不能 optional) | `OPTIONAL_DEP_CONFLICT` + `CORE_NOT_OPTIONAL` |
| `presence=optional` 节点在 `completion.optional_node_types` 中 | 允许(一致) | — |

**optional 依赖的级联处理:**

| 场景 | 行为 |
|---|---|
| optional dep 节点 done | 不触发下游 ready(因下游 ready 谓词忽略 optional dep);但发 `OPTIONAL_DEP_DONE` 通知 |
| optional dep 节点 changed | 按 coupling 判定:hard→下游 blocked;soft/informational→通知不改状态 |
| optional dep 节点 deprecated | 发 `DEPRECATED_NOTIFY`;下游保持(有限期升级) |
| optional dep 节点 skipped | 发 `OPTIONAL_DEP_SKIPPED`;下游若全部 required deps 满足则保持 ready;若该 optional dep 是 `if_present` 则下游 ready 谓词重新评估 |
| optional 节点后到依赖到达(`OPTIONAL_DEP_ARRIVED`) | 下游若处于 skipped 可经 S2 转 ready;若已 done 则发 `OPTIONAL_DEP_LATE_ARRIVAL` warning |

### 7.5 节点引用完整性

| 校验项 | 规则 | 失败错误码 |
|---|---|---|
| `deps` 引用存在 | 每个 dep 必须在 nodes 列表中(或为 hub_ref 跨管线引用) | `DANGLING_REF` |
| `deps` 不自引用 | `node.deps` 不含 `node.id` | `SELF_DEPENDENCY` |
| 控制节点 `deps` 非空 | gate/approval/fork 至少 1 dep | `CONTROL_NO_DEPS` |
| fork 节点 `deps` ≥ 2 | fork 设计为多入边汇合 | `FORK_TOO_FEW_DEPS`(warning,非强制) |
| approval 节点 `approver` 必填 | 非空字符串 | `APPROVAL_NO_APPROVER` |
| gate 节点 `policy` 必填 | 至少含一项 lint/test/coverage/security | `GATE_NO_POLICY` |
| switch 节点 `routes` 必填 | 至少 2 条路由 | `SWITCH_TOO_FEW_ROUTES` |
| 产物节点 `role` 必填 | 在 product/server/design/client 中 | `INVALID_ROLE` |
| 产物节点 `type` 合法 | 在开放命名空间({role}.{name})中 | `INVALID_NODE_TYPE` |

### 7.6 控制节点配置校验

| 控制节点 | 必填字段 | 取值约束 |
|---|---|---|
| `gate` | `policy` | `policy.lint`/`policy.test`/`policy.coverage_min`/`policy.security` 至少一项;`coverage_min` 为 0-100 整数 |
| `approval` | `approver`, `timeout_hours`(可选) | `approver` 非空;`timeout_hours` 默认 24,范围 [1, 168] |
| `fork` | (无额外) | `deps` ≥ 2(建议) |
| `switch` | `routes` | `routes` 是 list,每项 `{field, op, value, target_branch}`;`op` ∈ {eq, gt, lt, gte, lte, in} |
| `notify` | `channel`, `target` | `channel` ∈ {feishu, slack, github, webhook};`target` 非空 |

### 7.7 热重载机制

**支持的热重载场景:**

| 场景 | 触发 | 行为 |
|---|---|---|
| 新增节点(扩展管线) | `pipeline.yaml` git push | 加载新版本 → 校验 → 对运行中 pipeline 增量添加节点(初始 `blocked`)→ 不影响已有节点状态 |
| 删除节点(收缩管线) | `pipeline.yaml` git push | **拒绝**若该节点已 `done` 或 `pending_review`;允许若 `blocked` 且无下游 |
| 修改 deps | `pipeline.yaml` git push | 重新校验无环 → 重新计算下游 ready 状态 → 发 `DEPS_CHANGED` event |
| 修改 gate policy | `set_gate_policy` MCP 工具 | 仅对未执行 gate 生效;已 `done` 的 gate 不追溯 |
| 修改 approval approver | admin 手动 | 仅对未 approve 的 approval 生效 |
| 修改 ParticipationProfile | `pipeline.yaml` git push | **拒绝热重载**(profile 变更影响 materialize,需新 pipeline_id 迁移) |

**热重载实现**:
- `pipeline.yaml` 进 git,webhook 触发重载
- 重载用新 `pipeline_id`(版本化,如 `login-feature@v2`),旧 pipeline_id 继续运行至完成或手动迁移
- 迁移工具 `migrate_pipeline(old_id, new_id)` 拷贝 state,按新 DAG 校验一致性

### 7.8 管线加载校验清单

- [ ] YAML 语法合法
- [ ] 所有 `node.id` 唯一
- [ ] 所有 `node.deps` 引用存在(`DANGLING_REF`)
- [ ] 无自引用(`SELF_DEPENDENCY`)
- [ ] DAG 无环(`CYCLE_DETECTED`,Kahn)
- [ ] 跨管线 hub:// 引用无环(§7.2 `validate_cross_pipeline_acyclic`)
- [ ] 产物节点 `role` + `type` 合法(开放命名空间)
- [ ] 控制节点配置完整(§7.6)
- [ ] 至少 1 个根节点(无 required deps,允许多根)
- [ ] 至少 1 个叶子节点(无下游)
- [ ] switch 路由目标分支都存在
- [ ] gate policy 字段类型正确
- [ ] approval approver 在角色列表中
- [ ] ParticipationProfile 合法(§7.3)
- [ ] materialize 后无 dangling deps(§7.3)
- [ ] optional 依赖配置一致(§7.4,`OPTIONAL_DEP_CONFLICT`)
- [ ] core_node_types 中无 optional 节点(§7.4)
- [ ] `presence=if_present` 的 dep 指向的节点若存在则需校验类型匹配

---

## 8. 控制节点边界条件

PRD §2.5 只给出控制节点正常路径,本节穷举边界条件。

### 8.1 gate 节点边界条件

| 边界条件 | 行为 |
|---|---|
| policy 全通过 | gate→done,cascade 下游 |
| **policy 部分通过**(如 lint 过 test 失败) | gate→失败,上游产物节点回 `in_progress`,发 `GATE_FAIL` event 含失败项详情 |
| policy 缺失(配置错误) | gate 不执行,发 `GATE_CONFIG_MISSING` event,标记 `blocked` 等待 admin 修复 |
| 上游 changed 后 gate 状态 | gate 自动回 `blocked`(T16 cascade 失效),等上游重新 done 后重评 |
| gate 评估超时 | 指数退避重试 3 次 → DLQ,gate 保持 `in_progress` |
| 上游多入边部分 done | gate 保持 `blocked`,等全部上游 done |
| gate 已 done 后 policy 变更 | 不追溯,新 policy 对下次 gate 生效 |
| coverage_min 边界(刚好等于) | 视为通过(`>=`) |

### 8.2 approval 节点边界条件

| 边界条件 | 行为 |
|---|---|
| approve | approval→done,cascade 下游 |
| **reject** | approval→changed(T15),上游最近产物节点 changed,递归失效下游 |
| **超时**(默认 24h,可配 `timeout_hours`) | 自动 reject,发 `APPROVAL_TIMEOUT` event,通知 admin;超时计 1 次驳回 |
| 多审批人(approver 列表) | 全部 approve 才 done;任一 reject 即 reject;`pending_approvals` 存已 approve 集合 |
| approver 离线 | 不影响 approval 节点状态,超时机制兜底;admin 可重新指定 approver |
| 重复 approve(同 approver) | 幂等,返回首次结果,不重复 cascade |
| approval 已 done 后再次 reject | 拒绝,返回 `INVALID_TRANSITION`(done→changed 需走重提 PR 路径) |
| 上游 changed 后 approval 状态 | approval 自动回 `blocked`(T16),等上游重 done 后重新 review |
| approval 上游是控制节点(嵌套) | 递归找最近的产物节点 changed;若全是控制节点,标记 `NO_ARTIFACT_UPSTREAM` 告警 |

### 8.3 fork 节点边界条件

| 边界条件 | 行为 |
|---|---|
| 多入边全 done | fork→done(透传),cascade 下游 |
| 多入边部分 done 部分 blocked | fork 保持 `blocked` |
| **多入边部分 changed** | fork 自动回 `blocked`(任一上游 changed 触发 T16 递归),等上游重 done |
| 多入边全 changed | 同上,fork blocked,所有上游需重审 |
| fork 下游已 done 后某上游 changed | fork→blocked(递归),下游 cascade 失效 |
| 单入边 fork(配置错误但允许) | 退化为普通透传,发 `FORK_SINGLE_EDGE` warning |
| fork 上游包含 fork(嵌套) | 正常处理,递归判 done |

### 8.4 switch 节点边界条件

| 边界条件 | 行为 |
|---|---|
| 路由字段存在,匹配某分支 | switch→done,cascade 路由目标分支的下游 |
| **路由字段缺失** | switch 保持 `blocked`,发 `SWITCH_FIELD_MISSING` event,等上游补字段(重提 PR) |
| **多分支同时满足** | 按声明顺序取第一个匹配分支,发 `SWITCH_MULTI_MATCH` warning |
| 无分支匹配 | switch→done(默认透传),发 `SWITCH_NO_MATCH` warning;或配置 `default: reject` 则 reject |
| 路由目标分支节点不存在 | 加载时校验拒绝(`SWITCH_INVALID_TARGET`) |
| 上游 changed 后 switch 状态 | switch 回 blocked,等上游重 done 重评 |
| switch 嵌套(目标分支是另一个 switch) | 递归处理 |

### 8.5 notify 节点边界条件

| 边界条件 | 行为 |
|---|---|
| 上游 done | 触发外部通知 → notify→done,cascade 下游 |
| **外部系统不可达**(飞书/Slack webhook 超时) | 指数退避重试 3 次 → 仍失败则 **notify 仍→done**(通知是 best-effort,不阻塞管线),发 `NOTIFY_FAIL` event + DLQ 记录供重放 |
| 通知成功但下游 cascade 失败 | notify 已 done,下游 cascade 走正常错误恢复(§5) |
| 上游 changed 后 notify 状态 | notify 回 blocked,等上游重 done 后重新触发通知 |
| notify 配置 channel 不支持 | 加载时校验拒绝(`NOTIFY_INVALID_CHANNEL`) |
| 重复触发(上游 done→changed→done) | 每次重新触发通知,不幂等(通知是外部副作用,需调用方自行幂等) |

### 8.6 控制节点边界条件完整表(汇总)

| 控制节点 | 全过/成功 | 部分失败 | 超时 | 上游 changed | 配置缺失 |
|---|---|---|---|---|---|
| `gate` | →done | 上游回 in_progress | DLQ + 保持 in_progress | →blocked | blocked + 告警 |
| `approval` | →done | (无部分概念) | 自动 reject→上游 changed | →blocked | 加载拒绝 |
| `fork` | →done(透传) | blocked | (无超时) | →blocked | (无需配置) |
| `switch` | →done 路由分支 | 字段缺失→blocked;多匹配取首 | (无超时) | →blocked | 加载拒绝 |
| `notify` | →done + 发通知 | (无部分概念) | 仍→done + DLQ | →blocked | 加载拒绝 |

---

## 9. LangGraph 编译配置

### 9.1 StateGraph 编译选项

```python
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Interrupt, Command

# 见 §6.1 checkpointer 配置
checkpointer = AsyncPostgresSaver.from_conn_string(DB_DSN)
await checkpointer.setup()  # 自动建表

graph_builder = StateGraph(PipelineState)

# 注册节点
graph_builder.add_node("bootstrap", bootstrap_node)
graph_builder.add_node("dispatch_router", dispatch_router)
graph_builder.add_node("crewai_assign", crewai_assign_node)
graph_builder.add_node("cascade", cascade_node)
graph_builder.add_node("invalidate", invalidate_node)
graph_builder.add_node("approval", approval_node)
graph_builder.add_node("wait", wait_node)
graph_builder.add_node("gate_eval", gate_eval_node)
graph_builder.add_node("notify_send", notify_send_node)

# 入口
graph_builder.add_edge(START, "bootstrap")
graph_builder.add_edge("bootstrap", "dispatch_router")

# 条件路由(声明式)
graph_builder.add_conditional_edges(
    "dispatch_router",
    dispatch_router_fn,
    {
        "crewai_assign": "crewai_assign",
        "approval": "approval",
        "cascade": "cascade",
        "invalidate": "invalidate",
        "gate_eval": "gate_eval",
        "notify_send": "notify_send",
        "wait": "wait",
        "end": END,
    },
)

# 回环
graph_builder.add_edge("crewai_assign", "dispatch_router")
graph_builder.add_edge("cascade", "dispatch_router")
graph_builder.add_edge("invalidate", "dispatch_router")
graph_builder.add_edge("gate_eval", "dispatch_router")
graph_builder.add_edge("notify_send", "dispatch_router")
graph_builder.add_edge("approval", "dispatch_router")
graph_builder.add_edge("wait", "dispatch_router")

# 编译(关键配置)
graph = graph_builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["approval"],   # HITL:approval 前暂停等人工
    interrupt_after=[],              # 无 after 中断
    # recursion_limit 见 §9.3
)
```

### 9.2 Interrupt 配置(HITL approval)

**`approval` 控制节点需人工介入**:用 `interrupt_before=["approval"]` 在进入 approval 节点前暂停,等待人工 `approve` / `reject`。

```python
# 触发 approval 暂停
async def trigger_approval(state, node_id):
    # invoke 到 approval 节点前自动暂停(interrupt_before)
    await graph.ainvoke(
        {"trigger_approval": node_id},
        config={"configurable": {"thread_id": state["pipeline_id"]}},
    )
    # 此时 state 处于 interrupted,等人工

# 人工 approve 后恢复
async def human_approve(pipeline_id, approver):
    # 写入 approval 决定到 state(用 Command 恢复)
    await graph.aupdate_state(
        config={"configurable": {"thread_id": pipeline_id}},
        values={"pending_approvals": {current_node: approver},
                "events": [{"type": "HUMAN_APPROVE", "approver": approver}]},
    )
    # 恢复执行
    await graph.ainvoke(None, config={"configurable": {"thread_id": pipeline_id}})
```

**interrupt 与 MCP 工具对应:**
- MCP `request_approval` → 触发 invoke,LangGraph 自动在 approval 节点前 interrupt
- MCP `approve` / `reject` → `aupdate_state` + `ainvoke(None)` 恢复

### 9.3 recursion_limit

**为何需要**:LangGraph 默认 `recursion_limit=25`,即一次 invoke 内最多经过 25 个节点。本平台 `dispatch_router → cascade → dispatch_router → ...` 循环可能超限。

**配置**:

```python
RECURRENCY_LIMIT_PER_PIPELINE = 200  # 单管线一次 invoke 上限

async def safe_invoke(pipeline_id, inputs):
    try:
        return await graph.ainvoke(
            inputs,
            config={
                "configurable": {"thread_id": pipeline_id},
                "recursion_limit": RECURRENCY_LIMIT_PER_PIPELINE,
            },
        )
    except langgraph.errors.RecursionLimit:
        # 超限 → 拆分:把剩余 ready 节点写入 state,返回当前进度
        # 下次 invoke 从 checkpoint 恢复继续
        logger.warning(f"pipeline {pipeline_id} 触发 recursion_limit,拆分重入")
        return await graph.ainvoke(
            None,  # 从 checkpoint 恢复
            config={
                "configurable": {"thread_id": pipeline_id},
                "recursion_limit": RECURRENCY_LIMIT_PER_PIPELINE,
            },
        )
```

**循环检测**:除 recursion_limit 兜底,`dispatch_router` 内置 visited set,同一节点同状态被访问 3 次即抛 `LOOP_DETECTED` 错误入 DLQ。

### 9.4 并行 fan-out(Send API)

**场景**:`cascade_node` 一次解锁多个下游 ready 节点,需并行分配 CrewAI Task。

```python
from langgraph.types import Send

def dispatch_router_fn(state: PipelineState) -> list[Send] | str:
    """并行 fan-out:多个 ready 节点同时分发(11 态扩展版)"""
    ready_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.READY]
    review_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.REVIEW]
    changed_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.CHANGED]
    done_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.DONE]
    draft_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.DRAFT]
    deprecated_nodes = [nid for nid, s in state["node_states"].items() if s == NodeStatus.DEPRECATED]

    sends = []
    # 并行 fan-out 多个 ready 节点到 crewai_assign
    for nid in ready_nodes:
        sends.append(Send("crewai_assign", {"target_node": nid}))
    # 并行 fan-out 多个 review 节点到 approval
    for nid in review_nodes:
        sends.append(Send("approval", {"target_node": nid}))
    # 并行 fan-out 多个 changed 节点到 invalidate
    for nid in changed_nodes:
        sends.append(Send("invalidate", {"target_node": nid}))
    # done 节点并行 cascade
    for nid in done_nodes:
        sends.append(Send("cascade", {"target_node": nid}))
    # draft 节点并行通知订阅者(draft_publish_node)
    for nid in draft_nodes:
        sends.append(Send("draft_publish", {"target_node": nid}))
    # deprecated 节点并行通知引用方(external_health_node 检查 sunset)
    for nid in deprecated_nodes:
        sends.append(Send("external_health", {"target_node": nid}))

    if not sends:
        # 无待处理 → 检查 completed 谓词(core 全 done + optional done 或 skipped)
        participation = state["participation"]
        completion = participation["completion"]
        core_types = set(completion["core_node_types"])
        optional_types = set(completion.get("optional_node_types", []))

        def is_complete(nid, s):
            node = get_node_def(nid)
            if node["type"] in core_types:
                return s == NodeStatus.DONE
            if node["type"] in optional_types:
                return s in (NodeStatus.DONE, NodeStatus.SKIPPED)
            return s == NodeStatus.DONE  # 其他节点默认需 done

        if all(is_complete(nid, s) for nid, s in state["node_states"].items()):
            return END  # 进 completed(P5)
        return "wait"
    return sends
```

> **11 态扩展说明**:新增 `draft` 节点路由到 `draft_publish_node`(通知订阅者);`deprecated` 节点路由到 `external_health_node`(检查 sunset 倒计时);`skipped`/`sunset` 是终态,不需 dispatch。completed 谓词按 `core_nodes_done` 模式判定(core 全 done + optional done 或 skipped)。

**Send API 行为**:
- 返回 `list[Send]` 时,LangGraph 并行执行所有目标节点
- 各分支产出的 state 增量用 `Annotated` 合并策略汇聚(`events` 追加,`node_states` last-write-wins + 版本号)
- 分支全部完成后才进下一轮 `dispatch_router`

### 9.5 完整编译代码(整合)

见 §9.1 + §9.2 + §9.3 + §9.4,核心配置汇总:

| 配置项 | 值 | 理由 |
|---|---|---|
| `checkpointer` | `AsyncPostgresSaver` | 持久化 + 多进程共享 |
| `interrupt_before` | `["approval"]` | HITL approval 暂停 |
| `interrupt_after` | `[]` | 无 after 中断 |
| `recursion_limit` | 200 | 允许长管线循环 |
| 条件边 | `dispatch_router_fn` 返回 `list[Send]` | 并行 fan-out |
| `thread_id` | `pipeline_id` | 一管线一 thread |

---

## 10. 事件溯源

### 10.1 events 累积策略

`PipelineState.events` 用 `Annotated[Sequence[dict], operator.add]`,所有节点产出的 event 自动追加,不覆盖。event 流是**只追加日志(append-only log)**,永不修改/删除(除合规清理)。

### 10.2 事件 schema

```python
class Event(TypedDict):
    event_id: str            # UUID
    ts: str                  # ISO8601
    type: str                # BLOCKED / READY / PENDING_REVIEW / DONE / CHANGED / REJECT / INVALIDATED / GATE_FAIL / DLQ_ENQUEUED / ...
    node_id: str
    pipeline_id: str
    from_state: str | None   # 状态转移源
    to_state: str | None     # 状态转移目标
    actor: str               # agent_id / reviewer / system
    trace_id: str            # Langfuse 关联
    payload: dict            # 类型相关上下文(PR id / commit / 失败原因 ...)
    rejected: bool           # Guard 拒绝的转移也记录
    idempotency_key: str | None
    version: int             # state 版本号(对应 node_versions)
```

### 10.3 事件回放

**用途**:state 损坏/丢失时,从事件流重建 state;审计调查时回放历史。

```python
async def replay_state_from_events(pipeline_id: str, up_to_ts: str | None = None) -> PipelineState:
    """从 events 表回放重建 PipelineState(到指定时间点)"""
    events = await db.fetch_all(
        "SELECT * FROM events WHERE pipeline_id=$1 AND ts <= COALESCE($2, now()) ORDER BY ts, event_id",
        pipeline_id, up_to_ts,
    )
    state = initial_empty_state(pipeline_id)
    for ev in events:
        if ev["rejected"]:
            continue  # 被拒转移不影响 state
        apply_event(state, ev)
    return state

def apply_event(state: PipelineState, ev: dict):
    """单个 event 应用到 state(幂等)"""
    nid = ev["node_id"]
    if ev["type"] in ("BLOCKED", "READY", "PENDING_REVIEW", "IN_PROGRESS", "REVIEW", "DONE", "CHANGED"):
        state["node_states"][nid] = ev["to_state"]
        state["node_versions"][nid] = ev["version"]
    elif ev["type"] == "INVALIDATED":
        state["artifact_refs"].pop(nid, None)
        state["pending_prs"].pop(nid, None)
        state["node_states"][nid] = "blocked"
    elif ev["type"] == "DONE":
        if ev.get("payload", {}).get("artifact_ref"):
            state["artifact_refs"][nid] = ev["payload"]["artifact_ref"]
    # ... 其他类型
```

### 10.4 state 重建(图 10-1)

```mermaid
flowchart LR
    DB[(events 表<br/>append-only)] --> QUERY[按 pipeline_id + ts 查询]
    QUERY --> SORT[排序]
    SORT --> ITER[逐条迭代]
    ITER --> FILTER{rejected?}
    FILTER -->|是| SKIP[跳过]
    FILTER -->|否| APPLY[apply_event]
    APPLY --> ITER
    ITER -->|完成| STATE[重建 PipelineState]
    STATE --> DIFF[与当前 state 对比]
    DIFF -->|一致| OK[✓ 一致]
    DIFF -->|不一致| ALERT[告警 STATE_DRIFT<br/>触发修复]

    style OK fill:#3fb950,color:#fff
    style ALERT fill:#b3261e,color:#fff
```

### 10.5 审计与合规

| 审计需求 | 实现 |
|---|---|
| 单节点完整生命周期 | `SELECT * FROM events WHERE node_id=$1 ORDER BY ts` |
| 单 PR 审核链 | `SELECT * FROM events WHERE payload->>'pr_id'=$1 ORDER BY ts` |
| 单 trace 全链路 | `SELECT * FROM events WHERE trace_id=$1 ORDER BY ts` |
| 状态漂移检测 | 定时任务:回放最近 N 个 pipeline 的 state,与 checkpointer 当前 state 比对,不一致告警 |
| 合规清理 | events 保留 ≥ 1 年(NFR9),超期归档冷存储,不删除 |
| 不可篡改 | events 表 append-only,应用层禁止 UPDATE/DELETE;DB 层用触发器拒绝修改 |

**state 漂移告警处理**:
- 漂移检测发现不一致 → 写 `STATE_DRIFT` event
- 自动用回放 state 覆盖 checkpointer state(以回放为准,因 events 是 source of truth)
- 同时告警 admin 排查 checkpointer 写入 bug

---

## 11. 验收扩展(补充 AC2.x)

> **编号说明**:主 PRD v3.0 §FR2.6 已有 AC2.1-AC2.22(含 draft/deprecated/addendum/topology 相关)。本节深化验收从 **AC2.24** 起,避免与主 PRD 编号冲突(对齐评审 P0-4 的 AC 编号去重原则)。

| 编号 | 验收项 | 验证方法 |
|---|---|---|
| AC2.24 | 非法状态转移被 Guard 拒绝(11 态全覆盖) | 单测覆盖 §2.2 全部 51 条非法转移防护表,断言返回 `INVALID_TRANSITION` |
| AC2.25 | 同节点并发状态变更串行化 | 50 并发对同 node_id 调 `submit_artifact`,断言只 1 成功,其余 `PR_ALREADY_PENDING` 或排队 |
| AC2.26 | 异节点并发真并行 | 50 agent 并发提交 50 不同 node_id,断言 P95 延迟 < 单节点 5x |
| AC2.27 | 同 commit 重提幂等 | 重复 `submit_artifact` 同 commit,断言返回首次 pr_id,不重复开 PR |
| AC2.28 | 节点崩溃后从 checkpoint 恢复 | kill 进程后重启,断言 state 从最后 checkpoint 恢复,in_flight 节点回退 |
| AC2.29 | DAG 有环被拒 | 构造环路 pipeline.yaml,断言加载失败 `CYCLE_DETECTED` |
| AC2.30 | gate 部分通过打回上游 | lint 过 test 失败,断言上游产物节点回 `in_progress`,event 含失败项 |
| AC2.31 | approval 超时自动 reject | 配置 `timeout_hours=1`,等待超时,断言自动 reject + 上游 changed |
| AC2.32 | fork 部分上游 changed 后 blocked | fork 上游之一 changed,断言 fork 回 `blocked` |
| AC2.33 | switch 路由字段缺失保持 blocked | 上游产物无路由字段,断言 switch 保持 `blocked` + `SWITCH_FIELD_MISSING` event |
| AC2.34 | notify 失败不阻塞管线 | 飞书 webhook 不可达,断言 notify 仍→done + DLQ 记录 |
| AC2.35 | 错误重试耗尽入 DLQ | 模拟 git merge 连续 3 次冲突,断言入 DLQ + 通知 admin |
| AC2.36 | 事件回放重建 state 一致 | 回放 events 重建 state,与 checkpointer state 比对一致 |
| AC2.37 | 热重载新增节点不影响已有 | 运行中 pipeline 添加新节点,断言旧节点状态不变,新节点 `blocked` |
| AC2.38 | recursion_limit 触发拆分重入 | 构造 200+ 节点管线,断言 recursion_limit 后拆分恢复继续 |
| AC2.39 | approval interrupt 暂停等人工 | invoke 到 approval 节点前自动暂停,断言 state `interrupted` |
| AC2.40 | **draft 态:soft_submit 后不触发 cascade** | 调 `soft_submit_artifact`,断言 `node_states[nid]==draft` + 下游未收到 `READY` event |
| AC2.41 | **draft 态:草案 push 通知订阅者** | draft 节点 feat 分支 push 新 commit,断言 `draft_subscribers` 中下游收到 `DRAFT_UPDATED` |
| AC2.42 | **draft 态:abandon 后回 ready** | 调 `abandon_draft`,断言 `node_states[nid]==ready` + `draft_refs[nid]` 清空 |
| AC2.43 | **draft 态:in_progress 不能直接 soft_submit** | in_progress 节点调 `soft_submit_artifact`,断言返回 `INVALID_TRANSITION` + `IN_PROGRESS_NO_DRAFT` |
| AC2.44 | **deprecated 态:仅 done 可进入** | 非 done 节点调 `mark_deprecated`,断言返回 `INVALID_TRANSITION` + `NOT_DONE` |
| AC2.45 | **deprecated 态:不可逆(不能回 done)** | deprecated 节点调 `submit_artifact`,断言返回 `INVALID_TRANSITION` + `DEPRECATED_IRREVERSIBLE` |
| AC2.46 | **sunset 态:终态不可转出** | sunset 节点调任意状态变更,断言返回 `INVALID_TRANSITION` + `SUNSET_TERMINAL` |
| AC2.47 | **sunset 态:下游强制 blocked** | 上游 sunset,断言下游 `node_states[ds]==blocked` + 事件流含 `INVALIDATED` |
| AC2.48 | **skipped 态:仅 optional 节点可 skip** | required 节点调 `skip_node`,断言返回 `INVALID_TRANSITION` + `REQUIRED_NOT_SKIPPABLE` |
| AC2.49 | **skipped 态:不阻塞 completed** | optional 节点 skipped + core 全 done,断言管线进 `completed` |
| AC2.50 | **skipped 态:可逆(S2 回 ready)** | skipped 节点调 `reactivate_node`,断言 `node_states[nid]==ready` + `REACTIVATED` event |
| AC2.51 | **外部 URL 失效触发 deprecated(D7)** | ExternalHealthMonitor 检测到 URL 不可达,断言 `node_states[nid]==deprecated` + `DEPRECATED` event |
| AC2.52 | **CVE 漏洞触发 deprecated(D9)** | 安全扫描命中 CVE,断言 `node_states[nid]==deprecated` + 触发 `handle_security_incident` |
| AC2.53 | **optional 依赖不参与 ready 判定** | 节点有 1 required(done)+ 1 optional(blocked),断言节点 `ready` |
| AC2.54 | **ParticipationProfile materialize 裁剪** | `server_only` profile,断言 design/client 节点被裁剪 + 无 dangling deps |
| AC2.55 | **跨管线 hub:// 环检测** | 构造 A.n1→B.n2→A.n1 跨管线环,断言注册时拒绝 `CYCLE_DETECTED` |
| AC2.56 | **管线 paused 时 cascade 挂起** | pause 管线后 done 节点 cascade,断言 `cascade_pending` 非空 + 下游未变 ready |
| AC2.57 | **管线 resume 应用挂起的 cascade** | resume 管线,断言 `cascade_pending` 清空 + 下游变 ready |
| AC2.58 | **管线 cancelled 后拒绝节点状态变更** | cancel 管线后调 `submit_artifact`,断言返回 `PIPELINE_CANCELLED` |

---

## 12. 与 PRD 主文档的对齐说明

| PRD v3.0 章节 | 本深化补充 | 一致性 |
|---|---|---|
| §FR2.1 状态机 **11 态** | §2.1 完整转移表 T1-T18 + D1-D10 + S1-S3 | ✅ v3.0 已对齐(7→11 态) |
| §FR2.2 DAG 规则 + DepDeclaration | §3 并发模型 + §7 加载校验 + §7.4 optional 依赖校验 | ✅ 补全并发与校验 |
| §FR2.2.1 ParticipationProfile | §7.3 materialize 规则 + ready 谓词 | ✅ v3.0 新增对齐 |
| §FR2.3 PipelineState(13 字段) | §3.1 Annotated 累积策略(15 字段扩展) | ✅ 对齐 + 扩展 node_versions/idempotency_seen |
| §FR2.4 StateGraph 节点(11 节点) | §9 编译配置 + Send API | ✅ 补全 fan-out 与 interrupt |
| §FR2.5 控制节点行为 | §8 边界条件完整表 | ✅ 补全边界 |
| §FR2.5.1 addendum 机制 | §14 addendum 级联机制 | ✅ v3.0 新增对齐 |
| §FR2.6 验收标准(AC2.1-AC2.22) | §11 AC2.24-AC2.58(深化编号从 AC2.24 起,避免冲突)+ §14 AC2.16-AC2.18(addendum) | ✅ 扩展 35 项 |
| §FR2.7 管线级生命周期 5 态 | §13 管线级生命周期转移表 | ✅ v3.0 新增对齐 |
| 附录 D11 P0-R5.17 skipped 态 | §2.1.4 skipped 转移表 S1-S3 | ✅ v3.0 新增对齐 |

**本深化 v3.0 已修复 S1(状态机三重不一致)**:7 态 → 11 态,与主 PRD v3.0 §FR2.1 + 附录 D11 完全对齐。所有扩展均为补全边界条件与配置细节。若实施中发现冲突,以主 PRD v3.0 为权威源。

---

## 13. 管线级生命周期(5 态)

> 对齐主 PRD v3.0 §FR2.7。管线级状态机与节点级状态机(11 态)正交:管线级状态控制节点级 dispatch 的开关,但不直接改变节点状态。

### 13.1 管线级 5 态定义

| 管线状态 | 含义 | 进入条件 | 退出条件 |
|---|---|---|---|
| `active` | 正常运行 | 管线启动(bootstrap) | paused / cancelled / completed / merged |
| `paused` | 暂停(ready 节点不再 dispatch,级联事件挂起) | `pause_pipeline` | `resume_pipeline` |
| `cancelled` | 取消(终态) | `cancel_pipeline` | —(终态) |
| `merged` | 已合并到其他管线(终态) | `merge_pipelines` | —(终态) |
| `completed` | 全节点 done(optional 节点可 skipped) | AC2.7 谓词满足 | —(终态) |

### 13.2 管线级转移表

| # | 源状态 | 目标状态 | 触发事件 | 前置 Guard | 副作用 | 备注 |
|---|---|---|---|---|---|---|
| P1 | `(初始)` | `active` | `bootstrap_node` 完成 | DAG 校验通过;ParticipationProfile 合法 | 写 `pipeline_status=active`,发 `PIPELINE_ACTIVE` event | 管线启动 |
| P2 | `active` | `paused` | `pause_pipeline` | 调用方为 admin | 写 `pipeline_status=paused`;ready 节点不再 dispatch;**级联事件写入 `cascade_pending`**;发 `PIPELINE_PAUSED` event | 暂停 |
| P3 | `paused` | `active` | `resume_pipeline` | 调用方为 admin | 写 `pipeline_status=active`;**逐条应用 `cascade_pending` 后清空**;校验依赖一致性;发 `PIPELINE_RESUMED` event | 恢复 |
| P4 | `active`/`paused` | `cancelled` | `cancel_pipeline` | 调用方为 admin | 写 `pipeline_status=cancelled`;释放所有 in_progress 锁;**已 done 产物标记 deprecated**(D5);in_progress/pending_review 节点保持原状态(不再 dispatch);发 `PIPELINE_CANCELLED` event | 终态 |
| P5 | `active` | `completed` | `skip_finalize_node` 后 core_nodes_done 谓词满足 | 所有 core 节点 done;optional 节点 done 或 skipped | 写 `pipeline_status=completed`;发 `PIPELINE_COMPLETED` event;**不再接受新的节点状态变更**(终态) | AC2.7 |
| P6 | `active` | `merged` | `merge_pipelines` | 调用方为 admin;目标管线存在 | 写 `pipeline_status=merged`;节点 ID 重映射到目标管线;产物归属迁移;发 `PIPELINE_MERGED` event | 终态 |

### 13.3 paused 与节点级状态的交互

> 对齐评审 P2-2.6。明确 paused 时各节点状态的行为。

| 节点状态 | paused 时的行为 | resume 时的行为 |
|---|---|---|
| `blocked` | 保持 blocked(无变化) | 重新评估 ready 谓词 |
| `ready` | **不再 dispatch**(CrewAI 不分配) | 恢复 dispatch |
| `in_progress` | agent 仍在执行 Task;完成后调 `submit_artifact` **被接受**(进 pending_review) | 无变化(已在 pending_review) |
| `pending_review` | PR 审核仍可进行;`approve_pr`/`reject_pr` **被接受** | 无变化 |
| `review` | approval 节点仍可 approve/reject | 无变化 |
| `done` | cascade 解锁下游 **挂起**(写入 `cascade_pending`) | 逐条应用挂起的 cascade |
| `changed` | invalidate 失效下游 **挂起**(写入 `cascade_pending`) | 逐条应用挂起的 invalidate |
| `draft` | 草案 push 通知 **挂起** | 逐条应用挂起的通知 |
| `deprecated`/`sunset`/`skipped` | 保持(无 dispatch) | 无变化 |

**paused/blocked 优先级**:节点同时处于 blocked(依赖未满足)和管线 paused 时,resume 管线后该节点**仍是 blocked**(需先满足依赖才能 ready)。paused 只挂起 dispatch 和 cascade,不改变 ready 谓词判定。

**cancelled 时节点终态处理**:
- `in_progress`/`pending_review`/`review` 节点:**保持原状态**(不再 dispatch),审计标记 `cancelled_at`
- `blocked`/`ready` 节点:保持原状态(不再 dispatch)
- `done` 节点:标记 deprecated(D5),防止被新管线依赖
- `draft` 节点:草案作废(D4),清 `draft_refs`
- `skipped`/`deprecated`/`sunset`:保持(已是终态/中间终态)
- cancelled 后**所有节点级状态变更被拒绝**(返回 `PIPELINE_CANCELLED` 错误)

### 13.4 管线级状态机(图 13-1)

```mermaid
stateDiagram-v2
    direction TB
    [*] --> active : P1 bootstrap
    active --> paused : P2 pause_pipeline\\n[guard: caller=admin]
    paused --> active : P3 resume_pipeline\\n[guard: caller=admin]\\n[副作用: 应用cascade_pending]
    active --> cancelled : P4 cancel_pipeline\\n[guard: caller=admin]\\n[副作用: done→deprecated]
    paused --> cancelled : P4 cancel_pipeline
    active --> completed : P5 core_nodes_done\\n[guard: core全done+optional done或skipped]
    active --> merged : P6 merge_pipelines\\n[guard: 目标管线存在]

    note right of paused
        paused 行为:
        - ready 不 dispatch
        - cascade/invalidate 挂起到 cascade_pending
        - in_progress/pending_review 可继续
        - approve_pr/reject_pr 被接受
    end note

    note right of cancelled
        cancelled 是终态:
        - 释放 in_progress 锁
        - done 产物 deprecated
        - 不再接受节点状态变更
    end note

    note right of completed
        completed 是终态:
        - core 节点全 done
        - optional 节点 done 或 skipped
        - 不再接受节点状态变更
    end note
```

### 13.5 管线级 MCP 工具

| 工具 | 调用方 | 作用 | 关键参数 |
|---|---|---|---|
| `pause_pipeline` | admin | 暂停管线,挂起 cascade | pipeline_id |
| `resume_pipeline` | admin | 恢复管线,应用挂起的 cascade | pipeline_id |
| `cancel_pipeline` | admin | 取消管线,释放锁,done→deprecated | pipeline_id, reason |
| `merge_pipelines` | admin | 合并管线,节点 ID 重映射 | source_pipeline_id, target_pipeline_id |
| `split_pipeline` | admin | 拆分管线,节点分配 | pipeline_id, node_groups |

---

## 14. addendum 级联机制

> 对齐主 PRD v3.0 §FR2.5.1。addendum 是 done 态上的"附加层",不改节点状态(done 保持 done),按 `cascade_level`(must/should/info)分级通知下游。

### 14.1 addendum 数据结构

```python
class Addendum(TypedDict):
    addendum_id: str               # 全局唯一,如 "login-feature.n2.add-001"
    node_id: str                   # 所属节点(必须处于 done)
    author: str                    # 添加者(current_owner 或 admin)
    content: str                   # 补充内容(自由格式,markdown/json 均可)
    content_integrity_hash: str    # sha256,防篡改
    cascade_level: str             # must | should | info
    incompatible_with: list[str]   # 声明与哪些下游版本不兼容(可选,用于 must 级判定)
    created_at: str
    provenance: Provenance         # 溯源(作者/时间/工具)
    reacks: dict[str, str]         # node_id -> ack_status(pending/accepted/rejected)
    deprecated_at: str | None      # ack 超时后下游 changed 时记录
```

**`ArtifactRef.addenda` 字段扩展**:`addenda: list[Addendum]`(append-only 补充列表,不改原产物内容/版本/provenance)。

### 14.2 addendum 级联策略(三级光谱)

| cascade_level | 对下游动作 | 下游是否改状态 | 下游是否需 ack | 超时处理 |
|---|---|---|---|---|
| `must` | 发 `ADDENDUM_MUST_ACK` 事件;下游在 `incompatible_with` 列表中则需主动 changed | **是**(下游若 incompatible 则 → changed;否则保持) | 是(7 天内) | 超时自动 → changed |
| `should` | 发 `ADDENDUM_SHOULD_ACK` 事件;下游 warning 通知 | 否(保持原状态) | 可选 | 超时仅告警 |
| `info` | 发 `ADDENDUM_INFO` 事件;仅记录 | 否 | 否 | — |

### 14.3 addendum 级联事件定义

| 事件类型 | 触发 | 接收方 | 接收方动作 |
|---|---|---|---|
| `ADDENDUM_MUST_ACK` | must 级 addendum 创建 | `incompatible_with` 中的下游 + 所有直接下游 | 7 天内调 `reack_addendum`;若 incompatible 则主动 changed(T10) |
| `ADDENDUM_SHOULD_ACK` | should 级 addendum 创建 | 所有直接下游 | 可选 ack;warning 通知 |
| `ADDENDUM_INFO` | info 级 addendum 创建 | 所有直接下游 | 仅记录,无需动作 |
| `ADDENDUM_TIMEOUT` | must 级 addendum 7 天未 ack | 下游 owner + admin | 下游自动 → changed(强制重新审核) |
| `ADDENDUM_ACKED` | 下游调 `reack_addendum` | addendum author | 记录 ack_status(accepted/rejected) |

### 14.4 addendum_cascade_node(StateGraph 节点)

> 对齐主 PRD v3.0 §FR2.4 StateGraph 节点表(行 709)。addendum 级联由独立 StateGraph 节点执行,与 cascade_node(解锁)/invalidate_node(失效)职责分离。

**节点职责:**
1. `add_addendum` 调用后,`addendum_cascade_node` 按 `cascade_level` 分发事件
2. must 级:检查下游 `incompatible_with` 列表,委托 `invalidate_node` 触发下游 → changed
3. should/info 级:仅发通知,不改状态
4. 定时扫描 must 级 addendum 超时(7 天),超时则委托 `invalidate_node` 触发下游 → changed

```python
async def addendum_cascade_node(state: PipelineState, addendum: Addendum) -> dict:
    """addendum 级联节点:按 cascade_level 分发。"""
    events = []
    node_id = addendum["node_id"]
    downstream_nodes = get_downstream_nodes(node_id, state)

    if addendum["cascade_level"] == "must":
        # must 级:incompatible_with 中的下游需 changed
        for ds_node_id in downstream_nodes:
            if ds_node_id in addendum["incompatible_with"]:
                # 委托 invalidate_node 触发 changed(复用现有失效逻辑)
                events.append({
                    "type": "ADDENDUM_MUST_ACK",
                    "node_id": ds_node_id,
                    "addendum_id": addendum["addendum_id"],
                    "action": "must_changed",
                    "deadline": addendum["created_at"] + timedelta(days=7),
                })
            else:
                events.append({
                    "type": "ADDENDUM_MUST_ACK",
                    "node_id": ds_node_id,
                    "addendum_id": addendum["addendum_id"],
                    "action": "ack_required",
                    "deadline": addendum["created_at"] + timedelta(days=7),
                })
    elif addendum["cascade_level"] == "should":
        for ds_node_id in downstream_nodes:
            events.append({
                "type": "ADDENDUM_SHOULD_ACK",
                "node_id": ds_node_id,
                "addendum_id": addendum["addendum_id"],
                "action": "ack_optional",
            })
    else:  # info
        for ds_node_id in downstream_nodes:
            events.append({
                "type": "ADDENDUM_INFO",
                "node_id": ds_node_id,
                "addendum_id": addendum["addendum_id"],
                "action": "record_only",
            })

    return {"events": events}


async def addendum_timeout_scan(state: PipelineState) -> dict:
    """定时任务:扫描 must 级 addendum 超时(7 天未 ack)。"""
    events = []
    for node_id, refs in state["artifact_refs"].items():
        for version, ref in refs.items():
            for addendum in ref.get("addenda", []):
                if addendum["cascade_level"] != "must":
                    continue
                if is_acked(addendum):
                    continue
                if now() - addendum["created_at"] < timedelta(days=7):
                    continue
                # 超时:下游自动 → changed
                for ds_node_id in get_downstream_nodes(node_id, state):
                    if ds_node_id in addendum.get("reacks", {}):
                        continue  # 已 ack
                    # 委托 invalidate_node
                    events.append({
                        "type": "ADDENDUM_TIMEOUT",
                        "node_id": ds_node_id,
                        "addendum_id": addendum["addendum_id"],
                        "action": "auto_changed",
                    })
    return {"events": events}
```

### 14.5 addendum vs changed 判定边界

> 对齐主 PRD v3.0 §FR2.5.1.2。提交方在重提 PR 时必须声明 `modification_type`,审核方校验一致性。

**判定矩阵**(审核方校验 `modification_type` 与实际改动一致性):

| 实际改动 | 提交方声明 | 审核方动作 |
|---|---|---|
| 只新增内容(不改原文件) | addendum | ✅ 通过 |
| 只新增内容(不改原文件) | changed | ⚠️ 告警:建议用 addendum,但允许(提交方可能需要版本 bump) |
| 修改原文件内容 | addendum | ❌ reject:内容已变,必须走 changed |
| 修改原文件内容 | changed | ✅ 通过,按 change_class 级联 |

**"只新增内容"的技术判定**(管理方可执行,不违反"不解析内容"):
- PR diff 中原文件行无删除/修改(纯新增行)
- 原产物文件的 `content_integrity_hash` 不变
- 新增内容在 `addenda/` 目录或原文件的 `---addendum---` 分隔符之后

**强制走 changed 的场景**(即使提交方声明 addendum):
- 修改了产物文件的 `version` 字段
- 修改了 `deps` 声明
- 修改了 `artifact_kind` / `artifact_qualifier` / `classification`
- 删除了原产物文件的部分内容

### 14.6 addendum 与节点状态的交互

> 对齐主 PRD v3.0 §FR2.5.1.4。addendum 不改节点状态(done 保持 done),但 must 级 addendum 可能触发下游 changed。

| 下游状态 | 上游 addendum(must) | 上游 addendum(should) | 上游 addendum(info) |
|---|---|---|---|
| `in_progress` | 发 ADDENDUM_MUST_ACK,7 天内 ack;若 incompatible 则 blocked | 通知,不改状态 | 通知,不改状态 |
| `draft` | 发 ADDENDUM_MUST_ACK;若 incompatible 则 blocked(草案作废) | 通知,不改状态 | 通知,不改状态 |
| `pending_review` | 发 ADDENDUM_MUST_ACK;若 incompatible 则 PR 自动 reject → ready | 通知,不改状态 | 通知,不改状态 |
| `ready` | 发 ADDENDUM_MUST_ACK;若 incompatible 则 blocked | 通知,不改状态 | 通知,不改状态 |
| `done` | 发 ADDENDUM_MUST_ACK;若 incompatible 则 → changed(T10);超时 → changed | 通知,不改状态 | 通知,不改状态 |
| `blocked`/`changed`/`review` | 发 ADDENDUM_MUST_ACK(等待状态恢复后处理) | 通知 | 通知 |
| `deprecated`/`sunset`/`skipped` | 不发(终态/废弃节点不接收 addendum) | 不发 | 不发 |

### 14.7 addendum 审核规则

| 规则 | 校验内容 | priority | on_fail |
|---|---|---|---|
| `R_ADDENDUM_FORMAT` | addendum content 非空 + content_integrity_hash 计算 | 80 | reject |
| `R_ADDENDUM_AUTH` | author 必须是 current_owner 或 admin | 90 | reject |
| `R_ADDENDUM_INCOMPATIBLE_VALIDITY` | `cascade_level=must` 时 `incompatible_with` 中的 node_id 必须是本节点的直接下游 | 75 | reject |

### 14.8 addendum 验收标准(对齐 AC2.16-AC2.18)

| 编号 | 验收项 | 验证方法 |
|---|---|---|
| AC2.16 | `add_addendum` 后节点状态保持 done,`addenda` 列表新增一项 | 调用 `add_addendum`,断言 `node_states[nid]==done` 且 `artifact_refs[nid][ver].addenda` 长度 +1 |
| AC2.17 | `cascade_level=must` 的 addendum 发出后,`incompatible_with` 中的下游收到 `ADDENDUM_MUST_ACK` 事件 | 调用 `add_addendum(must, incompatible_with=[ds])`,断言下游事件流含 `ADDENDUM_MUST_ACK` |
| AC2.18 | `must` 级 addendum 超时 7 天未 ack,下游自动 → changed | 配置超时 7 天,等待超时,断言下游 `node_states[ds]==changed` + 事件流含 `ADDENDUM_TIMEOUT` |

### 14.9 addendum MCP 工具

| 工具 | 调用方 | 作用 | 关键参数 |
|---|---|---|---|
| `add_addendum` | current_owner / admin | 给 done 产物附加补充 | node_id, content, cascade_level, incompatible_with |
| `reack_addendum` | 下游 node 的 owner | 确认/拒绝 addendum | addendum_id, ack_status(accepted/rejected), note |
| `list_addenda` | 任意角色 | 查询节点的所有 addendum | node_id |

---

## 附录 A:Postgres 完整 DDL 汇总

```sql
-- LangGraph 内置表由 AsyncPostgresSaver.setup() 创建,此处省略

-- 平台扩展表
CREATE TABLE idempotency_keys (
    key TEXT PRIMARY KEY,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_idem_expires ON idempotency_keys(expires_at);

CREATE TABLE node_path_registry (
    pipeline_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    commit TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pipeline_id, node_id),
    UNIQUE (pipeline_id, artifact_path)
);

CREATE TABLE dlq (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pipeline_id TEXT NOT NULL,
    node_id TEXT,
    operation TEXT NOT NULL,
    payload JSONB NOT NULL,
    last_error TEXT NOT NULL,
    attempts INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_note TEXT
);
CREATE INDEX idx_dlq_status_pipeline ON dlq(status, pipeline_id);

CREATE TABLE audit_log (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    pr_id BIGINT,
    node_id TEXT,
    node_type TEXT,
    artifact_path TEXT,
    merge_commit TEXT,
    reviewer TEXT,
    submitter TEXT,
    skill_used TEXT,
    skill_verdict TEXT,
    deps_at_review JSONB,
    note TEXT,
    trace_id TEXT,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_node ON audit_log(node_id, ts);
CREATE INDEX idx_audit_reviewer ON audit_log(reviewer, ts);
CREATE INDEX idx_audit_action ON audit_log(action, ts);

CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    pipeline_id TEXT NOT NULL,
    node_id TEXT,
    type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    actor TEXT,
    trace_id TEXT,
    payload JSONB,
    rejected BOOLEAN NOT NULL DEFAULT false,
    idempotency_key TEXT,
    version INT
);
CREATE INDEX idx_events_pipeline_ts ON events(pipeline_id, ts);
CREATE INDEX idx_events_node ON events(node_id, ts);
CREATE INDEX idx_events_trace ON events(trace_id);

CREATE TABLE pipeline_registry (
    pipeline_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    yaml_hash TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    active BOOLEAN NOT NULL DEFAULT true
);

-- 防篡改触发器:events/audit_log 禁止 UPDATE/DELETE
CREATE OR REPLACE FUNCTION reject_modify() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'append-only table, modification rejected';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER no_update_events BEFORE UPDATE ON events
  FOR EACH ROW EXECUTE FUNCTION reject_modify();
CREATE TRIGGER no_delete_events BEFORE DELETE ON events
  FOR EACH ROW EXECUTE FUNCTION reject_modify();
CREATE TRIGGER no_update_audit BEFORE UPDATE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION reject_modify();
CREATE TRIGGER no_delete_audit BEFORE DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION reject_modify();
```

---

## 附录 B:关键参数默认值

| 参数 | 默认值 | 环境变量 |
|---|---|---|
| `recursion_limit` | 200 | `LG_RECURSION_LIMIT` |
| advisory lock 超时 | 30s | `LG_LOCK_TIMEOUT_MS` |
| `submit_artifact` 重试 | 3 次,base 1s,max 10s | `LG_SUBMIT_RETRY_*` |
| `approve_pr` 重试 | 3 次,base 2s,max 30s | `LG_APPROVE_RETRY_*` |
| checkpointer 重试 | 5 次,base 0.5s,max 5s | `LG_CKPT_RETRY_*` |
| approval 默认超时 | 24h | `APPROVAL_TIMEOUT_HOURS` |
| 幂等键 TTL | 7 天 | `IDEM_KEY_TTL_DAYS` |
| events 保留 | 365 天 | `EVENTS_RETENTION_DAYS` |
| DLQ 重放上限 | 3 次 | `DLQ_REPLAY_MAX` |
| DLQ abandoned 阈值 | 3 次失败 | `DLQ_ABANDON_THRESHOLD` |

---

**深化结束。** 本文档 v3.0 覆盖 FR2 的 11 个薄弱点(含 v3.0 新增管线级生命周期 + addendum 级联),与主 PRD v3.0 §FR2.1-§FR2.7 完全对齐(11 态状态机 + T1-T18 + D1-D10 + S1-S3 转移表 + 51 条非法转移防护),提供可实施的代码示例、完整状态转移表、并发与错误恢复策略、Postgres schema、控制节点边界条件、ParticipationProfile materialize、optional 依赖校验、管线级 5 态生命周期、addendum 级联机制,以及 7 张 Mermaid 设计图。
