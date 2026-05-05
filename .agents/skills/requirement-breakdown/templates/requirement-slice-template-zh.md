<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# 需求切片

## 元数据

- `requirement_id`：        # 父需求标识
- `subreq_id`：             # 本切片唯一标识
- `title`：                 # 简短描述名称
- `type`：                  # Global Rule | Shared Foundation | Shared Component | Feature Module | Cross-Feature Infrastructure
- `parent_requirement`：    # 父需求文档路径

## 源需求覆盖
<!-- 每个覆盖项将原始需求的一个段落链接到本切片。 -->

### 覆盖项 1

- `source_ref`：            # 原始文档中的行范围，如 "req.md#L14-L22"
- `coverage_kind`：`direct | shared_rule | partial | unresolved`
    # direct       — 段落独占归属于本切片
    # shared_rule  — 段落是影响多个切片的横切规则
    # partial      — 段落被拆分，本切片拥有其中一部分
    # unresolved   — 归属尚不明确
- `coverage_status`：`covered | deferred | unresolved`
    # covered      — 段落已完整覆盖
    # deferred     — 段落有意搁置，原因见 notes
    # unresolved   — 覆盖关系需要进一步澄清
- `notes`：                 # 补充说明，特别是 deferred/unresolved 的原因

## 规范化切片陈述
<!-- 一句话概括本切片做什么。从源推导，非逐字照抄。 -->

- `statement`：             # 一句话概括
- `source_basis`：          # 此陈述所依据的 source_ref
- `normalization_type`：`none | wording cleanup | merged adjacent lines | partial extraction`
- `normalization_note`：    # 做了什么规范化以及为什么

## 范围边界

### 范围内

- `statement`：             # 包含什么
- `source_ref`：            # 源依据
- `derived_from`：`source coverage | normalized statement`

### 范围外

- `statement`：             # 明确排除什么
- `source_ref`：
- `derived_from`：`source coverage | normalized statement`

### 输入

- `input`：                 # 本切片需要的外部输入（数据、API、上游切片）
- `source_ref`：

### 输出

- `output`：                # 本切片产出什么
- `source_ref`：

### 非目标

- `non_goal`：              # 明确不做的事情（防止范围蔓延）
- `source_ref`：

## 依赖契约

### 依赖项

- `dependency`：            # 所依赖的子需求 subreq_id
- `why`：                   # 依赖原因
- `source_ref`：

### 外部约束

- `constraint`：            # 外部系统或接口施加的约束
- `source_ref`：

## 验收信号
<!-- 可验证的完成条件。证明切片已满足。 -->

### 信号 1

- `signal`：                # 可验证的验收条件
- `source_ref`：
- `derived_from`：`source coverage | normalized statement`

## 待解决问题
<!-- 拆分过程中无法解决的问题。 -->

### 问题 1

- `question`：              # 问题描述
- `why_open`：              # 为什么当前无法解决（缺信息、源冲突等）
- `related_source_ref`：

## 歧义与冲突
<!-- 源文档中发现的模糊或矛盾之处。 -->

### 项 1

- `issue`：                 # 歧义或冲突描述
- `conflict_type`：`source ambiguity | source conflict | shared-rule overlap | missing business fact`
    # source ambiguity        — 源措辞模糊，可做多种解读
    # source conflict         — 源内部自相矛盾
    # shared-rule overlap     — 横切规则与切片范围冲突
    # missing business fact   — 关键业务事实在源中缺失
- `related_source_ref`：
- `resolution_path`：       # 建议的解决路径
