# 深度优化客户端：Qt / HyperOS / HyperOS 平板 / HarmonyOS 2

当前深度优化客户端：

```text
Qt 桌面
澎湃 OS / HyperOS 手机
HyperOS 平板
鸿蒙 2 / HarmonyOS 2 手机
```

不做：

```text
原生 Android 独立客户端
EMUI
```

## 粒度

```text
一功能一版本
设计/架构/API/页面/系统能力/性能分开
```

## 原生规则

```text
不加载 Vue/WebView
用平台原生语言重写
共用后端 REST / WebSocket
不复制业务 API
单独设计稿、单独排期、单独性能验收
```

## 技术栈

| 客户端 | UI | 核心 / 系统 |
|---|---|---|
| Qt 桌面（Windows / Linux） | C++20 + Qt 6 + QML | Windows：QRhi/D3D11 特效；Linux：Vulkan/OpenGL；QtNetwork / SQLite / 原生托盘 |
| HyperOS 手机 | Kotlin + Jetpack Compose | Rust JNI/NDK；通知/自启动/省电 |
| HyperOS 平板 | Kotlin + Jetpack Compose | Rust JNI/NDK；多窗口/手写笔 |
| HarmonyOS 2 手机 | Java UI 或 JS UI（FA 模型，按设备 API 版本） | C/C++ Native API；HAP；通知/后台 |

说明：

```text
HarmonyOS 2 不是 HarmonyOS NEXT，不直接套 ArkTS/Stage 模型
先按真机 API 版本确定 Java/JS FA 工程
如果设备只支持 Android APK，只能跑套壳，不算鸿蒙原生深度优化
```

## 设计稿

原生设计单独出：

```text
docs/design/v35/native/qt/
docs/design/v35/native/qt/linux/

渲染与特效：[QT-RENDERING.md](QT-RENDERING.md) · [MOBILE-RENDERING.md](MOBILE-RENDERING.md)
docs/design/v35/native/hyperos/
docs/design/v35/native/hyperos-tablet/
docs/design/v35/native/harmonyos2/
```

不套 Vue/Web 稿，不在实现阶段边写边设计。

## 版本门槛

```text
v35.11.0.0 Qt 设计稿 + 原生架构
v35.11.4.0 Linux X11/Wayland 适配
v35.13.0.0 HyperOS 设计稿 + 原生架构
v35.13.2.5 HyperOS RenderEffect/AGSL 特效
v35.14.0.0 HyperOS 平板设计稿 + 设备 profile
v35.15.0.0 HarmonyOS 2 设计稿 + 原生架构
v35.15.2.5 HarmonyOS 2 原生动画/OpenGL ES 特效
```

v35.12 原生 Android、EMUI 不排期。
