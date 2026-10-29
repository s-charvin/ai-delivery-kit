<!-- ai-delivery-template-language
实例化本模板时，所有人类可读的标题、标签、结果摘要和评审说明都使用用户当前对话语言。ID、路径、命令、代码符号、状态值、占位符和 `ai-delivery-verification:*` 标记保持原样。完成产物前删除本注释。
-->

# 验收证据：{{subreq_id}}

> 本文件是 `verify-before-completion` 的**硬证据**。缺少必备的语言无关标记时，验证器将判定 `merged` / `archived` 不合法。
> 每条评审轮次追加到 §1 末尾；预算耗尽仍未通过 → 升级人工（**永不自动合并**）。

<!-- ai-delivery-verification:review-rounds -->
## 1. 评审轮次记录
### Round 1 — <日期>
- 评审人：
- 结论：clean / 需修改
- 摘要：

<!-- ai-delivery-verification:commands-results -->
## 2. 验证命令与结果
- 静态分析：`<命令>` → `<结果>`
- 测试：`<命令>` → `<结果>`

### 需求与测试覆盖
| 需求来源 / B-### / AC-### | 实际测试路径与名称 | 结果 / 证据 | 未覆盖风险或批准的偏离 |
|---|---|---|---|
| ... | ... | ... | ... |

- 原始来源复核：<遗漏、冲突和用户决策引用>
- 边界、失败与事件顺序覆盖：<已测场景与重要排除项>
- 回归证据：<适用时记录修复前失败及修复后通过的结果>

## 3. 视觉验收
- 结构化证据：`visual-acceptance.json`
- 绑定的 UI truth index SHA-256：`<64-lowercase-hex-sha256>`
- Scenario 覆盖：`<所有已索引 scenario id 均 passed 或明确 waived>`
- 稳定 Figma 位图比较：`<reference/candidate/diff 与 threshold，或不可用>`
- 结论：通过 / 不通过

### 最终用户验收（仅启用 UI truth 时）
- 已审阅的场景/unit ID 与预览绝对路径：
- 当前 UI truth index SHA-256 与静态/动效证据哈希：
- 用户答复、验收人和时间：
- 静态验收与独立动效/无动效验收或限定范围的豁免：
- 被拒绝、延后或尚未审阅的项：

一次明确的整批答复可以覆盖所有已列出的当前证据。不得从静态批准推断动效
验收，不得把遗漏项视为已批准。

<!-- ai-delivery-verification:sign-off -->
## 4. 签署
- 实现者：
- 评审者：
- 日期：

每轮评审记录批次范围与输入身份。原始结果只存原生报告；复用时记录原命令/run、当前输入/工具链/变体、产物 hash、覆盖范围与复用核对，不能冒称新执行。可选 progress 仅引用本记录。
