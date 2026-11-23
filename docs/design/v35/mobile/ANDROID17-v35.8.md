# Android 17 / API 37 与 HyperOS 4 适配

## 现状

```text
compileSdk 35
targetSdk 35
AGP 8.7.2
Gradle 8.11.1
SDK 只安装了 platforms;android-35 / build-tools 35.0.0
```

Android 17（API 37）与 HyperOS 4 不能只改版本号，必须同步升级工具链。

## 目标

```text
compileSdk 37
targetSdk 37
minSdk 23 不变
API 37 模拟器 + HyperOS 4 真机通过
```

## 工具链

```text
Android Studio 最新稳定版
SDK Platform 37
Build Tools 37.0.0
Platform Tools 最新
AGP 支持 API 37 的版本
Gradle 与 AGP 匹配
JDK 17 或 AGP 要求的新 JDK
```

不复制旧 Gradle 缓存硬编版本；按 AGP 官方矩阵升级。

## 行为变更

```text
edge-to-edge 强制
预测性返回 / 系统返回回调
16KB page size 原生库
前台服务类型与权限
notification / exact alarm
本地网络权限（如 API 37 强制）
HyperOS 4 自启动/省电
WebView 版本
```

## 升级顺序

```text
1. 安装 SDK 37 + Build Tools 37
2. 升级 AGP / Gradle / AndroidX / Capacitor
3. compileSdk 37，targetSdk 仍 35，先保证能编
4. targetSdk 37，逐个处理行为变更
5. API 37 模拟器回归
6. HyperOS 4 真机回归
7. 再切正式发布
```

## 风险

```text
Capacitor 7 对 target 37 的支持需要验证
edge-to-edge 退出开关可能失效
16KB 页要求所有 so 对齐
预测性返回会改变现有返回逻辑
HyperOS 4 后台策略未知
```

## 版本

```text
v35.8.5.0 Android 17 / API 37 编译基线
v35.8.5.1 target 37 行为适配
v35.8.5.2 HyperOS 4 真机回归
```

在 SDK 37 安装和 AGP 兼容验证之前，不把当前正式包直接切到 target 37。
