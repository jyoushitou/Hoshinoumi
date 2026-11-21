# 运行

```powershell
cd integrations/web
pnpm build
cd ../../clients/electron
pnpm install
pnpm start
```

Electron 内置 Chromium，不依赖系统 WebView/WebView2。

窗口：

```text
1440 × 900
最小 1180 × 760
autoHideMenuBar
```

下一阶段：自定义标题栏、托盘、小窗、更新。


## 迷你窗口

```text
默认关闭
托盘右键 → 设置 → 启用迷你窗口
尺寸 360×130，无边框，置顶，不进任务栏
快捷键 Ctrl/Cmd+Shift+M（启用后生效）
```
