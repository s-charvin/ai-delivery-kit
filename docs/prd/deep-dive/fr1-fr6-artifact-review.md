# PRD 深化:FR1 产物仓库管理 & FR6 产物审核机制

> **文档性质**:对主 PRD `coordination-platform-prd.md` 中 FR1 与 FR6 的深化补充
> **版本**:v1.0 | **日期**:2026-08-04 | **状态**:待评审
> **上游文档**:[coordination-platform-prd.md](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/prd/coordination-platform-prd.md)、[调研报告第25章](file:///Users/zuiyou/develop/skills/ai-delivery-kit/docs/research/ai-multi-agent-dev-dashboard-research.md)
> **深化范围**:目录规范、manifest schema、审核规则引擎、并发冲突、SLA、驳回重试、CI 校验

---

## 目录

- [1. 设计目标与深化边界](#1-设计目标与深化边界)
- [2. 产物仓库目录规范(细粒度)](#2-产物仓库目录规范细粒度)
  - [2.1 命名规则](#21-命名规则)
  - [2.2 版本化策略](#22-版本化策略)
  - [2.3 多产物共存](#23-多产物共存)
  - [2.4 目录结构演进](#24-目录结构演进)
- [3. manifest JSON Schema 完整定义](#3-manifest-json-schema-完整定义)
- [4. 审核规则引擎设计](#4-审核规则引擎设计)
  - [4.1 规则配置格式](#41-规则配置格式)
  - [4.2 规则优先级](#42-规则优先级)
  - [4.3 规则组合逻辑(AND/OR)](#43-规则组合逻辑andor)
  - [4.4 规则引擎执行模型](#44-规则引擎执行模型)
- [5. 并发审核冲突处理](#5-并发审核冲突处理)
  - [5.1 冲突场景分类](#51-冲突场景分类)
  - [5.2 锁机制设计](#52-锁机制设计)
  - [5.3 冲突检测与解决](#53-冲突检测与解决)
- [6. 审核 SLA 与超时升级策略](#6-审核-sla-与超时升级策略)
  - [6.1 SLA 分级](#61-sla-分级)
  - [6.2 自动审核超时](#62-自动审核超时)
  - [6.3 人工审核 SLA 与超时升级](#63-人工审核-sla-与超时升级)
- [7. 驳回后重试流程](#7-驳回后重试流程)
  - [7.1 驳回原因规范](#71-驳回原因规范)
  - [7.2 重试流程](#72-重试流程)
  - [7.3 历史追溯](#73-历史追溯)
- [8. 产物仓库 CI 校验](#8-产物仓库-ci-校验)
  - [8.1 CI 检查项](#81-ci-检查项)
  - [8.2 CI 失败处理](#82-ci-失败处理)
- [9. Mermaid 设计图](#9-mermaid-设计图)
  - [9.1 审核决策树(完整)](#91-审核决策树完整)
  - [9.2 并发冲突处理流程](#92-并发冲突处理流程)
  - [9.3 驳回重试流程](#93-驳回重试流程)
- [10. 与主 PRD 的对齐与修正](#10-与主-prd-的对齐与修正)

---

## 1. 设计目标与深化边界

### 1.1 深化目标

主 PRD 的 FR1/FR6 已定义"产物仓库受分支保护 + PR 审核 + skill 校验 + 合并推进"的主干流程,但以下 8 个薄弱点缺少落地级设计,本深化逐一补全:

| # | 薄弱点 | 本文章节 |
|---|---|---|
| 1 | 产物仓库目录规范的细粒度设计(命名/版本化/多产物共存/演进) | §2 |
| 2 | manifest schema 完整定义(字段/类型/约束/JSON Schema) | §3 |
| 3 | 审核规则引擎设计(规则可配置/优先级/AND-OR 组合) | §4 |
| 4 | 并发审核冲突处理(同节点多 PR/同产物多方提交/锁机制) | §5 |
| 5 | 审核超时与 SLA(自动审核超时/人工 SLA/升级) | §6 |
| 6 | 驳回后重试流程(驳回原因规范/重提/历史追溯) | §7 |
| 7 | 审核决策树完整图(所有审核路径) | §9.1 |
| 8 | 产物仓库 CI 校验(检查项/失败处理) | §8 |

### 1.2 不变的核心原则(继承自主 PRD)

- **产物内容存独立 git 仓库**,管理方只存引用(`repo + path + commit`)
- **所有产物 PR 需管理方审核**(skill 约束校验 + 依赖检查)才能合并
- **管理方不解析产物内容**,只校验元数据 + 文件格式
- **产物格式中立**(YAML/JSON/Markdown/Figma 链接均可)
- **合并即推进**:PR 合并后才触发 LangGraph `set_done + cascade`

### 1.3 与主 PRD 的关系

本深化是 FR1/FR6 的**补充细化**,不改变主干流程。涉及与主 PRD 不一致处,在 §10 明确列出修正项。实现时以本深化为准。

---

## 2. 产物仓库目录规范(细粒度)

主 PRD FR1.1 仅给出"按产物类型分目录 + 序号前缀文件名"的粗粒度结构,缺少命名规则、版本化、多产物共存与演进策略。本节细化。

### 2.1 命名规则

#### 2.1.1 目录命名

| 目录类别 | 命名规则 | 示例 | 说明 |
|---|---|---|---|
| 产物类型目录 | `<node_type>`(与节点 type 完全一致) | `product_spec/`、`api_contract/`、`design_asset/` | 9 种产物节点类型各一目录,见主 PRD §2.1 |
| manifest 目录 | `manifests/` | `manifests/n2_v1.json` | 元数据副本(可选,供管理方快速查询,详见 §3.5) |
| CI 配置目录 | `.github/` 或 `.gitlab-ci.yml` | `.github/workflows/artifact-ci.yml` | CI 校验配置 |
| PR 模板 | `.github/pull_request_template.md` | — | 强制声明 node_id/deps |
| Skill 索引 | `.skills-index.yaml` | — | 管理方 skill 版本索引(详见 §4.1.3) |

**约束:**
- 产物类型目录名**必须**与节点 `type` 字段完全一致(大小写敏感),CI 校验
- 禁止在产物类型目录下建子目录(扁平化,避免路径歧义),例外见 §2.3.2 多产物共存
- 不允许出现未在 9 种产物类型之外的目录(CI 阻断)

#### 2.1.2 产物文件命名

主 PRD 建议"序号前缀",本深化明确为**三段式命名**:

```
<seq>_<slug>.<ext>
```

| 段 | 规则 | 示例 |
|---|---|---|
| `seq` | 3 位零填充序号,按 PR 合并到 main 的先后递增,**全局唯一**(同类型目录内) | `001`、`002` |
| `slug` | 小写 kebab-case,简短描述(可省略),仅 ASCII 字母/数字/连字符 | `login-contract`、`user-profile` |
| `ext` | 文件扩展名,必须在 skill 的 `allowed_extensions` 内 | `.yaml`、`.json`、`.md` |

**完整示例:** `api_contract/001_login-contract.yaml`

**命名约束(CI 校验):**
- `seq` 不可重复、不可跳号(001 后不可直接 003,除非中间记录被删除并有 audit 说明)
- `slug` 可省略,省略时文件名为 `001.yaml`
- `ext` 必须在 skill 配置的 `allowed_extensions` 白名单内
- 文件名禁止空格、中文、大写字母(CI 报错)
- 单文件最大 `max_size_kb`(skill 配置,默认 512KB)

#### 2.1.3 feat 分支命名

主 PRD 给出 `feat/{role}/{node_type}-{seq}`,本深化补充 `seq` 预分配机制(避免并发分支 seq 冲突,详见 §5.2):

```
feat/{role}/{node_type}-{seq}-{short-uuid}
```

**示例:** `feat/server/api_contract-001-a3f2`

- `short-uuid`:分支创建时生成(8 位),仅用于分支去重,不进文件名
- 文件 `seq` 在 PR 合并时由管理方 bot 最终确认(详见 §5.2.4)

### 2.2 版本化策略

#### 2.2.1 双重版本化模型

产物版本化采用**语义版本(semantic versioning) + git commit**双重模型:

| 版本维度 | 载体 | 用途 |
|---|---|---|
| **语义版本** | manifest 的 `version` 字段(semver) | 依赖最低版本校验(`min_version`)、变更影响面判断 |
| **git commit** | 产物仓库的 commit hash | 内容不可变快照,管理方 ArtifactRef 持有 |

**关系:** 一个 semver 对应一个 main 分支上的 commit(squash merge 后一一对应)。同一 semver 不可重复合并(详见 §5.3.2)。

#### 2.2.2 semver 语义约定

产物(非代码,故 semver 语义略有调整):

| 版本号 | 何时 bump | 示例 |
|---|---|---|
| MAJOR | 产物结构 breaking 变更(如 API 契约删字段、改字段类型) | `1.0.0` → `2.0.0` |
| MINOR | 向后兼容的新增(如 API 新增可选字段、新增错误码) | `1.0.0` → `1.1.0` |
| PATCH | 修复性变更(如修正描述文案、修正示例值) | `1.0.0` → `1.0.1` |

**约束:**
- 首次提交版本为 `1.0.0`(不允许 `0.x.y`,因产物需"可被下游依赖"视为稳定)
- 版本号必须在 PR 模板中声明,且必须 > 当前 main 上的最新版本(CI 校验,详见 §8.1)
- 变更已 done 产物(即 `changed` 路径)必须 bump 版本,否则 CI 拒绝

#### 2.2.3 版本历史查询

管理方通过 `get_audit_log(node_id=...)` 可查某节点所有版本序列(每次 approve 一条记录,含 merge_commit)。产物仓库 `git log --oneline -- <path>` 亦可查 commit 历史。

### 2.3 多产物共存

#### 2.3.1 同一节点的多版本共存

同一节点(node_id)在不同时期产出多个版本(变更迭代),它们**以不同 seq 共存于同一类型目录**:

```
api_contract/
├─ 001_login-contract.yaml      # n2 v1.0.0(commit a1b2c3)
├─ 002_login-contract.yaml      # n2 v1.1.0(commit b2c3d4,变更)
└─ 003_login-contract.yaml      # n2 v2.0.0(commit c3d4e5,breaking)
```

**关键:管理方 ArtifactRef 只指向"当前生效版本"的 commit**,旧版本文件保留在仓库(可追溯)但不被引用。`changed` → 重提 PR → 合并新版本 → ArtifactRef 更新指向新 commit → 下游失效重算。

#### 2.3.2 不同节点的同类型产物共存

多个节点同为 `api_contract` 类型(如 n2 登录契约、n12 用户信息契约),它们以不同 seq 共存:

```
api_contract/
├─ 001_login-contract.yaml      # n2
├─ 002_user-profile.yaml        # n12
└─ 003_login-contract.yaml      # n2 变更版本
```

**约束:** seq 是类型目录内全局递增,不按节点分段。node_id 与 seq 的映射通过 manifest 的 `node_id` 字段维护(管理方不依赖文件名反推 node_id)。

#### 2.3.3 引用型产物的特殊共存

`server_impl`/`client_ui` 等引用型产物(`*_ref.json`)指向外部代码仓库 commit,其共存策略同上,但文件内容是引用 JSON 而非实际代码:

```json
// server_impl/001_ref.json
{
  "code_repo": "org/backend-services",
  "code_commit": "e5f6g7h8",
  "code_path": "src/api/login.py",
  "build_status": "passed"
}
```

### 2.4 目录结构演进

#### 2.4.1 演进原则

- **目录只增不删**:新增产物类型目录随节点类型扩展,但已有目录不删除(历史产物可追溯)
- **迁移需迁移 PR**:目录重命名/合并必须通过专门的 migration PR,经 admin 审批,且更新所有 manifest 的 path
- **向后兼容**:新目录结构不得破坏已有 ArtifactRef 的 `path` 可解析性

#### 2.4.2 演进场景与处理

| 场景 | 处理 |
|---|---|
| 新增节点类型(如 `metric_spec`) | 新建同名目录,CI 白名单更新,skill 新增 |
| 产物类型拆分(如 `api_contract` 拆 `rest_contract` + `rpc_contract`) | migration PR:旧目录保留只读,新目录承接新提交,manifest 增加 `supersedes` 字段指向旧路径 |
| 文件格式迁移(如 YAML → JSON) | 同节点新版本可用新扩展名,旧版本文件保留;skill 的 `allowed_extensions` 同时含两者 |
| 目录层级扁平化调整 | 仅当扁平化被破坏时(如出现子目录)才需 migration,正常情况保持扁平 |

#### 2.4.3 演进版本号

仓库本身有结构版本,记录在 `repo-meta.yaml`:

```yaml
# repo-meta.yaml(仓库根)
schema_version: "1.0"
directory_layout_version: "1.0"
node_types_supported: [product_spec, api_contract, design_proto, ...]
```

`directory_layout_version` 在 migration PR 中 bump,管理方启动时校验兼容性。

---

## 3. manifest JSON Schema 完整定义

主 PRD 与调研报告展示了 manifest 示例,但未给出可机器校验的 JSON Schema。本节给出完整定义,作为 CI 校验与管理方审核的权威依据。

### 3.1 设计原则

- **中立性**:schema 只约束元数据,**不含产物内容**;`content` 字段禁止出现
- **可校验**:每个字段有明确类型与约束,CI 用 JSON Schema 校验
- **可演进**:`schema_version` 字段支持未来扩展
- **关联性**:与 ArtifactRef、AuditLogEntry 字段对齐(主 PRD §5.1)

### 3.2 manifest 文件位置

每个产物**必须**附带一个 manifest 文件,与产物文件同目录、同名不同扩展:

```
api_contract/
├─ 001_login-contract.yaml          # 产物内容(格式中立)
└─ 001_login-contract.manifest.json # 元数据(manifest)
```

**例外:** 引用型产物(`*_ref.json`)自身即元数据,不需额外 manifest 文件;其内容须符合 §3.3 的引用型子 schema。

### 3.3 完整 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://coordination-platform/schemas/artifact-manifest.json",
  "title": "Artifact Manifest",
  "description": "产物元数据,管理方唯一强制的 schema;不含产物内容",
  "type": "object",
  "required": [
    "manifest_version",
    "node_id",
    "node_type",
    "role",
    "title",
    "version",
    "source",
    "toolspec",
    "deps",
    "created_at",
    "submitter"
  ],
  "additionalProperties": false,
  "properties": {
    "manifest_version": {
      "type": "string",
      "description": "manifest schema 版本,当前 1.0",
      "enum": ["1.0"]
    },
    "node_id": {
      "type": "string",
      "description": "对应管线节点 ID",
      "pattern": "^n[0-9]+$",
      "examples": ["n2"]
    },
    "node_type": {
      "type": "string",
      "description": "产物节点类型,与目录名一致",
      "enum": [
        "product_spec",
        "api_contract",
        "server_impl",
        "server_test",
        "design_proto",
        "design_asset",
        "client_ui",
        "client_func",
        "client_delivery"
      ]
    },
    "role": {
      "type": "string",
      "description": "产出方角色",
      "enum": ["product", "server", "design", "client"]
    },
    "title": {
      "type": "string",
      "description": "产物标题(人类可读)",
      "minLength": 1,
      "maxLength": 200
    },
    "description": {
      "type": "string",
      "description": "产物说明(自由填写,管理方不限制内容)",
      "maxLength": 2000
    },
    "version": {
      "type": "string",
      "description": "语义版本(semver),首次为 1.0.0",
      "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
      "examples": ["1.0.0", "1.2.3"]
    },
    "supersedes": {
      "type": "string",
      "description": "本版本取代的上一版本 commit(变更时填,首次为 null)",
      "pattern": "^[0-9a-f]{7,40}$"
    },
    "source": {
      "type": "object",
      "description": "产物内容位置(管理方不解析内容)",
      "required": ["path"],
      "properties": {
        "path": {
          "type": "string",
          "description": "产物在仓库内相对路径",
          "pattern": "^[a-z_]+/[0-9]{3}[_a-z0-9-]*\\.(yaml|yml|json|md|mdx)$",
          "examples": ["api_contract/001_login-contract.yaml"]
        }
      },
      "additionalProperties": false
    },
    "toolspec": {
      "type": "object",
      "description": "生成该产物用的方案(中立,不限取值)",
      "required": ["framework"],
      "properties": {
        "framework": {
          "type": "string",
          "description": "生成工具/框架名,管理方不限制取值",
          "minLength": 1,
          "maxLength": 50,
          "examples": ["spec-kit", "openspec", "ecc", "superpowers", "custom"]
        },
        "version": {
          "type": "string",
          "description": "工具版本(可选)",
          "pattern": "^[0-9]+\\.[0-9]+(\\.[0-9]+)?$"
        },
        "schema_ref": {
          "type": "string",
          "description": "若产物有自定义 schema,可填引用(管理方不强校验)"
        }
      },
      "additionalProperties": false
    },
    "deps": {
      "type": "array",
      "description": "依赖声明(管理方校验依赖已 done 且版本达标)",
      "items": {
        "type": "object",
        "required": ["node_id", "node_type"],
        "properties": {
          "node_id": {
            "type": "string",
            "pattern": "^n[0-9]+$"
          },
          "node_type": {
            "type": "string",
            "enum": [
              "product_spec", "api_contract", "server_impl", "server_test",
              "design_proto", "design_asset", "client_ui", "client_func", "client_delivery"
            ]
          },
          "min_version": {
            "type": "string",
            "description": "依赖最低版本(可选,semver)",
            "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$"
          },
          "artifact_path": {
            "type": "string",
            "description": "依赖产物路径(可选,便于审核定位)"
          }
        },
        "additionalProperties": false
      },
      "uniqueItems": true
    },
    "lock": {
      "type": ["object", "null"],
      "description": "编辑锁(详见 §5.2),null 表示可编辑",
      "properties": {
        "holder": { "type": "string", "description": "持锁者 agent_id/user_id" },
        "acquired_at": { "type": "string", "format": "date-time" },
        "expires_at": { "type": "string", "format": "date-time" }
      },
      "additionalProperties": false
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "产物创建时间(ISO 8601)"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "本版本更新时间"
    },
    "submitter": {
      "type": "string",
      "description": "提交者标识(agent_id 或 user_id)",
      "minLength": 1,
      "maxLength": 100
    },
    "trace_id": {
      "type": "string",
      "description": "Langfuse trace 关联(审核时填入)",
      "pattern": "^lf_[a-zA-Z0-9]+$"
    }
  }
}
```

### 3.4 引用型产物子 schema

`server_impl`/`server_test`/`client_ui`/`client_func`/`client_delivery` 的产物文件本身是引用 JSON,需符合:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://coordination-platform/schemas/artifact-ref-content.json",
  "title": "Artifact Reference Content",
  "type": "object",
  "required": ["code_repo", "code_commit", "code_path"],
  "properties": {
    "code_repo": { "type": "string", "description": "代码仓库地址" },
    "code_commit": { "type": "string", "pattern": "^[0-9a-f]{7,40}$" },
    "code_path": { "type": "string", "description": "代码路径" },
    "build_status": { "type": "string", "enum": ["passed", "failed", "skipped"] },
    "test_summary": { "type": "object", "description": "测试摘要(可选)" }
  },
  "additionalProperties": true
}
```

### 3.5 manifest 副本机制(可选)

`manifests/` 目录可选地存放管理方合并后写入的 manifest 副本,供快速查询而无需 `git show`:

```
manifests/
└─ n2_v1.1.0.json     # 命名:<node_id>_v<version>.json
```

副本由管理方 bot 在 approve_pr 后写入,内容为合并时 manifest 加 `merge_commit`、`reviewer`、`approved_at` 字段。副本非权威源,权威源是产物文件旁的 manifest。

---

## 4. 审核规则引擎设计

主 PRD FR6.2 的审核逻辑是硬编码的 if-else 链。本节将其抽象为**可配置规则引擎**,支持规则配置化、优先级、AND/OR 组合,便于演进而不改代码。

### 4.1 规则配置格式

#### 4.1.1 规则结构

每条审核规则是一个 YAML 对象,定义于 Constraint Skill 的 `review_rules` 字段:

```yaml
# skills/api-contract-skill/skill.yaml 片段
review_rules:
  - id: R_META_REQUIRED
    name: 元数据必填字段校验
    priority: 100                    # 数值越大优先级越高(先执行)
    combinators: AND                  # 规则内子条件组合(详见 4.3)
    on_fail: reject                   # 失败动作:reject | needs_human | warn
    checks:
      - field: title
        op: exists
      - field: version
        op: regex
        value: "^[0-9]+\\.[0-9]+\\.[0-9]+$"
      - field: source.path
        op: exists
      - field: toolspec.framework
        op: exists
      - field: node_id
        op: regex
        value: "^n[0-9]+$"

  - id: R_DEPS_DONE
    name: 依赖完整性校验
    priority: 90
    combinators: AND
    on_fail: reject
    checks:
      - field: deps
        op: all_deps_done            # 自定义 op:所有依赖节点状态=done

  - id: R_DEPS_MIN_VERSION
    name: 依赖最低版本校验
    priority: 85
    combinators: AND
    on_fail: reject
    checks:
      - field: deps
        op: all_deps_min_version     # 自定义 op:依赖版本 ≥ min_version

  - id: R_FILE_FORMAT
    name: 文件格式校验
    priority: 80
    combinators: AND
    on_fail: reject
    checks:
      - field: __files__
        op: extensions_in
        value: [".yaml", ".yml", ".json"]
      - field: __files__
        op: size_le
        value_kb: 512

  - id: R_FILE_EXISTS
    name: 文件存在性校验
    priority: 75
    combinators: AND
    on_fail: reject
    checks:
      - field: __files__
        op: git_ls_file_exists       # 自定义 op:git ls-file 校验

  - id: R_VERSION_BUMP
    name: 版本递增校验
    priority: 70
    combinators: AND
    on_fail: reject
    checks:
      - field: version
        op: gt_current_main_version  # 自定义 op:版本 > main 上当前版本

  - id: R_HUMAN_REVIEW
    name: 高危节点人工审核
    priority: 50
    combinators: AND
    on_fail: needs_human             # 失败(命中)转人工
    checks:
      - field: __skill__.requires_human_review
        op: equals
        value: true
```

#### 4.1.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 规则唯一标识,大写下划线 |
| `name` | string | 是 | 人类可读名称 |
| `priority` | integer | 是 | 优先级,100 最高,先执行;同优先级按声明顺序 |
| `combinators` | `AND`/`OR` | 是 | 规则内多个 check 的组合逻辑 |
| `on_fail` | `reject`/`needs_human`/`warn` | 是 | 规则失败时的动作 |
| `checks` | array | 是 | 子条件列表,每项含 `field`/`op`/`value` |
| `checks[].field` | string | 是 | 校验字段;`__files__` 表示文件级,`__skill__.*` 表示 skill 配置 |
| `checks[].op` | string | 是 | 操作符(见 4.1.4) |
| `checks[].value` | any | 否 | 比较值 |

#### 4.1.3 规则索引与版本

各 skill 的规则集合版本记录在仓库根 `.skills-index.yaml`:

```yaml
# .skills-index.yaml
skills:
  product-spec-skill:
    version: "1.0.0"
    rules_version: "1.0"
    rules_count: 5
  api-contract-skill:
    version: "1.0.0"
    rules_version: "1.1"      # 规则演进时 bump
    rules_count: 7
```

审核时记录所用 `rules_version` 到审计日志,保证可追溯。

#### 4.1.4 操作符(op)清单

| op | 适用 field | 说明 |
|---|---|---|
| `exists` | 任意 manifest 字段 | 字段存在且非 null |
| `equals` | 任意 | 等于 value |
| `regex` | string 字段 | 匹配正则 value |
| `in` | 任意 | 值在 value 数组中 |
| `extensions_in` | `__files__` | 所有文件扩展名在 value 列表内 |
| `size_le` | `__files__` | 所有文件大小 ≤ value_kb |
| `all_deps_done` | `deps` | 所有依赖节点状态为 done |
| `all_deps_min_version` | `deps` | 所有依赖版本 ≥ min_version |
| `git_ls_file_exists` | `__files__` | git ls-file 校验文件存在于 feat 分支 |
| `gt_current_main_version` | `version` | 版本号 > main 上当前 node_id 的版本 |
| `no_path_traversal` | `source.path` | 路径无 `..`、绝对路径等危险模式 |

### 4.2 规则优先级

#### 4.2.1 优先级语义

- **数值越大越先执行**(100 最高)
- 高优先级规则失败时,低优先级规则**不再执行**(短路),直接返回 on_fail 动作
- 同优先级规则按 YAML 声明顺序执行

#### 4.2.2 默认优先级分层

| 层级 | priority 范围 | 规则类别 | 示例 |
|---|---|---|---|
| P0 安全 | 90-100 | 元数据/安全 | `R_META_REQUIRED`、`R_NO_PATH_TRAVERSAL` |
| P1 依赖 | 80-89 | 依赖完整性/版本 | `R_DEPS_DONE`、`R_DEPS_MIN_VERSION` |
| P2 格式 | 70-79 | 文件格式/大小 | `R_FILE_FORMAT`、`R_FILE_EXISTS` |
| P3 业务 | 50-69 | 业务规则/版本递增 | `R_VERSION_BUMP`、`R_HUMAN_REVIEW` |
| P4 提示 | 1-49 | 软提示(不阻断) | `R_GUIDE_SUGGESTION`(on_fail=warn) |

#### 4.2.3 优先级与 on_fail 的交互

| on_fail | 短路后续规则? | 决策影响 |
|---|---|---|
| `reject` | 是 | 直接 reject,不再执行低优先级规则 |
| `needs_human` | 否(继续执行) | 标记需人工,但继续校验其他规则(收集全部问题) |
| `warn` | 否 | 记录 warning,不影响决策 |

**设计理由:** `reject` 短路避免无意义校验;`needs_human`/`warn` 不短路,让人工审核者看到全部问题。

### 4.3 规则组合逻辑(AND/OR)

#### 4.3.1 单规则内组合(`combinators`)

每条规则的 `checks` 数组用 `combinators` 字段声明组合:

- `AND`:所有 check 通过,规则才通过;任一失败则规则失败
- `OR`:任一 check 通过,规则即通过;全部失败才规则失败

#### 4.3.2 跨规则组合(规则集级别)

规则集(一个 skill 的所有规则)之间**默认是 AND**:所有规则必须通过,审核才通过(除 `warn` 外)。

但支持声明**规则组(group)**实现更复杂的 OR 语义:

```yaml
review_rule_groups:
  - id: G_FORMAT_FLEXIBLE
    combinators: OR                   # 组内规则 OR:任一通过即可
    rules:
      - R_FILE_FORMAT_YAML            # 是 YAML 且符合 schema
      - R_FILE_FORMAT_JSON            # 或是 JSON 且符合 schema
```

组内规则 OR:产物是 YAML 或 JSON 任一即可。组与组之间、组与独立规则之间仍是 AND。

#### 4.3.3 组合逻辑示例

某 PR 审核,规则集如下:

```
R_META_REQUIRED (AND, on_fail=reject)        ← 元数据全有
R_DEPS_DONE (AND, on_fail=reject)            ← 依赖全 done
G_FORMAT_FLEXIBLE (OR: R_YAML | R_JSON)      ← 格式 YAML 或 JSON
R_HUMAN_REVIEW (AND, on_fail=needs_human)    ← 高危转人工
```

最终决策:
- `R_META_REQUIRED` 失败 → 短路 reject
- 前两者过,`G_FORMAT_FLEXIBLE` 都失败 → reject(格式不符)
- 前三者过,`R_HUMAN_REVIEW` 命中 → needs_human(转人工,但已收集全部信息)

### 4.4 规则引擎执行模型

#### 4.4.1 执行流程(伪码)

```python
def run_review_engine(pr, skill, state) -> ReviewVerdict:
    rules = skill.review_rules
    groups = skill.review_rule_groups or []
    verdict = ReviewVerdict(action="approve", failures=[], warnings=[])

    # 1. 按优先级排序(降序)
    sorted_rules = sorted(rules, key=lambda r: -r.priority)

    for rule in sorted_rules:
        result = evaluate_rule(rule, pr, state)
        if not result.passed:
            if rule.on_fail == "reject":
                verdict.failures.append({rule_id: rule.id, check: result.failed_check})
                return verdict.as_reject()          # 短路
            elif rule.on_fail == "needs_human":
                verdict.failures.append({rule_id: rule.id, check: result.failed_check})
                verdict.action = "needs_human"      # 不短路,继续收集
            elif rule.on_fail == "warn":
                verdict.warnings.append({rule_id: rule.id, check: result.failed_check})

    # 2. 规则组评估(OR 语义)
    for group in groups:
        group_passed = any(evaluate_rule(r, pr, state).passed for r in group.rules)
        if not group_passed:
            verdict.failures.append({group_id: group.id})
            return verdict.as_reject()

    # 3. 最终决策
    if verdict.action == "needs_human":
        return verdict.as_needs_human()
    return verdict.as_approve()


def evaluate_rule(rule, pr, state) -> RuleResult:
    checks_results = [evaluate_check(c, pr, state) for c in rule.checks]
    if rule.combinators == "AND":
        passed = all(checks_results)
    else:  # OR
        passed = any(checks_results)
    return RuleResult(passed=passed, failed_check=first_failure(checks_results))
```

#### 4.4.2 ReviewVerdict 结构

```python
class ReviewVerdict(TypedDict):
    action: str                  # approve | reject | needs_human
    failures: list[dict]         # 失败规则与 check
    warnings: list[dict]         # 警告(不阻断)
    rules_evaluated: list[str]   # 已评估规则 id(可追溯)
    rules_version: str           # skill rules_version
```

#### 4.4.3 与主 PRD FR6.2 的映射

主 PRD FR6.2 的硬编码校验项,迁移到规则引擎后:

| 主 PRD FR6.2 校验项 | 对应规则 id |
|---|---|
| 元数据校验 | `R_META_REQUIRED` |
| 依赖完整性 | `R_DEPS_DONE` |
| 文件格式 | `R_FILE_FORMAT`(或 `G_FORMAT_FLEXIBLE`) |
| 文件存在 | `R_FILE_EXISTS` |
| 人工审核 | `R_HUMAN_REVIEW` |

新增规则(本深化补充):`R_DEPS_MIN_VERSION`、`R_VERSION_BUMP`、`R_NO_PATH_TRAVERSAL`。

---

## 5. 并发审核冲突处理

主 PRD 未涉及并发场景。本节设计锁机制与冲突检测,处理:同一节点多个 PR、同一产物被多方提交、seq 冲突等。

### 5.1 冲突场景分类

| # | 场景 | 冲突类型 | 严重度 |
|---|---|---|---|
| C1 | 同一 node_id 同时有多个 PR(不同提交者) | 节点级并发 | 高 |
| C2 | 同一产物文件 path 被两个 PR 修改 | 路径冲突 | 高 |
| C3 | 两个 PR 的 seq 重复(并发分支预分配同 seq) | seq 冲突 | 中 |
| C4 | PR 审核期间,其依赖节点变 changed | 依赖失效 | 高 |
| C5 | 同一 feat 分支被多次推送新 commit | 分支漂移 | 低 |
| C6 | 两个 PR 互为依赖(循环) | DAG 违规 | 高(被无环校验拦截) |

### 5.2 锁机制设计

#### 5.2.1 节点级编辑锁

为防止 C1(同节点多 PR),引入**节点级编辑锁**,记录在 manifest 的 `lock` 字段(§3.3):

```json
{
  "lock": {
    "holder": "server-agent-01",
    "acquired_at": "2026-08-04T10:00:00Z",
    "expires_at": "2026-08-04T22:00:00Z"
  }
}
```

**锁规则:**
- 节点 `ready` 时,第一个调 `submit_artifact` 的 agent 获得锁
- 持锁者有权为该节点提 PR;其他 agent 提 PR 时,管理方 webhook 收到后**立即 reject**,提示"节点 n2 正在被 server-agent-01 编辑,请等待或协调"
- 锁有 TTL(默认 12 小时,可配置),超时自动释放(`expires_at`),避免死锁
- 持锁者完成 PR 合并或主动放弃时,锁释放

**锁状态查询:** MCP 新增 `get_node_lock(node_id)` 工具,返回当前持锁者与过期时间。

#### 5.2.2 seq 预分配锁

为防止 C3(seq 冲突),seq 分配采用**预分配 + 最终确认**两阶段:

1. **预分配**(分支创建时):agent 调 `reserve_seq(node_type)` 获得预分配 seq,写入分支名 `feat/server/api_contract-001-a3f2`。预分配记录在管理方内存表,有 30 分钟 TTL。
2. **最终确认**(PR 合并时):管理方 bot 在 squash merge 前,校验预分配 seq 与 main 上 max seq + 1 一致;不一致则 rebase 重命名文件后合并。

**简化方案(MVP):** 不预分配,seq 在 merge 时由 bot 统一分配(取 main 上 max seq + 1,原子操作),分支内文件名用临时 slug,merge 时 bot 重命名。这样彻底避免 seq 冲突,代价是分支内文件名与最终不一致(可接受,因分支是临时态)。

#### 5.2.3 锁的并发安全实现

锁状态存 Postgres,用 `SELECT ... FOR UPDATE` 或乐观锁(version 字段)保证原子获取:

```sql
-- 获取锁(原子)
INSERT INTO node_locks (node_id, holder, expires_at)
VALUES ($1, $2, $3)
ON CONFLICT (node_id) DO NOTHING
RETURNING holder;  -- 返回非空表示获锁成功,空表示已被持有
```

#### 5.2.4 锁与 PR 审核的关系

- **提 PR 前必须持锁**:webhook 收到 PR 时,先查 node_id 的锁,若提交者非持锁者 → 立即 reject(C1 解决)
- **PR pending_review 期间持锁**:锁不释放,防止他人在审核期间提新 PR
- **PR 合并后释放锁**:approve_pr 合并成功 → 释放锁
- **PR 驳回后释放锁**:reject_pr → 释放锁,节点回 ready,他人可竞争

### 5.3 冲突检测与解决

#### 5.3.1 路径冲突检测(C2)

PR 审核时,管理方检查 PR 修改的文件 path 是否已被其他 pending PR 修改:

```python
def detect_path_conflict(pr, pending_prs) -> list[str]:
    pr_paths = {f.path for f in pr.files}
    conflicts = []
    for other in pending_prs:
        if other.pr_id == pr.pr_id:
            continue
        other_paths = {f.path for f in other.files}
        overlap = pr_paths & other_paths
        if overlap:
            conflicts.append({pr_id: other.pr_id, paths: overlap})
    return conflicts
```

**解决:** 路径冲突时,后到的 PR 标记 `needs_human`,提示"PR #X 也在修改 path Y,请协调或等待"。人工决定哪个先合。

#### 5.3.2 同版本冲突检测(C2 变体)

两个 PR 为同 node_id 提交相同 `version`:

- 审核时检查 main 上该 node_id 是否已存在该 version → 存在则 reject("版本 X 已存在,请 bump")
- 检查其他 pending PR 是否已声明该 version → 存在则后到的 `needs_human`

#### 5.3.3 依赖失效处理(C4)

PR 处于 `pending_review` 期间,其声明的依赖节点变为 `changed`(被重新提交):

**检测:** 管理方在依赖节点状态变更时,扫描所有 pending PR,凡 deps 含该节点的 PR 标记 `stale`。

**处理:**
- 自动 reject 该 PR,原因"依赖 n1 已变更,请基于最新版本重新提交"
- 节点回 ready,锁释放,提交者可基于新依赖重提
- 这是保守策略,避免基于过期依赖的产物被合并

#### 5.3.4 分支漂移处理(C5)

PR 审核期间,feat 分支被推送新 commit(提交者修改产物):

- webhook 重新触发审核,旧审核结论作废,重新跑规则引擎
- 审核计时器重置(SLA 重新计算)
- 若 PR 已被 approve 但未 merge,新 commit 导致 approve 自动撤销(GitHub 原生行为),需重新审核

#### 5.3.5 冲突矩阵汇总

| 场景 | 检测时机 | 解决策略 |
|---|---|---|
| C1 同节点多 PR | webhook 收到时查锁 | 非持锁者立即 reject |
| C2 路径冲突 | 审核开始时扫 pending PRs | needs_human 协调 |
| C3 seq 冲突 | merge 时 | bot 统一分配 seq(简化方案) |
| C4 依赖失效 | 依赖状态变更时扫 pending PRs | 自动 reject,提示重提 |
| C5 分支漂移 | webhook 重触发 | 重新审核,SLA 重置 |
| C6 循环依赖 | 管线加载时 CI | DAG 无环校验,拒绝加载 |

---

## 6. 审核 SLA 与超时升级策略

主 PRD 无 SLA 设计。本节引入分级 SLA,覆盖自动审核超时与人工审核超时,并设计升级路径。

### 6.1 SLA 分级

| SLA 级别 | 适用场景 | 目标时长 | 超时动作 |
|---|---|---|---|
| SLA-Auto | 自动审核(review_artifact_pr) | 30 秒 | 告警 + 重试(见 6.2) |
| SLA-Human-1 | 人工审核(常规,如 design_asset) | 8 工作小时 | 升级到备份审核者(见 6.3) |
| SLA-Human-2 | 人工审核(关键,如 api_contract 首次、client_delivery) | 4 工作小时 | 升级到 admin + 告警 |
| SLA-Human-3 | 人工审核(交付级,如 client_delivery 最终) | 2 工作小时 | 升级到 admin + 飞书/Slack 加急通知 |

**SLA 级别由 skill 的 `sla_level` 字段配置:**

```yaml
# skill.yaml
sla:
  level: SLA-Human-2
  timeout_hours: 4
  escalate_to: admin
```

### 6.2 自动审核超时

#### 6.2.1 超时定义

`review_artifact_pr` 调用后 30 秒未返回 verdict,视为自动审核超时。

#### 6.2.2 处理策略

```
自动审核超时
  ├─ 第 1 次:重试(间隔 10 秒)
  ├─ 第 2 次:重试(间隔 30 秒)
  └─ 第 3 次仍超时:转人工审核(needs_human)
       + 记录 audit(action=auto_review_timeout)
       + Langfuse 告警 span
```

**设计理由:** 自动审核通常是 git 操作或规则引擎,偶发超时可能是 git 仓库抖动,重试合理;三次失败说明真异常,转人工兜底。

#### 6.2.3 自动审核失败(非超时)

规则引擎抛异常(非规则 fail,而是系统异常,如 git 不可达):

- 立即转人工(needs_human),不重试
- 记录 audit(action=auto_review_error, error=msg)
- 告警(飞书/Slack)

### 6.3 人工审核 SLA 与超时升级

#### 6.3.1 升级路径(escalation chain)

每个 approval 节点或 needs_human 的 PR,有一个升级链:

```yaml
# skill.yaml 或 pipeline DSL 中 approval 节点配置
escalation:
  - tier: 1
    approver: reviewer_agent        # 默认审核者
    sla_hours: 4
  - tier: 2
    approver: backup_reviewer       # 备份审核者
    sla_hours: 4
    notify: [feishu:reviewer-group]
  - tier: 3
    approver: admin
    sla_hours: 2
    notify: [feishu:admin-group, slack:#oncall]
    urgent: true
```

#### 6.3.2 升级触发

定时任务(每 5 分钟扫描)检查 pending 人工审核:

```
对于每个 pending_human 的 PR:
  当前 tier = 当前分配的 approver 对应的 tier
  elapsed = now - assigned_at
  if elapsed > tier.sla_hours:
    升级到 tier+1
    重新分配 approver
    发送 notify
    记录 audit(action=escalation, from_tier, to_tier)
    重置 SLA 计时(按 tier+1 的 sla_hours)
```

#### 6.3.3 升级可视化

升级事件经 SSE 推送到 Dashboard,节点详情面板显示:

```
当前审核者: admin(已升级,原 reviewer_agent 超时)
升级历史: tier1(reviewer_agent, 超时) → tier2(backup_reviewer, 超时) → tier3(admin)
剩余 SLA: 1h 30m
```

#### 6.3.4 全局超时兜底

若所有 tier 都超时(极端情况):

- PR 自动标记 `needs_admin_attention`(不自动 approve,保守原则)
- 飞书/Slack 加急通知 admin
- 节点保持 pending_review,Dashboard 红色高亮
- admin 手动处理(approve/reject/驳回重做)

**关键原则:超时可升级、可告警,但不可自动 approve。** 审核的本质是准入,自动放行违背需求 7。

---

## 7. 驳回后重试流程

主 PRD FR6.6 仅说"reject_pr 后节点回 ready + 通知提交方"。本节细化驳回原因规范、重提流程、历史追溯。

### 7.1 驳回原因规范

#### 7.1.1 结构化驳回原因

`reject_pr` 的 `reason` 字段须为结构化 JSON(非自由文本),便于提交者定位问题与历史统计:

```json
{
  "reason": {
    "code": "R_META_REQUIRED_FAILED",
    "category": "metadata",
    "failed_checks": [
      {
        "rule_id": "R_META_REQUIRED",
        "field": "version",
        "op": "regex",
        "expected": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
        "actual": "1.0"
      }
    ],
    "hint": "version 字段需为完整 semver,如 1.0.0",
    "retryable": true
  }
}
```

#### 7.1.2 驳回原因码清单

| code | category | 含义 | retryable |
|---|---|---|---|
| `R_META_REQUIRED_FAILED` | metadata | 元数据必填字段缺失/格式错 | true |
| `R_DEPS_NOT_DONE` | dependency | 依赖节点未 done | true(等依赖完成后) |
| `R_DEPS_VERSION_TOO_LOW` | dependency | 依赖版本低于 min_version | true |
| `R_FILE_FORMAT_INVALID` | format | 扩展名不在白名单 | true |
| `R_FILE_TOO_LARGE` | format | 文件超过 max_size | true |
| `R_FILE_NOT_FOUND` | format | git ls-file 未找到 | true |
| `R_VERSION_NOT_BUMPED` | business | 版本未递增 | true |
| `R_NODE_LOCKED_BY_OTHER` | concurrency | 节点被他人持锁 | true(等锁释放) |
| `R_PATH_CONFLICT` | concurrency | 路径与其他 PR 冲突 | true(协调后) |
| `R_DEPS_CHANGED` | concurrency | 依赖变更失效 | true(基于新依赖重提) |
| `R_HUMAN_REJECTED` | human | 人工审核驳回 | true |
| `R_DAG_CYCLE` | structure | 循环依赖 | false(需改管线) |
| `R_AUTO_REVIEW_ERROR` | system | 自动审核系统异常 | true(重试) |

#### 7.1.3 category 与 retryable 语义

- `metadata`/`format`/`business`:提交者修改后可重提
- `dependency`:等依赖 done 后重提,或调整 deps 声明
- `concurrency`:等冲突解决后重提
- `human`:按人工反馈修改后重提
- `structure`:需修改管线 DSL,不能简单重提(`retryable=false`)
- `system`:管理方异常,通常重试即可

### 7.2 重试流程

#### 7.2.1 重试前置条件

驳回后节点回 `ready`,提交者重提前需:

1. **读取驳回原因**:通过 `get_pr_detail(pr_id)` 或 `get_audit_log` 查 structured reason
2. **修复问题**:按 `failed_checks` 逐项修复
3. **重新持锁**:调 `submit_artifact` 重新获锁(旧锁已在 reject 时释放)
4. **bump 版本**(若已 done 节点的变更重提):版本必须 > 上次驳回时的版本

#### 7.2.2 重试次数限制

| 场景 | 限制 | 超限处理 |
|---|---|---|
| 同一 PR 反复推送 commit 重审 | 无限制(每次 push 重触发) | 但 SLA 重置,可能升级 |
| 同 node_id 反复提新 PR(每次驳回后重提) | 5 次/节点 | 第 6 次起强制 `needs_human`,人工介入辅导 |
| 系统异常重试 | 3 次 | 转人工 |

**设计理由:** 限制同节点反复驳回,避免 agent 死循环浪费资源;但不限制单 PR 的 commit 次数(允许渐进修改)。

#### 7.2.3 重试与版本递增

- 首次提交被驳回,重提时若产物未变可保持原 version(因 main 上无该版本)
- 已 done 节点变更重提被驳回,重提必须 bump version(因 main 上已有旧版本)
- CI 校验 `R_VERSION_BUMP` 自动判断

### 7.3 历史追溯

#### 7.3.1 驳回历史查询

`get_audit_log(node_id=n2, action=reject)` 返回该节点所有驳回记录,含:

- 每次 reject 的 structured reason
- 驳回时的 deps 状态(`deps_at_review`)
- 驳回者(reviewer 或 mgmt-bot)
- 关联的 pr_id(可在产物仓库查 PR 评论)

#### 7.3.2 重试链路可视化

Dashboard 节点详情面板展示重试链路:

```
n2 (api_contract) 重试历史:
  PR #42  v1.0.0  reject  R_META_REQUIRED_FAILED  (version 格式错)
  PR #45  v1.0.0  reject  R_DEPS_NOT_DONE          (n1 未 done)
  PR #48  v1.0.0  approve ✓                        (修复后通过)
```

#### 7.3.3 驳回统计

管理方可统计驳回率,识别常见问题:

- 按 `code` 聚合:哪种驳回原因最多 → 针对性优化 skill guide
- 按 `submitter` 聚合:谁被驳回最多 → 针对性辅导
- 按 `node_type` 聚合:哪类产物易出错 → 调整 skill 约束或引导

---

## 8. 产物仓库 CI 校验

主 PRD FR1.4 提到"CI 校验 manifest schema + skill 约束"但未细化。本节给出 CI 检查项与失败处理。

### 8.1 CI 检查项

CI 在 PR 提交时触发(GitHub Actions / GitLab CI),分两类:**仓库级检查**(CI 自身)+ **管理方审核**(webhook 触发 review_artifact_pr)。

#### 8.1.1 仓库级 CI 检查(CI 直接执行)

| 检查项 | 检查内容 | 失败动作 |
|---|---|---|
| CI-1 目录白名单 | 修改的目录在 9 种产物类型 + `manifests/` 内 | CI fail |
| CI-2 文件命名规范 | 文件名匹配 `<seq>_<slug>.<ext>` | CI fail |
| CI-3 manifest 存在 | 每个产物文件有对应 `.manifest.json`(引用型除外) | CI fail |
| CI-4 manifest schema | manifest 符合 §3.3 JSON Schema | CI fail |
| CI-5 扩展名白名单 | 扩展名在 skill 的 `allowed_extensions` | CI fail |
| CI-6 文件大小 | ≤ `max_size_kb` | CI fail |
| CI-7 路径安全 | `source.path` 无 `..`、无绝对路径(`no_path_traversal`) | CI fail |
| CI-8 seq 唯一性 | 同目录内 seq 不重复 | CI fail |
| CI-9 seq 连续性 | seq 无跳号(或跳号有 audit 说明) | CI warn |
| CI-10 节点类型与目录一致 | manifest.node_type 与所在目录名一致 | CI fail |
| CI-11 角色与节点类型一致 | manifest.role 与 node_type 的角色映射一致(主 PRD §2.1) | CI fail |

#### 8.1.2 管理方审核(webhook 触发,非 CI 直接执行)

以下检查由 `review_artifact_pr` 在管理方执行(规则引擎,§4):

| 检查项 | 对应规则 |
|---|---|
| 元数据必填字段 | `R_META_REQUIRED` |
| 依赖完整性(deps done) | `R_DEPS_DONE` |
| 依赖最低版本 | `R_DEPS_MIN_VERSION` |
| 版本递增 | `R_VERSION_BUMP` |
| 文件存在(git ls-file) | `R_FILE_EXISTS` |
| 高危节点人工审核 | `R_HUMAN_REVIEW` |
| 节点锁校验 | (锁机制,§5.2) |
| 路径冲突 | (冲突检测,§5.3) |
| 依赖失效 | (冲突检测,§5.3) |

**分工理由:** 仓库级 CI 校验"格式与结构"(无需管理方 state);管理方审核校验"业务与依赖"(需 PipelineState)。

#### 8.1.3 CI 配置示例

```yaml
# .github/workflows/artifact-ci.yml
name: Artifact CI
on:
  pull_request:
    paths:
      - 'product_spec/**'
      - 'api_contract/**'
      - 'design_proto/**'
      - 'design_asset/**'
      - 'server_impl/**'
      - 'server_test/**'
      - 'client_ui/**'
      - 'client_func/**'
      - 'client_delivery/**'
      - 'manifests/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Install coordination-platform-ci
        run: pip install coordination-platform-ci
      - name: Run CI checks
        run: coord-ci check --pr ${{ github.event.pull_request.number }}
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ci-report
          path: ci-report.json
```

### 8.2 CI 失败处理

#### 8.2.1 CI 失败与审核的关系

- **CI fail 阻止合并**:GitHub 分支保护要求 CI 必过才能合并,CI fail 的 PR 无法被 approve_pr 合并
- **CI fail 不触发管理方审核**:webhook 收到 PR 时,若 CI 未通过,管理方跳过审核(等 CI 过再审)
- **CI warn 不阻止**:警告类(CI-9 seq 连续性)记录但不阻断

#### 8.2.2 CI 失败反馈

CI 失败时,在 PR 上评论结构化报告:

```
❌ Artifact CI 失败 (3 项)

CI-2 文件命名规范: FAIL
  - api_contract/001_login contract.yaml 含空格
  
CI-4 manifest schema: FAIL
  - api_contract/001_login-contract.manifest.json
    - version: "1.0" 不匹配 ^[0-9]+\.[0-9]+\.[0-9]+$
    
CI-8 seq 唯一性: FAIL
  - api_contract/001 已存在

请修复后重新推送。
```

#### 8.2.3 CI 与规则引擎的边界

| 维度 | 仓库 CI | 管理方规则引擎 |
|---|---|---|
| 执行位置 | GitHub Actions / GitLab CI | 管理方进程 |
| 触发 | PR push | PR webhook + CI 过 |
| 数据源 | 产物仓库 | 产物仓库 + PipelineState |
| 校验内容 | 格式、结构、命名 | 业务、依赖、锁、冲突 |
| 失败动作 | CI fail,阻止合并 | reject/needs_human |
| 速度 | 快(秒级) | 中(含 git 操作,10-30 秒) |

**顺序:** PR push → CI 校验 → CI 过 → webhook 触发管理方审核 → 规则引擎 → 决策。CI 是第一道门,规则引擎是第二道门。

---

## 9. Mermaid 设计图

### 9.1 审核决策树(完整)

覆盖所有审核路径:CI → 规则引擎 → 锁/冲突 → 人工 → 合并/驳回/升级。

```mermaid
flowchart TD
    PR["PR 提交到产物仓库"]
    PR --> CI{"仓库 CI 校验<br/>(CI-1~CI-11)"}
    
    CI -->|FAIL| CI_FAIL["CI 评论失败报告<br/>阻止合并"]
    CI_FAIL --> FIX1["提交者修复<br/>重新 push"]
    FIX1 --> CI
    
    CI -->|PASS| HOOK["webhook 通知管理方"]
    
    HOOK --> LOCK{"节点锁校验<br/>(§5.2)"}
    LOCK -->|非持锁者| REJ_LOCK["reject<br/>R_NODE_LOCKED_BY_OTHER"]
    LOCK -->|持锁者| CONFLICT{"冲突检测<br/>(§5.3)"}
    
    CONFLICT -->|路径冲突| NH_CONFLICT["needs_human<br/>R_PATH_CONFLICT<br/>人工协调"]
    CONFLICT -->|依赖失效| REJ_DEPS["reject<br/>R_DEPS_CHANGED"]
    CONFLICT -->|无冲突| ENGINE{"规则引擎<br/>(§4)"}
    
    ENGINE --> P0{"P0 安全规则<br/>R_META_REQUIRED"}
    P0 -->|FAIL| REJ_META["reject<br/>R_META_REQUIRED_FAILED"]
    P0 -->|PASS| P1{"P1 依赖规则<br/>R_DEPS_DONE + R_DEPS_MIN_VERSION"}
    
    P1 -->|FAIL deps not done| REJ_DEPS_NOT["reject<br/>R_DEPS_NOT_DONE"]
    P1 -->|FAIL version low| REJ_VER_LOW["reject<br/>R_DEPS_VERSION_TOO_LOW"]
    P1 -->|PASS| P2{"P2 格式规则<br/>R_FILE_FORMAT + R_FILE_EXISTS"}
    
    P2 -->|FAIL| REJ_FMT["reject<br/>R_FILE_FORMAT_INVALID"]
    P2 -->|PASS| P3{"P3 业务规则<br/>R_VERSION_BUMP"}
    
    P3 -->|FAIL| REJ_BUMP["reject<br/>R_VERSION_NOT_BUMPED"]
    P3 -->|PASS| HUMAN{"R_HUMAN_REVIEW<br/>requires_human_review?"}
    
    HUMAN -->|true| NH_HUMAN["needs_human<br/>转人工审核"]
    HUMAN -->|false| AUTO_APPROVE["auto approve<br/>bot 合并"]
    
    NH_HUMAN --> SLA{"人工 SLA<br/>(§6.3)"}
    SLA -->|tier1 approve| MERGE["approve_pr<br/>bot 合并"]
    SLA -->|tier1 reject| REJ_HUMAN["reject<br/>R_HUMAN_REJECTED"]
    SLA -->|tier1 超时| ESCALATE1["升级 tier2<br/>重新计时"]
    ESCALATE1 --> SLA2{"tier2 SLA"}
    SLA2 -->|approve| MERGE
    SLA2 -->|超时| ESCALATE2["升级 tier3 admin<br/>加急通知"]
    ESCALATE2 --> SLA3{"tier3 SLA"}
    SLA3 -->|approve| MERGE
    SLA3 -->|超时| STUCK["needs_admin_attention<br/>不自动 approve"]
    
    AUTO_APPROVE --> MERGE
    MERGE --> POST["合并后处理<br/>(§FR6.3)"]
    POST --> AUDIT["记录审计日志"]
    POST --> LF["Langfuse trace"]
    POST --> LG["LangGraph set_done<br/>+ cascade 解锁下游"]
    POST --> UNLOCK["释放节点锁"]
    
    REJ_LOCK --> READY["节点回 ready"]
    REJ_DEPS --> READY
    REJ_META --> READY
    REJ_DEPS_NOT --> READY
    REJ_VER_LOW --> READY
    REJ_FMT --> READY
    REJ_BUMP --> READY
    REJ_HUMAN --> READY
    READY --> NOTIFY["通知提交者<br/>含 structured reason"]
    NOTIFY --> RETRY{"提交者重试<br/>(§7)"}
    RETRY --> RETRY_LIMIT{"重试 < 5 次?"}
    RETRY_LIMIT -->|是| PR
    RETRY_LIMIT -->|否| FORCE_HUMAN["强制 needs_human<br/>人工辅导"]
    
    style CI fill:#4a8ad6,color:#fff
    style ENGINE fill:#a371f7,color:#fff
    style MERGE fill:#3fb950,color:#fff
    style REJ_LOCK fill:#b3261e,color:#fff
    style STUCK fill:#b3261e,color:#fff
    style NH_HUMAN fill:#e3b341,color:#fff
```

### 9.2 并发冲突处理流程

展示同一节点多 PR、依赖失效、路径冲突的处理。

```mermaid
sequenceDiagram
    participant A1 as Agent-A
    participant A2 as Agent-B
    participant MCP as MCP Server
    participant LOCK as 锁服务
    participant REPO as 产物仓库
    participant HOOK as Webhook
    participant ENG as 规则引擎
    participant STATE as PipelineState
    participant AUDIT as 审计日志

    Note over A1,AUDIT: 场景 C1:同节点并发提 PR
    
    A1->>MCP: submit_artifact(n2)
    MCP->>LOCK: 获取锁(n2, A1)
    LOCK-->>MCP: 获锁成功(holder=A1, TTL=12h)
    MCP-->>A1: ok, 持锁,可提 PR
    
    A2->>MCP: submit_artifact(n2)
    MCP->>LOCK: 获取锁(n2, A2)
    LOCK-->>MCP: 获锁失败(已持锁)
    MCP-->>A2: 错误:n2 被 A1 持锁,请等待
    
    A1->>REPO: 推 feat 分支 + 开 PR #42
    REPO->>HOOK: PR webhook
    HOOK->>ENG: review_artifact_pr(#42)
    ENG->>LOCK: 校验持锁者=A1? 是
    ENG->>STATE: 查 deps(n1) 状态
    STATE-->>ENG: n1=done
    
    Note over A1,AUDIT: 场景 C4:审核期间依赖失效
    
    Note right of STATE: 另一线程:n1 被重提变更
    STATE->>STATE: n1 → changed
    
    STATE->>ENG: 扫描 pending PRs,标记 #42 stale
    ENG->>AUDIT: 记录 reject(R_DEPS_CHANGED)
    ENG-->>HOOK: reject(依赖 n1 变更)
    HOOK->>REPO: 评论 PR #42 驳回原因
    REPO-->>A1: 通知:依赖失效,请重提
    
    ENG->>LOCK: 释放锁(n2)
    LOCK-->>ENG: 已释放
    
    Note over A1,AUDIT: 场景 C2:路径冲突
    
    par 两个 PR 改同一 path
        A1->>REPO: PR #50 改 api_contract/001.yaml
    and
        A2->>REPO: PR #51 改 api_contract/001.yaml
    end
    REPO->>HOOK: 两个 webhook
    HOOK->>ENG: review(#50) 先到
    ENG->>ENG: 检测 path 冲突(#51 也改 001.yaml)
    ENG-->>HOOK: #50 needs_human(路径冲突,人工协调)
    ENG->>ENG: #51 也 needs_human
    ENG->>AUDIT: 记录两 PR 路径冲突
    
    Note over ENG: 人工决定 #50 先合,#51 rebase
```

### 9.3 驳回重试流程

展示驳回 → 修复 → 重提 → 通过的完整链路,含历史追溯。

```mermaid
flowchart LR
    subgraph CYCLE["重试循环(最多 5 次)"]
        direction TB
        PR1["PR #42 v1.0.0<br/>首次提交"]
        PR1 --> REV1["规则引擎审核"]
        REV1 --> REJ1["reject<br/>R_META_REQUIRED_FAILED<br/>version=1.0 格式错"]
        REJ1 --> READY1["节点回 ready<br/>释放锁"]
        READY1 --> NOTIF1["通知提交者<br/>structured reason"]
        
        NOTIF1 --> FIX1["提交者修复<br/>version → 1.0.0"]
        FIX1 --> PR2["PR #45 v1.0.0<br/>重提"]
        PR2 --> REV2["规则引擎审核"]
        REV2 --> REJ2["reject<br/>R_DEPS_NOT_DONE<br/>n1 未 done"]
        REJ2 --> READY2["节点回 ready"]
        READY2 --> WAIT["等待 n1 done<br/>(不需修改产物)"]
        WAIT --> PR3["PR #48 v1.0.0<br/>n1 done 后重提"]
        PR3 --> REV3["规则引擎审核"]
        REV3 --> APP["approve<br/>auto approve"]
    end
    
    APP --> MERGE["bot 合并"]
    MERGE --> AUDIT_H["审计历史"]
    
    subgraph HISTORY["历史追溯(get_audit_log)"]
        H1["PR #42  reject  R_META_REQUIRED_FAILED  ts=10:00"]
        H2["PR #45  reject  R_DEPS_NOT_DONE          ts=11:00"]
        H3["PR #48  approve ✓                        ts=12:00"]
        H1 --> H2 --> H3
    end
    
    AUDIT_H --> HISTORY
    
    READY1 --> COUNT{"重试计数<br/>(同 node_id)"}
    READY2 --> COUNT
    COUNT -->|< 5| CYCLE
    COUNT -->|≥ 5| FORCE["强制 needs_human<br/>人工辅导"]
    
    style REJ1 fill:#b3261e,color:#fff
    style REJ2 fill:#b3261e,color:#fff
    style APP fill:#3fb950,color:#fff
    style MERGE fill:#3fb950,color:#fff
    style FORCE fill:#e3b341,color:#fff
    style HISTORY fill:#1a2a4a,color:#fff
```

---

## 10. 与主 PRD 的对齐与修正

### 10.1 字段对齐

| 本深化字段 | 主 PRD 对应 | 说明 |
|---|---|---|
| manifest `version`(semver) | 主 PRD PR 模板未显式 version | **补充**:PR 模板须含 version 字段 |
| manifest `lock` | 主 PRD 无 | **新增**:并发锁机制 |
| manifest `supersedes` | 主 PRD 无 | **新增**:变更版本追溯 |
| manifest `manifest_version` | 主 PRD 无 | **新增**:schema 演进 |
| `ReviewVerdict.failures`/`warnings` | 主 PRD `verdict`/`reason` | **扩展**:结构化 verdict |
| `review_rules`(skill.yaml) | 主 PRD `artifact_constraints` | **重构**:约束 → 规则引擎 |
| `sla`(skill.yaml) | 主 PRD 无 | **新增**:SLA 配置 |
| `escalation` | 主 PRD 无 | **新增**:升级链 |

### 10.2 对主 PRD 的修正项

| 主 PRD 内容 | 修正为 | 理由 |
|---|---|---|
| FR1.1 文件名"建议序号前缀" | §2.1.2 三段式命名 `<seq>_<slug>.<ext>`(CI 强制) | 避免命名歧义 |
| FR1.1 "管理方不解析内容,只校验文件存在性 + 扩展名/大小" | 补充:CI 校验 manifest schema + 命名规范(§8) | 元数据也需校验 |
| FR1.3 PR 模板 | 补充 `version`、`supersedes` 字段 | 版本化需要 |
| FR5.2 skill.yaml 的 `artifact_constraints` | 重构为 `review_rules`(规则引擎,§4) | 可配置化 |
| FR6.2 审核逻辑(硬编码 if-else) | 规则引擎执行(§4.4) | 可演进 |
| FR6.2 校验项"元数据/依赖/格式/文件/人工" | 对应规则 R_META/R_DEPS/R_FILE/R_HUMAN(§4.1.1) | 映射清晰 |
| FR6.6 "reject_pr 后节点回 ready" | 补充:结构化 reason + 重试限制 + 历史追溯(§7) | 可追溯 |
| FR6 审核流程 | 补充:CI → 锁 → 冲突 → 规则引擎 → SLA(§9.1) | 完整路径 |
| 无并发处理 | 新增锁机制 + 冲突检测(§5) | C1-C6 场景 |
| 无 SLA | 新增分级 SLA + 升级链(§6) | 超时兜底 |

### 10.3 不变项(确认对齐)

以下主 PRD 设计**不变**,本深化确认对齐:

- 产物仓库独立 git、main 分支保护、squash merge
- 管理方不解析内容、格式中立
- 合并即推进(set_done + cascade)
- 审计日志结构(AuditLogEntry)
- ArtifactRef 结构(repo + path + commit + toolspec_framework + trace_id)
- 状态机 7 态(blocked/ready/pending_review/in_progress/review/done/changed)
- Constraint Skill 6 个(product-spec/api-contract/design-handoff/server-impl/client-ui/client-delivery)
- 审核策略矩阵(按产物类型分级,FR6.4)

### 10.4 实施建议

| 阶段 | 本深化内容 | 优先级 |
|---|---|---|
| Phase 1 MVP | §2 命名规则 + §3 manifest schema + §4 规则引擎(基础规则)+ §8 CI(基础检查) | P0 |
| Phase 1 MVP | §5.2 节点锁(C1 解决)+ §7 驳回重试(基础) | P0 |
| Phase 2 | §5.3 冲突检测(C2/C4)+ §6 SLA + 升级链 | P1 |
| Phase 2 | §4.3 规则组(OR 逻辑)+ §7.3 驳回统计 | P1 |
| Phase 3 | §2.4 目录演进 + §6.3.4 全局超时兜底 + 可视化 | P2 |

---

## 附录 A:规则引擎与主 PRD 校验项的完整映射

| 主 PRD FR6.2 校验项 | 本深化规则 id | priority | on_fail | op |
|---|---|---|---|---|
| 元数据校验 | `R_META_REQUIRED` | 100 | reject | exists/regex |
| 依赖完整性 | `R_DEPS_DONE` | 90 | reject | all_deps_done |
| (新增)依赖最低版本 | `R_DEPS_MIN_VERSION` | 85 | reject | all_deps_min_version |
| 文件格式 | `R_FILE_FORMAT` | 80 | reject | extensions_in/size_le |
| 文件存在 | `R_FILE_EXISTS` | 75 | reject | git_ls_file_exists |
| (新增)版本递增 | `R_VERSION_BUMP` | 70 | reject | gt_current_main_version |
| 人工审核 | `R_HUMAN_REVIEW` | 50 | needs_human | equals(true) |
| (新增)路径安全 | `R_NO_PATH_TRAVERSAL` | 95 | reject | no_path_traversal |

## 附录 B:冲突场景与解决速查

| 场景 | 检测 | 解决 | 章节 |
|---|---|---|---|
| 同节点多 PR | 锁校验 | 非持锁者 reject | §5.2 |
| 路径冲突 | 扫 pending PRs | needs_human 协调 | §5.3.1 |
| seq 冲突 | merge 时 | bot 统一分配 | §5.2.2 |
| 依赖失效 | 依赖状态变更扫 PRs | reject + 重提 | §5.3.3 |
| 分支漂移 | webhook 重触发 | 重新审核 | §5.3.4 |
| 循环依赖 | 管线加载 CI | 拒绝加载 | §5.3.5 |
| 同版本冲突 | 审核查 main 版本 | reject + bump | §5.3.2 |
