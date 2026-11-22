# v35.8 手机套壳 App 开发计划

> 定位：Android 优先的 Capacitor/WebView 套壳，加载**同一套**手机 Vue 页面；不是第二套业务 UI。

## 设计稿

- [交互演示 HTML](hoshinoumi-mobile-shell-v35.8-demo.html)
- [静态设计稿 HTML](hoshinoumi-mobile-shell-v35.8.html)
- [hoshinoumi-mobile-shell-v35.8.png](hoshinoumi-mobile-shell-v35.8.png)

## 交互演示范围

```text
启动动画 / 加载 / 登录
首次使用邀请码注册
后端 URL / QQ / token 连接设置
WebView 内 v35.7 全功能页面
断网 / 安全拦截 / 权限 / 更新 / 自检
```

## 账号与首次登录

账号不是前端公开注册，QQ 身份由 NapCat 绑定，邀请人先创建账号：

```text
邀请人（朋友 / 主人）：!adduser <QQ> → 生成一次性 setup code
普通账号首次登录：QQ + setup code + 新密码
之后登录：QQ + 密码
主人 Web：QQ + owner token
```

所以壳里的“首次登录”只显示：

```text
QQ 号（必填）
邀请人提供的 setup code
新密码 / 确认密码
[设置密码并登录]
```

不再让用户填邀请码、QQ、昵称重新注册；设置密码时需要输入 QQ。
不提供游客模式；未登录不能进入业务页面。

## WebView 过旧与 APK 更新

```text
系统 WebView 108 < 120：自检拦截
主路径：下载最新 Hoshinoumi APK，安装后进入兼容模式
APK 来源：GitHub Releases（不上架应用市场）
备路径：系统设置更新 Android System WebView
```

边界：

```text
APK 更新的是 Hoshinoumi，不会升级系统 WebView
兼容模式需要单独实现；没有兼容层时安装新 APK 仍会自检失败
不能假装安装 APK 就修好了 WebView
```

## 1. 架构

```text
Android App (Capacitor)
  └─ WebView
       └─ 同一 URL 的 v35.7 / v35.9.30 手机 Vue
            └─ /api/* 后端
```

规则：

```text
同一 URL、同一套 Vue、同一套 API
壳只补系统能力，不重写业务页面
登录态存在 WebView 持久存储；退出清空
只允许 https + 配置的站点 host
文件/相机/麦克风/下载/分享走 Capacitor 桥
不内置第二套聊天、记忆、存钱页面
```

## 2. 列次版本

| 列次 | 内容 |
|---|---|
| v35.8.0 | 壳骨架 / WebView / 登录 |
| v35.8.1 | 安全区 / 键盘 / 文件 / 媒体 / 生命周期 |
| v35.8.2 | 签名打包 / 自检 / 更新 / 真机验收 |
| v35.8.3 | 接入 v35.9.30 手机最终页面并收口 |

## 3. 次次版本

### v35.8.0 壳骨架

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.0.0 | Capacitor / Android 工程初始化、包名、版本号、最低 SDK | 能编译空壳 |
| v35.8.0.1 | WebView 加载手机 Web URL、登录页、Cookie/存储持久化 | 能登录并保持 |
| v35.8.0.2 | 加载失败页、重试、离线提示、host allowlist | 断网不白屏 |
| v35.8.0.3 | 深色状态栏、启动图、图标、WebView 安全配置 | 启动无闪烁/无混合内容 |

### v35.8.1 系统能力

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.1.0 | 安全区 / 状态栏 / 导航栏 / 键盘避让 | 刘海和 Home 条不挡内容 |
| v35.8.1.1 | 文件选择 / 相机 / 相册 / 图片发送 | 手机能发图 |
| v35.8.1.2 | 麦克风权限 / 语音录制 / 发送 | 能录音发送 |
| v35.8.1.3 | 返回键 / 手势 / 前后台切换 / 恢复会话 | 返回不误退，后台回来不丢 |
| v35.8.1.4 | 下载 / 分享 / 外部打开 / 权限拒绝提示 | 图片语音可下载分享 |

### v35.8.2 打包 / 自检 / 更新

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.2.0 | Android 签名配置、release APK、GitHub Releases 资产 | 可安装 |
| v35.8.2.1 | 启动自检：WebView 版本 / 网络 / host / 存储 / 崩溃日志 | 出错有可读提示 |
| v35.8.2.2 | 版本检查、下载、安装、失败回退 | 更新失败回旧版 |
| v35.8.2.3 | 真机矩阵：Android 10–15、刘海/挖孔、手势导航、平板 | 验收表通过 |

### v35.8.3 收口

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.3.0 | 接入 v35.9.30 手机最终页面，删除临时适配 | 壳内页面与手机 Web 一致 |

## 4. 与其它版本边界

```text
v35.7     手机浏览器 Web
v35.8     手机安装壳（Capacitor/WebView）
v35.9.30  手机 Vue 最终页面
v35.10    Electron 壳接 v35.9 全功能
v35.12    Android 原生（Kotlin + Compose）
```

## 5. 风险

```text
iOS 不做在 v35.8，后续单独评估 WKWebView
WebView 版本旧 → 启动自检提示升级或使用 v35.12 原生
下载/文件权限 → 拒绝时明确提示，不静默失败
更新安装受系统权限限制 → 失败保留旧版
```
