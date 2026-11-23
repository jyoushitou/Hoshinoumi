# 原生客户端设计稿

结论：深度优化客户端的界面必须单独设计，不能拿 Vue/Web 设计稿直接套。

```text
Web / Vue 设计稿  ≠  Qt / Android / HyperOS / EMUI 原生设计稿
```

## 目录计划

```text
docs/design/v35/native/
├─ tokens.md              原生颜色/字号/间距/动效统一口径
├─ qt/                    Qt 6 桌面
├─ android/               Android 原生
├─ hyperos/               HyperOS 4 手机
├─ hyperos-tablet/        HyperOS 3 平板
└─ emui/                  EMUI
```

旧 `docs/design/v35/qt|android|emui` 只作为旧版参考，不作为原生重写基线。

## 每个客户端必须先出

```text
1. 设计 tokens / 组件
2. 登录 / 首次配置
3. 主界面 + 聊天
4. 业务页面（记忆/关系/存钱/周计划/信息/人设/命令/定时/日志/设置）
5. 深色 / 大字体 / 无障碍
6. 系统能力页（权限 / 通知 / 后台）
7. 交互动效和空态
```

## 设计差异

| 端 | 设计基准 |
|---|---|
| Qt 桌面 | 原生窗口 / 托盘 / 小窗 / 键鼠 |
| Android | Material 3，系统权限与通知 |
| HyperOS 手机 | HyperOS 视觉、系统通知/小组件、自启动页 |
| HyperOS 平板 | 双栏、横屏/分屏、手写笔/键鼠 |
| EMUI | 情景卡片、服务按钮，不套底部六导航 |

## 冻结规则

```text
设计稿冻结后，原生实现按稿开发
实现阶段不重新“边写边设计”
缺页面先补设计稿，不靠代码想象
```

## 与实现版本的关系

```text
v35.11.0.0  Qt 原生设计 + 工程架构
v35.12.0.0  Android 原生设计 + 工程架构
v35.13.0.0  HyperOS 手机原生设计 + 架构
v35.14.0.0  HyperOS 平板设计 + 设备 profile
v35.15.0.0  EMUI 原生设计 + 工程架构
```
