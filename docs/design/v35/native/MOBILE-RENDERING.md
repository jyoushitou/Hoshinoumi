# 手机原生渲染与特效

## HyperOS / Android 基线

```text
Kotlin + Jetpack Compose
RenderEffect / BlurEffect（API 31+）
AGSL RuntimeShader（API 33+）
Compose graphicsLayer / 动画
OpenGL ES / Vulkan（重特效时）
120Hz 高刷
```

适合：

```text
消息进入
页面转场
底部栏/弹层
背景模糊
高光/渐变
轻量粒子
```

## HarmonyOS 2

```text
Java UI / JS UI 原生动画
Canvas / 组件动画
C/C++ Native API
OpenGL ES
HAP 原生渲染
```

适合：

```text
页面转场
服务卡片
弹层/遮罩
轻量粒子
通知卡片
```

HarmonyOS 2 没有 DX11，也不套 Android RenderEffect。

## 共同原则

```text
动画优先 transform / opacity
不每帧重建纹理
控制 overdraw
静态内容缓存
低端机自动降级
关闭特效不影响功能
```

## 性能验收

```text
60Hz / 120Hz 帧率稳定
帧时间 p95 有上限
GPU/内存有上限
降级后无明显卡顿
```

具体数值按真机实测，HyperOS 与 HarmonyOS 2 分开验收。

## 版本

```text
v35.13.2.5 HyperOS Compose/RenderEffect/AGSL 特效
v35.15.2.5 HarmonyOS 2 原生动画/OpenGL ES 特效
```
