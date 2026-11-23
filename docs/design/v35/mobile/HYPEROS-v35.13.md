# v35.13 HyperOS 4 深度优化（原生重写）

定位：HyperOS 4 手机原生客户端，Kotlin + Compose UI，Rust 核心通过 JNI/NDK；不加载 Vue/WebView。

## 粒度

```text
一功能一版本
设计 / 架构 / API / 页面 / 系统能力 / 性能分开
每个版本独立提交、独立验收
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.13.0.0 | HyperOS 设计 tokens / 组件冻结 | 设计稿可交付 |
| v35.13.0.1 | 设备 profile / 能力上报 API | 客户端能力可查 |
| v35.13.0.2 | Compose 工程 / 导航 / 主题 | 空壳可启动 |
| v35.13.0.3 | Rust 核心 + JNI 桥 | 核心调用通 |
| v35.13.0.4 | 网络层 / WebSocket / token 存储 | 能连后端 |
| v35.13.0.5 | 登录页 / 错误态 / 冷启动恢复 | 能登录并保持 |
| v35.13.1.0 | 会话列表 / 同步 / 未读 | 列表可用 |
| v35.13.1.1 | 私聊历史 / 分页 | 历史可读 |
| v35.13.1.2 | 群聊 / 成员 | 群聊可用 |
| v35.13.1.3 | 发送 / 流式回复 / 重试 | 消息可收发 |
| v35.13.1.4 | 撤回 / 已读 | 状态正确 |
| v35.13.1.5 | 图片 / 语音 / 表情 | 媒体可发 |
| v35.13.1.6 | 下载 / 分享 | 附件可用 |
| v35.13.1.7 | 聊天内搜索 | 搜索可用 |
| v35.13.1.8 | Compose/RenderEffect/AGSL 特效 | 动画帧率达标 |
| v35.13.2.0 | 记忆 | 页面与接口一致 |
| v35.13.2.1 | 关系 | 页面与接口一致 |
| v35.13.2.2 | 存钱总览 / 目标 | 金额可对账 |
| v35.13.2.3 | 账户 / 冻结 / 定期 / 基金 | 资金位置完整 |
| v35.13.2.4 | 周计划 | 按周读写 |
| v35.13.2.5 | 信息 | 状态可读 |
| v35.13.2.6 | 人设 | 激活 / 切换 |
| v35.13.2.7 | 命令 | 执行 / 输出 |
| v35.13.2.8 | 定时 | 增删启停 |
| v35.13.2.9 | 运行日志 | 筛选 / 搜索 |
| v35.13.2.10 | 设置 | 连接 / 账号 / 快捷入口 |
| v35.13.2.11 | 文件页 | 上传 / 下载 / 预览 |
| v35.13.3.0 | 通知渠道 / 权限 | 权限真实 |
| v35.13.3.1 | UnifiedPush/ntfy 原生接入 | 后台能收 |
| v35.13.3.2 | 通知点击 / deep link | 进对应页 |
| v35.13.3.3 | 前台服务 / 后台恢复 | 回前台可恢复 |
| v35.13.3.4 | 自启动 / 省电引导 | 系统设置可跳转 |
| v35.13.3.5 | 桌面小组件 / 服务卡片 | 数据来自后端 |
| v35.13.3.6 | 自由小窗 | 系统能力可用 |
| v35.13.3.7 | 全局侧边栏 | 系统能力可用 |
| v35.13.3.8 | 分屏 | 系统能力可用 |
| v35.13.4.0 | Room / 离线缓存 schema | 断网可读 |
| v35.13.4.1 | 媒体缓存 / 压缩 | 图片语音可用 |
| v35.13.4.2 | 权限子页真实状态 | 开关与系统一致 |
| v35.13.4.3 | Keystore / token / 隐私 | 密钥不落明文 |
| v35.13.5.0 | 启动性能 / 首帧 | 指标达标 |
| v35.13.5.1 | 120Hz 帧率 / 特效降级 | 掉帧达标 |
| v35.13.5.2 | 内存 / 包体 / ABI | 包体达标 |
| v35.13.5.3 | 深色 / 大字体 / 无障碍 | 系统跟随 |
| v35.13.5.4 | 真机矩阵 / 签名 / 发布 | HyperOS 真机通过 |

## 边界

```text
不加载 Vue/WebView
不复制后端业务 API
基础推送协议与 v35.8.4 一致，v35.13 只接原生通知
HyperOS 系统限制只跳转，不伪造状态
```

## 开发环境下载清单

必装：

```text
Android Studio（支持 API 37 的最新版）
Android SDK Platform 37（Android 17）
Android SDK Build-Tools 37
Android SDK Platform-Tools
NDK（Rust JNI 用）
JDK 17
Rust + cargo-ndk
```

小米开发者平台里真正需要看的：

```text
多任务与多窗口（文档/系统 API）
小部件适配（AppWidget 文档）
通知与状态栏（文档）
权限管理（文档 + Android 运行时权限）
系统设置（HyperOS 跳转 intent）
MiHaptic（可选，触感）
小米推送服务（可选；用 ntfy 时不需要）
超级岛（可选，实时状态）
```

不需要：

```text
小米网页秒开引擎（原生重写不用 WebView）
小米账号服务（登录仍用 QQ/token）
小米运动健康 / 妙播 / 车钥匙 / 支付 / 游戏服务
CloudKit / 相机生态引擎（CameraX 足够）
```

说明：

```text
HyperOS 没有一套“澎湃专用 SDK”能替代 Android
普通原生应用仍是 Android Studio + Android SDK
小米能力只在推送、账号、触感、超级岛等模块按需接入
```

## Level 1 独家体验适配

目标不是“能启动”，而是达到 HyperOS Level 1 独家体验要求。

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.13.6.0 | 画中画 PiP：进入/退出、回桌面自动进入 | 视频/媒体可 PiP |
| v35.13.6.1 | MediaSession / MediaStyle / 系统播控 | 播控中心显示并可控制 |
| v35.13.6.2 | 播控收藏 / 歌词 / 字幕接口 | 系统播控可收藏、显示歌词 |
| v35.13.6.3 | 系统字体大小跟随 | 0.85–2.0 倍不截断 |
| v35.13.6.4 | 无障碍 / TalkBack / 自动填充 / 色彩校正 / 音频增强 | 关键控件有标签、可聚焦 |
| v35.13.6.5 | 中英双语 / 跟随系统 / 英文兜底 | 系统语言切换不重启破版 |
| v35.13.6.6 | 应用接力（跨设备流转） | 同账号设备可接力 |
| v35.13.6.7 | 小米妙播（投播） | 发现并投放媒体 |
| v35.13.6.8 | 相机生态引擎 SDK | 拍照体验接入 |
| v35.13.6.9 | 通行密钥 Passkey | 创建/验证通行密钥 |
| v35.13.6.10 | 小米账号快速登录 | 授权登录/绑定 |

依赖与边界：

```text
应用接力 / 妙播 / 相机引擎 / Passkey / 小米账号：
需要小米开发者平台对应 SDK、应用登记和真机验证，不能只靠 Android API

PiP / MediaSession / 字体 / 无障碍 / 多语言：
Android 标准能力 + HyperOS 适配规范

没有对应设备或资质时，明确标记“未验收”，不伪造 Level 1 通过
```

验收口径：

```text
每项独立提交、独立真机验收
不完全依赖“上架/认证”才做基础适配
认证状态与代码状态分开记录
```


## Android 17（API 37）行为变更

来源：[Android 17 应用适配指南](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2297)

编译基线：

```text
compileSdk 37
targetSdk 37
Build-Tools 37
Android Studio 支持 API 37
真机：HyperOS Android 17
```

对本项目影响最大的项：

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.13.0.6 | 升 compileSdk/targetSdk 37 / API 37 工程 | 能编译启动 |
| v35.13.0.7 | 明文流量迁移到 Network Security Config | 不再依赖 usesCleartextTraffic |
| v35.13.0.8 | ACCESS_LOCAL_NETWORK 运行时权限 | 局域网后端可连 |
| v35.13.0.9 | 分享/相机显式 URI 授权 | 不再依赖隐式授权 |
| v35.13.0.10 | IME 旋转恢复 / configChanges 适配 | 旋转后键盘行为正确 |
| v35.13.0.11 | 后台音频 / mediaPlayback FGS | 后台播放不被静默 |
| v35.13.0.12 | 开发者验证（条件项：公开/GMS 设备） | 按分发范围决定 |

说明：

```text
usesCleartextTraffic 预计 Android 18 失效 → 现在改用 networkSecurityConfig
targetSdk 37 访问局域网必须申请 ACCESS_LOCAL_NETWORK
ACTION_SEND / ACTION_IMAGE_CAPTURE 要显式加 FLAG_GRANT_*_URI_PERMISSION
Android 17 旋转后 IME 不自动恢复 → 依赖 configChanges 或显式 showSoftInput
后台音量/焦点/播放会被严格限制 → 媒体播放用可见时启动的 FGS
大屏 targetSdk 37 忽略方向限制 → 平板必须自适应
PQC 混合签名 / 开发者验证属于发布阶段，不阻塞功能
```


## Android 开发者验证（Developer Verification）

来源：[Android 开发者验证](https://developer.android.com/developer-verification/guides?hl=zh-cn)

执行节奏：

```text
2026-09 起：部分地区开始强制
2027 年后：全球推广
```

对分发方式的影响：

| 分发方式 | 影响 |
|---|---|
| Google Play | 98% 自动注册，基本无感 |
| GitHub Releases APK 侧载 | 未验证开发者可能触发高级确认，甚至被拦 |
| ADB 安装 | 始终绕过，但只适合开发者 |
| 企业托管设备 | 豁免 |
| 国内无 GMS 的 HyperOS | 由小米安装器策略决定，不等于不受影响 |

是否需要做：

```text
只自己用 + ADB 安装：
  不需要注册；ADB 始终绕过

只发给国内无 GMS 的 HyperOS 用户：
  Google 验证通常不生效；但小米“未知来源”提示仍在
  不注册也能装，公开分发需自担风险

公开 GitHub，面向全球/GMS 认证设备：
  需要注册开发者、登记包名和签名证书
  GitHub 不是豁免渠道
```

如果要做：

```text
提前注册开发者身份
登记包名 com.hoshinoumi.mobile
登记 release 签名证书
保持同一签名密钥，不轮换
GitHub Release 附安装说明和高级确认步骤
不能把“ADB 绕过”当作用户安装方案
```

边界：

```text
Google 验证不改变 APK 功能
国内 HyperOS 是否弹验证，取决于设备上的验证代理/小米策略
未注册时先保留 GitHub APK + 手动安装说明，但必须标注风险
```
