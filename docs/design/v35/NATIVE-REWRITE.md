# 深度优化客户端：原生重写规则

适用：

```text
v35.11 Qt 桌面
v35.12 Android
v35.13 HyperOS 4 手机
v35.14 HyperOS 3 平板
v35.15 EMUI
```

## 定义

“深度优化”= 用平台原生语言和原生 UI 重写整个客户端，不加载 Vue/WebView。

```text
不加载 HTML/CSS/JS
不复用 WebView 壳
不把页面搬进 iframe
后端 REST/WebSocket 契约保持同一套
```

## 语言与栈

| 客户端 | UI | 核心 / 系统 |
|---|---|---|
| Qt 桌面 | C++20 + Qt 6 + QML | QtNetwork / SQLite / 原生托盘 |
| Android | Kotlin + Jetpack Compose | Rust JNI/NDK；Room、OkHttp、CameraX、Media3 |
| HyperOS 手机 | Kotlin + Jetpack Compose | Rust JNI/NDK + HyperOS 系统能力 |
| HyperOS 平板 | Kotlin + Compose | Rust JNI/NDK + 多窗口/手写笔 |
| EMUI | Kotlin + Compose（Android 基线） | Rust JNI/NDK + EMUI 系统能力 |

## 设计稿必须先出

每个原生客户端单独设计，不套 Web/Vue 稿：

```text
tokens / 组件
登录 / 配置
主界面 + 聊天
业务页面
权限 / 通知 / 后台
深色 / 大字体 / 无障碍
```

目录与冻结规则：[native/README.md](native/README.md)。

## 性能口径

```text
冷启动 / 首帧有明确上限
120Hz 掉帧率可测
常驻内存有上限
包体按 ABI 统计
崩溃率有上限
```

具体数值按客户端写，不拿桌面指标套手机。

## 版本规则

```text
每个原生客户端独立列次版本
先架构/登录，再聊天，再业务页面，最后性能和真机
不和 v35.8 套壳小版本混做
不复制后端业务 API
```

## 非深度优化客户端

```text
Electron / Capacitor / VS Code / Qoder / DSH 插件：
允许 WebView / Vue，只补壳和系统能力。
```
