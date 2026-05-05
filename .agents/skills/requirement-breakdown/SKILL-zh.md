---
name: requirement-breakdown
description: 当需要将需求文档拆分为可独立追踪的子需求并保留源产物的场景下使用。
---

# 需求拆分

将顶层需求文档拆分为子需求。每个子需求通过行范围引用源文档（不逐字复制），并添加规范化陈述。

此技能只做一件事：读取需求 → 产生子需求。它不管理状态、不决定下一步运行什么、也不处理阻塞项。

## 输入

一个需求文档（路径或粘贴的文本）。

## 输出

```
<output-dir>/
├── breakdown-summary.md     # 输入源、子需求索引、待解决问题
├── global-rules.md          # 仅横切规则
├── dependency-graph.json    # 无环有向图（仅 depends_on — 不含 blocks，blocks 由 orchestrator 管理）
└── <subreq-dir>/
    └── requirement-slice.md # source_ref 行范围引用 + 规范化陈述
```

## 工作流

### 1. 清点来源
- 阅读需求文档。记录每个章节的行号。
- 识别哪些章节属于哪个子需求边界。

### 2. 确定边界
按交付含义拆分。子需求应满足以下至少一项：
- 可以独立开发、集成、测试或验收
- 拥有一个连贯的依赖或能力接口

有效类型：`Global Rule`、`Shared Foundation`、`Shared Component`、`Feature Module`、`Cross-Feature Infrastructure`。

规则：
- 在功能模块之前提取共享基础和跨功能基础设施。
- 影响 2 个以上子需求的横切规则放入 `global-rules.md`，不重复。
- 不要为实现便利而过度拆分。

### 3. 编写产物
- `requirement-slice.md` 引用源文档的行范围（章节）。不要逐字复制原文 — 浪费 token。
- `dependency-graph.json` 必须是无环的。只列 `depends_on` — `blocks` 由 orchestrator 管理，不由此技能负责。

### 4. 重新审计
- 重新阅读原始需求。验证没有章节被静默丢弃。
- 验证每个验收信号追溯到源引用。
- 验证依赖图是无环的且全局规则未重复。

## 源引用模式

```
source_ref: "original-requirement.md#L14-L22, L30-L35"
  — 此切片覆盖的原始文档中的行范围。
  — 多个不连续的范围用逗号连接列出。
  — 每个范围代表一个逻辑章节/段落，而非随机行号。

规范化陈述：
  - statement: 此切片涵盖设置中的项目名称编辑。
  - source_basis: original-requirement.md#L14-L22
  - normalization_type: 措辞清理
```

不要将原始文本复制到切片中。`source_ref` 已足够 — 下游工具和人类可以打开原始文档查看。
