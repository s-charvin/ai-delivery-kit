# 复盘机制与轻量产物组织：实施及评估记录

本次已修改本机技能的真实源仓库，未提交或发布。安装入口 `/Users/zuiyou/.codex/skills/ai-delivery-orchestrator` 指向 `/Users/zuiyou/ai-delivery-kit/.agents/skills/ai-delivery-orchestrator/`，其物理仓库为 `/Users/zuiyou/develop/skills/ai-delivery-kit`。开始时工作树干净，基线提交为 `0ede22b744a6d96c456e3387bae45f93cde4dc33`；补丁逐文件应用前校验当前字节哈希，避免覆盖并发修改。

## 现状判断与修改归属

| 责任层 | 实际证据及处理 |
|---|---|
| 规则缺失／冲突 | 旧入口排除机械修正，旧指导明确“只记录可复用问题”；基线执行因此漏收用户已指出的一行错字。改为全部已知问题同规则收集，需求级收录与项目索引资格分离。 |
| 触发缺失 | Stage 4只接入可复用分诊，Stage 2未明确把UI纠正持续接入台账。接收、恢复、执行中新消息、Stage 2／4发现、批次收尾及归档前均有简短触发和详细指导引用。 |
| 实际执行违约 | 既有UI真值已约束来源、父合成、状态、动效及宿主接线；漏做这些不能全部归因于规则缺失。不削弱有效真值／验收约束，以具体错误判断、尝试、验证范围进入复盘。 |
| 验证不足 | 原归档证明日期、表格及索引条件，不能证明所有已知问题已收录。现在增加客观结构检查；语义完整性仍靠原始反馈逐项核对和模型应用评估，不能冒充关键词扫描能力。 |

主要修改如下，中英文行为对应，人类可读文件手工维护；现有同步脚本只复制非语言文件，没有用它冒充翻译：

- [入口](../../.agents/skills/ai-delivery-orchestrator/SKILL.md)和[复盘详细指导](../../.agents/skills/ai-delivery-orchestrator/references/retrospective-guidance.md)：统一收集、UI适用视角、同机制归并、未知与未验边界、源发现反查、禁止修订批次式补充。保留渐进读取及既有五字段索引资格。
- [框架／产物指导](../../.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md)：职责决定整合／原始留存／按需／禁止，辅助材料默认归属、排序、当前入口、证据保存状态与完整用户输入。
- `references/stage-breakdown.md`、`stage-ui-truth.md`、`stage-implementation.md`：接收、实施、评审、验证及收尾接入；`templates/retrospective-template.md`、`verification-template.md`与新增[用户原文模板](../../.agents/skills/ai-delivery-orchestrator/templates/user-prompt-record-template.md)承接实际维护。
- [归档脚本](../../scripts/archive-subrequirement.py)、[既有复盘测试](../../tests/ai-delivery-skills/retrospective-feature.test.sh)、新增[结构回归](../../tests/ai-delivery-skills/retrospective-structure.test.py)、中英文同步测试及[行为场景](../../tests/ai-delivery-skills/retrospective-behavior-scenarios.md)。

没有修改 `layout.py`、project-binding协议、状态schema、UI真值合同、checkpoint、原有验收规则或权限。没有增加目录／命名扫描器、产物管理服务、第二问题账本或历史整理阶段。

## 只读取样

重新清点六个需求的可见文件，依次为41、25、892、576、2031、35；数量包含工作树可见材料，只用于核对样本规模，不作为违规统计或完成指标。检查了根入口、实际project-binding、路径解析器和同步脚本职责，并读取UI-002原始审查、R97状态审计及用户反馈修复记录。1.2.0样本较之前清点增加4份，未归因于本任务或擅自整理。

历史案例只支持调查方法：字重与字号／行框不能混为一项，属性适用状态不能共用过窄门禁，组件正确不证明父合成或正式接线，静态图不证明动效，旧断言可能固化偏差。未把节点、数值、字段或被撤回产品方案写成通用规则。未修改这六个需求、App、交付状态、历史验收或原件；没有操作Figma、设备及业务账号。

## 实际结构与兼容验证

最终实际执行通过：

| 验证 | 结果与范围 |
|---|---|
| `bash tests/ai-delivery-skills/retrospective-feature.test.sh` | 通过，包含19条真实parser／preflight／CLI结构回归及既有索引资格、幂等、旧格式拒绝、自定义路径、空台账和日期行为。非法输入在实际归档CLI中失败且状态字节不变。 |
| `bash tests/ai-delivery-skills/archive-immutability.test.sh` | 通过，归档原位收敛，不复制正式产物。 |
| `zsh tests/ai-delivery-skills/sync-agents-zh.test.sh` | 通过，新增模板双语存在；非语言资产仍按原约定一致。 |
| `bash scripts/validate-project-ai-delivery-skills.sh` | 通过，真实技能入口、模板、链接和机器约束有效。 |
| `GOCACHE=/private/tmp/ai-delivery-kit-go-cache zsh tests/ai-delivery-skills/bootstrap-project.test.sh` | 通过，实际初始化临时宿主并检查安装后技能。 |
| 同一临时GOCACHE下 `go test ./...` | 全包通过，含嵌入资产、bootstrap、CLI、initflow及repo测试；未发布产物。 |
| skill-creator `quick_validate.py`、`git diff --check` | 通过；前者使用本机Python 3.12及已有PyYAML。 |

此外实际通过的相关检查：`artifact-language-policy`、`english-source-policy`、`artifact-layout`、`layout`、`orchestrator-stage4-skill-markers`、`kit-root-boundary`、`reconcile-delivery`、`verification-gate`、`unified-design-flow`、`visual-acceptance-validator`、`ui-truth-index-validator`。后两项是原有UI门禁回归，不是设备或产品视觉验收。

RED／修正证据也保留：初始新增13条结构用例在原脚本上失败11项；独立审查后补充的合法锚点／带标题链接／章节边界及伪data-id用例先失败再修复。最终19条通过，9个独立边界探针通过。校验与索引共用本地片段解析，HTML锚点按真实id/name属性解析，不误把data-id当锚点；前置锚点归属其后标题，不能落入上一个RET。

执行中遇到并纠正了验证环境／夹具问题：系统Python 3.9不接受测试时间尾部Z，改夹具为显式时区；默认Go缓存无写权限，改用临时缓存；系统Python缺PyYAML，使用已有依赖的Python3.12；bootstrap使用zsh；新入口的带片段相对链接不被旧技能校验器支持，改为清楚命名的文件链接，没有扩大修改旧校验器。

## 模型应用与独立内容核对

采用宿主默认模型的独立子任务上下文，没有固定模型版本／随机种子，也没有新增自动模型评测平台。执行者读取真实指导后实际维护临时文件，主会话另做原文、案例及证据核对；独立审查者检查源差量并运行边界探针。结构自动测试、自动字节／链接比较和人工语义审查分别报告，不把它们混称自动模型评估。

| 场景 | 实际观察 |
|---|---|
| 原指导控制组 | 生成12个RET；执行者明确写出因“机械且无复用价值”排除已修错字的理由。其他未知反馈／产品决定仍保留。这个漏记由实际输出证实，不只是搜索到了冲突句。 |
| 混合问题与绿色测试 | 候选输出14个RET，U1–U10、AI迁移问题、评审初始化问题及状态／动效缺口都有具体案例；已修错字在RET-008，未复现夜间在RET-009，产品改变在RET-010。保留未验范围，无虚构运行RED或验收。 |
| 同机制维护与真实新上下文 | 执行者先从磁盘恢复，将U11融入RET-001；另一个全新上下文读取已保存文件，再融入U12。U2、旧失败及第二次修复未验证仍在，同一14个RET不增日期附录。主会话将实际输出交给生产parser读取，14条有效、0条具备索引资格。 |
| 连续用户原文 | 初始长文本、列表、代码、三／四层反引号、补充、纠正选B、次日续接、实际同文重发、独立SDK任务和返回原任务、跨需求主归属均实际保存。初始8条逐字核对；新鲜上下文再写第9条，聊天组8条、SDK组1条，既有原文未变。附件内容相同，AI选项说明分离，历史／附件缺口明示。 |
| 产物轻量维护 | 小需求不生成空目录。复杂例有研究、源导出、审查、诊断、Mock及原生运行入口；当前清单、摘要和复盘原位维护，未复制整批旧报告或建立第二最新清单。两个独立运行即使日志／图像相同仍保留各自身份。 |
| 排序、固定文件及证据限制 | 实际字典序002在010之前、2月在10月之前；跨日补充保留原提示词文件名。37份原始夹具不变、23份保护文件不变、无删除，33个Markdown链接可定位。历史/tmp及build原件缺失被标明，不倒推旧测试失败、不宣称当前通过、不擅自运行设备。 |

上述文件数是原件保全核对的观察量，不是产物越少越好的指标。产物样例中的XML标签修改、SDK／Figma和运行数据都是隔离合成夹具，未执行真实SDK／Figma／设备行为。第一次恢复是同一执行者的磁盘恢复模拟，后一次是确实全新上下文；两者没有混报。

完整实际文本、输出哈希、RED结果、最终命令记录和独立复核见[评估证据](2026-11-03_002_Evaluation-evidence.json)。证据以来源键区分基线、候选、原始消息、实际输出和复核，不让临时路径成为唯一保存位置；真实业务历史未复制进技能。场景文档可用于后续独立重跑，模型结果仍需人工逐项看具体案例，不能只跑文件存在检查。

## 剩余边界

客观脚本只能识别所支持的结构和已知修订批次标题，不能证明所有已知问题已记录、根因真实或任意措辞都无补丁式正文；原始发现反查不可省。稳定机器标记仍是文档级协议，不适合原样复制一整套标记代码示例；不是任意Markdown方言解析器。

本次是代表性隔离应用及人工核对，不是多模型、多平台或五次以上独立重复的可靠性研究；没有自动化全量对话导出或不可见历史恢复。未执行真实UI运行、业务验收、归档或设备测试，也未声称Dokimo现有复盘已补全。

源技能经安装符号链接已可读取新指导。现有宿主复制的 `.ai-delivery/scripts/` 不会因修改源仓库自动升级；本任务没有对Dokimo执行 `init --upgrade` 或替换其脚本。需要升级已有宿主时另按宿主授权和既有升级机制操作。历史整理、提交、发布均未执行。
