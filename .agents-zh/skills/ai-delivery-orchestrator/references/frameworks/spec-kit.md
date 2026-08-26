# 框架指南：spec-kit

已安装 spec-kit 时，`spec` / `plan` / `tasks` 动作使用本档位。

## 检测标志

- 仓库根存在 `.specify/` 目录，或
- PATH 上有 `specify` CLI。

若 `.specify/` 存在但 CLI 缺失或损坏，受影响的子需求降级到原生档，并在 `decisions.md` 记录原因。绝不自行重装或升级 spec-kit。

## 覆盖的动作

| 动作 | spec-kit 用法 | 输出产物 |
|------|---------------|----------|
| `spec` | 对 `requirement-slice.md` 应用 `/speckit-specify` 的推理方式（UI 切片另附已评审的冻结宿主组件 / `ui-truth-index.json`） | 由 layout key `spec` 解析的路径（默认 `spec/spec.md`） |
| `plan` | 应用 `/speckit-plan` 的推理方式 | 由 layout key `plan` 解析的路径（默认 `spec/plan.md`） |
| `tasks` | 应用 `/speckit-tasks` 的推理方式 | 由 layout key `tasks` 解析的路径（默认 `spec/tasks.md`） |

## 产物边界

- 使用 `speckit-*` skill 或命令前，通过编排器 layout resolver 从 `.ai-delivery/meta/project-binding.json` 解析 layout key `spec`、`plan`、`tasks`，再传入这些准确的仓库相对 canonical 路径。默认后缀是 `spec/spec.md`、`spec/plan.md`、`spec/tasks.md`；定制 binding 时不得用默认值替代。
- `.specify/**` 只用于检测或读取配置。不得在其中新增或更新 feature spec、plan、tasks、检查清单、状态或代理元数据。
- 若 `speckit-*` 命令坚持写入 `.specify/**` 且不接受 canonical 映射，则不调用该持久化步骤；在当前会话应用相同流程，并把结果直接写入 `.ai-delivery`。
- 禁止先写 `.specify/**` 再复制回 canonical。推进状态前执行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。

## 使用意见

- 喂给 spec-kit 的是治理输入而非自由文本：`requirement-slice.md`、每个启用 UI truth 的单元的冻结宿主组件 / `ui-truth-index.json`、可用时的 API 文档，以及依赖图。
- UI truth 切片的 spec-kit 输入就是已评审的冻结宿主组件 + v2 `ui-truth-index.json`；引用每个 unit/scenario id 及其证据来源，不要再写第二份可能与契约漂移的视觉描述。
- 推进状态前逐一审计输出：
  - `spec.md` → 对照每个已冻结 unit/scenario id 审计状态转换、内容策略、动效、资源、无障碍与验收标准（UI）→ `spec_ready`
  - `plan.md` → 审计交付切片顺序与 scenario 的实现/验证归属 → `plan_ready`
  - `tasks.md` → 审计粒度、依赖顺序、文件范围，以及完整的 scenario 到测试/验收覆盖 → `tasks_ready`
- 生成产物与冻结契约或需求冲突时，开启 `blocked_spec_mismatch`；不要悄悄改契约去迁就。

## Constitution 处理

spec-kit 项目可能定义了 constitution。在不与 `.ai-delivery` 治理真值冲突时尊重它。冲突时以 `.ai-delivery` 真值为准，并在 `decisions.md` 记录冲突。

## 可追溯性记录

子需求 `traceability.json` 只使用 canonical `artifacts[]` 结构。每个 `kind`（`spec`、`plan`、`tasks`）都添加一个字段完整的对象；不得写 legacy path 字段：

```json
{
  "spec_refs": {
    "tier": "spec-kit",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": "<由 layout key spec 解析出的仓库相对路径>",
        "derived_paths": [],
        "content_sha256": "<canonical 内容的 sha256>",
        "sync_state": "synced"
      }
    ]
  }
}
```

另为每个产物添加一条 `source_index.spec` 记录，`ref_type` 为 `spec` / `plan` / `tasks`。

## 边界

- 不要在仓库内 fork 或复述官方 `speckit-*` 技能。
- 不得让 spec-kit 在 `.ai-delivery/` 之外持久化流程/治理产物。
- `design_mode=full` 审批未满足（`design_approved: false`）前不得启动 `speckit-*` 步骤；UI truth 切片还必须先 `acceptance_frozen`。
- spec-kit 只覆盖规格类动作；`implement` / `finish` 按 [../framework-adaptation.md](../framework-adaptation.md) 分发给 superpowers、ECC 或原生档。
