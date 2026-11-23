# 深度优化客户端：仅 HyperOS 与 HarmonyOS 2

只做两台有真机的手机：

```text
澎湃 OS / HyperOS 手机
鸿蒙 2 / HarmonyOS 2 手机
```

不做：

```text
原生 Android 独立客户端
Qt 桌面原生重写
HyperOS 平板
EMUI
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
| HyperOS 手机 | Kotlin + Jetpack Compose | Rust JNI/NDK；通知/自启动/省电 |
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
docs/design/v35/native/hyperos/
docs/design/v35/native/harmonyos2/
```

不套 Vue/Web 稿，不在实现阶段边写边设计。

## 版本门槛

```text
v35.13.0.0 HyperOS 设计稿 + 原生架构
v35.15.0.0 HarmonyOS 2 设计稿 + 原生架构
```

其余客户端不排期。
