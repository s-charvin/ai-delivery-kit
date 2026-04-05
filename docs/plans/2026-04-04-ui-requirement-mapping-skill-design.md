# UI Requirement Mapping Skill Design

## Skill Name

- `ui-requirement-mapping`

## Goal

将子需求的功能切片与 Figma 设计证据做双向绑定，生成后续开发可直接消费的一比一实现依据。

## Position In The Workflow

该 skill 位于：

- `requirement-breakdown` 之后
- `ui-interaction-design` 之前
- `Spec Kit Phase` 之前

## References And Upstream Dependencies

主参考：

- `figma`
- `figma-implement-design`

依赖：

- `requirement-breakdown`
- 已存在的 `requirement-slice.md`

## Responsibilities

- 读取子需求切片
- 拉取并缓存 Figma 结构、节点、截图、注释、token
- 建立 `Requirement <-> Figma Node` 双向映射
- 识别本子需求必做 UI
- 识别因高保真还原必须伴随实现的 UI
- 输出一比一实现依据
- 发现冲突时进入阻塞态

## Non-Responsibilities

- 不生成最终代码
- 不新增页面、字段、组件、状态
- 不把缺失设计稿的部分按常识补上
- 不把视觉差异解释为业务真相

## Inputs

必需输入：

- `subreq-id`
- Figma file/link 或已绑定 Figma file
- 对应子需求目录

可选输入：

- 指定节点列表
- token 文件
- 注释导出

## Figma Retrieval Rules

取数顺序固定为：

1. 先获取结构化设计上下文
2. 必要时获取 metadata 缩小范围
3. 再获取 screenshot
4. 最后处理 asset / token / comment

没有 screenshot 时，不得判定“映射已完成”。

## Cache Layout

原始证据缓存：

```text
.ai-delivery/figma-cache/<figma-file-id>/
├── structure.json
├── nodes/<node-id>.json
├── screenshots/<node-id>.png
├── comments/<node-id>.json
└── tokens/<token-set>.json
```

子需求消费结果：

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── figma-mapping.md
├── traceability.json
└── decisions.md
```

## Cache Policy

默认策略：

- 优先读缓存
- 不重复请求 Figma

仅以下情况强制刷新：

- 用户明确要求刷新
- 缓存缺失
- 缓存版本落后于指定设计版本
- 关键节点损坏或取数失败

## Governed Admin Contract

当 admin 治理面可用时，本 skill 依赖其支持以下受控写入：

- `figma-mapping.md`
- `traceability.json`
- `decisions.md`
- 与 `figma_mapped` 相关的状态流转
- 与设计冲突相关的 blocker 写入与恢复

其中：

- `traceability.json` 必须被视为一等治理对象
- 不允许因为它是 JSON 就绕过治理面直接把映射真相藏进本地 sidecar

对于 `figma-cache/`：

- admin 主要负责读取、索引、freshness 判断
- raw screenshot、node dump、token 文件仍属于项目内原始证据，不走通用文档编辑模式

## Mapping Output Requirements

### `figma-mapping.md`

至少包含：

- 对应 Figma file / frame / node
- 每个需求点映射到哪些设计节点
- 每个设计节点属于哪个需求点
- 必做 UI 清单
- 伴随实现 UI 清单
- 缺失设计证据清单
- 冲突清单

### `traceability.json`

至少包含：

- `requirement_refs`
- `figma_nodes`
- `mapping_type`
- `confidence`
- `conflicts`
- `last_verified_at`

## Dual Source Rules

- `Requirement` 管功能真相
- `Figma` 管视觉真相

对应阻塞规则：

- Requirement 有功能但 Figma 无视觉承载：`blocked_missing_design`
- Figma 有明显视觉/状态但 Requirement 明确排除：`blocked_requirement_figma_conflict`
- 关键节点无法验证：保持阻塞，不允许继续推进

## Shared Node Rule

如果一个视觉节点属于多个子需求：

- 必须显式记录共享归属
- 必须在 `traceability.json` 中登记
- 不允许因为“方便实现”就隐式吞掉边界

## Executable Node Rule

- 不允许使用顶层大 `SECTION` 作为最终执行节点
- 必须收敛到真实可实现的 frame / component / region
- 不允许仅凭节点名完成映射
- 必须有结构化上下文或 screenshot 佐证

## Companion UI Rule

如果某个 UI 区域与当前主节点强耦合，拆开会破坏一比一还原，则可记为：

- `伴随实现 UI`

但伴随实现 UI 只代表视觉交付边界完整，不代表业务范围扩大。

所有伴随实现项都必须写入 `figma-mapping.md`。

## Completion Criteria

完成时必须满足：

- 子需求至少绑定一个已验证 Figma 节点
- 已有 screenshot 与结构化设计上下文
- Requirement/Figma 双向映射可读可查
- 所有冲突要么阻塞，要么已有人工决议
- 子需求状态可以推进到 `figma_mapped`

## Recovery Rule

如果本 skill 因设计冲突或证据缺失进入阻塞态：

- 恢复动作应通过受控 blocker / status 恢复路径完成
- 不应靠手工改写 `status.json` 假装已经恢复
