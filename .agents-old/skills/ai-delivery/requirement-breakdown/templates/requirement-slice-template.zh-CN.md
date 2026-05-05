<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# 需求切片

## 元数据

- `requirement_id`:
- `subreq_id`:
- `title`:
- `type`:
- `status`:
- `parent_requirement`:
- `source_coverage_status`: `complete | partial | blocked`
- `split_readiness_note`:

## 能力概况

<!-- 标记此子需求拥有的能力面，以便下游阶段知道稍后应冻结屏幕契约、共享传播还是集成行为。 -->

- `contains_page_states`: `true | false`
- `contains_shared_state`: `true | false`
- `contains_integration`: `true | false`
- `contains_infra_only`: `true | false`
- `boundary_note`:

## 源需求覆盖

<!-- 详尽映射此切片所依赖的每个顶层来源片段。如果一个片段与另一个切片共享，请明确说明。 -->

### 覆盖项 1

- `source_ref`:
- `coverage_kind`: `direct | shared_rule | partial | unresolved`
- `coverage_status`: `covered | deferred | blocked`
- `mapped_into`:
- `notes`:

## 逐字源摘录

<!-- 此部分对于任何可能达到 split_ready 的切片都是必需的。在总结之前复制原始措辞。 -->

### 摘录 1

- `source_ref`:
- `why_preserved_verbatim`:
- `quoted_text`:

> `<在此处按原样复制原始需求文本>`

## 规范化切片陈述

<!-- 仅在上方保留原始文本之后进行规范化。不要引入新的业务真相。 -->

- `statement`:
- `source_basis`:
- `normalization_type`: `none | wording cleanup | merged adjacent lines | partial extraction`
- `normalization_note`:

## 范围边界

### 范围内

- `statement`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`

### 范围外

- `statement`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`

### 输入

- `input`:
- `source_ref`:

### 输出

- `output`:
- `source_ref`:

### 非目标

- `non_goal`:
- `source_ref`:

## 依赖契约

### 依赖项

- `dependency`:
- `why`:
- `source_ref`:

### 阻塞项

- `downstream_item`:
- `why`:
- `source_ref`:

### 外部约束

- `constraint`:
- `source_ref`:

## 交付切片候选

<!-- 现在记录可能的执行切片，但在后续契约阶段之前不要冻结最终的页面状态切片。 -->

### 候选 1

- `candidate_id`:
- `candidate_type`: `page-state | shared-state | integration`
- `owned_truth`:
- `why_now`:
- `freeze_later_at`: `ui-acceptance-contract | ui-interaction-design | n/a`
- `source_basis`:

## 验收信号

### 信号 1

- `signal`:
- `source_ref`:
- `derived_from`: `verbatim excerpt | normalized statement`
- `verification_note`:

## 未解决问题

### 问题 1

- `question`:
- `why_open`:
- `blocking_status`: `non_blocking | blocks_acceptance_contract | blocks_slice_synthesis | blocked`
- `related_source_ref`:

## 歧义和冲突

### 项 1

- `issue`:
- `conflict_type`: `source ambiguity | source conflict | shared-rule overlap | missing business fact`
- `related_source_ref`:
- `resolution_path`:

## 压缩警告

### 警告 1

- `risk`:
- `affected_source_ref`:
- `what_was_compressed`:
- `mitigation`: `copied verbatim | left unresolved | blocked`

## 源需求参考索引

- `source_ref`:
- `used_in_sections`:

---

## 模板编写规则

1. `requirement-slice.md` 是子需求的权威下游契约。应以最小压缩保留顶层需求含义。
2. 详尽填写"源需求覆盖"。如果一个顶层片段对此切片重要，即使它也被另一个切片或全局规则使用，也必须在此出现。
3. "逐字源摘录"在将切片提升为 `split_ready` 之前是必需的。严格按原样引用关键源文本。
4. "规范化切片陈述"可以提高可读性，但不能取代摘录或编造产品真相。
5. 每个范围项、依赖项、验收信号和未解决问题都应可追溯到 `source_ref`。
6. "歧义和冲突"应捕获不稳定或冲突的真相，而不是平滑处理。
7. "压缩警告"应指出切片结构可能压缩顶层需求细微差别的地方。
8. 不要将"模板编写规则"或"模板示例"部分复制到生成的切片工件中。

## 模板示例

```md
# 需求切片

## 元数据
- `requirement_id`: `account-settings`
- `subreq_id`: `profile-settings-edit-form`
- `title`: `Profile Settings Edit Form`
- `type`: `Feature Module`
- `status`: `draft`
- `parent_requirement`: `account-settings`
- `source_coverage_status`: `partial`
- `split_readiness_note`: `需要确定头像上传失败是否保留已编辑的名称输入。`

## 能力概况
- `contains_page_states`: `true`
- `contains_shared_state`: `false`
- `contains_integration`: `false`
- `contains_infra_only`: `false`
- `boundary_note`: `此切片拥有一个承载页面的编辑面，但不拥有跨页面传播真相。`

## 源需求覆盖
### 覆盖项 1
- `source_ref`: `requirement.md#L12-L16`
- `coverage_kind`: `direct`
- `coverage_status`: `covered`
- `mapped_into`: `逐字源摘录 > 摘录 1；规范化切片陈述；范围边界 > 范围内；验收信号 > 信号 1`
- `notes`: `核心编辑表单和保存门控需求。`

### 覆盖项 2
- `source_ref`: `requirement.md#L17-L18`
- `coverage_kind`: `partial`
- `coverage_status`: `deferred`
- `mapped_into`: `未解决问题 > 问题 1；压缩警告 > 警告 1`
- `notes`: `提到了成功和失败行为，但确切的结果处理方式不清楚。`

## 逐字源摘录
### 摘录 1
- `source_ref`: `requirement.md#L12-L16`
- `why_preserved_verbatim`: `保存门控如果过于激进而被概括，容易被扭曲。`
- `quoted_text`:
> 用户可以从个人设置屏幕编辑他们的个人资料名称和头像。保存保持禁用状态，直到存在有效更改。

### 摘录 2
- `source_ref`: `requirement.md#L17-L18`
- `why_preserved_verbatim`: `保留确切的失败措辞以供后续澄清。`
- `quoted_text`:
> 如果头像上传失败，显示可重试错误并让用户保持在上下文中。

## 规范化切片陈述
- `statement`: `此切片涵盖从个人设置编辑个人资料名称和头像，包括在存在有效更改之前的禁用保存门控。`
- `source_basis`: `摘录 1`
- `normalization_type`: `merged adjacent lines`
- `normalization_note`: `未添加新规则；相邻行被合并为一个切片级陈述。`

## 范围边界
### 范围内
- `statement`: `个人资料名称编辑交互。`
- `source_ref`: `requirement.md#L12-L16`
- `derived_from`: `verbatim excerpt`

- `statement`: `头像编辑交互。`
- `source_ref`: `requirement.md#L12-L18`
- `derived_from`: `verbatim excerpt`

### 范围外
- `statement`: `密码重置和账户删除。`
- `source_ref`: `requirement.md#L20-L24`
- `derived_from`: `normalized statement`

### 输入
- `input`: `当前个人资料值、编辑后的名称值、选定的头像文件。`
- `source_ref`: `requirement.md#L12-L18`

### 输出
- `output`: `成功提交后保存的个人资料更改。`
- `source_ref`: `requirement.md#L17-L18`

### 非目标
- `non_goal`: `如果需求从未定义，则不要推断图片裁剪、调整大小或审核行为。`
- `source_ref`: `requirement.md#L12-L18`

## 依赖契约
### 依赖项
- `dependency`: `profile-settings-shell`
- `why`: `此表单托管在设置界面内。`
- `source_ref`: `requirement.md#L10-L11`

### 阻塞项
- `downstream_item`: `profile-settings-edit-figma-mapping`
- `why`: `下游映射必须保留相同的字段和保存状态契约。`
- `source_ref`: `requirement.md#L12-L16`

### 外部约束
- `constraint`: `在没有更清晰的产品真相时，不要重新定义上传重试行为。`
- `source_ref`: `requirement.md#L17-L18`

## 交付切片候选
### 候选 1
- `candidate_id`: `profile-settings-edit-idle`
- `candidate_type`: `page-state`
- `owned_truth`: `提交前可编辑的个人设置屏幕状态。`
- `why_now`: `需求已经建立了一个稳定的承载页面状态和字段集。`
- `freeze_later_at`: `ui-acceptance-contract`
- `source_basis`: `摘录 1`

## 验收信号
### 信号 1
- `signal`: `用户可以从个人设置编辑个人资料名称和头像。`
- `source_ref`: `requirement.md#L12-L13`
- `derived_from`: `verbatim excerpt`
- `verification_note`: `不要将两个可编辑字段合并为一个通用的"个人资料更新"标签。`

### 信号 2
- `signal`: `直到存在有效更改之前，保存保持禁用状态。`
- `source_ref`: `requirement.md#L14-L16`
- `derived_from`: `verbatim excerpt`
- `verification_note`: `保持门控规则的来源链接，因为它容易被规定不足。`

## 未解决问题
### 问题 1
- `question`: `当头像上传失败时，已编辑的名称是否应在本地保留并可保存？`
- `why_open`: `需求定义了可重试错误，但未定义部分成功行为。`
- `blocking_status`: `blocks_slice_synthesis`
- `related_source_ref`: `requirement.md#L17-L18`

## 歧义和冲突
### 项 1
- `issue`: `来源暗示了可重试的失败处理，但未说明保存是否在名称和头像更改之间是原子性的。`
- `conflict_type`: `source ambiguity`
- `related_source_ref`: `requirement.md#L17-L18`
- `resolution_path`: `保持为未解决问题，在耦合规则明确之前不要提升为 split_ready，如果下游映射依赖于它。`

## 压缩警告
### 警告 1
- `risk`: `名称编辑加头像编辑的单个切片可能压缩了这些编辑是一起提交还是独立提交。`
- `affected_source_ref`: `requirement.md#L12-L18`
- `what_was_compressed`: `提交耦合和混合成功行为。`
- `mitigation`: `left unresolved`

## 源需求参考索引
- `source_ref`: `requirement.md#L10-L11`
- `used_in_sections`: `依赖契约 > 依赖项`

- `source_ref`: `requirement.md#L12-L16`
- `used_in_sections`: `源需求覆盖；逐字源摘录；规范化切片陈述；范围边界；验收信号`

- `source_ref`: `requirement.md#L17-L18`
- `used_in_sections`: `源需求覆盖；逐字源摘录；输出；未解决问题；歧义和冲突；压缩警告`
```
