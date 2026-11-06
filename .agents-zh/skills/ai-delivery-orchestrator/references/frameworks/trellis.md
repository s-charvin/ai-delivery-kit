# Trellis 有限适配

只复用已有规范及 before-dev/check/update-spec/break-loop 的方法，不执行 Trellis init、Task/journal、自动提交或默认代理派发。规范通过 [质量闭环](../delivery-quality-loop.md) 的 context.sources 引用，不复制正文。

- before-dev：映射既有 requirement/design 与四项执行 brief，按真实模块和 owner 读规范。
- check：从实际变更独立重算适用规范，核对原始需求、正式接线与原生结果。
- update-spec：在明确 writable 的唯一来源维护稳定知识，导入默认只读；不自行降标。
- break-loop：保留失败与用户原话，做能区分原因的检查，沿既有三轮预算处理。

检测到 Trellis 自动入口不代表它与 kit 兼容；出现任务权威竞争时明确诊断，保留用户配置。Channel 仅在用户已有环境、明确外部执行需要且权限/输入完整性通过验证后另行适配，不作为本闭环依赖。

Shopify Helix 的小步、同态取证与评审反馈归现有阶段规则；不存在可以直接调用的官方公开 Helix runtime。本适配不依赖同名社区实现，也不安装 Stop gate。
