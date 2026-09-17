# Android View 捕获适配

用于生产 XML/ViewBinding、Activity、Fragment、RecyclerView 和自定义 View，
不引入 Compose。功能所有权、MVI、Flow/生命周期、设计和设备验证规则读取同级
编排技能的 `references/framework-adapters/android-view.md`。

## 渲染器和证据范围

复用已验证的项目捕获设施。缺少时推荐 Robolectric Native Graphics + Roborazzi。
两者都是社区工具，不是 Android 官方渲染测试 API。共享「官方栈预览」要求在此
指使用已声明的社区测试设施运行真实 Android View，不承诺设备等价渲染。记录
渲染器、版本、命令及限制。

使用生产 XML、生成的 binding、资源、主题和 View 控件。Layout Editor/`tools:`
数据不能证明真实渲染。显式配置尺寸、density、fontScale、locale/RTL、夜间模式
和 insets。按 scenario 适用性断言 `wrap_content`、`match_parent`、ConstraintLayout
`0dp`、长文本和列表边界。使用真实且批准的资源，不能拿 kit 演示视觉充当业务证据。

- `component-only`：在测试容器挂载生产组件，并记录未覆盖的宿主组合。
- `host-static`：既有可运行入口必须挂载生产 Activity/Fragment、布局、主题、
  资源和真实组件边界。
- `host-runtime`：在模拟器/设备运行生产宿主，完成平台预检及有界视觉 smoke
  后再做昂贵生命周期测试。

捕获前完成所有共享宿主能力检查。拼装组件的合成测试 Activity 不是生产宿主证据。
Dialog 和 PopupWindow 捕获自身窗口。SurfaceView、WebView、媒体、GL/Spine、
平台 IME、权限和真实系统返回需按能力补充设备覆盖，明确记录缺少的证据。
Activity 重建不证明进程死亡恢复。

## PNG 与动态 GIF

PNG 使用 Roborazzi 或项目既有链路。动效采用共享的
[AnimatedViewCapture.kt](AnimatedViewCapture.kt)，先验证它在目标 View 和测试
设施中的时钟/栅格行为。kit 的 `tests/fixtures/android-view/` 消费同一源文件，
不要维护漂移的副本。辅助代码存在不代表项目捕获已经运行。

1. 挂载并布局真实 View，通过真实点击或生产事件启动动画，禁止逐帧赋属性伪造动效。
2. 按累计时间推进 Robolectric 主 Looper/Choreographer，25 fps（40 ms）采样。
   使用已验证不会清空动画队列或自动跳到终态的 View/Bitmap 捕获路径。
   辅助代码先派发首个 VSync，用 `startOffsetMs` 单独报告从触发到首帧的偏移。
   动画时间零以首帧为准，不把该偏移混入动画时长。回调按 1 ms 步进，画面仍每
   40 ms 捕获；大步跳动 Looper 会把 VSync 推迟到跳步终点，破坏动画起点或串联转换。
3. 包含时间零、中间帧和精确终态。终点非 40 ms 整步时追加终态采样，不能为采样
   节奏放慢产品动画。终态审阅停留与动画时长分开计算。
4. 仅用 JDK ImageIO 编码，显式设置 GIF 延时、disposal 和无限循环元数据；透明
   内容合成到真实背景。GIF 延时精度为 10 ms，声明舍入策略和实际时间误差。
   不需要 ffmpeg、WebP、MP4 或额外编码器。
5. 发布前解码，断言帧尺寸/数量、开始和中间画面变化、预期终态、含独立停留的
   总时长、disposal 和无限循环元数据。文字和颜色精度以 PNG 为准；GIF 调色板
   量化不能声称像素保真。
6. 成功和失败都关闭 ImageIO writer/stream、回收测试 bitmap、停止动画和释放
   宿主资源。中间帧只放忽略/临时目录，在 `finally` 清理。仅发布完整验证的新
   输出；失败输出必须失效/删除，不能让旧 GIF 冒充本次证据。辅助代码必须验证
   重复运行及注入编码失败路径。

参考本地 GIF 链路失败时不能移除多帧断言或换成仅设备流程。分别诊断时钟、挂载、
捕获和编码器并报告真实阻塞。业务宿主没有确定性链路时，沿用既有明确动效决策及
延后运行时验证规则，不能声称已捕获不可用的预览。

## v3 索引和验收

使用 `stack: "android-view"`。`component_path` 是仓库内的 `.kt`、`.java` 或
`.xml` 文件。`golden_test` 必填并指向真实 `.kt` 或 `.java` 测试。静态预览用
PNG，动效预览用 GIF。保留共享来源、coverage、scope、静态确认、独立动效
确认/豁免及最终集成验收契约。

每个 Android unit 必须提供 `render_inputs: [{path, sha256}]`，列出影响 scenario
的生产代码、XML、资源、主题、适用时的生产宿主以及构建/配置文件。路径唯一、
仓库相对、解析符号链接后仍在仓内，hash 绑定当前文件字节。测试及共享辅助代码
影响渲染时也列入。仅组件文件 hash 无法绑定资源/主题和构建变化。

任何输入变化后，重跑受影响测试并重新捕获预览，再更新输入 hash。仅当对应预览
以及已批准行为/动效契约均未改变，才能保留静态或动效确认。行为或动效契约变化
后，仅像素相同不足以保留批准。宿主范围必须绑定 `host_binding` 及位于
`.ai-delivery/` 外的原生测试证据；scope 标签不能代替真实宿主来源。既有
Flutter/Web v3 记录无需新字段或 schema 迁移。

## 可复制的测试入口

将 `AnimatedViewCapture.kt` 放入业务项目的测试源码，不能放入生产源码。
它依赖 Robolectric、JUnit 和 JDK ImageIO；PNG 另用 Roborazzi 捕获。
本地单测需启用 Android 资源。仅在明确生成预览时设置
`roborazzi.test.record=true`，普通基线比较不能自动覆盖已批准图片。

Android Kotlin 编译可能在本地测试中仍屏蔽 JDK desktop API。对于参考版本的
Kotlin Gradle 插件，仅对 JVM 单测任务开放：

```kotlin
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile>().configureEach {
    if (name.contains("UnitTest")) compilerOptions.noJdk.set(false)
}
```

生产和设备测试的 Android 编译保持不变。ImageIO 属于宿主 JVM 的测试依赖，
不是 Android 运行时 API。

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], qualifiers = "w360dp-h640dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
class MotionReviewTest {
    @Test fun review() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(ProductionActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val root = activity.findViewById<View>(android.R.id.content)
                root.captureRoboImage(File("build/outputs/ui-review/initial.png"))
                val result = AnimatedViewCapture.capture(
                    root, File("build/outputs/ui-review/transition.gif"),
                    durationMs = 400, terminalHoldMs = 80,
                    trigger = { activity.findViewById<View>(R.id.trigger).performClick() },
                    onFrame = { elapsed -> /* 在这里断言真实时间线。 */ },
                )
                assertEquals(480, result.durationMs)
            }
        }
    }
}
```

将入口和触发器替换为实际生产代码符号。辅助代码要求 View 已挂载、完成布局，
且具有不透明的生产背景；透明子组件应选择适当生产祖先作为捕获边界。
它不合成背景、不捕获独立窗口，也不证明 SurfaceView 或媒体输出。
场景断言必须验证画面变化及真实终态，仅编码成功不足以验收。
为独立测试宿主使用 `withHost`：成功或失败时关闭宿主、恢复时钟模式，并最多
派发两个已调度的 VSync，每次不超过配置的帧间隔。API 35 窗口销毁会调用
`BackProgressAnimator.reset()`，其 Spring `skipToEnd` 第一帧建立时间基准，
第二帧才处理结束请求。这些清理帧不计入 GIF 时间线。共享主 Looper 上不要并发
运行独立捕获。生产宿主仍负责在正常生命周期销毁中取消自身动画和订阅；
辅助代码不会取消任意应用任务，也不会清空无限循环动画。
禁止重置全局动画注册表或增加任意延时来让生命周期测试通过。额外清理必须限定
在宿主拥有的资源内；出现其他待执行任务时应定位原因。此测试设施处理不代表
已经验收真实系统返回手势。

使用业务项目实际模块/variant 的测试命令。在 kit 源码中运行
`bash scripts/test-android-view.sh` 可执行无需模拟器的样例测试和 lint；
该脚本与工程不随 `init` 安装到业务项目。
