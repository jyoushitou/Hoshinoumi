# 项目本地 Android 构建环境（不修改系统 JAVA_HOME）
# 用法：. .\scripts\android-env.ps1

$ErrorActionPreference = "Stop"
$Jdk = "D:\path\jdk-17_windows-x64_bin\jdk-17.0.8"
if (-not (Test-Path (Join-Path $Jdk "bin\java.exe"))) {
    throw "找不到 JDK17：$Jdk"
}
$env:JAVA_HOME = $Jdk
$env:Path = (Join-Path $Jdk "bin") + ";" + $env:Path

$sdkCandidates = @(
    "$env:LOCALAPPDATA\Android\Sdk",
    "C:\Android\Sdk",
    "D:\Android\Sdk",
    "E:\app\AndroidSDK"
)
foreach ($sdk in $sdkCandidates) {
    if (Test-Path (Join-Path $sdk "platform-tools\adb.exe")) {
        $env:ANDROID_HOME = $sdk
        $env:ANDROID_SDK_ROOT = $sdk
        $env:Path = (Join-Path $sdk "platform-tools") + ";" + (Join-Path $sdk "cmdline-tools\latest\bin") + ";" + $env:Path
        break
    }
}

Write-Host "JAVA_HOME=$env:JAVA_HOME"
if ($env:ANDROID_HOME) {
    Write-Host "ANDROID_HOME=$env:ANDROID_HOME"
} else {
    Write-Host "ANDROID_HOME=<未安装 Android SDK>"
}
