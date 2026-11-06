package workspace

// NewInstalledReader 为真实发行入口构造 reader。用途在构造时固定，解析/读取不改变用途。
// 零值 Reader 仅用于尚未安装资源的低层原始协议调查；实际 CLI 不暴露此选择。
func NewInstalledReader() Reader { return Reader{requireInstalledResources: true} }
