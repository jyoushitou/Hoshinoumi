# Windows 安装 Android SDK（VS Code 用，无需 Android Studio）

目标路径：`E:\app\AndroidSDK`  
JDK17：`D:\path\jdk-17_windows-x64_bin\jdk-17.0.8`

## 1. 建目录/下载命令行工具

Google 直连超时，使用腾讯镜像。

```powershell
$root = 'E:\app\AndroidSDK'
$jdk  = 'D:\path\jdk-17_windows-x64_bin\jdk-17.0.8'
$zip  = "$env:TEMP\commandlinetools-win.zip"
$tmp  = "$env:TEMP\commandlinetools-extract"

New-Item -ItemType Directory -Force -Path $root, $tmp | Out-Null
Invoke-WebRequest `
  'https://mirrors.cloud.tencent.com/AndroidSDK/commandlinetools-win-13114758_latest.zip' `
  -OutFile $zip -UseBasicParsing
Expand-Archive $zip -DestinationPath $tmp -Force

New-Item -ItemType Directory -Force -Path "$root\cmdline-tools\latest" | Out-Null
Copy-Item "$tmp\cmdline-tools\*" "$root\cmdline-tools\latest" -Recurse -Force
```

检查目录：

```text
E:\app\AndroidSDK\cmdline-tools\latest\bin\sdkmanager.bat
```

> 注意：不要用 `16111833` 新版 cmdline-tools。它的 `android.exe` 会去 dl.google.com 下载 Android CLI，国内会超时。使用 `13114758` 这一版。

## 2. 当前 PowerShell 设置环境

```powershell
$env:JAVA_HOME = 'D:\path\jdk-17_windows-x64_bin\jdk-17.0.8'
$env:ANDROID_HOME = 'E:\app\AndroidSDK'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:SDK_TEST_BASE_URL = 'https://mirrors.cloud.tencent.com/AndroidSDK/'
$env:Path = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\cmdline-tools\latest\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\emulator;$env:Path"

sdkmanager --version
```

> `SDK_TEST_BASE_URL` 末尾必须有 `/`。它让 sdkmanager 从腾讯镜像拉 repository，而不是超时的 dl.google.com。

## 3. 接受 license

```powershell
sdkmanager --licenses
```

一路输入 `y`，直到结束。

## 4. 安装编译 + 模拟器组件

```powershell
sdkmanager --install `
  "platform-tools" `
  "platforms;android-35" `
  "build-tools;35.0.0" `
  "emulator" `
  "system-images;android-35;google_apis;x86_64"
```

体积大致：

```text
cmdline-tools   155MB
platform-tools  ~10MB
platform 35     ~100MB
build-tools 35  ~150MB
emulator        ~450MB
system image    ~1.5GB
```

## 5. 创建模拟器

```powershell
avdmanager create avd `
  -n Hoshinoumi_Pixel `
  -k "system-images;android-35;google_apis;x86_64" `
  -d "pixel_7" `
  --force
```

查看：

```powershell
emulator -list-avds
```

## 6. 检查硬件加速

```powershell
emulator -accel-check
```

如果提示没有加速：

```text
启用 Windows 功能：
  Windows Hypervisor Platform
  （或 Hyper-V，二选一，按机器情况）
重启后再运行
```

## 7. 启动模拟器

```powershell
emulator -avd Hoshinoumi_Pixel
```

等桌面出现后，另开 PowerShell：

```powershell
adb devices
```

应看到：

```text
emulator-5554   device
```

## 8. 连接本机开发服务

前端：

```powershell
cd integrations/web
pnpm dev --host 0.0.0.0 --port 27006
```

后端：

```powershell
python run.py
```

端口转发：

```powershell
adb reverse tcp:27006 tcp:27006
```

模拟器 Chrome 打开：

```text
http://127.0.0.1:27006/chat
```

## 9. 安装测试 APK（v35.8 后）

```powershell
adb install -r app-release.apk
adb logcat | Select-String "Hoshinoumi"
```

## 10. 环境脚本

项目已有：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\android-env.ps1
```

装完 SDK 后，把脚本里的 Android SDK 候选路径加上：

```text
E:\app\AndroidSDK
```
