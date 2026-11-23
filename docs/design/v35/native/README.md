# 原生客户端设计稿

深度优化客户端：

```text
Qt 桌面
HyperOS 手机
HyperOS 平板
HarmonyOS 2 手机
```

## 目录

```text
docs/design/v35/native/
├─ tokens.md
├─ qt/
├─ hyperos/
├─ hyperos-tablet/
└─ harmonyos2/
```

旧 `qt/`、`android/`、`emui/` 只作历史参考，不再作为新设计基线。

## 每个客户端必须先出

```text
原生 tokens / 组件
登录 / 首次配置
主界面 + 聊天
业务页面
权限 / 通知 / 后台
深色 / 大字体 / 无障碍
空态 / 动效
```

## 差异

| 端 | 设计基准 |
|---|---|
| Qt | 原生窗口 / 托盘 / 小窗 / 键鼠；Windows + Linux（X11/Wayland） |
| HyperOS 手机 | HyperOS 视觉；系统通知、自启动/省电入口、小组件 |
| HyperOS 平板 | 双栏 / 分屏 / 平行窗口 / 手写笔 |
| HarmonyOS 2 | 鸿蒙 2 FA/Java/JS 风格；服务卡片、通知、后台 |

## 冻结规则

```text
设计稿冻结后再写原生实现
缺页面先补设计，不靠代码想象
不在实现阶段临时重画
```

## 版本门槛

```text
v35.11.0.0 Qt 设计稿 + 架构
v35.11.4.0 Linux 桌面适配
v35.13.0.0 HyperOS 设计稿 + 架构
v35.14.0.0 HyperOS 平板设计稿 + 设备 profile
v35.15.0.0 HarmonyOS 2 设计稿 + 架构
```
