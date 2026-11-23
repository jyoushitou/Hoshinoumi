# Android 权限与后台子页（v35.8.1.5）

定位：先做 Android 权限与后台子页；HyperOS 深度优化等 Android 稳定后再单独排期。

## 权限子页

入口：

```text
设置 → 权限与后台
```

分组：

```text
应用权限
  通知
  相机
  麦克风
  照片与文件

后台限制
  自启动
  电池优化
  后台弹窗 / 悬浮窗

系统信息
  WebView 版本
  Android 版本
```

状态：

```text
granted       已允许
denied        已拒绝
prompt        未询问
manual        只能去系统设置
unavailable   当前系统不支持
```

规则：

```text
通知/相机/麦克风/照片：读取真实权限，点击 request() 或跳系统设置
自启动/电池优化/悬浮窗：不能由 App 直接开关，只显示“去设置”
不允许伪造“已开启”
用户从系统设置返回后重新读取状态
```

## 原生能力

```text
checkSelfPermission
requestPermissions
Settings.ACTION_APPLICATION_DETAILS_SETTINGS
Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS
Settings.ACTION_MANAGE_OVERLAY_PERMISSION
厂商自启动 intent 放到后续 HyperOS 适配，失败回退应用详情页
```

## 设计

- [手机权限子页](hoshinoumi-mobile-v35.7-demo.html?screen=permissions)
- [权限与后台设计](hoshinoumi-mobile-v35.7-demo.html?screen=permissions)

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.1.5 | 权限与后台子页 / 真实状态读取 / 请求权限 | 开关与系统状态一致 |

## 后续（不排期）

```text
HyperOS 自启动 / 电池 / 悬浮窗跳转
澎湃桌面小组件
HyperOS 深色模式 / 大字体 / 后台策略
```

Android 先通过；HyperOS 深度优化等真机阶段再做，不建立第二套页面或 API。
