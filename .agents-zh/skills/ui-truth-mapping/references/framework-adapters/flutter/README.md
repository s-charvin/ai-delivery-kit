# Flutter 适配器参考

本目录是框架无关 UI 真值映射契约的 Flutter 实现参考。它不是默认流程，
也不是生产 Widget 模板。只有宿主项目确实使用 Flutter，且现有测试/资源
惯例支持这些示例时才使用。

## 静态捕获

`golden-preview-test.dart.example` 展示官方 `flutter_test` 方式：挂载真实
Widget，配置一个确定性视觉 scenario，使用 `RepaintBoundary` 和
`matchesGoldenFile`，并用宿主正常测试命令更新 golden。示例的画布和 profile
是证据设置，不是运行时布局常量。

## Golden 预览的文字保真度

文字字形也属于本次审阅范围时，应使用项目真实的文字样式、locale、方向与缩放配置，
并确认生产文字确实选择了预期字体族和字重。仅把字体字节加载到测试 FontLoader，
不会改变仍选择其他字体族的组件。如果 Flutter 测试渲染器回退到了测试字体（Ahem），
截图仍可用于证明几何布局，但不能宣称它证明了生产字形保真。所需字体不可用时，
字形级确认应保持阻塞，而不是授权使用视觉替代物。

## 动效捕获

`motion-preview-test.dart.example` 展示宿主已走通的动效链路：

- 触发真实 Widget 行为；
- 按声明的节奏推进累计 fake time；
- 通过 `matchesGoldenFile` 将每帧写入临时/忽略的帧目录；
- 使用已有 concat/VFR 链路编码保留时长的 GIF；
- 解码并校验帧数、总时长、终态/循环状态和自动循环；
- 在 `finally` 中清理帧、manifest 和编码器临时文件，包括失败路径。

示例有意使用 `testWidgets`、`pump`、`matchesGoldenFile` 等 Flutter API。这些
是适配器细节，不是核心 skill 要求。其他框架可以使用不同的官方渲染器、
时钟、捕获 API 和编码器，但必须产出相同治理下的证据字段。
