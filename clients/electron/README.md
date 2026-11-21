# Hoshinoumi Electron 桌面壳

当前方案：Electron 38.8.6，内置 Chromium，不依赖系统 WebView/WebView2。

## 开发运行

```powershell
cd integrations/web
pnpm build
cd ../../clients/electron
pnpm install
pnpm start
```

窗口：

```text
1440 × 900
最小 1180 × 760
```

## 已实现

```text
v35.6.0.0  Electron 壳骨架 / 窗口 / 最小尺寸
v35.6.0.1  复用 Vue 三栏 / 导航 / 页面容器
v35.6.0.2  托盘图标 / 菜单 / 单实例
v35.6.0.3  迷你窗口 360×130 / 置顶 / 托盘入口
v35.6.0.4  后端入口 / API 前缀 / 启动页
v35.6.0.5  迷你窗口默认关闭，设置中启用
v35.6.1.0  内置 Chromium
v35.6.1.1  Electron 38.8.6 版本锁定
v35.6.2.0  Chromium 能力探针 / 兼容标记
v35.6.2.1  本地兜底页 / 渲染崩溃回退
v35.6.3.0  electron-builder 打包配置 / 检查更新
v35.6.3.1  更新下载 / SHA256 / 安装 / 回退
v35.6.4.0  全路由加载 Vue 构建
v35.6.4.1  壳级验收清单
```

## 发布包

```text
clients/electron/dist/Hoshinoumi-35.6.0-win.zip
```

解压后双击：

```text
启动 Hoshinoumi.cmd
```

不要直接双击 `Hoshinoumi.exe`：当前机器需要启动参数和本地 user-data 目录，启动脚本已处理。

```text
--no-sandbox
--disable-gpu
--disable-crash-reporter
--disable-breakpad
--user-data-dir=%~dp0user-data
```

## 设置

托盘右键 → 设置，可配置：

```text
后端入口
API 前缀
启动页
更新源 URL
启用迷你窗口（默认关闭）
```

## 已知限制

```text
NSIS Setup.exe 在本机被临时目录策略阻止，不发布
portable 依赖 NSIS 解包，不推荐
更新流程需要真实更新源，未联调
页面内容验收随 v35.9 推进
```

## 验收

见 [ACCEPTANCE.md](ACCEPTANCE.md)。
