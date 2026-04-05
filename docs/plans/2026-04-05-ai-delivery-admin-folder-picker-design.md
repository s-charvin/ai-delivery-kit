# AI Delivery Admin Folder Picker Design

## Goal

为 `ai-delivery-admin` 的 `Bound Project` 区域增加系统原生文件夹选择能力，避免用户只能手动输入绝对路径。

## Problem

当前 `Project Root` 只能靠文本输入。对于本地控制台来说，这会带来两个体验问题：

- 输入绝对路径成本高，容易输错
- 用户知道“应该选一个文件夹”，但界面没有直接表达这个动作

## Constraints

- `bindProject` 仍然需要拿到真实绝对路径
- 纯浏览器前端不能可靠地直接拿到系统级绝对目录路径
- `ai-delivery-admin` 是本地 Node 服务，因此可以由服务端调用系统级选择器
- 当前用户环境是 macOS 路径形态，因此本次实现优先保证 macOS 原生文件夹选择

## Options

### Option 1: Browser `showDirectoryPicker`

优点：

- 前端实现简单
- 不需要服务端新增接口

缺点：

- 不能稳定拿到可直接回传给后端绑定的绝对路径
- 浏览器兼容性和权限模型不适合当前“本地 Node 控制台绑定项目路径”的需求

结论：

- 不采用

### Option 2: Local server route opens native folder picker

优点：

- 能返回真实绝对路径
- 符合当前本地 Node 控制台的能力边界
- 前端只需要一个清晰的“选择文件夹”动作

缺点：

- 需要服务端新增一条受控路由
- 平台能力需要处理取消和不支持场景

结论：

- 推荐并采用

### Option 3: Desktop-specific bridge or plugin API

优点：

- 能力更强，可以与宿主环境更深集成

缺点：

- 偏离当前 Hono + React 控制台的通用结构
- 增加额外耦合，不符合本次最小改动目标

结论：

- 不采用

## Selected Design

在 `ai-delivery-admin` 服务端新增一个受控接口，例如：

- `POST /api/system/select-project-root`

返回结构：

```json
{
  "project_root": "/absolute/path",
  "cancelled": false
}
```

用户取消时：

```json
{
  "project_root": null,
  "cancelled": true
}
```

## Server Behavior

- 在 macOS 下通过原生系统文件夹选择器获取目录
- 优先使用内置 Node 能力加系统命令，不新增额外依赖
- 对“用户取消”与“系统失败”做明确区分
- 对不支持的平台返回清晰错误，而不是静默失败

## Web Behavior

在 `Bound Project` 区域新增一个按钮：

- `Choose Folder`

交互规则：

- 点击后显示按钮级 loading
- 成功选择则把返回路径写入 `Project Root` 输入框
- 取消选择不报错，不清空已有路径
- 系统调用失败时显示明确错误
- 保留手动输入能力，文件夹选择是增强而不是替代

## Accessibility And Feedback

- 按钮要有清晰标签
- loading 只作用于该按钮，不锁死整个表单
- 错误通过现有错误反馈机制展示
- 取消不应被当成错误弹窗骚扰用户

## Verification

- 服务端测试：接口能返回注入的目录路径，并能表达取消
- 前端测试：点击 `Choose Folder` 后，输入框会回填选择结果
- 最终验证：`npm test`、`npm run typecheck`、`npm run build:web`
