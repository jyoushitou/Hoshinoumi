# APK 签名与更新（v35.8）

## 结论

```text
同一 applicationId
+ 同一 release keystore
+ versionCode 递增
= 可以覆盖安装
```

签名不一致：

```text
INSTALL_FAILED_UPDATE_INCOMPATIBLE
只能卸载旧版再装，本地数据会丢
```

## 密钥

release keystore 只生成一次，之后所有版本都用它：

```powershell
keytool -genkeypair -v `
  -keystore hoshinoumi-release.jks `
  -alias hoshinoumi `
  -keyalg RSA -keysize 4096 -validity 10000
```

要求：

```text
keystore 不进 git
密码不进 git
keystore.properties gitignore
离线备份两份
密码放密码管理器
```

`keystore.properties`：

```properties
storeFile=../keystore/hoshinoumi-release.jks
storePassword=...
keyAlias=hoshinoumi
keyPassword=...
```

## Gradle

```kotlin
signingConfigs {
  create("release") {
    val props = loadKeystoreProperties()
    storeFile = file(props["storeFile"] as String)
    storePassword = props["storePassword"] as String
    keyAlias = props["keyAlias"] as String
    keyPassword = props["keyPassword"] as String
  }
}
buildTypes {
  release {
    signingConfig = signingConfigs.getByName("release")
    isMinifyEnabled = true
  }
}
```

## 构建与校验

```powershell
./gradlew assembleRelease
apksigner verify --print-certs app-release.apk
```

记录证书 SHA-256 指纹，写进更新清单：

```json
{
  "versionCode": 35801,
  "versionName": "35.8.1",
  "apkUrl": "https://.../hoshinoumi-35.8.1.apk",
  "sha256": "...",
  "certSha256": "..."
}
```

## 客户端更新校验

安装前：

```text
1. 下载 APK 到应用缓存
2. 校验文件 SHA-256
3. PackageManager 读取 APK 的 applicationId
4. 读取签名证书 SHA-256，和当前安装包比较
5. versionCode 必须大于当前版本
6. 通过 FileProvider + ACTION_VIEW 调系统安装器
```

任何一步失败：

```text
不安装
提示具体原因
不删除旧版
```

## 发布方式：GitHub Releases

不上架应用市场，只发布签名 APK：

```text
GitHub Release: v35.8.1
Assets:
  hoshinoumi-35.8.1.apk
  latest.json
  SHA256SUMS
```

`latest.json`：

```json
{
  "versionCode": 35801,
  "versionName": "35.8.1",
  "apkUrl": "https://github.com/<owner>/<repo>/releases/download/v35.8.1/hoshinoumi-35.8.1.apk",
  "sha256": "...",
  "certSha256": "..."
}
```

更新流程：

```text
GET latest.json（release 固定链接或 raw）
→ 比较 versionCode
→ 下载 APK
→ 校验 SHA-256 / applicationId / 证书指纹 / versionCode
→ FileProvider + ACTION_VIEW 安装
```

GitHub 注意事项：

```text
Release asset 会 302 到 objects.githubusercontent.com，DownloadManager 需跟随跳转
不要依赖 GitHub API 限流；优先用 latest.json 固定链接
国内网络可能无法访问 GitHub，失败要有手动打开 Release 页的兜底
APK 不通过 AAB / bundletool 发布
```

## 密钥丢失

```text
不能换 key 覆盖安装
只能卸载重装
重装前先导出/备份数据
所以 release keystore 必须离线备份
```

## 对应版本

```text
v35.8.2.0  签名配置 / release APK
v35.8.2.2  更新下载 / 签名校验 / 安装
v35.8.2.3  真机覆盖安装验收
v35.8.2.4  WebView 兼容模式 / APK 兜底
```
