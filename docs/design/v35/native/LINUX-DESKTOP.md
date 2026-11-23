# Linux 桌面适配（Qt 线）

定位：v35.11 Qt 原生桌面的 Linux 平台适配，不是 Electron/WebView 套壳。

## 目标

```text
Ubuntu / Debian / Fedora
GNOME / KDE Plasma
X11 / Wayland
HiDPI / 多显示器
```

## 系统能力

```text
StatusNotifierItem / AppIndicator 托盘
XDG 自启动
D-Bus 通知
xdg-desktop-portal 文件选择
libsecret / KWallet 安全存储
单实例
系统主题 / 深色
键盘快捷键
```

## 打包

```text
AppImage（主分发，GitHub Releases）
deb（可选）
rpm（可选）
```

签名与校验：

```text
AppImage 校验和
发布 SHA256SUMS
不依赖发行版商店
```

## 设计

Qt 原生窗口 + Linux 桌面习惯：

```text
窗口边框/标题栏符合桌面
托盘菜单
文件选择走 Portal
字体/缩放不写死
```

设计稿目录：

```text
docs/design/v35/native/qt/linux/
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.11.4.0 | Wayland / X11 适配 / HiDPI / 多显示器 | 两种会话能启动 |
| v35.11.5.0 | 托盘 / 自启 / D-Bus 通知 / Portal 文件选择 / 密钥环 | 桌面集成可用 |
| v35.11.6.0 | AppImage 打包 / SHA256 / deb/rpm 可选 | GitHub 可下载运行 |

## 边界

```text
不引入 WebView
不复制业务 API
Linux 适配不改变 Qt 原生 UI 主体
没有 Linux 真机/虚拟机就不宣称通过
```
