# v35.13 HyperOS 4 深度优化（原生重写）

定位：**不是 WebView 套壳优化，而是 HyperOS 4 原生客户端重写。**

技术选型：

```text
UI：Kotlin + Jetpack Compose（Material 3，HyperOS 视觉）
异步：Kotlin Coroutines + Flow
本地存储：Room / SQLite / DataStore
网络：OkHttp / HTTP2 / WebSocket
图片：Coil
媒体：CameraX / Media3 / AudioRecord
后台：WorkManager / ForegroundService
通知：NotificationChannel + UnifiedPush/ntfy
核心：Rust（协议/状态/缓存/加密）通过 JNI/NDK
安全：Android Keystore
```

不做：

```text
不加载 Vue
不加载 WebView
不复用 HTML/CSS
不复制后端业务 API
```

需要重写的页面：

```text
聊天列表 / 私聊 / 群聊 / 媒体
记忆
关系
存钱
周计划
信息
人设
命令
定时任务
运行日志
设置 / 权限与后台
```

性能目标（验收口径，不是承诺）：

```text
冷启动 ≤ 1s
首帧 ≤ 800ms（中端机）
120Hz 下掉帧 < 1%
常驻内存 ≤ 150MB
APK 单 ABI ≤ 30MB
崩溃率 < 0.5%
```

数据与迁移：

```text
仍用 v35 后端 REST / WebSocket
登录、token、账号模型复用
本地缓存 Room，离线可读
不迁移旧 WebView 的 localStorage 为唯一数据源
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.13.0.0 | 原生架构决策 / 设备 profile / 能力上报 API | 技术选型定稿 |
| v35.13.1.0 | Kotlin/Compose 工程 / Rust JNI 桥 / 网络层 | 空壳能登录 |
| v35.13.2.0 | 聊天列表 / 私聊 / 群聊 / 流式消息 | 核心聊天可用 |
| v35.13.3.0 | 记忆 / 关系 / 存钱 / 周计划 | 主要业务页面 |
| v35.13.4.0 | 信息 / 人设 / 命令 / 定时 / 日志 / 设置 / 文件 | 页面齐 |
| v35.13.5.0 | 原生通知 / 后台保活 / HyperOS 自启动 / 省电 | 后台能收能恢复 |
| v35.13.6.0 | 离线缓存 / 媒体 / 权限 / Keystore | 断网可用，权限真实 |
| v35.13.7.0 | 性能 / 包体 / 无障碍 / 真机回归 / 发布 | 性能口径达标 |

## 与 v35.8 的关系

```text
v35.8：Android Capacitor 套壳，先可用
v35.13：HyperOS 原生重写，替代套壳
```

v35.8.4 的通知能力是套壳基线；v35.13 不做“再实现一遍推送”，而是把同一后端推送协议接到原生 NotificationChannel / UnifiedPush。

## 风险

```text
全量重写工作量大，不能和 v35.8 小版本混做
Rust + JNI 需要单独构建和崩溃符号
Compose 与 HyperOS 动效需要真机调
原生客户端必须单独做登录/存储/媒体/权限，不复用 Vue
先保证 feature parity，再谈性能数字
```
