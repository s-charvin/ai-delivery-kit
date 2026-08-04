# 第五轮压力测试总报告:全流程灵活性与角色缺位

> **文档性质**:对《coordination-platform-prd.md》v3.0 的第五轮压力测试汇总
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:架构评审输入
> **父文档**:[coordination-platform-prd.md](../coordination-platform-prd.md)
> **测试方法**:聚焦"全流程开发"中**角色缺位、人员交接、多源头并行、可选依赖**四类真实场景,验证需求 1"通用性"
> **场景文件**:
> - [scenario-role-absence.md](./scenario-role-absence.md)(A37-A39)
> - [scenario-owner-handover.md](./scenario-owner-handover.md)(A40)
> - [scenario-multi-source-optional-dep.md](./scenario-multi-source-optional-dep.md)(A41)

---

## 1. 测试覆盖

| 场景 | 主题 | 参与角色 | 缺失角色/维度 | 缺陷数 | Critical | High |
|---|---|---|---|---|---|---|
| A37 | 纯 UI 驱动(banner 换皮) | design + client | product + server | 4 | 1 | 1 |
| A38 | 纯服务端(数据清洗) | product + server | design + client | 3 | 0 | 1 |
| A39 | 纯客户端逻辑(埋点/网络层) | client(可选 product) | product + design + server | 5 | 1 | 3 |
| A40 | 产品 owner 交接(3 子场景) | product(A→B) | — | 10 | 1 | 6 |
| A41 | 多源头 + 可选依赖 | product + research + server + client | — | 10 | 2 | 4 |
| **合计** | **5 场景** | — | — | **32** | **5** | **15** |

**严重度分布**:5 Critical / 15 High / 12 Medium / 2 Low

---

## 2. 五大根因

第五轮 32 个缺陷可归为 5 大根因,均与"通用性"诉求直接相关:

### 根因 1:PRD 隐含"4 角色全参与 + product 唯一起点"假设(12 缺陷)

**表现**:
- A37 纯 UI 管线无 product_spec,DAG 根节点缺失,bootstrap_node 不知从何起
- A38 纯服务端管线无 design/client,但 server_impl 默认下游是 client_func,叶子节点无下游无法触发交付
- A41 多源头(product_spec + research_spike 并行),DAG 假设单根
- A39 client_func 强依赖 design_asset,纯逻辑功能无法独立存在

**根因**:PRD §2.1 节点类型清单和 §FR2.4 bootstrap_node 隐含"所有角色都参与、product_spec 是唯一源头"的工程假设,与需求 1"通用性"冲突。

### 根因 2:skill.deps 是静态硬约束,不支持条件依赖(8 缺陷)

**表现**:
- A37 design-handoff-skill.deps 硬编码 `[product_spec]`,纯 UI 管线无 product_spec 时 skill 无法匹配(Critical)
- A39 client-delivery-skill.deps 硬编码 `[client_ui, server_impl]`,纯逻辑功能无 UI 无 server 时阻断(Critical)
- A41 client-ui-skill.deps 硬编码 `[api_contract, design_asset]`,可选依赖 design_asset 时 skill 不知如何处理

**根因**:Constraint Skill 的 deps 字段是"静态全量依赖",不支持"条件依赖"(required: false + condition)。

### 根因 3:RoleInstance 团队级实例化,无人员级 owner 概念(7 缺陷)

**表现**:
- A40 产品经理 A 离职 B 接手,RoleInstance 只到团队级,无 owner 转移机制
- A40 子场景 2(B 部分认同):无"轻量补充"机制,要么不改要么触发 changed 全链路回滚
- provenance.submitter 是不可变历史,当前 owner 变了无法表达
- token/权限/agent 上下文(decision_log)无传承机制

**根因**:RoleInstance 解决了"多团队"(组织维度),但没解决"同团队内人员交接"(个人维度)——两者正交。

### 根因 4:DAG 级联和终止条件不支持"可选节点"(5 缺陷)

**表现**:
- A41 design_asset 是可选依赖,未 done 时 client_ui 是否 ready?级联公式未定义
- A41 optional dep 后到(已 done 下游是否 re-evaluate)?无机制
- A37/A39 可选角色未参与时,管线能否终止?AC2.7"全节点 done"会阻塞
- fork(全 done)和 optional(可选)语义混淆

**根因**:DAG 模型是"全量依赖 + 全 done 终止",不支持"部分依赖可选 + 部分节点可跳过"。

### 根因 5:节点类型清单不够通用,缺关键节点类型(3 缺陷)

**表现**:
- A39 纯客户端逻辑(埋点/网络层)无对应节点类型,client_func 是"UI 联调"不匹配
- A38 纯服务端管线无 server_delivery 节点(对称补全 client_delivery)
- A41 research_spike 虽在 PRD 但未在主节点类型清单(§2.1)中明确列出

**根因**:节点类型清单仍偏向"标准 4 角色全参与流程",未充分覆盖"角色缺位"场景的产物类型。

---

## 3. P0 修正项(17 项