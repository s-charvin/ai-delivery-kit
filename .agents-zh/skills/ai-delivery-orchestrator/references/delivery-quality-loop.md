# 规范上下文与质量闭环

Trellis 的按需规范加载与 Shopify Helix 的小步验证在 kit 的同一合同、路由和检查点内执行。不启动上游 Task/checkpoint/journal/Stop hook，不新增人审关卡。参考来源：[Trellis](https://docs.trytrellis.app/zh)、[Shopify Helix](https://shopify.engineering/helix)。

## 进入与恢复

每批开工、阶段切换、范围扩大或上下文恢复时，先用真实需求目录和明确切片生成上下文：

```sh
ai-delivery context --project . --req <req-id> --subreq SR-001 \
  --role implement --changed-path src/owner.go --format json
```

角色：`analysis`、`design`、`ui`、`implement`、`review`、`recovery`、`finish`。阶段主持技能与既有 UI 模式不变；只有 `figma`/`runtime-baseline` 进入 Stage 2。`context_complete` 只表示所选必需上下文完整提供且未发现输入错误，不是实施授权；执行权限由当前显式 scope 的 `check`、设计 review 和既有检查点决定。CLI 不输出旧队列或全局选片授权。

`--changed-path` 明确归属本批的范围，可重复；评审者独立核对暂存/未暂存/新增及删除/重命名两侧，发现新范围要重新加载。路径清单不证明业务规则已全部发现，仍需沿真实调用链核对 owner、原始需求和领域边界。未归属脏文件不自动进入修改/提交范围。

声明与实际变化始终共同参与阅读规则选择，非空声明不能隐藏真实跨模块变化。目录声明从自身 AGENTS 开始收集并匹配登记来源。必读义务先按阶段和既有引用确定，不能因文件消失而取消：活跃设计阶段需原始需求和 canonical design，明确引用的切片缺失仍为 missing；draft intake 和真正非拆分需求保留适用例外。显式来源配置优先于自动索引提示。

输出区分 `provided`、`needs_read`、`missing`，携带来源、原因、性质及字节 hash。预算不足时按路径补读完整正文；只有索引或截断内容不能声称完整提供。补读后继续使用同一原始规范，不能为了让 `context_complete` 变真而删除来源。每次调用读取当前内容，不用 mtime/会话缓存证明有效。无需 hook 或 Trellis 安装。

## 项目来源

`workflow-policy.json` version 4 的 `context.sources` 引用唯一正文，例如：

```json
{
  "context": {
    "sources": [
      {"path":"docs/architecture.md","paths":["src/**"],"roles":["implement","review"],"kind":"standard","required":true,"writable":false},
      {"path":"docs/knowledge/state-owner.md","paths":["src/**"],"kind":"knowledge","required":true,"writable":false}
    ]
  }
}
```

不带 paths/roles 表示所有范围/角色适用；paths 使用仓内 POSIX 路径、大小写敏感 `fnmatch` 通配。分析/设计尚无路径时保守加载登记来源，不按扩展名猜领域。来源只允许仓内相对路径，禁止 `..` 和越界 symlink。根/模块 AGENTS 优先提供，普通规范不能覆盖用户授权、原始需求或 UI 真值。

`kind` 为 `standard`、`knowledge` 或 `advice`；必读知识仍是当前观察，不自动获得制定强制标准的权力。`writable` 只是明确维护范围，默认 false，不是改变产品、降低验收或自动接受知识的许可。没有额外规范时空 sources 合法。

已有 `.trellis/spec/`、`docs/knowledge/`、`docs/harness/` 的具体叶子可直接登记；索引只提供发现线索，不执行上游加载命令或覆盖 kit 规则。导入默认只读，不创建整套目录或空模板。发现竞争的自动任务入口时诊断来源，不擅自改写用户配置。

## 小步验证与纠错

一个连贯批次跟随可观察行为/真实状态 owner，包含完整接线和适用测试。新架构、持久化、并发或权限边界先做最小可运行证明，再扩大实现；不要按文件数拆代理/人审。原实现者承接修复；评审用新鲜上下文，同时核对需求/遗漏和规范/架构，专项风险才增加 reviewer。

先执行最便宜且真正证明行为的原生检查，再做所需集成、视觉及运行时检查。复用正式 owner 和既有测试设施，不另写一套 CLI 业务逻辑迎合测试。保留最终必需检查范围；只重跑缺失或输入失效的证明。

检查结果有明确区别：

| result | 含义和下一步 |
|---|---|
| `passed` | 有当前输入与真实原始结果，仍须核对覆盖和语义 |
| `failed` | 有效检查发现不满足，修复实现及受影响接线，再重验 |
| `invalid` | 错状态截图、错误范围或过期输入，先修取证再判断代码 |
| `not_run` / `blocked` | 未执行或前置不可用，保留缺口，不能当通过 |
| `not_applicable` | 有设计范围依据；不能用于覆盖必需 AC |
| `waived` | 沿既有规则取得明确、有范围的用户授权；不能由实现者自授 |

UI 证据继续绑定既有 profile/state/scenario、evidence_scope 和 host binding；同状态/区域才比较。component-only 不证明 host，静态截图不证明交互或动效。官方同栈 golden 保留其作用，不照搬跨栈迁移中放弃 pixel diff 的判断。

finding 要有位置、来源与处置。硬缺陷不能降成建议，偏好不能升成必修；可以有证据地反驳错误 finding。禁止修改期望、阈值或规范来迎合当前输出。实质需求/真值冲突走现有决定与设计更新，不绕过确认。复用当前 `review_loop.max_rounds`（默认 3）；换代理/改批次名不能清零。无进展时先找区分性证据，预算耗尽保留失败与恢复指向。允许正常停止/取消，停止不写通过。

## verification v2

新 init 使用 policy v4 + `verification_contract_version: 2`。普通 upgrade 在刷新受管资产前检查 binding/policy 的当前格式并保留兼容配置。不支持的数据停止依赖操作；用户可平级选择自行备份后用自己的 AI 或手动迁移，或显式运行 `ai-delivery init --upgrade --reset-data /path/to/repo` 备份重建，两者都不自动执行。当前格式、可复制迁移提示词与备份恢复边界见 [升级选择](version-upgrade.md)。

唯一 `verification.md` 保留原三段 marker、人类评审轮次和 sign-off，并增加唯一结果块：

```text
<!-- ai-delivery-verification:contract:v2 -->
带 version:2 的 JSON fenced block
<!-- /ai-delivery-verification:contract:v2 -->
```

JSON 包含 `subreq_id`、`inputs`、`checks`、`reviews`。inputs 为实际文件的 `{path,sha256}`，必须含当前 design 及相关生产/测试/资源/依赖/规范输入；不放会随状态改变的 status 或 verification 自身。用工具计算真实字节与 review 输入摘要：

```sh
ai-delivery evidence fingerprint --project . \
  --input src/owner.go --input tests/owner_test.go \
  --input .ai-delivery/requirements/<req-id>/sub-requirements/SR-001/design.md
```

checks 的每项记录 `id`、`acceptance_ids`、`required`、`result`；passed 还需 `mode`（executed/reused/manual）、实际 `command`、执行退出码和非空原生证据 `{path,sha256}`。复用需 `reuse_reason`，核对测试/依赖/工具链/运行条件仍有效；手工验证需 `confirmation`，豁免需 `waiver`，均包含 `by/at/reason/source_ref`。这是来源记录，不是脚本认证了任意人类身份。全部 AC 必须有通过/合法豁免证据。

reviews 保留轮次；最后一项是当前完整范围的适用结论，含实际可见 `reviewer`、`context:fresh`、`result:clean`、`input_sha256`、`verification_sha256` 和 `findings`。后一个摘要绑定完整 `version/subreq_id/inputs/checks`，涵盖命令、结果、覆盖、证据、复用理由与授权记录；排除 reviews 本身，避免自引用。结果声明定稿后计算两个摘要，让独立评审者绑定实际审过的版本：

```sh
ai-delivery evidence review-digest --project . --file <verification-path>
```

该命令只计算内容身份，不生成评审或授予通过；声明变化需重新取得适用评审。finding 含 `id/source_ref/disposition`（resolved/rejected/advisory/waived），不能保留 open 却宣称 clean。不得伪造独立代理身份。文件 hash 能发现漂移，不能证明输入清单没有漏项，原始需求独立核对仍必需。

### 可选原生执行采集

原生检查具有精确命令和已知输入时，可用 `ai-delivery run` 采集真实输出流、
退出事实与收据。在适用设计评审前，将方法登记到 canonical `design.md` 的验收节。
这是可选机制：不选择时省略整个块，不插入空块或占位块。没有 native block 时，
既有 external executed/reused 及合法 manual 路径仍可使用，证据、复用与确认义务
继续遵循上文。

精确格式为 `version: 1` 与非空 `checks`；每项仅含 `id`、`acceptance_ids`、
`argv`、`cwd`、`parser_id`、`input_paths`、`report_paths`、`source_refs`。
ID 唯一且不能占用核心检查名，AC 必须存在于当前设计。`argv` 是非空字符串数组，
不是 shell 字符串；`cwd` 是规范项目相对目录，`.` 合法。`parser_id` 为
`exit-code` 或 `go-test-json`，后者要求实际成功的测试事件。`input_paths` 与
`source_refs` 是非空的真实项目相对文件数组，不是目录、glob、URL 或 `#L` 定位。
`report_paths` 必须是数组，无额外报告也写 `[]`；额外报告须由本轮产生于
`{run_dir}/...` 内。

例如，产品 API 的实际文件如下，AC-001 至 AC-004 覆盖过滤、非法参数及 Store
行为不变，可在既有验收节、traceability 之前登记：

````markdown
<!-- ai-delivery:native-methods:v1 -->
```json
{
  "version": 1,
  "checks": [{
    "id": "go-products",
    "acceptance_ids": ["AC-001", "AC-002", "AC-003", "AC-004"],
    "argv": ["go", "test", "-json", "-count=1", "./..."],
    "cwd": ".",
    "parser_id": "go-test-json",
    "input_paths": [
      "go.mod", "api/router.go", "api/handler.go", "api/store.go",
      "api/legacy_test.go", "api/acceptance_test.go", "cmd/server/main.go",
      "notes/preserve.txt"
    ],
    "report_paths": [],
    "source_refs": [
      ".ai-delivery/requirements/F01-D1/sub-requirements/SR-001/requirement-slice.md"
    ]
  }]
}
```
<!-- /ai-delivery:native-methods:v1 -->
````

换成当前真实范围、AC、文件和已确认工具链；不存在 `go.sum` 时不要虚构。
缺失锁文件若影响执行，可用本次 `--input go.sum` 声明 absence，不把缺失文件
放进注册 `input_paths`。注册未覆盖的相关输入用可重复 `--input` 补充；此机制
不会自动发现宿主全部依赖、环境、工具链或设备条件，仍须保留适用证据。

当前设计字节已有适用评审、当前阶段允许执行后，在宿主根目录运行：

```sh
ai-delivery run --project . --req F01-D1 --subreq SR-001 \
  --check go-products --cwd . --timeout 120 --format json \
  -- go test -json -count=1 ./...
```

这里运行完整包模式。`go-test-json` parser 要求至少一个实际测试有 `run` 后接
`pass`，且每个已启动测试都成功。正常完成的无测试文件包可以用包级 `skip`
终结，但不计入成功测试。实际测试跳过（包括 `t.Skip`）以及完全没有实际测试的
命令，即使退出 0 仍为 `invalid`。全包执行不扩大登记的 AC 覆盖，也不替代其他
必要证据。

`--` 后 argv 与 `--cwd` 必须精确匹配已审阅方法。也可使用已确认的 Go 绝对路径，
但注册与执行两处必须相同。不能为套用例子安装/降级工具或自动联网取依赖。
方法变化会改变 design 字节，须重新完成适用评审。当前参数见 `run --help`；
不存在 `--parser` 参数或 receipt 转换命令。

按以下步骤消费返回的 JSON：

1. 保留 `receipt_path`、原始 stdout/stderr 和报告，失败/未运行尝试也保留。
   `result: passed` 且无映射诊断时，将返回的 `check` 用作 verification v2
   `checks` 中该 ID 的实际条目；其他结果如实保留，退出码 0 本身不够。
2. 以返回的 `inputs` 为 execution 输入基础，按 path 合并本范围其余真实设计、
   生产、测试、依赖和规范输入及当前 hash；身份冲突须查清，不能覆盖。不要复制
   收据整个 `inputs_before`，其中还含 prerequisite。排除 verification 自身及
   随状态变化的记账字段；若测试显式消费 status 文件，它也属于 execution 输入。
3. 更新唯一 `verification.md` 的现有 v2 对象：`version: 2`、
   `subreq_id: SR-001`、`inputs`、`checks`、`reviews`。保留已有轮次，只记录
   真实评审结论。覆盖 AC-001–AC-004 的测试不能冒认 AC-005 的结构/草稿完整性
   检查或 fresh review。run 不写 verification、不授予确认/豁免、不合并/归档。
4. 组合声明后计算真实 review 身份：

   ```sh
   ai-delivery evidence review-digest --project . --file .ai-delivery/requirements/F01-D1/sub-requirements/SR-001/verification.md
   ```

   将 `input_sha256` 与 `verification_sha256` 交给独立 reviewer 绑定实际审过的
   版本。此命令接收 verification，不接收 receipt，不生成评审。普通
   `check`/`advance` 仍是后续门禁。

一旦注册 native 方法，其 executed/reused 检查就必须有真实 receipt；不能删
`receipt_path` 或换 check ID 伪装普通 external 绕过。合法 manual 与显式 waiver
仍遵循既有授权规则；不能静默删除方法代替已审阅的设计变更。external 路径中的
`evidence fingerprint` 只计算显式文件/absence 当前身份，事后 hash 不证明历史执行。

## 当前证据与归档历史

当前转换和新任务复用需要当前输入、报告及适用批准。只有 canonical 行为合同 acceptance 节定义 AC 义务，历史说明中的 AC 不额外增加验收。共享 validator 返回本次真正消费的文件集合，包括 UI 传递引用与真实目标身份；归档在输出替换前复核同一集合，不要求 AI 手抄第二份清单。

新归档在既有 status entry 的 `archive_evidence` 固定终态 entry、design、verification 及适用 UI 合同身份。历史读取核对原记录完整性，生产源码和原生日志后续可合法演进；旧合同被改仍失败。新任务复用旧结果时必须验证新任务当前输入，历史完整不等于当前可复用。没有该身份的旧归档不受支持；不能用当前字节补造历史批准，也不能将验收降为 marker-only。按升级指引自行选择处理方式。

## 默认推广与效果评估

实现完成与适合默认采用分别判断。推广前验证消费者一致、迁移中断恢复、支持的旧 schema、真实安装入口，以及连续切片合法更新同一 owner。已有 v4 宿主保留当前验收强度；关闭可选提示不降低门禁。

新增上下文和评审指导应与已保留可靠性修复的安全基线比较，固定任务输入、模型、权限、预算及验收，保留全部尝试和失败。质量与实际工具/模型成本分别报告；字符量、结构测试通过或子进程减少都不能证明模型更准或开发提速。

## 经验维护与自我评估

问题完整收进唯一 retrospective；成功模式先留 design/decisions 来源，不虚构 RET。发现稳定知识后，先核实当前代码/测试和规范性来源，再维护已登记且 writable 的唯一规范源。已有代码只能证明现状；升级为强制规范需已确认架构，或用户/具有明确范围维护权限的维护者作出的实际决定。独立审查提供证据，不自授维护权限。提案与已采纳规范分开：修改规范前，在已有 decisions/retrospective 中记录真实提案/来源、获授权 actor、决定、范围和当前来源身份。writable 本身不是采纳，不能伪造 human 批准或自动晋升自己的建议。规范变化同步原生检查和上下文来源，不回溯授权旧合同。

优先使用已有模块 AGENTS 或已登记规范；无合适来源时才按需新增 `.ai-delivery/standards/` 主题并登记 sources，不造成功经验账本或学习数据库。维护范围不允许向只读导入回写；产品/权限/真值变化仍走原有决定路径。后续任务须在无历史聊天的新上下文，把当前已采纳规范实际应用到生产 owner 与原生行为；context 选中或索引命中不算应用证据。

当前获授权合同替代旧规则时，按已有维护权限取得有范围的实际决定，更新当前规范并刷新 context 后再实施。撤回及其来源写入当前任务，原始提案、采纳及已归档复盘/索引历史保留；历史建议不能覆盖当前合同。撤回前核对旧规则确实覆盖该 owner，搬出目录规避不构成证明。candidate-only 跨任务链只能说明观察到的应用/撤回，不证明因果提速或通用学习收益。

kit 自身改进用固定版本/初始文件/场景/验收和预算对照，完整记录失败、阻塞、不可比项及全部运行；Mock/关键词命中不代表真实模型稳定性。观察需求漏项、错误放行，也观察错误阻断、无效 finding、用户打断及返工。质量变差的提速不采纳，只有流程更繁琐而无收益时应精简。

## 单程序查询范围

`ai-delivery validate --kind status --project . --req <req-id> --subreq <subreq-id>` 仅检查当前状态字段、UI mode 和禁止产物；通过不证明阶段或交付就绪。`validate --kind layout --project .` 仅检查项目布局配置（`scope: project-layout-configuration`）。带切片的 layout 查询必须提供 `--intent`；`--to` 始终需要 `--intent`。

完整作用域证据和状态边验收使用 `check`，或等价薄入口 `validate --kind layout --project . --req <req-id> --subreq <subreq-id> --intent <intent> --to <target-status>`；二者调用同一核心并返回同一动作报告。`validate --kind skills|sources|api-policy` 校验受管人读资源，不接受动作/切片参数。不带 `--host` 的 `hook` 与 `check` 使用相同参数和 JSON；可选[原生 transport](native-hooks.md)在同程序投影 Codex SessionStart/PreToolUse 的 stdin/输出，不启动第二个 kit 程序。
