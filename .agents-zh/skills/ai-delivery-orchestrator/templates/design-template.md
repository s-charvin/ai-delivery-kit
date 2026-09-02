<!-- ai-delivery-meta: {"version":1,"artifact_type":"solution-design","layout_key":"solution_design","canonical_path":"design.md","updated_at":"<ISO8601>","updated_by":"<agent>"} -->
<!-- ai-delivery-template-language
实例化本模板时，保留 ai-delivery-meta 注释及其机器键，仅替换时间戳和作者占位符。所有人类可读的标题、标签和正文都使用用户当前对话语言。ID、路径、命令、代码符号和协议字面量保持原样。完成产物前删除本语言指令注释。
-->

# 方案设计：{{subreq_id}}

> 本文件是子需求 `{subreq_id}` 的**规范方案设计记录**，替代原先塞在 `status.json` `notes` 中的设计碎片。
> - 活跃开发期（status < archived）：本文件为**派生产物**，可随 spec 再生（living spec 模式）。
> - 归档后（archived）：canonical 产物原位保留为历史事实源，变更需求请开新需求目录。

## 1. 背景与目标
（为什么这样做，约束与边界是什么）

## 2. 关键决策
- 决策点 A：选择 X，理由…
- 决策点 B：…

## 3. 方案概述
（技术选型、模块划分、交互流程；可用文字 / 伪代码 / 图表链接）

## 4. UI 场景引用（仅启用 UI truth 模式）

运行时覆盖的唯一真相源是 `contracts/ui-truth-index.json`。本文件只引用已索引的 scenario，不重复维护 Runtime Coverage Plan。

### Unit 与 Scenario 追踪
| Unit ID | 场景 IDs | 职责 | 验证负责人 |
|---------|--------------|------|------------|
| ... | ... | ... | ... |

### 状态与转换模型
| From | Trigger | To | Loading/error/interrupt 行为 |
|------|---------|----|----------------------------------|
| ... | ... | ... | ... |

对每个引用的 scenario 写明实现职责与验证命令或测试负责人。运行时维度（state、layout、content、interaction、motion、assets、theme、accessibility、platform、performance）留在 UI truth index 中。分别记录 Figma 可见真值与来自需求、项目规范或用户决策的运行时行为。不得把非 Figma 场景称为 1:1 还原 Figma。

## 5. 风险与缓解
| 风险 | 影响 | 缓解 |
|---|---|---|
| … | … | … |

## 6. 待决问题 / 开放项
- …
