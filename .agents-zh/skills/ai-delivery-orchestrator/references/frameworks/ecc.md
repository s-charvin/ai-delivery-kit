# 框架指南：ECC

已安装 ECC 时，用于 `solution-design`、`implement` 和 `finish` 的设计、
执行与评审纪律。首次使用只读列出实际可用命令/agent，并在 `decisions.md`
记录映射；禁止猜测、安装或配置。

## 产物边界

- 调用前传入 canonical 根、输出映射和准确 workspace。ECC 只提供方法。
- 解析 layout key `solution_design`、`decisions`、`progress` 与
  `verification`；设计、评审 finding、fix brief、报告、checklist 与会话元数据
  只能写对应 canonical 路径。
- 无法遵守映射的持久化步骤不得运行；禁止先生成再搬运。
- 宿主树只允许写生产源码、项目原生测试、官方预览和运行时资源。

## 使用

- ECC 设计方法以需求切片、启用的 UI truth、API 和依赖图为输入，输出仍写唯一
  `design.md`。人工评审只由 `user_decision_required` 决定。
- 实现时从当前设计契约形成完整批次并默认 inline 实现；ECC review agent 承担新鲜上下文
  评审：实现 → finding → 修复 → 重新评审，直到 clean 或预算耗尽。
- UI truth 切片必须覆盖每个索引 scenario 并写结构化
  `visual-acceptance.json`；文件存在或单张截图不是验收。
- hook 失败属于验证失败，不能绕过。
- 多框架并存时只选当前动作最合适的方法；任何框架都不得新增 design/spec/plan/task
  持久化产物。

在 `traceability.json` `source_index.design` 记录实际 ECC 方法和 canonical
`design.md` 路径/hash；不生成 `spec_refs`。gate、blocker、status 和 merge
决定始终在主会话。

按 Stage 4 子代理及证据复用策略执行：已安装 agent 不触发强制委派或重复全量检查。默认同一实现者连续完成、独立集成批次评审，修复后只复审变化及关联影响。最终检查范围保持，核对输入与产物后复用有效结果，只补跑失效或缺失检查。
