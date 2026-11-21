# Hoshinoumi Electron 桌面壳

Electron 38.8.6，内置 Chromium，不依赖系统 WebView/WebView2。

---

## 1. 环境要求

```text
Windows 10/11 x64
Node.js 22+
pnpm 10+
```

首次安装依赖：

```powershell
cd clients\electron
pnpm install
```

注意：本机 TLS 证书链可能阻止 Electron 二进制下载，安装失败时先看第 6 节。

---

## 2. 开发运行

```powershell
cd integrations\web
pnpm build

cd ..\..\clients\electron
pnpm start
```

窗口：

```text
1440 × 900
最小 1180 × 760
```

开发启动参数由 `start.js` 自动带上：

```text
--no-sandbox
--disable-gpu
--disable-crash-reporter
--disable-breakpad
--user-data-dir=clients\electron\user-data
```

不要直接运行 `electron .`，否则可能因为系统沙箱/crashpad 直接退出。

---

## 3. 构建发布包

开发包（zip，推荐发布）：

```powershell
cd clients\electron

$env:NODE_TLS_REJECT_UNAUTHORIZED='0'
$env:ELECTRON_BUILDER_BINARIES_MIRROR='https://npmmirror.com/mirrors/electron-builder-binaries/'
pnpm exec electron-builder --win zip
```

输出：

```text
clients/electron/dist/Hoshinoumi-35.6.0-win.zip
```

构建前建议先确认 Web 已构建：

```powershell
cd integrations\web
pnpm build
```

打包时会把 `integrations/web/dist` 复制为：

```text
resources/web-dist/
```

---

## 4. 安装 / 运行发布包

### 推荐：免安装 zip

1. 解压 `Hoshinoumi-35.6.0-win.zip`
2. 双击：

```text
启动 Hoshinoumi.cmd
```

不要直接双击 `Hoshinoumi.exe`。

启动脚本会带上当前机器需要的参数：

```text
--no-sandbox
--disable-gpu
--disable-crash-reporter
--disable-breakpad
--user-data-dir=.\user-data
```

### 直接运行目录版

```text
clients/electron/dist/win-unpacked/
```

同样运行其中的 `启动 Hoshinoumi.cmd`。

---

## 5. 安装包说明

| 目标 | 状态 | 说明 |
|---|---|---|
| zip | ✅ 发布 | 解压运行，当前推荐 |
| win-unpacked | ✅ 可用 | 免安装目录 |
| NSIS Setup.exe | ❌ 不发布 | 本机临时目录策略报错 |
| portable exe | ⚠️ 不推荐 | 依赖 NSIS 解包 |

本机 NSIS 报错：

```text
Error writing temporary file. Make sure your temp folder is valid.
```

这是系统临时目录/权限问题，不是应用代码问题。

---

## 6. Electron 安装失败修复

报错：

```text
Electron failed to install correctly, please delete node_modules/electron and try installing again
```

原因：`pnpm install` 后 Electron 运行时目录不完整。

修复：

```powershell
$e = (Resolve-Path clients\electron\node_modules\electron).Path
$zip = (Get-ChildItem "$env:LOCALAPPDATA\electron\Cache" -Recurse -Filter 'electron-v38.8.6-win32-x64.zip' | Select-Object -First 1).FullName

Remove-Item "$e\dist" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "$e\dist" | Out-Null
Expand-Archive $zip "$e\dist" -Force
'electron.exe' | Set-Content "$e\path.txt" -Encoding ascii -NoNewline
```

如果缓存没有 zip，再执行：

```powershell
$env:NODE_TLS_REJECT_UNAUTHORIZED='0'
$env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
pnpm rebuild electron
```

---

## 7. 设置

托盘右键 → 设置：

```text
后端入口
API 前缀
启动页
更新源 URL
启用迷你窗口（默认关闭）
```

保存后主窗口自动重载。

---

## 8. 窗口 / 托盘行为

```text
点最小化 → 隐藏到托盘
点关闭   → 隐藏到托盘
托盘左键 → 显示/隐藏主窗口
托盘右键 → 打开主窗口 / 迷你窗口 / 设置 / 检查更新 / 回退上一版本 / 退出
```

迷你窗口：

```text
360 × 130
无边框
置顶
不进任务栏
默认关闭
```

Windows 可能把托盘图标折叠到 `^`，可在系统设置里固定。

---

## 9. 更新

设置中填写更新源 URL，返回格式：

```json
{
  "version": "35.6.1",
  "url": "https://example.com/Hoshinoumi-35.6.1.exe",
  "sha256": "....",
  "notes": "修复说明"
}
```

流程：

```text
检查更新 → 下载 → SHA256 校验 → 启动安装包
回退上一版本 → 启动上一次保存的安装包
```

需要真实更新服务器联调；未配置更新源时只提示，不会伪造更新。

---

## 10. 当前状态

```text
v35.6.0.0–v35.6.4.1 代码已完成
发布包：dist/Hoshinoumi-35.6.0-win.zip
验收：ACCEPTANCE.md
```

已知限制：

```text
NSIS Setup.exe 不发布
更新流程未做真实服务器联调
完整页面内容验收随 v35.9 推进
```
