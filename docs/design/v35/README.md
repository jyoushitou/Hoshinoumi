# v35 多端页面设计稿

> 当前代码版本：v35.4.15  
> 设计稿版本：v35 多端，2026-11-19  
> 每个终端一个文件夹；相同页面在不同端使用相同文件名。

## 目录

```text
docs/design/v35/
├─ common.css
├─ render.ps1
├─ mobile/
│  └─ hoshinoumi-mobile-v35.7.html / .png  v35.7 手机 Vue 设计稿（六屏）
│      hoshinoumi-mobile-v35.7-demo.html   可交互演示
├─ web/
│  ├─ hoshinoumi-web-v35.5.html / .png    v35.5 聊天室演示
│  ├─ DEVELOPMENT.md                     v35.5 开发拆分
│  ├─ chat.png / chat.html                旧版页面留档
│  ├─ command.png / command.html
│  ├─ savings.png / savings.html
│  ├─ info.png / info.html
│  ├─ plugins.png / plugins.html
│  └─ persona.png / persona.html
├─ qt/
│  └─ chat.png / chat.html
├─ android/
│  ├─ chat.png / chat.html
│  ├─ savings.png / savings.html
│  └─ settings.png / settings.html
├─ emui/
│  ├─ chat.png / chat.html
│  ├─ settings.png / settings.html
│  └─ privacy.png / privacy.html
└─ dsh/
   ├─ chat.png / chat.html            工作区 > nao
   ├─ plugin.png / plugin.html        自动化任务 > 命令
   ├─ scheduled.png / scheduled.html  自动化任务 > 定时任务
   ├─ logs.png / logs.html            自动化任务 > 运行日志
   ├─ setup.png                       首次打开：配置后端地址
   ├─ demo.html / demo.png            可交互动画演示
   └─ demo-overview.png               全部功能总览演示预览
```

## 原生客户端设计

深度优化客户端（Qt / Android 原生 / HyperOS / 平板 / EMUI）使用单独设计稿，不复用 Web/Vue 设计：

- [native/README.md](native/README.md)

旧 `qt/`、`android/`、`emui/` 目录只作旧版参考。

## Mobile v35.7 演示（已定稿）

```text
docs/design/v35/mobile/
```

- 六屏：登录 / 会话 / 聊天 / 记忆 / 关系 / 设置
- 390 × 844 基准，安全区、底部导航、输入法避让
- 页面映射见 `mobile/README.md`

## Web v35.5 演示

```text
web/hoshinoumi-web-v35.5.html
```

- 四栏：导航 / 会话 / 聊天 / 上下文
- 使用 Hoshinoumi 彩色 Logo
- 数据全部标注 MOCK
- 窄屏会隐藏上下文和会话栏
- 开发拆分见 `web/DEVELOPMENT.md`

## 同名规则

```text
同一页面在不同端，文件名相同：
  chat
  savings
  settings
  info
  plugins
  persona
平台由文件夹区分，不再写 web-chat / android-chat。
```

## 设计差异

```text
web       三栏桌面，信息密度最高
qt        原生窗口 + 桌宠/小窗，不做 Vue 套壳
android   Material 深色，底部六导航
emui      浅色卡片，情景卡 + 服务按钮，不用底部六导航
dsh       浅色桌面页；聊天在工作区 nao；命令页保留侧栏，无四 tab，全量 51 命令
```

## DSH 首次配置

```text
打开插件 → 检查 localStorage 后端地址
没有 → 弹出“连接 Hoshinoumi”对话框
有   → 直接进入

对话框：后端地址 / token / 测试连接 / 保存并连接 / 稍后配置
右上角 ⚙ 可重新打开
```

## DSH 聊天后端

```text
DSH 只负责界面和模型显示名“nao”
聊天请求 → POST /api/chat → Hoshinoumi get_character_reply()
和 QQ 共用记忆；不调用 DSH 模型
```

## DSH 全部功能

```text
工作区
├─ nao              聊天 / 历史
└─ nao 功能          全部功能总览

总览包含：聊天 / 记忆 / 存钱 / 信息 / 人设 / 设置 / 插件 / 命令 / 定时任务 / 运行日志
```

## DSH 可交互演示

```text
dsh/demo.html   自动加载历史 + 消息动画 + 命令页全量 51 命令
```

直接浏览器打开即可，不需要服务端。

## DSH 信息架构

```text
工作区
└─ nao                 → dsh/chat.png

自动化任务
├─ 命令                 → dsh/plugin.png
│  全量 51 个命令 + 选中命令详情/执行
├─ 定时任务             → dsh/scheduled.png
└─ 运行日志             → dsh/logs.png
```

## 改图方式

源文件是 HTML + `common.css`，PNG 只是渲染结果。

```powershell
powershell -ExecutionPolicy Bypass -File docs/design/v35/render.ps1
```

也可以直接改对应终端文件夹里的 PNG；后续实现以你改后的图为准。

## 下一步

你确认或修改某一端后，我只做那一端；一次实现对应一个次次版本、一个提交。
