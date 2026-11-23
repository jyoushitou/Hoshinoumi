# v35.23 游乐园 U3D 模块

## 定位

主 App 保持聊天/记忆/关系；游乐园是独立的 Unity 3D 模块。

```text
刚开始：只有入口和下载引导
资源未下载：入口显示“未安装”，不启动 Unity
资源下载完成：入口可用
下载完成后：底部“信息”替换为“游乐园”
```

## 关键限制

Unity 的 Android 运行时（so + player）不能像图片一样在安装后动态补进 APK。

```text
方案 A：Unity runtime 打进主 APK，只下载场景/角色/家具资源
方案 B：游乐园做成独立 APK，主 App 深链拉起
方案 C：Google Play Dynamic Feature（GitHub 直发不适用）
```

本计划默认 **方案 A**：

```text
主 APK 会增加 Unity runtime（约 20–50MB）
场景资源按需下载（几百 MB 起）
```

如果必须保持主 APK 3MB，只能走方案 B。

## 状态机

```text
not_installed   只有入口，未下载资源
downloading     下载中，可暂停/继续
ready           资源校验通过，可以进入
updating        资源更新中
broken          校验失败，可重下
```

## 入口

```text
信息页/设置页先放“游乐园”入口
未安装：点击 → 资源下载页
已安装：点击 → Unity Activity
```

下载完成后导航替换：

```text
底部 tab：信息 → 游乐园
信息页仍可从设置进入
卸载资源后恢复“信息”
```

## 资源分发

```text
GET /api/park/manifest
{
  version, min_app_version,
  total_bytes,
  files: [{path, url, sha256, bytes}]
}
```

```text
CDN/对象存储
分卷下载
断点续传
SHA256 校验
Wi-Fi 下载提示
磁盘空间预检查
失败回退主 App，不白屏
禁止下载可执行 so/dex
```

## Unity 技术口径

```text
Unity LTS + URP
IL2CPP + ARM64
ASTC 纹理
Addressables / AssetBundle
烘焙光照，不用 Lumen/Nanite
低端机降级画质
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.23.0.0 | 引擎选型 ADR / 设备门槛 / 资源规范 | 方案定稿 |
| v35.23.0.1 | 游乐园入口占位 / 未安装状态 | 不下载也能看到入口 |
| v35.23.0.2 | 设置 → 游乐园资源管理页 | 可查看大小/状态 |
| v35.23.0.3 | manifest API / CDN / SHA256 / 版本 | 清单可校验 |
| v35.23.0.4 | 下载器 / 断点续传 / 磁盘检查 / 失败回退 | 下载可恢复 |
| v35.23.0.5 | Unity Activity / token 深链 / 返回主 App | 能进能退 |
| v35.23.0.6 | 信息 tab 动态替换为游乐园 | 状态持久化 |
| v35.23.0.7 | 基础场景 / 加载 / 生命周期 | 场景可进 |
| v35.23.0.8 | 资源更新 / 回滚 / 清理 | 不残留旧版本 |
| v35.23.0.9 | 低端机降级 / 性能 / 真机验收 | Honor 10 有明确降级 |

## 边界

```text
不把 Unity/UE5 塞进聊天主页面
不下载未签名的 AssetBundle
不因为游乐园下载失败影响聊天
不做 UE5 手机端嵌入
```
