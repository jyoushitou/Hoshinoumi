# 客户端清单

`clients.json` 可选，格式：

```json
{"clients":[{"id":"android","name":"Android APK","kind":"mobile","platform":"android","version":"35.9.3.13","versionCode":359313,"file":"latest.apk","notes":"Debug 包","recommended":true}]}
```

`file` 相对 `data/apk/`；没有配置时，网关自动把 `latest.apk` 作为 Android 客户端返回。
手机、桌面、后续深度优化版本都通过同一接口返回；文件不存在不会出现在列表里。
