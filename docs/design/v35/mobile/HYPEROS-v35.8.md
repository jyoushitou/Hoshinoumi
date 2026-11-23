# HyperOS 深度适配与权限子页（v35.8.5）

定位：不改变 Capacitor/Vue 主体，只补 HyperOS 上最容易出问题的系统能力和权限状态。

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

HyperOS 后台
  自启动
  电池优化
  后台弹窗 / 悬浮窗

系统信息
  WebView 版本
  HyperOS / Android 版本
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
HyperOS 自启动 intent，失败回退应用详情页
```

## 设计

- [手机权限子页](hoshinoumi-mobile-v35.7-demo.html?screen=permissions)
- [HyperOS 说明](HYPEROS-v35.8.md)

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.5.0 | 权限与后台子页 / 真实状态读取 / 请求权限 | 开关与系统状态一致 |
| v35.8.5.1 | HyperOS 自启动 / 电池 / 悬浮窗跳转 | 跳转失败有回退 |
| v35.8.5.2 | 澎湃桌面小组件（可选） | 小组件数据来自后端 |

## 深度适配

```text
Android 15 edge-to-edge
输入法/键盘避让
HyperOS 自启动与省电策略
通知渠道与权限
WebView 版本
深色模式 / 大字体
后台恢复
小组件 / deep link（可选）
```

HyperOS 本质是 Android，不建立第二套页面或第二套业务 API。
