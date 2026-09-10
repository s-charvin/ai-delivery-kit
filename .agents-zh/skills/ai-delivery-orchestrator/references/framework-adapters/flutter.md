# Flutter Stage 4 适配器

仅当宿主项目使用 Flutter，且既有测试栈支持对应捕获模式时使用本适配器。
它实现框架无关的证据范围契约，不会扩大 scenario 已冻结的范围。

## 能力映射

- `component-only`：在项目已有 widget golden 脚手架中挂载真实生产 Widget。
  preview 可以使用 `RepaintBoundary`，但被测 Widget 必须仍是生产组件；行为另行断言。
- `host-static`：使用已有页面/Widget 测试入口挂载生产页面或面板。通过生产交互
  驱动到目标状态，再走项目官方 golden 或 viewport capture 链路。
- `host-runtime`：原生视图、媒体解码器、插件或运行时资源必需时，在受支持的
  真实设备上使用 integration test 入口。通过生产导航与交互进入生产宿主后截图。

把多个生产组件手工放进新的 `Column`、`Stack` 或测试专用页面所形成的 Widget 树
不是生产宿主。它只能证明组件行为，必须归类为 `component-only`。

## 确定性静态捕获

1. 复用项目既有 binding、依赖注入、本地化、主题、屏幕尺寸及图片 fixture 设置。
2. `host-static` 必须挂载真实生产宿主，禁止把其子布局复制进测试。
3. 通过既有 controller、repository、route 或测试依赖边界准备确定性应用状态。
4. 截图前等待图片元数据、解码与首个已绘制帧。使用有上限的 pump 或明确 ready
   信号；持续活动的媒体周围禁止无界 settle。
5. 使用已有 `RepaintBoundary` 或项目 viewport screenshot 设施捕获索引边界。
6. 对必见元素和空间约束增加 geometry assertions。通过 finder/render object 解析
   实际渲染矩形；产图前验证可见性、包含关系、边缘 inset、相对位置、间距和
   hug/fill/fixed 行为。
7. 在索引声明的原生测试证据目录中，把机器可读断言报告放在截图旁边。二者均
   必须位于 `.ai-delivery/` 外。

## 设备与媒体预检

执行 `host-runtime` 前先做低成本预检。任一必需条件失败时，在编译或启动昂贵
生命周期套件前停止：

- 只有目标真实设备已连接并授权；
- battery 电量足以完成预计运行，或设备正在充电；
- 所需媒体/存储权限已授予，或可被确定性处理；
- 目标平台与 ABI 支持全部待测原生插件；
- 确定性媒体已存在，并能从生产边界读取；
- 截图和断言报告目录可写；
- 选定测试可以启动并到达首个生产路由。

scenario 要求真实设备时不得默认改用模拟器。设备、媒体或捕获前提未解决时，
不得反复运行完整 integration suite。

## 原生生命周期前的视觉 smoke

把运行时验证拆为两个命令或可过滤阶段：

1. `visual smoke`：启动、进入生产宿主、准备一个确定性 item、验证必需控件可见、
   执行 geometry assertions、捕获一张截图，并确认文件非空且可复核。
2. `native lifecycle`：仅在 smoke 通过后，按适用性验证开始、松手/停止、播放完成、
   关闭中断、切页中断、路由退出中断和原生资源释放。

对 `xc_video_player` 或其他原生媒体播放器，通过生产 controller/plugin 边界观察
生命周期。mock controller 可以证明 Dart 状态投影，但不能证明原生播放或资源释放。

## Live 媒体证据边界

Flutter UI 投影可以接收真实 `AssetEntity`，并由测试媒体源确定性地把它标记为 Live。
这能证明 UI capability：badge、toggle、routing 与播放器状态投影；不能证明 Android
媒体栈能够识别 iOS Live Photo 配对。

除非在归属平台上使用真实配对媒体和生产 classifier 执行过验证，否则把原生分类
记录为平台未覆盖。Android 设备可以验证可见投影和通用图片/视频播放，但绝不能被
引用为 iOS Live Photo 识别已通过的证据。

## 证据输出

宿主范围的 `runtime-capture` 指向：

- 索引声明的项目原生测试证据根目录下的截图；
- 精确的 widget/integration test 源文件及 SHA-256；
- geometry assertion report 及 SHA-256；
- 精确命令，适用时还包括真实设备 id；
- 与 `host_binding` 一致的生产宿主路径、入口和捕获边界；
- 报告已验证的全部必见元素及空间约束 id；
- 评审者身份、时间戳与 `reviewed_capture_sha256`。

绝不能把运行时截图复制进 `.ai-delivery/`。治理产物只保留仓内相对指针与 hash。
