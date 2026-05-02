<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# `<subreq_id>` `<title>`

## 元数据

- `subreq_id`:
- `title`:
- `type`: `Global Rule | Shared Foundation | Shared Component | Feature Module | Cross-Feature Infrastructure`
- `status`: `draft | split_ready | blocked_*`
- `parent_requirement`:
- `requirement_package`:

## 导航摘要

- `one_line_purpose`:
- `primary_surface_or_actor`:
- `recommended_read_order`: `README.md -> requirement-slice.md -> api-contract-mapping.md -> dependency.json -> traceability.json -> decisions.md`

## 能力概况

- `contains_page_states`: `true | false`
- `contains_shared_state`: `true | false`
- `contains_integration`: `true | false`
- `contains_infra_only`: `true | false`
- `boundary_note`:

## 顶层需求覆盖

<!-- 映射此子需求所覆盖的确切顶层来源片段。不要将多个来源片段合并为一个模糊的项目符号。 -->

### 覆盖项 1

- `source_ref`:
- `coverage_status`: `covered | partial | deferred | blocked`
- `why_in_this_subreq`:
- `copied_or_linked_in`:

## 关键逐字需求摘录

<!-- 按原样复制原始需求文本。先引用，再总结。 -->

### 摘录 1

- `source_ref`:
- `usage_in_this_subreq`:
- `quoted_text`:

> `<在此处按原样复制原始需求文本>`

## 子需求陈述

<!-- 此部分可以规范化措辞，但每个陈述必须指明其来源依据。 -->

- `statement`:
- `source_basis`:
- `normalization_note`:

## 边界

### 范围内

- `statement`:
- `source_ref`:

### 范围外

- `statement`:
- `source_ref`:

### 输入

- `input`:
- `source_ref`:

### 输出

- `output`:
- `source_ref`:

### 非目标

- `non_goal`:
- `source_ref`:

## 依赖关系

### 依赖项

- `dependency`:
- `why`:
- `source_ref`:

### 阻塞项

- `downstream_item`:
- `why`:
- `source_ref`:

## 交付切片候选

### 候选 1

- `candidate_id`:
- `candidate_type`: `page-state | shared-state | integration`
- `owned_truth`:
- `why_now`:
- `freeze_later_at`: `ui-acceptance-contract | ui-interaction-design | n/a`
- `source_basis`:

## 带有来源链接的验收信号

<!-- 每个验收信号必须指向具体的源片段或引用的摘录。 -->

### 信号 1

- `signal`:
- `source_ref`:
- `derived_from`: `quoted excerpt | normalized statement`
- `notes`:

## 未解决问题

### 问题 1

- `question`:
- `why_open`:
- `blocking_status`: `non_blocking | blocks_acceptance_contract | blocks_slice_synthesis | blocked`
- `related_source_ref`:

## 压缩警告

<!-- 记录任何规范化可能压缩了细微差别、合并了条件或丢失了来源细节的地方。 -->

### 警告 1

- `risk`:
- `affected_source_ref`:
- `mitigation`: `copied verbatim | kept open | blocked`
- `follow_up_owner`:

## 当前状态

- `status`:
- `status_reason`:
- `next_safe_handoff`:

---

## 模板编写规则

1. `README.md` 是人类可读的导航文档。保持简洁，但绝不能没有来源支持。
2. 在"子需求陈述"中规范化关键源文本之前，先复制或引用它。
3. "顶层需求覆盖"应显示哪些原始段落或项目符号被拉入此子需求。如果一个源片段与另一个子需求共享，请说明，而不是静默改写。
4. "关键逐字需求摘录"应保留下游读者通过摘要可能丢失的原始措辞。
5. 每个"范围内"、"范围外"、依赖项和验收项都应指明 `source_ref`。
6. 当顶层来源内容密集、跨领域或包含可能在简化时丢失的条件时，使用"压缩警告"。
7. 不要将"模板编写规则"或"模板示例"部分复制到生成的子需求工件中。

## 模板示例

```md
# `profile-settings-edit-form` `Profile Settings Edit Form`

## 元数据
- `subreq_id`: `profile-settings-edit-form`
- `title`: `Profile Settings Edit Form`
- `type`: `Feature Module`
- `status`: `draft`
- `parent_requirement`: `account-settings`
- `requirement_package`: `.ai-delivery/requirements/account-settings/`

## 导航摘要
- `one_line_purpose`: `涵盖从个人设置屏幕编辑个人资料名称和头像。`
- `primary_surface_or_actor`: `个人设置上的已登录用户`
- `recommended_read_order`: `README.md -> requirement-slice.md -> api-contract-mapping.md -> dependency.json -> traceability.json -> decisions.md`

## 能力概况
- `contains_page_states`: `true`
- `contains_shared_state`: `false`
- `contains_integration`: `false`
- `contains_infra_only`: `false`
- `boundary_note`: `拥有一个承载页面的需求面，并将跨面传播推迟。`

## 顶层需求覆盖
### 覆盖项 1
- `source_ref`: `requirement.md#L12-L16`
- `coverage_status`: `covered`
- `why_in_this_subreq`: `这些行定义了设置表单的可编辑字段和保存门控。`
- `copied_or_linked_in`: `关键逐字需求摘录 > 摘录 1；子需求陈述；带有来源链接的验收信号 > 信号 1`

## 关键逐字需求摘录
### 摘录 1
- `source_ref`: `requirement.md#L12-L16`
- `usage_in_this_subreq`: `在规范化之前保留确切的保存门控行为。`
- `quoted_text`:
> 用户可以从个人设置屏幕编辑他们的个人资料名称和头像。保存保持禁用状态，直到存在有效更改。

## 子需求陈述
- `statement`: `此切片涵盖个人设置编辑表单，包括个人资料名称和头像编辑，以及在存在有效更改之前的禁用保存门控。`
- `source_basis`: `摘录 1`
- `normalization_note`: `未添加业务规则；仅将两个句子分组为一个切片级陈述。`

## 边界
### 范围内
- `statement`: `从个人设置编辑个人资料名称和头像。`
- `source_ref`: `requirement.md#L12-L13`

### 范围外
- `statement`: `密码变更和账户删除流程。`
- `source_ref`: `requirement.md#L20-L24`

### 输入
- `input`: `当前个人资料名称、选定的头像图片、编辑后的个人资料名称。`
- `source_ref`: `requirement.md#L12-L18`

### 输出
- `output`: `成功保存后更新的个人资料值。`
- `source_ref`: `requirement.md#L17-L18`

### 非目标
- `non_goal`: `如果顶层需求从未提及，则不定义图片裁剪行为。`
- `source_ref`: `requirement.md#L12-L18`

## 依赖关系
### 依赖项
- `dependency`: `profile-settings-shell`
- `why`: `编辑表单位于现有设置外壳内。`
- `source_ref`: `requirement.md#L10-L11`

### 阻塞项
- `downstream_item`: `profile-settings-figma-mapping`
- `why`: `UI 映射应绑定到相同的字段和保存状态契约。`
- `source_ref`: `requirement.md#L12-L16`

## 交付切片候选
### 候选 1
- `candidate_id`: `profile-settings-edit-idle`
- `candidate_type`: `page-state`
- `owned_truth`: `个人设置编辑屏幕的默认可编辑状态。`
- `why_now`: `需求已经稳定了屏幕参与者和字段组。`
- `freeze_later_at`: `ui-acceptance-contract`
- `source_basis`: `摘录 1`

## 带有来源链接的验收信号
### 信号 1
- `signal`: `当没有有效更改时，保存保持禁用状态。`
- `source_ref`: `requirement.md#L14-L16`
- `derived_from`: `quoted excerpt`
- `notes`: `这应保持逐字不变，因为保存门控容易被过度概括。`

## 未解决问题
### 问题 1
- `question`: `头像上传失败是否会保留表单中已编辑的个人资料名称？`
- `why_open`: `顶层需求定义了编辑能力，但未定义混合成功和失败的行为。`
- `blocking_status`: `blocks_slice_synthesis`
- `related_source_ref`: `requirement.md#L12-L18`

## 压缩警告
### 警告 1
- `risk`: `将名称编辑和头像编辑合并到一个切片中可能会隐藏它们是独立保存还是一起保存。`
- `affected_source_ref`: `requirement.md#L12-L18`
- `mitigation`: `kept open`
- `follow_up_owner`: `requirement-breakdown`

## 当前状态
- `status`: `draft`
- `status_reason`: `核心范围清晰，但保存耦合行为仍未确定。`
- `next_safe_handoff`: `在提升为 split_ready 之前，解决混合成功问题。`
```
