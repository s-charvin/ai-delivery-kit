# Android View 交付适配

XML、Activity、Fragment、RecyclerView 或自定义 View 任务按需读取。沿用既有
阶段和唯一 `design.md`；本适配不引入 Compose、新状态或额外审批。

## Stage 1：按功能所有权分类

检查目标模块、Gradle variant、SDK/JDK、语言、架构、异步机制、资源、导航及
既有渲染/测试设施。记录本次属于旧功能扩展还是独立新功能。

| 所有权 | 实现规则 |
|---|---|
| 旧页面/功能的修复、扩展、辅助类提取 | 延续其 MVP/MVVM/MVI、语言和异步机制。 |
| 独立新页面或功能模块 | Kotlin + MVI + Flow/StateFlow + ViewBinding。 |
| 新功能复用既有 Repository、Service、导航 | 在既有边界适配，不重写旧实现。 |
| 工具、局部自定义 View、ViewHolder | 按职责采用技术，不创建无业务意义的 MVI Store。 |

新建文件不等于新功能。接入旧 Activity 的独立新功能仍拥有自己的 MVI 边界。
仅在不同所有权划分会实质影响范围或维护成本时询问并记录决策。

## Stage 3：唯一设计契约

默认用 AndroidX ViewModel 承载小型 MVI 闭环。View 提交 `Intent/Event`，纯
Reducer/Decision 返回状态和命令；ViewModel 执行 I/O，将结果事件回流。
仅暴露只读 `StateFlow<UiState>`，内部保留可变状态。不强制第三方 MVI 框架，
简单功能不要求独立 Store/Reducer/EffectHandler 类。

在 `design.md` 中记录业务状态、请求状态、局部输入与 UI 投影的所有权，以及
错误、重试、取消、重复操作、并发、过期结果和恢复策略。简单行为使用紧凑
转换表，实际复杂时才展开既有复杂状态流契约。MVI 本身不触发
`state_flow_required` 或 CP-DESIGN。

一次性 `UiEffect` 与持久 `UiState` 分开。明确后台、旋转、返回和重建时的
投递、丢弃或确认语义。Channel 或 SharedFlow 配置本身不能保证可靠投递。
必须跨断连或进程死亡投递时，明确所有权、持久存储、标识与确认机制。
按需复用 Repository/SavedStateHandle 边界；ViewModel 保留不证明进程恢复。
未知业务预期沿用既有需求冲突询问协议。

使用 `repeatOnLifecycle(STARTED)` 收集 Flow。Fragment 使用
`viewLifecycleOwner.lifecycleScope` 及其生命周期，不绑定寿命更长的 Fragment。
在 `onDestroyView` 释放 binding、监听器、动画回调及 View 引用；ViewHolder
拥有自己的 binding。取消和重新订阅必须符合已声明的状态/Effect 语义。

## Stage 2 与 Stage 4：渲染和验证

PNG/GIF 捕获及 v3 证据绑定读取同级 UI Truth Mapping 技能的
`references/framework-adapters/android-view/README.md`。复用项目已有设施；
缺少时推荐 Robolectric Native Graphics 与 Roborazzi。它们是运行真实 Android
View 的社区工具，并非 Android 官方截图 API。这是共享宿主栈预览要求在
Android 下的具体解释，不代表设备级保真能力。

挂载生产 XML、binding、主题、资源和控件。测试可通过生产边界提供确定性数据；
kit fixture 的视觉资源不能代替业务项目有来源证据的资源。按适用性验证
density/dp/sp/px、fontScale、locale/RTL、夜间模式、insets、`wrap_content`、
`match_parent`、ConstraintLayout `0dp`、长文本及列表边界。Layout Editor 和
XML `tools:` 值不是渲染验收证据。

旧功能沿用既有测试。新功能覆盖纯转换、ViewModel/Flow、真实 View 渲染、重复
操作、取消、过期响应、Effect 消费、Fragment View 重建/binding 释放、订阅
停止/重启以及 RecyclerView 复用。重复捕获及失败路径检查时钟、监听器、资源
泄漏和旧产物误用。

本地测试验证状态、交互、几何、重建和资源所有权。真实权限弹窗、IME、系统
返回、窗口行为、平台媒体和原生表面使用模拟器/设备证据。Dialog/PopupWindow
必须捕获其真实窗口。SurfaceView、WebView、媒体、GL/Spine 等按具体能力补充
设备覆盖。Activity 重建不等于进程死亡验证。逐项记录未覆盖的平台行为，不能
以本地通过证明这些能力。

`component-only` 在测试容器挂载生产组件；`host-static` 使用挂载生产 Activity
或 Fragment 的既有入口；`host-runtime` 在设备捕获生产宿主。合成测试页面不能
制造宿主证据。保留独立静态、动效（含明确无动效）及最终人工集成验收。

## 参考环境和分发

kit fixture 位于 `tests/fixtures/android-view/`。参考版本为 JDK 17、AGP 8.13.2、
Gradle 8.13、Kotlin 2.3.21、compileSdk 36、Robolectric 4.14.1、Roborazzi 1.74.0。
固定并运行 fixture 后才可声称该组合在对应环境可用；版本列表不是测试证据。
不强制业务项目升级到该组合。

指南/捕获辅助代码随技能资源分发。fixture 仅供 kit 使用；`init` 不复制 fixture、
不修改业务 Gradle 依赖、不在 kit 根目录创建治理状态。独立 Android CI 必须具备
JDK/SDK，缺少即失败；普通 Go/release 检查不依赖 Android SDK。
