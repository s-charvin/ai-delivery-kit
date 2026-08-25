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

## 3. 视觉验收
- 结构化证据：`visual-acceptance.json`
- 绑定的 UI truth index SHA-256：`<64-lowercase-hex-sha256>`
- Scenario 覆盖：`<所有已索引 scenario id 均 passed 或明确 waived>`
- 稳定 Figma 位图比较：`<reference/candidate/diff 与 threshold，或不可用>`
- 结论：通过 / 不通过

<!-- ai-delivery-verification:sign-off -->
## 4. 签署
- 实现者：
- 评审者：
- 日期：
