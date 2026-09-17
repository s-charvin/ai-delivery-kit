# Android View 可运行验证工程

此工程只验证 kit 的通用适配能力，不是业务项目模板，不随 `ai-delivery init` 分发。
生产示例采用 Kotlin、AndroidX ViewModel、纯 Reducer、StateFlow、SharedFlow 和
ViewBinding；另有 Java View 兼容测试。没有 Compose 依赖或设备前置条件。

## 运行

准备 JDK 17、Android SDK platform 36 和 build-tools 35.0.0，设置 `JAVA_HOME`
与 `ANDROID_HOME`，从 kit 根目录执行：

```bash
bash scripts/test-android-view.sh
```

Gradle Wrapper 固定 8.13，并校验官方分发包 SHA-256；首次运行需联网下载
Gradle、AGP、AndroidX、Robolectric Android SDK 和原生渲染依赖。
CI 使用独立 Android job；通用 release rehearsal 不要求 Android SDK。

## 可审查输出

- `app/build/outputs/android-view/`：真实 View PNG、25 fps GIF。
- `app/build/reports/tests/testDebugUnitTest/`：单测报告。
- `app/build/reports/lint-results-debug.html`：Android lint。

这些文件均为忽略的构建产物；发布为业务证据时必须映射到场景和当前文件哈希。
示例始终明确生成新预览，不承担已批准视觉基线的自动更新。

## 状态和动效契约

| 输入 | 状态/结果 |
|---|---|
| Submit | 创建新 requestId，loading=true，异步执行示例命令 |
| loading 时重复 Submit | 忽略，不追加请求 |
| Cancel | 取消 Job，递增 requestId，退出 loading |
| 当前 requestId 的成功结果 | 完成计数增加，退出 loading，发出一次提示 Effect |
| 过期结果或已完成结果 | 忽略 |
| 当前请求失败 | failed=true；下一次 Submit 清除错误并重试 |

示例命令使用有界 delay 演示异步完成，不模拟真实业务接口或真实资源。
Effect 仅为无订阅时可丢弃、不重放的辅助无障碍提示；完成结果保留在 UiState。
它不示范可靠导航事件投递，也不提供进程死亡后的业务数据恢复。

动画由生产按钮触发 ObjectAnimator，移动 100dp、持续 400ms。
测试每 40ms 捕获，终态额外停留 80ms。辅助源码直接从英文 Skill 编译进
`test` source set，不进入生产 APK；中文镜像保持字节一致。
捕获先对齐首个真实 VSync，以 `startOffsetMs` 单独报告启动偏移，再按 1ms
推进回调、40ms 捕获画面。JVM 单测单独开放 JDK API，以使用 ImageIO。

## 当前验证边界

2026-09-17 在 macOS 上实测 JDK 17、AGP 8.13.2、Gradle 8.13、Kotlin 2.3.21、
compileSdk 36、Robolectric 4.14.1（运行 API 35）、Roborazzi 1.74.0：
13 项单测全部通过，包括真实 PNG、25 fps 多帧 GIF、开始/中间/终态、两次
完整捕获、动画中断后文件清理与宿主重新挂载，以及状态/生命周期测试。
标准示例 GIF 为 360×640、11 帧，动画 400ms 加独立终态停留 80ms，无限循环。
本地 lint 无错误，保留固定版本更新提示及验证工程相关警告；新增 Linux CI
尚未远端运行。本地首次下载使用临时仓库镜像，镜像配置不随工程分发。

API 35 窗口关闭会通过 `BackProgressAnimator.reset()` 请求 Spring 结束。
`withHost` 最多派发两个已调度的 VSync，分别建立时间基准和处理结束请求；
这避免中断动画后重建宿主被阻塞。清理不重置全局动画、不使用任意长延时，
也不把系统返回手势当成本地已验收能力。

本地验证不能证明系统权限弹窗、IME、真实进程终止恢复、系统返回手势、
SurfaceView/WebView、原生媒体或 OEM 差异。这些能力在业务项目中按需使用
模拟器或真机补充验证，不能从本工程通过推断已覆盖。
