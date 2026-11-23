# Hoshinoumi Android Shell

Capacitor 7 + 系统 WebView，加载同一套手机 Vue 页面。

## 环境

```text
JDK 17
Android SDK 35
Build Tools 34.0.0
```

本机 Build Tools 34 安装在：

```text
E:\Develop\AndroidSDK\build-tools\34.0.0
```

通过 junction 接到原 SDK：

```text
E:\app\AndroidSDK\build-tools\34.0.0
```

## 构建

```powershell
$env:JAVA_HOME='D:\path\jdk-17_windows-x64_bin\jdk-17.0.8'
$env:ANDROID_HOME='E:\app\AndroidSDK'
$env:ANDROID_SDK_ROOT='E:\app\AndroidSDK'
$env:Path="$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:Path"

cd clients\android\android
.\gradlew.bat assembleDebug --no-daemon
```

APK：

```text
app\build\outputs\apk\debug\hoshinoumi-35.8.4.4.apk
```

安装：

```powershell
adb install -r app\build\outputs\apk\debug\hoshinoumi-35.8.4.4.apk
adb shell am start -n com.hoshinoumi.mobile/.MainActivity
```

## 启动流程

```text
本地离线初始化页（www/index.html）
→ 用户填写后端 URL
→ localStorage 保存
→ location.href 加载远程手机 Web
```

不再把 `10.0.2.2:27006` 写死在 `capacitor.config.ts`。

## 开发地址

`capacitor.config.ts` 当前：

```text
http://10.0.2.2:27006
```

模拟器访问电脑 Vite；真机要改成电脑局域网 IP。

## 已知本地适配

```text
Capacitor 7 默认 Java 21，本机用 JDK 17，已把 capacitor 模块 source/target 改为 17
Gradle wrapper 用腾讯镜像
Maven 仓库用阿里云镜像
Capacitor 子项目的 google()/mavenCentral() 也改成了阿里云（node_modules 内，pnpm 重装会还原）
```

重新安装依赖后如果构建卡住，需要重新应用镜像和 Java 17 适配，或改用 JDK 21。

## 签名

参考：

```text
docs/design/v35/mobile/SIGNING-v35.8.md
clients/android/android/keystore.properties.example
```

真实 `keystore.properties` 不进 git。
