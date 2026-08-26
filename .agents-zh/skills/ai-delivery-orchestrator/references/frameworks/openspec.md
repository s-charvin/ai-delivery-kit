# 框架指南：OpenSpec

已安装 OpenSpec 时，`spec` / `plan` / `tasks` 动作使用本档位。OpenSpec 是轻量的 delta-spec 工作流，非常适合棕地仓库。

## 检测标志

- 仓库根存在 `openspec/` 目录（`openspec/specs/`、`openspec/changes/`），或
- PATH 上有 `openspec` CLI。

绝不自行初始化或安装 OpenSpec；检测不明确时询问用户一次，并把答案记入 `decisions.md`。

## 覆盖的动作

| 动作 | OpenSpec 用法 | 输出产物 |
|------|---------------|----------|
| `spec` | 对切片应用 OpenSpec proposal/delta 推理 | 由 layout key `spec` 解析的路径（默认 `spec/spec.md`） |
| `plan` | 应用 OpenSpec 技术设计推理 | 由 layout key `plan` 解析的路径（默认 `spec/plan.md`） |
| `tasks` | 应用 OpenSpec 检查清单推理 | 由 layout key `tasks` 解析的路径（默认 `spec/tasks.md`） |

## 产物边界

- 使用 OpenSpec skill 或命令前，通过编排器 layout resolver 从 `.ai-delivery/meta/project-binding.json` 解析 layout key `spec`、`plan`、`tasks`，再传入这些准确的仓库相对 canonical 路径。默认后缀是 `spec/spec.md`、`spec/plan.md`、`spec/tasks.md`；定制 binding 时不得用默认值替代。
- `openspec/**` 只用于检测或读取配置。不得在其中创建 change 目录、proposal、design、tasks、archive、状态或代理/会话元数据。
- 若 OpenSpec 命令必须写入 `openspec/**` 且不接受 canonical 映射，则不调用该持久化步骤；在当前会话应用其 proposal/design/task 方法，并把结果直接写入 `.ai-delivery`。
- 禁止先建 OpenSpec change 再复制回 canonical。推进状态前执行 [../framework-adaptation.md](../framework-adaptation.md) 的产物边界审计。

## 使用意见

- 以 `requirement-slice.md` 为种子起草 canonical spec；UI truth 切片中，冻结宿主组件 + 已确认 previews 仍是视觉真值。引用每个 v2 unit/scenario id 及其证据来源；描述运行时行为与验收，不重复 Runtime Coverage 细节。
- 推进状态前先对照切片范围人工审计并运行 kit validator。只有 `openspec validate` 能直接验证 canonical 文件且不会创建或更新 `openspec/**` 时才运行；否则跳过并在 `decisions.md` 记录原因。
  - proposal 在全部 state/content/motion/assets/accessibility 预期均映射到 unit/scenario id 后被接受 → `spec_ready`
  - `design.md` 对 scenario 实现与验证归属审计通过 → `plan_ready`
  - `tasks.md` 对粒度、依赖顺序、文件范围，以及完整的 scenario 到测试/验收覆盖审计通过 → `tasks_ready`
- 不运行 `openspec archive`；它会在 `.ai-delivery` 外写第二份治理副本。只有编排器 `archive` 动作负责将 canonical 三件套 + `design.md` + `verification.md` 冻结到 `.ai-delivery/requirements/<req>/sub-requirements/<SR>/archive/<ISO-ts>/` 并生成 `MANIFEST.json`。
- change 与冻结契约或需求冲突时，开启 `blocked_spec_mismatch`，而不是反复改 delta 直到"通过"。

## 可追溯性记录

子需求 `traceability.json` 只使用 canonical `artifacts[]` 结构。每个 `kind`（`spec`、`plan`、`tasks`）都添加一个字段完整的对象；不得写 legacy path 字段：

```json
{
  "spec_refs": {
    "tier": "openspec",
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

- 每个子需求一套 canonical spec；不要把多个切片合并进同一套。
- 不得让 OpenSpec 在 `.ai-delivery/` 之外持久化流程/治理产物。
- OpenSpec 只覆盖规格类动作；`implement` / `finish` 按 [../framework-adaptation.md](../framework-adaptation.md) 分发给 superpowers、ECC 或原生档。
