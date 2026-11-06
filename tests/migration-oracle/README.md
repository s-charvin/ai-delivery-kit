# 固定开发基线

此目录不参与发行、项目安装、默认 CI 或日常动作。候选只有单一 Go 核心；不能在失败时调用这里的文件。

`legacy/` 保留 T9 前明确列出的旧实现原字节，路径相对于旧 checkout；`legacy/source-manifest.json` 保存原路径、新路径与 SHA-256。该固定副本不接收业务修复、不扩大版本范围，也不提供项目入口 wrapper。显式使用 Python 的维护者可以把它作为函数级差分来源；需要完整旧命令环境时应使用已冻结的完整基线 archive，而非给候选补兼容层。

例如，独立准备语料后运行：

```sh
python3 tests/migration-oracle/ui_semantics.py --baseline /absolute/frozen-baseline --corpus /absolute/corpus
```

现有旧 shell 开发测试只可在明确的完整固定基线目录中运行；它们不证明 Go 候选通过。Go 候选以 `go test ./...` 中的领域、进程、锁、安装与无解释器真实 CLI 用例为准。宿主主动声明 Python/Node/Java 等时，那是宿主工具依赖，不是 kit 运行依赖。
