# 框架指南：OpenSpec

已安装 OpenSpec 时，`spec` / `plan` / `tasks` 动作使用本档位。OpenSpec 是轻量的 delta-spec 工作流，非常适合棕地仓库。

## 检测标志

- 仓库根存在 `openspec/` 目录（`openspec/specs/`、`openspec/changes/`），或
- PATH 上有 `openspec` CLI。

绝不自行初始化或安装 OpenSpec；检测不明确时询问用户一次，并把答案记入 `decisions.md`。

## 覆盖的动作

每个子需求对应一个 OpenSpec change：`openspec/changes/<subreq-id-slug>/`。

| 动作 | OpenSpec 用法 | 输出产物 |
|------|---------------|----------|
| `spec` | 创建变更提案：问题、动机、拟议行为 delta | `openspec/changes/<name>/proposal.md`（+ `specs/` 下的能力规格 delta） |
| `plan` | 变更的技术设计 | `openspec/changes/<name>/design.md` |
| `tasks` | 实现清单 | `openspec/changes/<name>/tasks.md` |

## 使用意见

- change 以子需求命名（如 `sr-001-friend-badge`），保持映射一目了然。
- 以 `requirement-slice.md` 为种子起草 proposal；UI truth 切片中，冻结宿主组件 + 已确认 previews 仍是视觉真值。引用每个 v2 unit/scenario id 及其证据来源；描述运行时行为与验收，不重复 Runtime Coverage 细节。
- 推进状态前先验证：`openspec validate <name>`（CLI 存在时）+ 人工对照切片范围审计。
  - proposal 在全部 state/content/motion/assets/accessibility 预期均映射到 unit/scenario id 后被接受 → `spec_ready`
  - `design.md` 对 scenario 实现与验证归属审计通过 → `plan_ready`
  - `tasks.md` 对粒度、依赖顺序、文件范围，以及完整的 scenario 到测试/验收覆盖审计通过 → `tasks_ready`
- 切片合并后执行归档步骤（`openspec archive <name>`），让 delta 落入 `openspec/specs/`。只在 `merged` 之后归档，并在那时把归档后的规格路径记入 `traceability.json`。
- change 与冻结契约或需求冲突时，开启 `blocked_spec_mismatch`，而不是反复改 delta 直到"通过"。

## 可追溯性记录

子需求 `traceability.json`：

- `spec_refs.tier`：`"openspec"`
- `spec_refs.spec_path`：`openspec/changes/<name>/proposal.md`
- `spec_refs.plan_path`：`openspec/changes/<name>/design.md`
- `spec_refs.tasks_path`：`openspec/changes/<name>/tasks.md`
- `source_index.spec`：每个产物一条记录，`ref_type` 为 `spec` / `plan` / `tasks`

## 边界

- 一个子需求一个 change；不要把多个切片合并进一个 change。
- OpenSpec 只覆盖规格类动作；`implement` / `finish` 按 [../framework-adaptation.md](../framework-adaptation.md) 分发给 superpowers、ECC 或原生档。
