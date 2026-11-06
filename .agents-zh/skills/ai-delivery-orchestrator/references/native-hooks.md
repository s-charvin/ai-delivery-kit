# 可选原生 hook

没有 hook 时，显式 `ai-delivery context`、`check`、`run`、`advance`、`archive`
流程仍完整可用。技能和外部框架只提供方法；当前协议、适用性、证据和动作由已安装 CLI
判断。hook 只是传输适配，不是另一权限引擎或任务库。

## 范围与支持

不带 `--host` 的 `hook` 仍是同进程 `check` 别名，输出 kit JSON。
`hook --host codex --event SessionStart|PreToolUse` 从 stdin 读取一个原生 JSON 对象。
明确提供绝对路径 `--project`；`cwd` 解析后必须在项目内，允许子目录，不增加 Git 要求。
同时提供 `--req` 和 `--subreq`；SessionStart 使用 `--role`，PreToolUse 使用
`--intent` 和可选 `--to`。不能从命令文本、session ID、transcript 或最近任务猜测。
部分 scope 是错误；两个 ID 均未提供时只返回有界的显式 CLI 提醒，不运行检查。

SessionStart 在同进程调用已有 context 入口。可重复 `--path`；`--budget-chars`
默认 4000，范围 0..64000。`needs_read` 或 `missing` 的必需来源仍须补读或处理；
上下文完整不等于获得权限。PreToolUse 调用同一作用域检查服务，通过时绝不输出
`permissionDecision:allow`，也不重写工具。只选明确且狭窄的写工具 matcher，
不要给全部 shell 命令加门禁而阻断解决缺口所需的阅读。适配器不解析 shell 命令或
patch 来分派任务所有权。

输入上限 1 MiB。重复键（包括嵌套）、尾随 JSON、非法编码/类型、事件错配、
不支持的事件/宿主及项目外 cwd 返回 exit 2 + stderr；允许未知扩展键。
`transcript_path` 可缺席、为 null 或字符串，其他类型拒绝；适配器不读取该 transcript。
核心拒绝当前明确动作时返回 exit 0 + 原生 `permissionDecision:deny` 和诊断理由。
资源漂移等核心错误返回 exit 2 + stderr，保留恢复指向。SessionStart 如实呈现
不完整上下文，不制造权限；输入/核心错误同样 exit 2。不新增 Stop、续跑循环、
权限覆盖、任务树、journal 或模型 API。

输出文字上限 12000 个 Unicode 字符。截断有明确提示，必须用显式 CLI 取得完整
来源/诊断。Codex 自身也可能将额外上下文 spill，注入成功不等于已完整阅读或应用。

## 可审查的显式启用示例

默认安装不添加 kit command hook，也不创建、启用、禁用或改写 `.codex/config.toml`。
用户已有 `features.hooks` true/false 和第三方定义保持用户选择。三个可选宿主 JSON
（`.codex/hooks.json`、`.claude/settings.json`、`.cursor/hooks.json`）不安装，
也不是 kit 资源清单的必需项，可缺席或省略 hooks。已有文件在 init/upgrade/reset 中
原位原字节保留，包括大整数和格式；用户自行创建或编辑 opt-in 定义。kit 不解析、
重编码、迁移或删除这些文件，遗留旧 hook 由其维护者自行审查。显式历史备份恢复仍
按原字节处理。当前受管 skills、AGENTS 区段及业务合同保持强身份检查；旧资源清单
通过显式 `init --upgrade` 刷新，不绕过身份。

先选定准确项目/切片/动作，再把已审查的定义合入用户现有项目 hooks 配置。替换下例的
绝对路径和 scope，并使用实际平台 shell 的路径引用方式。此例使用 POSIX command；
Windows 应按宿主文档使用 `commandWindows` 及其引用规则，并单独验证运行。

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{
      "type": "command",
      "command": "\"/absolute/path/ai-delivery\" hook --host codex --event SessionStart --project \"/absolute/project\" --req R --subreq SR-001 --role implement --path src --budget-chars 4000",
      "additionalContextLimit": 4000
    }]}],
    "PreToolUse": [{"matcher": "apply_patch", "hooks": [{
      "type": "command",
      "command": "\"/absolute/path/ai-delivery\" hook --host codex --event PreToolUse --project \"/absolute/project\" --req R --subreq SR-001 --intent implement --to in_dev"
    }]}]
  }
}
```

固定 scope 不适用于其他任务；范围改变时更新或禁用该定义。不得覆盖其他 hook、设置
全局信任或代用户确认宿主 hash 审查。非托管 hook 和项目来源仍需宿主自身信任流程，
定义改变后重新审查；CLI `/hooks` 或桌面 Review hooks 承载该选择。

## 证据边界

传输格式依据 2026-11-05 实际取得的 Codex 官方
[hooks](https://learn.chatgpt.com/docs/hooks) 与
[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
协议夹具和真实二进制 stdin/stdout/退出测试不证明本机 Codex 已启用、已信任、可连接或
实际回调；这些宿主行为尚未验证，也不认证任何本机宿主版本。不支持该协议的宿主版本
使用显式 CLI。Claude/Cursor 原生 transport 未实现。
宿主某些回调错误、超时或畸形响应可能继续工具，hook 是辅助护栏，不是完整执行边界；
最终显式动作检查仍须保留。
