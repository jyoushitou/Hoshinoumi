# v39 游乐园 U3D 资源与入口

## 定位

v39 是 Unity 3D 游乐园，不再按 2D 房间设计。

```text
主 App：聊天 / 记忆 / 关系 / 设置
v39：独立 Unity 3D 空间，通过 PlaygroundHost 进入
```

开始时只放入口：

```text
未下载资源：入口显示“未安装”
点击入口：进入资源下载页
下载完成：入口可用
下载完成：底部“信息”替换为“游乐园”
卸载资源：恢复“信息”
```

## 关键限制

Unity 运行时（so + player）不能安装后动态补进 APK。

```text
方案 A：Unity runtime 打进主 APK / 各 GUI 客户端
        场景、角色、家具资源按需下载
方案 B：游乐园独立 APK，主 App 深链拉起
方案 C：Google Play Dynamic Feature（GitHub 直发不适用）
```

v39 默认方案 A，主客户端体积会增加 Unity runtime；如果必须保持 3MB 主 App，只能走方案 B。

## 资源状态

```text
not_installed   只有入口，未下载
downloading     下载中，可暂停/继续
ready           校验通过，可以进入
updating        资源更新
broken          校验失败，可重下
```

## 清单

```text
GET /api/park/manifest
{
  version, min_app_version, total_bytes,
  files: [{path, url, sha256, bytes}]
}
```

```text
CDN / 对象存储
分卷下载
断点续传
SHA256 校验
磁盘空间预检查
Wi-Fi 下载提示
失败回主 App，不白屏
禁止下载 so/dex
```

## Unity 口径

```text
Unity LTS + URP
IL2CPP + ARM64
ASTC 纹理
Addressables
烘焙光照
不用 Lumen / Nanite
低端机降级
```

## v39 版本

在原有 v39.0 基础上增加：

| 版本 | 内容 | 验收 |
|---|---|---|
| v39.0.8.0 | 游乐园入口占位 / 未安装状态 | 不下载也能看到入口 |
| v39.0.9.0 | U3D 资源管理页 / manifest / 下载器 | 可下载并校验 |
| v39.0.10.0 | 资源完成后“信息”tab 替换为游乐园 | 状态持久化、可恢复 |

后续场景/角色/物件仍按 v39.1–v39.8 推进。

## 边界

```text
不把 Unity/UE5 塞进聊天主页面
不下载未签名 AssetBundle
游乐园下载失败不影响聊天
不做 UE5 手机端嵌入
```
