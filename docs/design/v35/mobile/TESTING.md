# v35.7 / v35.8 手机环境开发与测试


## 0. VS Code 开发（不装 Android Studio）

当前 Web 手机端开发只需要：

```text
VS Code
Node 24
pnpm
Chrome / Edge
```

本机已确认：

```text
code   1.143.1
node   v24.16.0
pnpm   12.6.0
JDK17  D:\path\jdk-17_windows-x64_bin\jdk-17.0.8（17.0.8）
```

项目本地环境脚本：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\android-env.ps1
```

当前终端要持久生效时用：

```powershell
. .\scripts\android-env.ps1
```

如被执行策略拦截，用上面的 `-ExecutionPolicy Bypass -File`。

只设置当前终端的 JAVA_HOME / ANDROID_HOME，不改系统环境。Android SDK 未安装时脚本会提示。

VS Code 推荐扩展：

```text
Vue - Official
ESLint
Prettier
TypeScript
YAML（配置文件高亮）
```

项目自带任务：

```text
Ctrl+Shift+P → Tasks: Run Task
  web: dev
  android: devices
  android: reverse 27006
  android: logcat
```

`.vscode/tasks.json` 已提供。

### 只连真机（最轻量）

不需要 Android Studio，也不需要 JDK：

```text
1. 下载 Android platform-tools（约 10MB）
   https://developer.android.com/tools/releases/platform-tools
2. 解压，把 platform-tools 加入 PATH
3. 手机打开开发者选项 → USB 调试
4. 数据线连接电脑
5. adb devices
6. adb reverse tcp:27006 tcp:27006
7. 手机 Chrome 打开 http://127.0.0.1:27006/chat
```

### 需要 Android 模拟器时才装 SDK

不装 Studio 也可以，用命令行 SDK：

```text
JDK 17
Android command-line tools
platform-tools
emulator
system image
```

大致流程：

```powershell
sdkmanager "platform-tools" "platforms;android-35" "emulator" "system-images;android-35;google_apis;x86_64"
avdmanager create avd -n Hoshinoumi_Pixel -k "system-images;android-35;google_apis;x86_64" -d pixel_7
emulator -avd Hoshinoumi_Pixel
adb reverse tcp:27006 tcp:27006
```

注意：

```text
首次下载 SDK/系统镜像较慢（几 GB）
只用真机测试的话，可以完全不装 Android SDK 模拟器
v35.8 Capacitor 打包时才需要 JDK 17 + Android SDK + Gradle
```

### v35.8 壳打包（后续）

VS Code 编辑 + 命令行构建，不需要 Android Studio：

```text
npx cap add android
npx cap sync android
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## 0.1 Windows 安装 Android SDK

腾讯镜像 + 无 Android Studio 的完整步骤见 [ANDROID-SETUP-WINDOWS.md](ANDROID-SETUP-WINDOWS.md)。

## 1. 先启动

前端：

```powershell
cd integrations/web
pnpm dev --host 0.0.0.0 --port 27006
```

后端（登录、提醒、周计划等需要）：

```powershell
python run.py
```

当前机器前端：

```text
http://127.0.0.1:27006/chat
```

同一 Wi-Fi 手机：

```text
http://10.86.124.70:27006/chat
```

后端没起来时登录弹窗无法通过；不提供游客模式。

## 2. 浏览器设备模式（最快）

Chrome / Edge：

```text
F12 → Ctrl+Shift+M → Responsive
宽度 390，高度 844，DPR 3
勾选 Touch
```

测试尺寸：

```text
390 × 844     手机竖屏
430 × 932     大屏手机
1009 × 1347   桌面（>820）
1347 × 1000   桌面横屏
```

注意：

```text
Chrome 设备模式不会模拟刘海安全区
不会弹真实软键盘
无法完整测 iOS Safari 键盘/安全区
```

所以布局和触摸可以在 DevTools 测，键盘、刘海、下载、文件选择建议上真机或模拟器。

如果桌面宽度想强制看手机布局：

```text
http://127.0.0.1:27006/chat?layout=mobile
```

## 3. Android 模拟器（推荐做 v35.8）

安装 Android Studio，创建模拟器：

```text
Pixel 7
Android 14 / API 34
```

启动模拟器后：

```powershell
adb devices
adb reverse tcp:27006 tcp:27006
```

模拟器 Chrome 打开：

```text
http://127.0.0.1:27006/chat
```

`adb reverse` 的意思是：手机里的 127.0.0.1:27006 转发到电脑开发服务器。

也可以在模拟器浏览器直接打开电脑局域网 IP：

```text
http://10.86.124.70:27006/chat
```

Android 模拟器能测：

```text
触摸
返回键
软键盘
刘海/挖孔安全区
文件选择 / 相机 / 麦克风
下载
```

v35.8 Capacitor 壳做出来后：

```powershell
adb install -r app-release.apk
adb logcat | Select-String "Hoshinoumi"
```

## 4. 真机（最接近用户）

手机和电脑同一 Wi-Fi：

```text
http://10.86.124.70:27006/chat
```

如果打不开：

```powershell
# 检查端口
Get-NetTCPConnection -LocalPort 27006 -State Listen

# Windows 防火墙放行 27006
New-NetFirewallRule -DisplayName "Hoshinoumi Web 27006" -Direction Inbound -Protocol TCP -LocalPort 27006 -Action Allow
```

真机重点测：

```text
刘海 / 灵动岛 / 底部 Home 条
软键盘弹起时输入框
横屏旋转
下拉刷新 / 回退手势
图片选择 / 语音权限
下载文件
```

## 5. iOS

有 Mac 时：

```text
Safari → 开发 → 进入响应式设计模式
或 Xcode Simulator + Safari
```

重点：

```text
Safari 地址栏收起
键盘弹起 visualViewport 变化
安全区 env(safe-area-inset-*)
输入框 16px 不缩放
```

没有 Mac 就只能用真机 iPhone 测。

## 6. 自动截图

已安装 Playwright 时：

```powershell
npx playwright screenshot --device="iPhone 13" `
  "http://127.0.0.1:27006/chat" `
  docs/design/v35/mobile/test-iphone13.png
```

或 Chrome DevTools 自带截图：

```text
Ctrl+Shift+P → Capture screenshot
```

## 7. 验收顺序

```text
1. 390×844 浏览器设备模式：布局 / 断点 / 搜索
2. Android 模拟器：触摸 / 键盘 / 安全区
3. 真机：刘海 / 键盘 / 权限 / 下载
4. 1009×1347：确认桌面 AppShell
5. 横屏：确认不横向溢出
```

## 8. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 手机打不开 | 用局域网 IP，不是 127.0.0.1；检查防火墙 |
| 登录失败 | 后端没启动 / token 错误 |
| 设备模式仍像桌面 | 宽度是否 >820；用 390 或 `?layout=mobile` |
| 安全区没效果 | Chrome 设备模式不模拟刘海，上真机 |
| 键盘遮输入框 | 用 Android/iOS 真机测，DevTools 不弹软键盘 |
| 图片/语音没权限 | 用模拟器/真机授权，浏览器需 https 或 localhost |
