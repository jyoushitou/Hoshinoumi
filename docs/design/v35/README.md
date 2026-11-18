# v35 多端页面设计稿

> 当前代码版本：v35.2.1.0  
> 设计稿版本：v35 多端，2026-11-18  
> 所有端独立设计，后续按“一端一端”实现。

## 设计稿

| 端 | 文件 | 设计方向 |
|---|---|---|
| Web | `screens/web-chat.png` | 三栏桌面：会话 / 聊天 / 关系与状态 |
| Web | `screens/web-command.png` | 命令中心：钩子 / 状态日志 / API 余额 |
| Web | `screens/web-savings.png` | 总余额置顶 / 分账户 / 目标 / 对账 |
| Web | `screens/web-info.png` | 信息卡片 + 子页入口 + 设置入口 |
| Web | `screens/web-plugins.png` | 插件安装 / 审批 / 权限 / 错误 |
| Web | `screens/web-persona.png` | 人设卡 / 预览 / 设置 / 后端地址 |
| Qt 桌面 | `screens/qt-desktop.png` | 原生窗口 + 托盘 + 悬浮小窗 + 桌宠 |
| Android | `screens/android-chat.png` | Material 深色，底部六导航 |
| Android | `screens/android-savings.png` | 手机存钱页：总余额 / 账户 / 目标 |
| Android | `screens/android-settings.png` | 后端 / 导航 / 显示 / 数据 |
| EMUI | `screens/emui-chat.png` | 独立浅色卡片设计，情景卡 + 服务入口 |
| EMUI | `screens/emui-settings.png` | 6GB 性能档 / 通知 / 后台 |
| EMUI | `screens/emui-privacy.png` | 数据边界 / 后端 / 页面 / 运维 |

## 独立性

```text
Web       三栏桌面，信息密度最高
Qt        原生窗口 + 桌宠/小窗，不做 Vue 套壳
Android   Material 深色，底部六导航
EMUI      浅色卡片，情景卡 + 服务按钮，不用底部六导航
Vue 套壳  复用 Web 页面，不单独设计
CLI       无 GUI，不出一套图
```

## 改图方式

源文件是 HTML + `common.css`，PNG 只是渲染结果：

```text
docs/design/v35/*.html
docs/design/v35/common.css
docs/design/v35/screens/*.png
```

改完后重新渲染：

```powershell
powershell -ExecutionPolicy Bypass -File docs/design/v35/render.ps1
```

也可以直接改 `screens/*.png`；后续实现以你改后的图为准。

## 下一步

你确认或修改某一端后，我只做那一端；一次实现对应一个次次版本、一个提交。
