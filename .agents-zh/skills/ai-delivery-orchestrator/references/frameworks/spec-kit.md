# 框架指南：spec-kit

已安装 spec-kit 时，`spec` / `plan` / `tasks` 动作使用本档位。

## 检测标志

- 仓库根存在 `.specify/` 目录，或
- PATH 上有 `specify` CLI。

若 `.specify/` 存在但 CLI 缺失或损坏，受影响的子需求降级到原生档，并在 `decisions.md` 记录原因。绝不自行重装或升级 spec-kit。

## 覆盖的动作

| 动作 | spec-kit 用法 | 输出产物 |
|------|---------------|----------|
| `spec` | 以 `requirement-slice.md`（UI 切片另附已评审的 `ui-contract.html`）为种子执行 `/speckit-specify` | spec-kit feature 分支区（`.specify/`）下的 `spec.md` |
| `plan` | `/speckit-plan` | `plan.md` |
| `tasks` | `/speckit-tasks` | `tasks.md` |

## 使用意见

- 喂给 spec-kit 的是治理输入而非自由文本：`requirement-slice.md`、每个单元的冻结 `ui-contract.html`（含 UI 时）、可用时的 API 文档，以及依赖图。
- 含 UI 的切片，spec-kit 的输入就是已评审的 `ui-contract.html`；不要再写第二份可能与契约漂移的视觉描述。
- 推进状态前逐一审计输出：
  - `spec.md` → 对照 HTML 契约的状态审计（UI）→ `spec_ready`
  - `plan.md` → 审计交付切片顺序 → `plan_ready`
  - `tasks.md` → 审计粒度、依赖顺序、文件范围 → `tasks_ready`
- 生成产物与冻结契约或需求冲突时，开启 `blocked_spec_mismatch`；不要悄悄改契约去迁就。

## Constitution 处理

spec-kit 项目可能定义了 constitution。在不与 `.ai-delivery` 治理真值冲突时尊重它。冲突时以 `.ai-delivery` 真值为准，并在 `decisions.md` 记录冲突。

## 可追溯性记录

子需求 `traceability.json`：

- `spec_refs.tier`：`"spec-kit"`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`：生成的 `spec.md` / `plan.md` / `tasks.md` 路径
- `source_index.spec`：每个产物一条记录，`ref_type` 为 `spec` / `plan` / `tasks`

## 边界

- 不要在仓库内 fork 或复述官方 `speckit-*` 技能。
- 设计批准（`design_approved: true`）前不得启动 `speckit-*` 步骤；UI 切片还必须先 `acceptance_frozen`。
- spec-kit 只覆盖规格类动作；`implement` / `finish` 按 [../framework-adaptation.md](../framework-adaptation.md) 分发给 superpowers、ECC 或原生档。
