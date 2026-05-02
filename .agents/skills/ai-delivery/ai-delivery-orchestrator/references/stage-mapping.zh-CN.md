# 阶段映射

## 需求

- 阶段：`requirement-breakdown`
- 固定输入：顶层需求文档
- 固定输出根目录：`.ai-delivery/requirements/<requirement-id>/...`
- 完成守卫：需求包存在且子需求已创建

## API

- 阶段：`api-contract-mapping`
- 固定输入：
  - `requirement-slice.md`
  - `traceability.json`
  - `status.json`
  - API 合约
- 完成守卫：子需求达到 `api_mapped` 或显式阻塞状态

## UI 证据

- 阶段：`ui-requirement-mapping`
- 固定输入：
  - `requirement-slice.md`
  - `api-contract-mapping.md`
  - Figma 设计源
- 固定证据规则：
  - 如果目标是大型 `SECTION`，从 `get_structure` 开始
  - 最终可执行状态仍需 `get_code`
- 完成守卫：子需求达到 `figma_mapped`

## UI 冻结

- 阶段：`ui-acceptance-contract`
- 固定输入：
  - `requirement-slice.md`
  - `figma-mapping.md`
  - 最终状态 `get_code` 证据
- 固定输出：
  - `ui-acceptance-contract.yaml`
- 完成守卫：子需求达到 `acceptance_frozen`

## 交互与切片合成

- 阶段：`ui-interaction-design`
- 固定输入：
  - `requirement-slice.md`
  - `figma-mapping.md`
  - `ui-acceptance-contract.yaml`
  - `api-contract-mapping.md`
- 固定输出：
  - `interaction-design.md`
  - `delivery-slices/index.json`
- 完成守卫：子需求达到 `slices_ready`
- `ui-interaction-design` 也是当前的`交付切片合成`负责人。

## Spec Kit 桥梁

- 阶段：`prepare-speckit-context`
- 固定输入：
  - `slice-contract.md`
  - `interaction-design.md`
  - `traceability.json`
  - 对 UI 切片读取 `ui-acceptance-contract.yaml`
  - 当 API 影响存在时读取 `api-contract-mapping.md`
- 固定输出：
  - `spec-kit-input.md`
- 完成守卫：`spec-kit-input.md` 存在且与当前受管控的切片真实数据保持一致

## 官方 Spec Kit

- 阶段：
  - `speckit-specify`
  - `speckit-plan`
  - `speckit-tasks`
- 主要输入：
  - `spec-kit-input.md`
- 固定规则：
  - 官方 `speckit-*` 指令保持在上游，不会被修补以重述仓库本地合约
- 完成守卫：
  - 生成的 `spec.md`
  - 生成的 `plan.md`
  - 生成的 `tasks.md`

## Spec Kit 绑定

- 阶段族：
  - 绑定 spec
  - 绑定 plan
  - 绑定 tasks
- 固定输入：
  - `spec-kit-input.md`
  - 生成的 `spec.md`、`plan.md` 或 `tasks.md`
  - `traceability.json`
  - `status.json`
- 固定输出：
  - `spec-kit-binding.json`
  - 更新的 `traceability.json.spec_kit_refs`
- 完成守卫：
  - `spec_ready`
  - `plan_ready`
  - `tasks_ready`

## 开发

- 固定输入：
  - `slice-contract.md`
  - `tasks.md`
  - `spec-kit-binding.json`
  - 可追溯性引用
- 可选上下文：
  - 当宿主仓库已提供时，项目本地的 `.agents/AGENTS.md`
- 范围边界：
  - 开发委托仅允许用于当前活动的 `SR-*`
  - 交付切片仍是该 `SR-*` 内的实现单元，而非更深的受管控子需求层级
- 固定执行规则：
  - 仅使用文件范围的补丁编辑代码；不要发送一次性重写多个文件的补丁
  - 仅在第二阶段且当前活动的 `SR-*` 内至少有两个独立可运行的实现任务已满足其依赖关系时，才使用子智能体
  - 如果少于两个独立可运行的实现任务存在，则保持在主会话中
  - 如果委托工作使用工作树，先完成编码，然后按依赖顺序逐个将已完成的工作树分支变基并重新整合回当前开发分支
  - 在工作树重新整合期间保持提交历史线性；不要使用合并提交
- 有序阶段：
  - `using-git-worktrees`
  - `test-driven-development`
  - 实现
  - `requesting-code-review`
  - 视觉验收
  - `verification-before-completion`
- 完成守卫：切片达到 `merged`
- 包含 UI 的切片必须在合并完成前达到 `visual_acceptance_passed`。
