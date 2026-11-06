# 当前协议与升级选择

ai-delivery-kit 只读取当前交付协议。不支持的格式会停止依赖该数据的操作。普通 `init --upgrade` 在刷新受管资产前只检查已有元数据，不迁移或重置业务数据，不证明所有需求均已通过验收。当前格式损坏、缺材料、测试失败和缺批准分别报告，不自动判为旧版本。

| 产物 | 当前要求 |
| --- | --- |
| `meta/project-binding.json` | `version: 3` |
| `meta/workflow-policy.json` | `version: 4`、`verification_contract_version: 2` |
| 需求 `status.json` | `_schema: "2.0"` |
| 适用的 `verification.md` | verification contract `version: 2` |
| 适用的 `contracts/ui-truth-index.json` | `schema_version: 3` |
| 适用的 `visual-acceptance.json` | `schema_version: 2` |
| archived entry | `archive_evidence.version: 1`，固定当前合同身份 |

新需求 intake 可以尚无 status，draft 不强制最终验证材料。当前自定义布局和 `context.sources` 继续有效。旧版本、未知更高版本、缺必需格式声明、旧豁免字段及 checkpoint 均拒绝。只改版本号不代表数据有效。

## 两种方案由你自行选择

**A. 迁移需要继续使用的数据。** 自行备份后，将下方提示词和完整错误输出交给自己的 AI，或手动处理。不绑定模型、provider、IDE，不要求调用 AI API。kit 不执行迁移、不管理迁移会话。

**B. 备份旧数据并初始化新交付工作区。** 显式运行：

```sh
ai-delivery init --upgrade --reset-data /absolute/project/path
```

已有自定义交付根时，明确给出项目内相对路径：

```sh
ai-delivery init --upgrade --reset-data=tooling/delivery /absolute/project/path
```

自定义根须有明确的项目内元数据边界；若标准 `.ai-delivery` 根已存在且冲突则拒绝重建。稳定的项目根 `.ai-delivery.lock` 让重建与归档串行，旧根移走时仍使用同一把锁。重建与交付动作共用平台原生锁；平台支持通过本机 CI 验证，交叉构建不替代实机证据。

含空格的路径须加引号。命令将原文件完整保存到活跃治理目录之外、项目内唯一的 `.ai-delivery-backups/` 目录，报告绝对位置，再初始化当前受管交付资产。不会继承旧任务状态，不要求迁移、重验或继续维护旧任务，不调用 AI，也不会在普通升级失败后自动运行。若完整备份后初始化失败，请保留备份并根据输出的恢复路径及已触及范围处理；失败命令不代表重建成功。不得覆盖旧备份。备份清单只服务文件恢复，不参与验收。

两种方案平级，普通入口不会替你选择。处理后重跑原命令；当前校验和授权仍须满足，“已备份”或“AI 说已迁移”都不能豁免。备份中的旧材料不参与现行任务发现。普通资产刷新可能保留旧受管 helper；备份后用户或其 AI 可清理过时的 kit 文件，当前入口不调用它们。不要删除无关 skills 或第三方配置。

`--upgrade-policy` 和 `--verify-archive` 已移除。正常运行不要求兼容开关、迁移收据、迁移来源摘要或备份登记。缺少有效当前身份的旧归档不能用当前字节补造历史批准。

## 可复制迁移提示词

```text
请帮助我处理这个项目的 ai-delivery-kit 数据升级问题。

项目、冲突文件、实际格式、目标格式和当前规范入口，以我附上的错误输出为准。
目标是让需要继续使用的数据满足当前 ai-delivery-kit 的唯一现行协议。
你可以使用自己的调查和操作方式，不需要调用特定 AI 服务或迁移命令。

请先读取项目规范和当前版本的模板、校验器及产物说明，再处理数据。
修改前请将旧交付数据及本次准备改动的配置/文件完整备份到活跃治理目录之外，
告诉我备份的绝对路径和包含范围。保留原始字节、文件名及链接关系，不覆盖旧备份。
不要把旧备份重新放进现行任务扫描范围。

对仍需继续的任务，保留原始需求、用户输入、来源和已确认的产品决定，
按当前格式整理设计、状态、依赖、验证和适用 UI 合同。
如果旧证据或批准不足以支撑当前阶段，明确记录缺口，恢复到有依据的阶段或阻塞状态，
不要伪造已执行测试、人工批准、独立评审或新的 archived 身份。
更改已批准文件会使原 hash 失效；只有确实需要新决定时才向我询问。

旧的已完成记录如已完整符合当前协议，可以保留；否则放在备份中供查阅，
不要新建旧版本解析器、豁免字段或假验收来让它们继续参与当前运行。
混合需求中移出旧记录前，处理活跃任务的依赖及引用，不能靠删依赖制造完成。
需要沿用的历史事实应作为有来源的背景，并由当前任务证明当前可用性。

不要为迁移顺手修改产品代码、删除第三方配置、自动提交或推送。
如果确需超出交付材料的产品修复，请先说明范围。

最后用当前安装的校验器和路由检查受影响任务，说明：
哪些数据迁入当前工作区、哪些只保留在备份、哪些材料仍待补齐，
以及实际验证结果和下一步。仅完成备份或改版本号不代表迁移成功。
```

## 当前嵌套根

从项目根自动发现仅检查标准根或直接一级自定义目录。已有当前数据根嵌套更深时，可显式传该根：`ai-delivery init --upgrade /project/tooling/delivery`。命令原位检查已有元数据，不扫描项目历史，也不创建第二份交付根。查询和恢复 IDE 备份同样可传这个路径：`ai-delivery ide-gates list /project/tooling/delivery`、`ai-delivery ide-gates restore --to <timestamp> /project/tooling/delivery`。备份重建仍传项目路径，并用相对 `--reset-data=tooling/delivery` 明确旧根。

## 当前程序与资源

直接下载所选发行的单一 `ai-delivery` 程序即可；kit 日常运行不需要 Go SDK、Python、Node 或 zsh。宿主声明的原生工具独立安装。`ai-delivery info --project <path>` 显示程序绝对路径、发行/revision 与 protocol/resources digest。缺失或不匹配的 `meta/kit-assets.json` 仅要求显式 `init --upgrade` 刷新资源，不要求重置业务数据。工具更新不自动刷新项目。

当前带时间的字段要求带时区 RFC3339Nano，例如 `2026-11-05T12:00:00+08:00`；不接受空格分隔等旧宽松形态，不自动归一化批准时间。资源可直接读取：`ai-delivery info --resource kit://ai-delivery-orchestrator/templates/verification-template.md`。`evidence review-digest` 同时返回 `input_sha256` 和 `verification_sha256`，只计算当前合同内容身份，不证明执行、评审或批准。

复盘 `reviewed-at` 标记也接受合法的 `YYYY-MM-DD` 日历日期；包含时间时必须使用同一严格带时区 RFC3339Nano 规则。此前宽松接受的无时区时间、单数字小时、逗号小数和 `+24:00` 偏移，现在需要用户自行确认原意并规范化，或选择显式备份重建。工具不猜测时区、不改写原标记。
