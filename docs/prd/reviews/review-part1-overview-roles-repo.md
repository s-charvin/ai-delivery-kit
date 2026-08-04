# PRD 内容审核报告 Part 1:产品概述 / 角色权限 / 产物仓库

> **审核范围**:§1-§3 + §FR1(主 PRD 第 1-357 行)+ 深化文档 fr1-fr6 §1-§3(仓库结构 / manifest schema / 审核规则)
> **审核维度**:内容缺失 / 边界模糊 / 细节不足 / 规则冲突
> **日期**:2026-08-04
> **审核基线**:主 PRD v3.1 + 深化文档 v1.0

---

## 1. 审核汇总

| 维度 | 发现数 |
|---|---|
| 内容缺失 | 16 |
| 边界模糊 | 10 |
| 细节不足 | 14 |
| 规则冲突或矛盾 | 16 |
| **合计** | **56** |

**P0 级(不修复将导致开发受阻或开发者随意猜测)**:**13 项**

**最关键认知**:深化文档 fr1-fr6 §3 的 manifest JSON Schema 与主 PRD §FR1.1/§FR1.3 在文件格式(yaml vs json)、node_id 模式、node_type 枚举数量、role 枚举、路径模式、依赖字段、必填字段上存在 **9 处硬冲突**,若直接按深化文档实现将导致 CI 全量误拦或全量放过。同时 §2.1 节点类型清单与附录 D11 的 P0 修正项(client_logic/server_delivery/research_spike/free_artifact)未回写,开发者无法判断清单是否封闭。

---

## 2. 详细发现

### 2.1 内容缺失

| # | 位置 | 缺失内容 | 影响 | 建议补充 |
|---|---|---|---|---|
| G1.1 | §1.4 范围边界(L65-72) | 未声明平台自身的部署、运维、账号体系边界(谁来部署管理方进程?谁来给 admin 开账号?) | 开发者不知账号体系是否本期实现,可能漏掉鉴权模块 | 增加"平台自身运维(部署/账号/升级)由 SRE 人工执行,本期不含平台自助管理" |
| G1.2 | §2 术语表(L78-100) | `SkillRegistry` 未定义,仅在 §2.1 注释中提到"SkillRegistry 按三级匹配" | 实现时不知 SkillRegistry 是文件系统扫描还是独立服务,影响启动流程 | 补充术语:"SkillRegistry:节点 ready 时加载 skills/ 目录的约束技能注册表,启动时扫描 + 热重载" |
| G1.3 | §2 术语表(L94) | `classification` 4 级(public/internal/confidential/restricted)只列名字,无判定标准 | 提交方不知该选哪级,审核方无依据驳回 | 补充每级定义:public=可对外公开 / internal=组织内可见 / confidential=仅项目组可见 / restricted=需逐项授权 |
| G1.4 | §2 术语表(L98) | `presence: if_present` 仅说"节点存在时才成为硬依赖",未说"节点存在"由什么判定 | materialize 规则无法实现,开发者需猜测判定源 | 明确:"if_present 由 ParticipationProfile.roles_present 与管线节点清单共同判定,节点被裁剪则该 dep 不生效" |
| G1.5 | §2.1(L104-119) | 附录 D4 P0-13 与 D11 P0-R5.2/R5.3/R5.6 提到 `free_artifact`/`client_logic`/`server_delivery`/`research_spike` 节点类型,但 §2.1 清单未列入 | 开发者不知这些类型是否本期实现,skill 目录也不知是否要建 | 在 §2.1 明确:"本期预置 10 种,D11 扩展类型(client_logic/server_delivery/research_spike/free_artifact)列入 Phase 2"或直接补入清单 |
| G1.6 | §3.1(L147-154) | RoleInstance 的创建、销毁、转移流程未定义 | 不知由谁创建实例、配置变更如何生效、实例废弃如何清理 | 补充:RoleInstance 由 admin 通过 `register_role_instance` / `update_role_instance` / `decommission_role_instance` 管理,配置存 Postgres |
| G1.7 | §3.1(L144-145) | reviewer 与 admin 角色的指派流程缺失(谁任命 reviewer?admin 是单人还是岗位?) | 无法实现权限初始化,可能写成单例 admin | 明确:reviewer 由 admin 通过 `assign_reviewer` 指派;admin 是岗位非单人,可多实例 |
| G1.8 | §3.1(L151-154) | Token 签发流程不完整:`bot_token`/`human_submit_token`/`admin_token` 的签发方、有效期、撤销条件未定义 | 无法实现 token 鉴权,开发者会自造流程 | 补充:bot_token 由管理方启动时从 Vault 加载;human_submit_token 由 admin 签发,默认 24h;admin_token 由 Vault 托管 |
| G1.9 | §FR1.1(L210, L228) | `GitProvider` 抽象只在 HubRepoConfig 出现 `provider: gitlab`,无接口契约 | 开发者不知要实现哪些方法,可能漏掉 webhook/分支保护 API | 补充 GitProvider 接口:`create_branch`/`open_pr`/`merge_pr`/`get_pr_files`/`setup_branch_protection`/`register_webhook`/`ls_remote` 共 7 方法 |
| G1.10 | §FR1.1(L246-249) | `emergency_local_commit` / `sync_pending_artifacts` / `emergency_approve` 三个降级操作只有一句话描述,无流程 | AC1.8/1.9 可测但实现路径不明,开发者会猜测存储位置与冲突处理 | 补充:本地暂存路径 `~/.coord-platform/pending/{pipeline_id}/`,含 manifest + content + 决策记录;恢复后按时间序补提,seq 冲突时 bot 重命名 |
| G1.11 | §FR1.1(L232) | `clone_strategy` 4 个取值(full/partial/shallow/on_demand)语义未定义 | 开发者不知选哪个,可能默认 full 导致大仓库性能问题 | 补充:full=完整 clone / partial=仅 features/ 目录 / shallow=--depth=1 / on_demand=按需 git show |
| G1.12 | §FR1.1(L233-235) | LFS 不可用时(自托管 GitLab 未启用 LFS)的降级策略缺失 | >10MB 文件提交会失败,管线阻塞 | 补充:LFS 不可用时,>10MB 文件 reject 并提示"LFS 未启用,请拆分或启用 LFS";不静默放行 |
| G1.13 | §FR1.1(L236-238) | `capacity.max_prs_per_hour: 50` / `max_concurrent_reviews: 10` 超限后的处理策略缺失 | 超限时不知是排队、reject 还是告警 | 补充:超限时 PR 进入 `queued` 状态,等待槽位释放;不 reject |
| G1.14 | §FR1.3(L275-338) | PR 模板字段无必填/可选标注 | CI 校验规则无法确定,AC1.3"字段缺失时报错"无明确字段清单 | 在模板中用注释标注 `# required` / `# optional`,并列出 CI 强制校验字段表 |
| G1.15 | §3.2 权限矩阵(L158-166) | 权限矩阵列出 6 个角色(product/server/design/client/reviewer/admin),**缺 generator 行** | generator 角色的权限(能否 update_progress?能否 get_dependencies?)无定义,实现时会被随意赋予 | 补充 generator 行:submit_artifact(仅 derived_artifact)✅ / update_progress ✅ / get_dependencies ✅ / request_approval ❌ / approve ❌ / set_gate ❌ / audit ❌ |
| G1.16 | §FR1.1(L213) | `config/hub-repo.yaml` 是 HubRepoConfig 唯一配置,但未说明由谁加载、何时校验、配置错误时行为 | 启动失败原因不明,可能静默用错配置 | 补充:管理方启动时加载 + JSON Schema 校验,失败则拒绝启动并告警 |

### 2.2 边界模糊

| # | 位置 | 模糊点 | 影响 | 建议明确 |
|---|---|---|---|---|
| B1.1 | §1.2(L48-54) | "管理层"与"执行层"的职责边界只说"不干预开发执行",未说清"提交协调"算管理还是执行 | Agent 调 submit_artifact 是管理层动作还是执行层动作?审核失败时谁负责修复? | 明确:管理层=状态机+审核+级联;执行层=产物内容生成+代码开发;Agent 是执行层的"提交协调员",不是管理层 |
| B1.2 | §1.4(L70) | "不校验产物内容格式(YAML/JSON/Figma 均可)" vs §FR5.2 `completeness_contract` 用 jsonpath 校验结构 | 开发者不知"结构校验"算不算"内容校验",实现时会自相矛盾 | 明确边界:"不解析业务语义"≠"不校验结构"——completeness_contract 校验的是"管理约束"(字段存在性/min_items),不是"业务正确性" |
| B1.3 | §1.4(L67-72) | "产物内容"与"产物元数据"的边界未定义 | manifest 是内容还是元数据?completeness_contract 算内容还是元数据? | 明确:元数据=manifest 字段(node_id/version/deps/classification 等);内容=产物文件本身;completeness_contract 是"元数据约束"非"内容约束" |
| B1.4 | §2.1(L104-106) | 节点类型清单说"10 种,可扩展"且"采用 {role}.{name} 开放命名空间",但表格用扁平名 `product_spec` | 开发者不知提交 `product.spec` 还是 `product_spec`,SkillRegistry 匹配规则不明 | 明确:预置类型用扁平名(`product_spec`),扩展类型用 `{role}.{name}`(如 `client.custom_logic`);SkillRegistry 先匹配扁平名再匹配角色前缀 |
| B1.5 | §3.1(L145) | admin 是单一角色实例还是可多实例?RoleInstance 定义只列 5 个角色(product/server/design/client/generator),不含 admin/reviewer | admin/reviewer 的实例化模型不清,可能被实现成单例 | 明确:admin 与 reviewer 是平台级角色(非 RoleInstance),由 admin 岗位人员持有;RoleInstance 仅针对 5 个开发角色 |
| B1.6 | §3.2(L176) | L3 `external_repo` 校验"仅引用型产物",但内容型产物是否完全跳过 L3? | 内容型产物的权限校验弱于引用型,可能存在越权 | 明确:L3 仅对 `artifact_kind=reference` 生效;内容型产物通过 L1+L2+classification 校验 |
| B1.7 | §FR1.1(L193-214) | 单一 hub 仓的容量边界与性能边界未声明 | 不知支持多少管线、多少产物、多大仓库后需分仓 | 补充 NFR:单 hub 仓支持 ≤500 管线 / ≤10k 产物文件 / 仓库体积 ≤5GB(含 LFS);超限时告警并规划分仓(v3) |
| B1.8 | §FR1.2(L257) | "main 禁止直接 push"与 `emergency_local_commit` 的关系:emergency 暂存后如何进 main? | 开发者不知 emergency 数据是否绕过分支保护,可能强行 push main | 明确:emergency 数据在 `sync_pending_artifacts` 时走正常 PR 流程(快速审核通道),不绕过 main 保护;仅 `emergency_approve` 在本地记录,恢复后回填审计 |
| B1.9 | §FR1.3(L315-316) | `consumers.on_failure: alert` 仅列一个值,但 §FR2.5(L720)说有 `ignore`/`mark_changed`/`alert` 三值 | 模板与规则文档不一致,开发者会漏实现 | 在 PR 模板注释列出完整枚举:`on_failure: ignore | mark_changed | alert` |
| B1.10 | §FR1/§FR6 | "审核"的边界:审什么不审什么未集中声明 | 开发者可能把"代码质量审核"也塞进管理方 | 集中声明:管理方审=元数据完整性+依赖状态+文件格式+安全扫描+密级+结构化完整性;不审=业务正确性+代码质量+设计美观 |

### 2.3 细节不足

| # | 位置 | 不足点 | 影响 | 建议细化 |
|---|---|---|---|---|
| D1.1 | §FR1.2(L263-269) | 四维分支命名 `feat/{pipeline_id}/{instance_id}/{node_type}-{seq}` 无完整 regex | CI 校验规则无法实现,AC1.5"命名符合四维规范"不可测 | 给出 regex:`^feat/[a-z0-9-]+/[a-z0-9_]+/[a-z_]+-[0-9]{3}$` |
| D1.2 | §FR1.1(L225-244) | HubRepoConfig 每个字段的取值范围与默认值未标注 | 配置错误时行为不可预期 | 为每个字段标注类型/枚举/默认值,如 `clone_strategy: enum[full,partial,shallow,on_demand] default=partial` |
| D1.3 | §FR1.1(L221) vs 深化 §3.2 | 主 PRD 说"每个管线目录下必须包含 `.manifest.yaml`",深化文档 §3.2 说"每个产物附 `.manifest.json`"——两处 manifest 格式与位置不同 | 开发者不知实现哪种,CI 校验对象不明 | 统一为:管线级 `.manifest.yaml`(管线产物索引)+ 产物级 `<file>.manifest.json`(单产物元数据),两者职责不同 |
| D1.4 | §FR1.1(L246-249) | `emergency_local_commit` / `sync_pending_artifacts` / `emergency_approve` 无时序图与数据结构 | AC1.8/1.9 可测但实现细节全靠猜 | 补充:本地暂存数据结构 + 恢复时序图 + 冲突处理(seq 重复、依赖已变更) |
| D1.5 | §FR1.3(L275-338) | PR 模板各字段无格式校验规则(version_constraint 格式、hub_ref 协议格式、jsonpath 语法) | CI 无法校验格式合法性,错误格式可能通过 | 补充每字段 regex/格式:`version_constraint: semver range(>=1.0.0 <2.0.0)` / `hub_ref: ^hub://[a-z0-9-]+/[a-z0-9._]+@[\^~]?[0-9.]+$` |
| D1.6 | §3.2(L170-178) | 权限三层校验(L1/L2/L3)的执行顺序未明确(串行短路?并行?) | 实现可能并行导致错误信息混乱,或串行但顺序错 | 明确:L1→L2→L3 串行,任一失败立即 reject 并返回该层错误;不并行 |
| D1.7 | §3.1(L149) | RoleInstance 的 `agent_config` 字段是 dict,但具体结构未定义(LLM 配置/backstory/max_concurrent 各字段) | 开发者会自造结构,跨实例不兼容 | 给出 agent_config 子结构:`{llm_model, llm_temperature, backstory, max_concurrent, max_retries}` |
| D1.8 | §2.1(L104-129) | 节点类型"开放命名空间 {role}.{name}"的具体规则未细化(命名约束、注册流程、与 SkillRegistry 的关系) | 扩展节点类型时命名混乱,skill 匹配失败 | 补充:{role}.{name} 中 role 必须是 5 个开发角色之一,name 为 `[a-z][a-z0-9_]*`;扩展类型必须在 skills/ 下建对应 skill.yaml |
| D1.9 | §FR1.1(L210) | `GitProvider` 抽象的接口契约(方法签名、参数、返回值、异常)未定义 | 多托管适配无法实现,可能写成 GitLab 专用 | 补充 GitProvider Protocol:`create_branch(repo, branch, from_commit) -> bool` 等 7 方法签名 |
| D1.10 | §FR1.3(L298) | `hub_ref: "hub://{pipeline_id}/{node_id}@{version}"` 协议完整规范未定义(version 是 semver range 还是固定版本?跨管线引用的权限校验?) | 跨管线引用实现不规范,可能漏权限校验 | 明确:hub_ref 中 version 支持 semver range;跨管线引用需 CrossPipelineReferenceRegistry 注册 + 目标管线 admin 授权 |
| D1.11 | §FR1.3(L295) | `version_constraint: ">=1.0.0 <2.0.0"` 格式未规范(空格分隔?逗号?npm 风格?) | CI 校验不一致,合法格式被拒 | 明确:采用 npm semver range 语法,空格分隔多个约束 |
| D1.12 | §FR1.4(L348) | AC1.5 "feat 分支命名符合四维规范,冲突概率可控"中"冲突概率可控"不可测 | 验收时无法判定是否通过 | 改为可测:"feat 分支命名匹配 regex,1000 次并发提交冲突率 < 1%" |
| D1.13 | §FR1.1(L231) | `branch_naming` 模板字符串 `feat/{pipeline_id}/{instance_id}/{node_type}-{seq}` 中 seq 的位数未固定 | seq 可能是 1 或 001,分支名不统一 | 明确:seq 为 3 位零填充(`001`),与产物文件名 seq 一致 |
| D1.14 | §3.2(L178) | `get_dependencies` 的 clearance 过滤:返回内容时是整条拒绝还是脱敏?拒绝时返回什么? | 实现可能泄露元数据(返回 path 但不返回 content) | 明确:clearance 不足时整条拒绝,返回 `{error: "clearance_insufficient", required: "confidential", actual: "internal"}`,不返回 path/content |

### 2.4 规则冲突或矛盾

| # | 位置1 | 位置2 | 冲突描述 | 建议修正 |
|---|---|---|---|---|
| C1.1 | §1.4(L70)"不校验产物内容格式" | §FR5.2(L1012-1018) `completeness_contract` 用 jsonpath 校验结构 | "不校验内容"与"jsonpath 校验结构"表面矛盾 | 修正 §1.4 表述为:"不校验产物业务语义,但校验管理约束(元数据完整性 + 结构化完整性契约 + 安全扫描)" |
| C1.2 | §2 术语(L87)"节点级 10 态状态机" | 附录 D11 P0-R5.17(L2128)"10 态 → 11 态(新增 skipped)" | 状态机态数不一致,开发者不知实现 10 还是 11 态 | 修正 §2 为 11 态,补 `skipped` 定义;或明确 skipped 在 Phase 2 |
| C1.3 | §2.1(L104)"产物节点 10 种" | 深化 §2.1.1(L88)"9 种产物节点类型各一目录" + CI-1(L1134)"9 种产物类型" | 主 PRD 10 种 vs 深化 9 种,CI 白名单不一致 | 统一为 10 种(含 derived_artifact),修正深化 §2.1.1 与 CI-1 |
| C1.4 | §2.1(L104-119) 节点类型清单 | 附录 D11 P0-R5.2/R5.3/R5.6 新增 `client_logic`/`server_delivery`/`research_spike` | D11 P0 修正项未回写 §2.1,开发者不知是否实现 | 在 §2.1 明确标注:"本期 10 种;D11 扩展类型 Phase 2 落地" |
| C1.5 | §3.1(L137-145) 角色定义含 7 角色(含 generator) | §3.2(L158-166) 权限矩阵仅 6 角色(无 generator) | generator 权限未定义,实现时可能漏掉或随意赋权 | 补充 generator 行(见 G1.15) |
| C1.6 | §FR1.1(L208, L221)"`.manifest.yaml`" | 深化 §3.2(L254-260)"`<file>.manifest.json`" | manifest 格式(yaml vs json)与位置(管线级 vs 产物级)冲突 | 明确两者职责不同:管线级 `.manifest.yaml`(索引)+ 产物级 `.manifest.json`(单产物元数据),深化 §3 校验产物级 |
| C1.7 | §FR1.1(L217)"路径 `features/{pipeline_id}/{node_type}/{artifact_qualifier}/{seq}_{slug}.{ext}`" | 深化 §2.1.2(L113)"`<node_type>/001_<slug>.<ext>`" + §3.3 source.path pattern `^[a-z_]+/[0-9]{3}[_a-z0-9-]*\.(yaml\|yml\|json\|md\|mdx)$` | 主 PRD 路径含 `features/{pipeline_id}/` 和 `{qualifier}/`,深化路径与 regex 不含 | 修正深化 §3.3 source.path pattern 为 `^features/[a-z0-9-]+/[a-z_]+/(official\|mock\|draft\|experimental)/[0-9]{3}[_a-z0-9-]*\.(yaml\|yml\|json\|md\|mdx)$` |
| C1.8 | §FR1.2(L261)"四维 `feat/{pipeline_id}/{instance_id}/{node_type}-{seq}`" | 深化 §2.1.3(L127)"`feat/{role}/{node_type}-{seq}-{short-uuid}`" | 分支命名维度不同(4 维 vs 3 维+uuid),CI 校验规则冲突 | 统一为四维 + 可选 uuid:`feat/{pipeline_id}/{instance_id}/{node_type}-{seq}[-{uuid8}]`,修正深化 §2.1.3 |
| C1.9 | 主 PRD §5.1(L1311)"节点 ID `{pipeline_id}.{local_id}` 如 `login-feature.n2`" | 深化 §3.3(L296) manifest schema `node_id` pattern `^n[0-9]+$` | node_id 模式冲突:主 PRD 含 pipeline_id 前缀,深化不含 | 修正深化 §3.3 pattern 为 `^[a-z0-9-]+\.n[0-9]+$` |
| C1.10 | §2.1(L104-119) 产物节点 10 种(含 `derived_artifact`) | 深化 §3.3(L302-312) `node_type` enum 仅 9 种(缺 `derived_artifact`) | manifest schema enum 缺 derived_artifact,该类型产物会被 CI 拒绝 | 补充深化 §3.3 enum 增加 `"derived_artifact"` |
| C1.11 | §3.1(L137-145) 角色 7 种(含 generator/reviewer/admin) | 深化 §3.3(L317) `role` enum 仅 `["product","server","design","client"]` | manifest role enum 缺 generator/reviewer/admin,generator 产物的 manifest 无法通过 schema 校验 | 补充 enum 增加 `"generator"`;reviewer/admin 不产出物无需加入 |
| C1.12 | §FR1.3(L289) PR 模板含 `classification` 字段 | 深化 §3.3 manifest schema `required` 与 `properties` 无 `classification` | manifest schema 缺 classification 字段,但主 PRD 要求必填 | 补充深化 §3.3 schema 增加 `classification` 字段(enum 4 值,required) |
| C1.13 | §FR1.3(L286-287) PR 模板含 `artifact_kind`/`artifact_qualifier` | 深化 §3.3 manifest schema 无这两个字段 | manifest schema 缺关键字段,CI 无法校验产物类型与完成度 | 补充深化 §3.3 schema 增加 `artifact_kind`/`artifact_qualifier` 字段(required) |
| C1.14 | §FR1.3(L301-316) PR 模板含 `external_resources`/`third_party_apis`/`consumers`/`completeness_contract`/`modification` | 深化 §3.3 manifest schema 无这些字段 | manifest schema 与 PR 模板严重不同步,大量字段无法校验 | 补充深化 §3.3 schema 或声明这些字段为 PR 模板字段(不进 manifest) |
| C1.15 | §FR2.2(L437-445) DepDeclaration 含 `hub_ref`/`version_constraint`/`format_slot`/`strictness`/`presence`/`coupling` | 深化 §3.3(L385-408) deps schema 仅 `node_id`/`node_type`/`min_version`/`artifact_path` | manifest deps schema 严重缺失第五轮扩展字段,依赖校验无法实现 | 补充深化 §3.3 deps schema 增加全部 DepDeclaration 字段 |
| C1.16 | §FR1.2(L257)"main 禁止直接 push" | §FR1.1(L246-249) `emergency_local_commit` 暂存后需合并到 main | 表面冲突:emergency 数据如何进 main? | 明确:emergency 数据不直接 push main;恢复后走 `sync_pending_artifacts` → 正常 PR → 快速审核 → squash merge |

---

## 3. 优先级排序(P0/P1/P2)

### P0 级(不修复将导致开发受阻或开发者随意猜测)— 13 项

| 编号 | 发现 | 理由 |
|---|---|---|
| C1.6 | manifest 格式 yaml vs json 冲突 | 开发者不知实现哪种,CI 校验对象不明,直接阻断 Phase 1 |
| C1.7 | 路径模式冲突(含 qualifier vs 不含) | CI regex 与主 PRD 路径不匹配,所有 PR 会被 CI 误拦 |
| C1.9 | node_id 模式冲突(含 pipeline_id 前缀 vs 不含) | manifest schema 会拒绝所有合规 node_id |
| C1.10 | manifest node_type enum 缺 derived_artifact | generator 产物无法通过 CI |
| C1.11 | manifest role enum 缺 generator | generator 产物 manifest 无法通过 schema |
| C1.12 | manifest schema 缺 classification | 主 PRD 必填但 schema 无,CI 无法校验 |
| C1.13 | manifest schema 缺 artifact_kind/qualifier | 产物类型与完成度无法校验 |
| C1.15 | manifest deps schema 缺第五轮字段 | 依赖校验(format_slot/strictness/presence/coupling)无法实现 |
| C1.3 | 节点类型 10 种 vs 9 种冲突 | CI 白名单不一致,derived_artifact 目录被拒 |
| C1.5 | 权限矩阵缺 generator 行 | generator 权限未定义,实现时随意赋权 |
| G1.10 | emergency 降级流程无细节 | AC1.8/1.9 可测但实现路径不明 |
| D1.1 | 分支命名无完整 regex | AC1.5 不可测,CI 校验规则无法实现 |
| G1.9 | GitProvider 接口契约缺失 | 多托管适配无法实现,可能写成 GitLab 专用 |

### P1 级(影响实现质量,但不直接阻断)— 18 项

C1.1, C1.2, C1.4, C1.8, C1.14, C1.16, G1.3, G1.5, G1.6, G1.8, G1.11, G1.12, G1.13, G1.15, B1.2, B1.4, D1.3, D1.6, D1.7, D1.9, D1.14

### P2 级(可在 Phase 2/3 补全)— 25 项

其余 G1.1/G1.2/G1.4/G1.7/G1.14/G1.16, B1.1/B1.3/B1.5/B1.6/B1.7/B1.8/B1.9/B1.10, D1.2/D1.4/D1.5/D1.8/D1.10/D1.11/D1.12/D1.13

---

## 4. 建议的补充内容(可直接粘贴到 PRD)

### 4.1 §1.4 范围边界修正(修正 C1.1)

```markdown
| 做什么(范围内) | 不做什么(范围外) |
|---|---|
| 产物仓库的分支保护 + PR 审核 | 不限制开发方用什么工具产出内容 |
| 状态机 + 依赖 DAG 编排 | 不执行代码开发(无执行层) |
| MCP 工具接口(submit/review/approve) | 不生成代码、不生成设计稿 |
| Constraint Skills 元数据约束 + 结构化完整性契约(管理约束,非业务校验) | 不校验产物业务语义(YAML/JSON/Figma 业务正确性均不审) |
| Langfuse 监控 + 可视化 Dashboard | 不做多租户/RBAC(v3 规划) |
| 变更级联(下游自动 blocked) | 成本硬预算本期落地;配额管理 v3 规划;密钥管理本期落地(NFR18) |
```

> **关键边界声明**:管理方校验"管理约束"(元数据完整性、文件格式、结构化完整性契约 jsonpath、安全扫描、密级),不校验"业务正确性"(API 设计是否合理、代码质量、设计美观)。completeness_contract 是"管理约束"——校验字段存在性与最小数量,不校验字段业务语义。

### 4.2 §2.1 节点类型清单补全(修正 C1.3/C1.4/G1.5)

```markdown
**产物节点(本期预置 10 种,可扩展):**

> 节点类型采用扁平命名(预置)或 `{role}.{name}` 开放命名(扩展)。SkillRegistry 按「精确匹配 → 角色兜底(`client.*`) → 通用(`*`)」三级匹配。

| 节点类型 | 角色 | 说明 | 阶段 |
|---|---|---|---|
| `product_spec` | product | 产品需求文档 | Phase 1 |
| `api_contract` | server | 接口契约 | Phase 1 |
| `server_impl` | server | 服务端实现引用 | Phase 1 |
| `server_test` | server | 服务端测试结果引用 | Phase 1 |
| `design_proto` | design | 设计原型 | Phase 2 |
| `design_asset` | design | 设计标注/切图 | Phase 2 |
| `client_ui` | client | 客户端 UI 实现 | Phase 2 |
| `client_func` | client | 客户端功能联调 | Phase 2 |
| `client_delivery` | client | 客户端交付物 | Phase 2 |
| `derived_artifact` | generator | 派生产物 | Phase 2 |
| `client_logic` | client | 客户端业务逻辑(非 UI) | Phase 2(D11) |
| `server_delivery` | server | 服务端交付物 | Phase 2(D11) |
| `research_spike` | any | 调研产物(无依赖旁路) | Phase 2(D11) |
| `free_artifact` | any | 自由产物(无固定依赖) | Phase 2(D11) |

**扩展规则**:
- 扩展类型必须用 `{role}.{name}` 格式,role 为 5 个开发角色之一
- 扩展类型必须在 `skills/` 下建对应 `skill.yaml`
- CI 白名单由 `repo-meta.yaml.node_types_supported` 控制,新增类型需 migration PR
```

### 4.3 §3.2 权限矩阵补 generator 行(修正 C1.5/G1.15)

```markdown
| 操作 | product | server | design | client | generator | reviewer | admin |
|---|---|---|---|---|---|---|---|
| 提交产物(submit_artifact) | ✅(仅 product_spec) | ✅(server 类) | ✅(design 类) | ✅(client 类) | ✅(仅 derived_artifact) | ❌ | ✅ |
| 更新进度(update_progress) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| 查询依赖(get_dependencies) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 请求审批(request_approval) | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| 审核PR(approve_pr/reject_pr) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 设置门禁(set_gate_policy) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查询审计(get_audit_log) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 报告生成状态(report_generation_status) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
```

### 4.4 §3.2 权限三层校验执行顺序(修正 D1.6)

```markdown
**提交产物权限三层校验(串行短路):**

执行顺序:L1 → L2 → L3,任一失败立即 reject 并返回该层错误,不继续后续校验。

| 层级 | 校验内容 | 适用范围 | 失败结果 | 失败返回 |
|---|---|---|---|---|
| L1 node_type | 提交方角色/RoleInstance 只能产出本端允许的节点类型 | 所有产物 | reject | `{layer: "L1", error: "node_type_not_allowed", role: "server", node_type: "client_ui"}` |
| L2 instance_id | 提交方 RoleInstance 与 `role_assignments[node_id]` 中的 `instance_id` 匹配 | 所有产物 | reject | `{layer: "L2", error: "instance_mismatch", expected: "team_a_server", actual: "team_b_server"}` |
| L3 external_repo | 引用型产物的 `external_repo` 必须在 RoleInstance.`allowed_external_repos` 白名单内 | 仅 `artifact_kind=reference` | reject | `{layer: "L3", error: "repo_not_whitelisted", repo: "org/other-repo"}` |

> L3 仅对引用型产物生效;内容型产物跳过 L3。
```

### 4.5 §FR1.1 HubRepoConfig 字段规范(修正 D1.2/G1.11/G1.12/G1.13)

```yaml
hub_repo:
  url: string                        # 必填,hub 仓 git 地址
  provider: enum[github,gitlab,bitbucket,gitea]  # 必填
  credential_ref: string             # 必填,Vault 路径
  webhook_secret_ref: string         # 必填,Vault 路径
  branch_naming: string              # 必填,默认 "feat/{pipeline_id}/{instance_id}/{node_type}-{seq}"
  clone_strategy: enum[full,partial,shallow,on_demand]  # 默认 partial
    # full=完整 clone / partial=仅 features/ / shallow=--depth=1 / on_demand=按需 git show
  lfs:
    enabled: boolean                 # 默认 true
    threshold_mb: integer            # 默认 10,> 该值走 LFS
    fallback_on_unavailable: enum[reject,warn]  # 默认 reject;LFS 不可用时 >threshold 文件 reject
  capacity:
    max_prs_per_hour: integer        # 默认 50,超限 PR 进 queued 状态
    max_concurrent_reviews: integer  # 默认 10,超限排队
    max_pipelines: integer           # 默认 500,超限告警
    max_repo_size_gb: integer        # 默认 5,超限告警并规划分仓
  branch_protection:
    main:
      require_pr: boolean            # 默认 true
      min_reviewers: integer         # 默认 1(管理方 bot)
      squash_merge: boolean          # 默认 true
```

### 4.6 §FR1.2 分支命名 regex(修正 D1.1)

```markdown
**四维分支命名规范**:

格式:`feat/{pipeline_id}/{instance_id}/{node_type}-{seq}[-{uuid8}]`

Regex(CI 校验):
```
^feat/[a-z0-9][a-z0-9-]{0,63}/[a-z0-9_]{1,32}/[a-z_]+-[0-9]{3}(-[a-f0-9]{8})?$
```

| 段 | 规则 | 示例 |
|---|---|---|
| `pipeline_id` | 全局唯一管线标识,小写 kebab-case,1-64 字符 | `login-feature` |
| `instance_id` | RoleInstance ID,小写 snake_case,1-32 字符 | `team_a_server` |
| `node_type` | 节点类型,小写 snake_case | `api_contract` |
| `seq` | 3 位零填充序号,与产物文件名 seq 一致 | `001` |
| `uuid8` | 可选,8 位 hex,分支去重 | `a3f2b1c4` |

示例:`feat/login-feature/team_a_server/api_contract-001` 或 `feat/login-feature/team_a_server/api_contract-001-a3f2b1c4`
```

### 4.7 §FR1.1 GitProvider 接口契约(修正 G1.9/D1.9)

```python
class GitProvider(Protocol):
    """Git 托管抽象层,屏蔽 GitHub/GitLab/Bitbucket 差异"""

    def create_branch(self, repo: str, branch: str, from_commit: str) -> bool:
        """从指定 commit 创建分支"""

    def open_pr(self, repo: str, branch: str, title: str, body: str) -> int:
        """开 PR,返回 pr_id"""

    def merge_pr(self, repo: str, pr_id: int, squash: bool = True) -> str:
        """合并 PR,返回 merge_commit hash"""

    def get_pr_files(self, repo: str, pr_id: int) -> list[dict]:
        """获取 PR 修改的文件列表 [{path, status, additions, deletions}]"""

    def setup_branch_protection(self, repo: str, branch: str, rules: dict) -> bool:
        """配置分支保护(require_pr/min_reviewers/squash_merge)"""

    def register_webhook(self, repo: str, url: str, events: list[str], secret: str) -> bool:
        """注册 webhook(PR push/review 等)"""

    def ls_remote(self, repo: str, ref: str) -> str | None:
        """校验外部代码仓 commit 存在性(不 clone),返回 commit hash 或 None"""
```

### 4.8 §FR1.1 emergency 降级流程(修正 G1.10/D1.4)

```markdown
**hub 仓单点故障降级流程**:

1. **检测**:管理方调用 GitProvider 失败,重试 3 次后标记 hub 仓 `unavailable`,触发降级模式

2. **emergency_local_commit(admin 调用)**:
   - 暂存路径:`~/.coord-platform/pending/{pipeline_id}/{node_id}_{timestamp}/`
   - 暂存内容:`manifest.json` + `content.<ext>` + `decision.json`(含 admin 签名 + 时间戳)
   - 状态:节点标记 `pending_sync`,不入 hub 仓
   - 限制:同 node_id 只能有一个 pending_sync,避免冲突

3. **emergency_approve(admin 调用)**:
   - 紧急审批在 `decision.json` 中记录(approver/reason/ts)
   - 不触发 LangGraph set_done(因产物未入 hub 仓,无 commit hash)
   - 标记节点 `pending_sync_done`,下游不级联(保守)

4. **sync_pending_artifacts(admin 调用,恢复后)**:
   - 按时间序遍历 pending 目录
   - 每个 pending 产物走正常流程:bot 创建 feat 分支 → 推内容 → 开 PR → 快速审核(跳过 L2 instance_id 校验,因 admin 已签)→ squash merge
   - seq 冲突处理:bot 自动取 main 上 max_seq + 1,重命名文件
   - 依赖已变更处理:若 deps 已 changed,pending 产物标记 `needs_resubmit`,通知原提交方
   - 合并后补写审计日志(action=`emergency_sync`),关联原 decision.json

5. **恢复完成**:所有 pending 清空后,管理方退出降级模式,恢复正常流程
```

### 4.9 深化 §3.3 manifest schema 修正(修正 C1.6~C1.15)

```json
{
  "required": [
    "manifest_version", "node_id", "node_type", "role", "title", "version",
    "source", "toolspec", "deps", "created_at", "submitter",
    "artifact_kind", "artifact_qualifier", "classification"
  ],
  "properties": {
    "node_id": {
      "type": "string",
      "pattern": "^[a-z0-9][a-z0-9-]*\\.n[0-9]+$",
      "examples": ["login-feature.n2"]
    },
    "node_type": {
      "enum": ["product_spec","api_contract","server_impl","server_test",
               "design_proto","design_asset","client_ui","client_func",
               "client_delivery","derived_artifact"]
    },
    "role": {
      "enum": ["product","server","design","client","generator"]
    },
    "source": {
      "properties": {
        "path": {
          "pattern": "^features/[a-z0-9][a-z0-9-]*/[a-z_]+/(official|mock|draft|experimental)/[0-9]{3}[_a-z0-9-]*\\.(yaml|yml|json|md|mdx)$"
        }
      }
    },
    "artifact_kind": {"enum": ["content","reference"]},
    "artifact_qualifier": {"enum": ["official","mock","draft","experimental"]},
    "classification": {"enum": ["public","internal","confidential","restricted"]},
    "deps": {
      "items": {
        "properties": {
          "node_id": {"type": "string"},
          "hub_ref": {"type": "string"},
          "version_constraint": {"type": "string"},
          "min_version": {"type": "string"},
          "format_slot": {"type": "string"},
          "strictness": {"enum": ["strict","accepts_draft"]},
          "presence": {"enum": ["required","optional","if_present"]},
          "coupling": {"enum": ["hard","soft","informational"]}
        }
      }
    }
  }
}
```

> 注:以上为修正片段,完整 schema 需在深化文档 §3.3 中替换。`consumers`/`external_resources`/`completeness_contract`/`modification` 为 PR 模板字段(不进产物级 manifest,因它们属于 PR 提交时的声明,合并后由管理方写入 PipelineState.artifact_refs)。

---

## 5. 审核结论

### 5.1 阻断性问题

**深化文档 fr1-fr6 §3 的 manifest JSON Schema 与主 PRD §FR1.1/§FR1.3 存在 9 处硬冲突(C1.6~C1.15),若不修正直接实现将导致:**
- CI 全量误拦(node_id pattern 不匹配、node_type/role enum 缺值、source.path pattern 不匹配)
- 或 CI 全量放过(additionalProperties 未严格限制时)
- 依赖校验无法实现(deps schema 缺第五轮字段)

**建议**:以主 PRD §FR1.1/§FR1.3/§FR2.2/§5.1 为权威源,重写深化 §3.3 manifest schema,确保字段、枚举、pattern 与主 PRD 完全一致。

### 5.2 一致性问题

**§2.1 节点类型清单与附录 D11 P0 修正项未同步**:D11 明确提出 `client_logic`/`server_delivery`/`research_spike`/`free_artifact` 为 P0 修正,但 §2.1 清单未列入,开发者无法判断本期是否实现。建议在 §2.1 明确标注阶段。

**§2 术语"10 态状态机"与 D11"11 态"冲突**:需明确 skipped 态是否本期实现。

### 5.3 可开发性评估

- §1-§3 主干逻辑清晰,可进入实现
- §FR1 的 HubRepoConfig/分支保护/PR 模板主干可实现,但缺 regex/接口契约/降级流程细节
- **深化文档 §3 manifest schema 必须修正后方可作为 CI 校验依据**
- 13 项 P0 发现需在 Phase 1 启动前修正
